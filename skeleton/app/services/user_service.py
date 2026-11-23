"""사용자/인증 서비스 (ARCHITECTURE.md §8) — 비즈니스 로직.

라우터는 얇게 두고, 사용자 조회·인증·시드는 여기서 처리한다.
"""
import logging
import math
from datetime import timedelta

from sqlalchemy import and_, case, select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    dummy_password_hash,
    hash_password,
    now,
    validate_new_password,
    verify_password,
)
from app.models.auth_session import LoginThrottle
from app.models.user import User, UserRole
from app.services.exceptions import ServiceError

logger = logging.getLogger(__name__)
# 보안 이벤트(로그인 성공/실패/잠금)는 일반 로그와 분리 수집할 수 있도록 전용 로거를 쓴다.
audit = logging.getLogger("app.audit")

# 로그인 실패 메시지는 원인(자격증명 불일치/비활성 계정)과 무관하게 동일하게 유지한다
# — 응답으로 계정 존재·상태가 구분되지 않도록. 원인 구분은 서버 로그에만 남긴다.
INVALID_CREDENTIALS_MESSAGE = "아이디 또는 비밀번호가 올바르지 않습니다."

# 잠금(429) 메시지도 계정 존재를 드러내지 않는 일반 문구다 — 미존재 계정도 스로틀 행을 만들어
# 같은 조건에서 같은 429 를 받으므로, 잠금 응답 유무로도 존재 여부가 구분되지 않는다.
TOO_MANY_ATTEMPTS_MESSAGE = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요."

# 미존재 계정에서도 bcrypt 검증을 1회 수행해 응답 시간을 맞춘다(security.dummy_password_hash).
# 실패 메시지를 통일해도 bcrypt 를 건너뛰면 타이밍(실측 186 ms vs 0.28 ms)으로 계정 존재
# 여부가 그대로 드러난다. 더미 해시는 실제 해시와 같은 비용(BCRYPT_ROUNDS)으로 만든다(테스트로 고정).

# 기본 관리자 (처음 실행 시 자동 생성). 시드 여부·초기 비밀번호는 설정(SEED_DEFAULT_ADMIN,
# DEFAULT_ADMIN_PASSWORD)으로 제어하며, 운영에서는 즉시 비밀번호를 변경해야 한다.
DEFAULT_ADMIN_USERNAME = "admin"


def get_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.USER,
) -> User:
    validate_new_password(password)
    if get_by_username(db, username) is not None:
        raise ServiceError("user_exists", "이미 존재하는 사용자입니다.")
    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        # 사전 조회(check)와 INSERT 사이의 동시 요청 레이스 — unique 제약 위반을
        # unhandled 500 대신 기존 도메인 에러로 변환한다.
        db.rollback()
        raise ServiceError("user_exists", "이미 존재하는 사용자입니다.") from e
    db.refresh(user)
    return user


def _get_throttle(db: Session, username: str) -> LoginThrottle | None:
    return db.execute(
        select(LoginThrottle).where(LoginThrottle.username == username)
    ).scalar_one_or_none()


def _check_not_locked(db: Session, username: str) -> None:
    """잠금 중이면 ServiceError("too_many_attempts", retry_after=남은 초) — 라우터가 429 + Retry-After 로 변환한다.

    남은 시간은 올림한 정수 초(≥1)다 — 내림하면 클라이언트가 잠금 해제 직전에 재시도해 다시 429 를 받는다.
    미존재 계정도 같은 스로틀 행을 거치므로 Retry-After 유무·값으로도 계정 존재가 드러나지 않는다.
    """
    throttle = _get_throttle(db, username)
    if throttle is None or throttle.locked_until is None:
        return
    remaining = (throttle.locked_until - now()).total_seconds()
    if remaining > 0:
        audit.warning("로그인 거부(잠금 중): username=%s", username)
        raise ServiceError(
            "too_many_attempts",
            TOO_MANY_ATTEMPTS_MESSAGE,
            retry_after=max(1, math.ceil(remaining)),
        )


def _insert_throttle_if_missing(db: Session, username: str) -> None:
    """스로틀 행이 없으면 만든다. 동시 요청이 먼저 만들었으면 아무것도 하지 않는다(ON CONFLICT DO NOTHING)."""
    dialect = db.get_bind().dialect.name
    insert_fn = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}.get(dialect)
    values = {"username": username, "failed_count": 0, "last_failed_at": now()}
    if insert_fn is not None:
        db.execute(
            insert_fn(LoginThrottle).values(**values).on_conflict_do_nothing(
                index_elements=[LoginThrottle.username]
            )
        )
        return
    # 그 밖의 DB(지원 대상 아님) — 사전 조회 후 INSERT, 경쟁은 IntegrityError 로 흡수한다.
    if _get_throttle(db, username) is None:
        try:
            db.add(LoginThrottle(**values))
            db.flush()
        except IntegrityError:
            db.rollback()


def _record_login_failure(db: Session, username: str) -> None:
    """실패 카운트를 원자적으로 올리고 임계치(LOGIN_MAX_FAILURES) 이상이면 잠금을 건다.

    읽고-고치고-쓰기(+= 1)는 동시 요청에서 증가분이 사라져(lost update) 병렬 대입 공격에 제한이
    느슨해진다. 그래서 증가·잠금 해제 판정·잠금 설정을 모두 SQL 식 하나로 처리한다.
    미존재 계정도 행을 만들어 같은 조건에서 같은 429 를 받게 한다 — 잠금 응답 유무로
    계정 존재가 드러나지 않게 하는 장치다(모델 주석 참고). 잠금이 이미 풀린 뒤의 실패는
    카운트를 처음부터 다시 센다(풀리자마자 1회 실패로 재잠금되면 사실상 영구 잠금이다).
    """
    settings = get_settings()
    ts = now()
    _insert_throttle_if_missing(db, username)
    lock_expired = and_(LoginThrottle.locked_until.is_not(None), LoginThrottle.locked_until <= ts)
    new_count = case((lock_expired, 1), else_=LoginThrottle.failed_count + 1)
    still_locked = and_(LoginThrottle.locked_until.is_not(None), LoginThrottle.locked_until > ts)
    db.execute(
        update(LoginThrottle)
        .where(LoginThrottle.username == username)
        .values(
            failed_count=new_count,
            last_failed_at=ts,
            # SET 의 모든 식은 갱신 전 값으로 계산된다 — 잠금 중이면 유지, 아니면 새 카운트로 판정한다.
            locked_until=case(
                (still_locked, LoginThrottle.locked_until),
                (
                    new_count >= settings.login_max_failures,
                    ts + timedelta(minutes=settings.login_lockout_minutes),
                ),
                else_=None,
            ),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    throttle = _get_throttle(db, username)
    if throttle is not None:
        db.refresh(throttle)
        if throttle.locked_until is not None and throttle.failed_count == settings.login_max_failures:
            audit.warning(
                "로그인 잠금 발동: username=%s failed_count=%s locked_until=%s",
                username,
                throttle.failed_count,
                throttle.locked_until,
            )


def _reset_login_failures(db: Session, username: str) -> None:
    """로그인 성공 시 스로틀 초기화 — 행을 지워 정상 사용자 흔적을 남기지 않는다."""
    throttle = _get_throttle(db, username)
    if throttle is None:
        return
    db.delete(throttle)
    db.commit()


def authenticate(db: Session, username: str, password: str) -> User:
    """성공 시 User, 실패 시 ServiceError("invalid_credentials" | "too_many_attempts").

    실패 사유(자격증명 불일치/비활성 계정)는 응답 메시지로 구분하지 않고
    서버 로그로만 구분한다. 계정이 없어도 더미 해시로 항상 1회 검증해 응답 시간으로도
    존재 여부가 드러나지 않게 한다. 계정별 연속 실패는 DB 스로틀(login_throttles)로
    제한한다 — 잠금 중이면 비밀번호 검증 전에 "too_many_attempts" 로 끝낸다(429).
    """
    _check_not_locked(db, username)
    user = get_by_username(db, username)
    hashed = user.hashed_password if user is not None else dummy_password_hash()
    password_ok = verify_password(password, hashed)
    if user is None or not password_ok:
        logger.info("로그인 실패(자격증명 불일치): username=%s", username)
        audit.info("로그인 실패: username=%s", username)
        _record_login_failure(db, username)
        raise ServiceError("invalid_credentials", INVALID_CREDENTIALS_MESSAGE)
    if not user.is_active:
        logger.info("로그인 실패(비활성 계정): username=%s", username)
        audit.info("로그인 실패: username=%s user_id=%s", username, user.id)
        _record_login_failure(db, username)
        raise ServiceError("invalid_credentials", INVALID_CREDENTIALS_MESSAGE)
    _reset_login_failures(db, username)
    audit.info("로그인 성공: username=%s user_id=%s", username, user.id)
    return user


def ensure_admin(db: Session, *, password: str) -> None:
    """관리자 계정이 하나도 없으면 기본 관리자(admin)를 생성한다 (idempotent)."""
    has_admin = db.execute(
        select(User.id).where(User.role == UserRole.ADMIN.value).limit(1)
    ).first()
    if has_admin is not None:
        return
    if get_by_username(db, DEFAULT_ADMIN_USERNAME) is not None:
        return
    create_user(
        db,
        username=DEFAULT_ADMIN_USERNAME,
        password=password,
        role=UserRole.ADMIN,
    )


def set_password(db: Session, *, username: str, password: str) -> User:
    """비밀번호를 바꾸고 그 사용자의 모든 세션을 폐기한다(운영 CLI 의 비밀번호 재설정).

    기존 세션을 남기면 비밀번호 변경의 목적(유출 자격증명 차단)이 달성되지 않는다.
    잠금 상태(login_throttles)도 함께 지워 새 비밀번호로 바로 로그인할 수 있게 한다.
    """
    from app.services import session_service  # 순환 import 방지(session_service → user 모델)

    validate_new_password(password)
    user = get_by_username(db, username)
    if user is None:
        raise ServiceError("not_found", "사용자를 찾을 수 없습니다.")
    user.hashed_password = hash_password(password)
    session_service.revoke_all_for_user(db, user.id, commit=False)
    throttle = _get_throttle(db, username)
    if throttle is not None:
        db.delete(throttle)
    db.commit()
    db.refresh(user)
    audit.info("비밀번호 재설정(CLI) — 세션 전체 폐기: username=%s user_id=%s", username, user.id)
    return user
