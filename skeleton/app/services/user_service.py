"""사용자/인증 서비스 (ARCHITECTURE.md §8) — 비즈니스 로직.

라우터는 얇게 두고, 사용자 조회·인증·시드는 여기서 처리한다.
"""
import ipaddress
import logging
import math
from datetime import timedelta

from sqlalchemy import and_, case, delete, func, or_, select, update
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
from app.models.auth_session import LOGIN_THROTTLE_KEY_LENGTH, LoginThrottle
from app.models.user import User, UserRole
from app.services.exceptions import ServiceError

logger = logging.getLogger(__name__)
# 보안 이벤트(로그인 성공/실패/잠금)는 일반 로그와 분리 수집할 수 있도록 전용 로거를 쓴다.
audit = logging.getLogger("app.audit")

# 로그인 실패 메시지는 원인(자격증명 불일치/비활성 계정)과 무관하게 동일하게 유지한다
# — 응답으로 계정 존재·상태가 구분되지 않도록. 원인 구분은 서버 로그에만 남긴다.
INVALID_CREDENTIALS_MESSAGE = "아이디 또는 비밀번호가 올바르지 않습니다."

# 잠금(429) 메시지도 계정 존재를 드러내지 않는 일반 문구다 — 미존재 계정도 스로틀 칸을 만들어
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


# ---------------------------------------------------------------------------
# 로그인 시도 제한 (login_throttles)
#
# 잠금 단위는 (username, 접속 IP) 칸이다 — 계정 단위로만 잠그면 누구나 아무 IP 에서 실패 5회를 보내
# 관리자를 계속 잠글 수 있다(서비스 거부). 대신 IP 를 바꿔 가며 대입하는 분산 공격을 막으려고 username
# 전체 합산 칸(client_ip="*")에 상한(LOGIN_MAX_FAILURES × GLOBAL_FAILURE_MULTIPLIER)을 둔다.
# 두 칸 모두 LOGIN_LOCKOUT_MINUTES 동안 잠그고, 잠금 없이 같은 시간이 지나면 횟수를 처음부터 센다.
#
# 시도는 bcrypt 검증 **전에** 칸을 원자적으로 예약(카운트 +1)하고, 성공하면 되돌린다. 확인(잠금 여부)과
# 기록(실패 +1)을 따로 하면 그 사이에 병렬 요청이 모두 확인을 통과해 상한보다 많이 검증된다(TOCTOU).
# 예약은 "잠기지 않은 칸만 +1" 하는 UPDATE 한 문장이라 PostgreSQL 에서도 동시 요청이 차례로 반영된다
# (READ COMMITTED 의 UPDATE 는 경쟁 행의 새 버전으로 WHERE 를 다시 평가한다).
# ---------------------------------------------------------------------------

# username 전체 합산 칸의 client_ip 값. IP 정규화 결과는 이 값이 될 수 없다(client_ip_key).
GLOBAL_THROTTLE_KEY = "*"
# 웹 계층이 접속 IP 를 넘기지 못했거나(None) 해석할 수 없는 값일 때 쓰는 고정 칸.
# 이 칸을 쓰는 요청끼리는 잠금을 공유한다(예전 계정 단위 잠금과 같은 동작).
UNKNOWN_CLIENT_IP_KEY = "unknown"
# 전체 합산 칸 상한 = LOGIN_MAX_FAILURES × 이 배수. 설정 키를 늘리지 않으려고 고정 배수로 둔다.
# 기본값(5회)이면 잠금 시간마다 IP 10개 이상에서 실패를 50회 모아야 계정 전체가 잠긴다.
GLOBAL_FAILURE_MULTIPLIER = 10
# IPv6 는 /64 네트워크 단위로 센다 — 한 회선이 보통 /64 를 통째로 받아 주소를 얼마든지 바꿀 수 있다.
IPV6_THROTTLE_PREFIX = 64
# 오래된 실패 기록 정리 기준(cleanup-auth) — 관리자 화면의 "최근 실패" 범위와 같다.
LOGIN_THROTTLE_RETENTION = timedelta(hours=24)


def client_ip_key(client_ip: str | None) -> str:
    """접속 IP 를 스로틀 칸 키로 정규화한다 — IPv4 는 그대로, IPv6 는 /64 네트워크, 그 밖은 UNKNOWN_CLIENT_IP_KEY.

    IPv4 매핑 IPv6(::ffff:a.b.c.d)는 IPv4 로 본다. 결과는 항상 ipaddress 가 만든 표기라 "*" 나 제어 문자가 될 수 없다.
    """
    if not client_ip or len(client_ip) > LOGIN_THROTTLE_KEY_LENGTH:
        return UNKNOWN_CLIENT_IP_KEY
    try:
        addr = ipaddress.ip_address(client_ip.strip())
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped is not None:
                return str(addr.ipv4_mapped)
            return str(ipaddress.IPv6Network((addr.packed, IPV6_THROTTLE_PREFIX), strict=False))
    except ValueError:
        return UNKNOWN_CLIENT_IP_KEY
    return str(addr)


def _throttle_limits() -> tuple[int, int, timedelta]:
    """(IP 칸 상한, 전체 합산 칸 상한, 잠금·집계 시간)."""
    settings = get_settings()
    return (
        settings.login_max_failures,
        settings.login_max_failures * GLOBAL_FAILURE_MULTIPLIER,
        timedelta(minutes=settings.login_lockout_minutes),
    )


def _throttle_key(username: str, key: str):
    return and_(LoginThrottle.username == username, LoginThrottle.client_ip == key)


def _scope(key: str) -> str:
    return "account" if key == GLOBAL_THROTTLE_KEY else "ip"


def _insert_throttle_if_missing(db: Session, username: str, key: str) -> None:
    """칸이 없으면 만든다. 동시 요청이 먼저 만들었으면 아무것도 하지 않는다(ON CONFLICT DO NOTHING)."""
    dialect = db.get_bind().dialect.name
    insert_fn = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}.get(dialect)
    values = {"username": username, "client_ip": key, "failed_count": 0, "last_failed_at": now()}
    if insert_fn is not None:
        db.execute(
            insert_fn(LoginThrottle)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[LoginThrottle.username, LoginThrottle.client_ip])
        )
        return
    # 그 밖의 DB(지원 대상 아님) — 사전 조회 후 INSERT, 경쟁은 IntegrityError 로 흡수한다.
    if db.execute(select(LoginThrottle.id).where(_throttle_key(username, key))).first() is None:
        try:
            with db.begin_nested():
                db.add(LoginThrottle(**values))
        except IntegrityError:
            pass


def _reserve_attempt(db: Session, username: str, key: str, limit: int, window: timedelta) -> int | None:
    """잠기지 않은 칸의 카운트를 원자적으로 1 올리고 새 카운트를 돌려준다. 잠겨 있으면 None.

    새 카운트가 limit 에 닿으면 그 자리에서 잠금을 건다 — 이 시도는 검증을 받지만 다음 시도부터 429 다.
    잠금이 풀렸거나 마지막 실패 뒤 window 가 지났으면 처음부터 센다(풀리자마자 1회로 재잠금되지 않게).
    SET 의 모든 식은 갱신 전 값으로 계산된다.
    """
    ts = now()
    unlocked = or_(LoginThrottle.locked_until.is_(None), LoginThrottle.locked_until <= ts)
    restart = or_(
        LoginThrottle.locked_until.is_not(None),  # unlocked 조건 아래에서는 "잠금이 이미 풀림"을 뜻한다
        LoginThrottle.last_failed_at <= ts - window,
    )
    new_count = case((restart, 1), else_=LoginThrottle.failed_count + 1)
    row = db.execute(
        update(LoginThrottle)
        .where(_throttle_key(username, key), unlocked)
        .values(
            failed_count=new_count,
            last_failed_at=ts,
            locked_until=case((new_count >= limit, ts + window), else_=None),
        )
        .returning(LoginThrottle.failed_count)
        .execution_options(synchronize_session=False)
    ).first()
    return None if row is None else int(row[0])


def _locked_error(db: Session, username: str, key: str) -> ServiceError:
    """ServiceError("too_many_attempts", retry_after=남은 초) — 라우터가 429 + Retry-After 로 변환한다.

    남은 시간은 올림한 정수 초(≥1)다 — 내림하면 클라이언트가 잠금 해제 직전에 재시도해 다시 429 를 받는다.
    미존재 계정도 같은 칸을 거치므로 Retry-After 유무·값으로도 계정 존재가 드러나지 않는다.
    """
    locked_until = db.scalar(select(LoginThrottle.locked_until).where(_throttle_key(username, key)))
    remaining = (locked_until - now()).total_seconds() if locked_until is not None else 0
    return ServiceError(
        "too_many_attempts",
        TOO_MANY_ATTEMPTS_MESSAGE,
        retry_after=max(1, math.ceil(remaining)),
    )


def _reserve_or_raise(db: Session, username: str, ip_key: str) -> bool:
    """IP 칸 → 전체 합산 칸 순서로 예약하고 커밋한다. 잠긴 칸이 있으면 too_many_attempts.

    IP 칸을 먼저 예약한다 — 잠긴 IP 의 시도가 전체 합산 칸을 계속 올려 계정 전체를 잠그지 못하게 한다.
    예약은 bcrypt 검증 전에 커밋한다(검증 동안 행 잠금을 쥐고 있지 않는다).
    돌려주는 값은 "이 시도가 전체 합산 칸의 잠금을 걸었는지"다(성공 시 되돌리기용).
    """
    ip_limit, global_limit, window = _throttle_limits()
    global_locked_by_me = False
    for key, limit in ((ip_key, ip_limit), (GLOBAL_THROTTLE_KEY, global_limit)):
        _insert_throttle_if_missing(db, username, key)
        count = _reserve_attempt(db, username, key, limit, window)
        if count is None:
            error = _locked_error(db, username, key)
            db.commit()
            audit.warning("로그인 거부(잠금 중): username=%r client_ip=%r scope=%s", username, ip_key, _scope(key))
            raise error
        if count == limit:
            audit.warning(
                "로그인 잠금 발동: username=%r client_ip=%r scope=%s failed_count=%s",
                username,
                ip_key,
                _scope(key),
                count,
            )
        if key == GLOBAL_THROTTLE_KEY:
            global_locked_by_me = count >= limit
    db.commit()
    return global_locked_by_me


def _release_on_success(db: Session, username: str, ip_key: str, *, global_locked_by_me: bool) -> None:
    """로그인 성공 — 이 IP 의 몫만 되돌린다. IP 칸은 지우고, 전체 합산 칸에서는 그 IP 칸의 횟수(이번 예약 포함)를 뺀다.

    다른 IP 의 실패까지 지우면 진행 중인 분산 대입의 횟수가 정상 로그인 한 번에 사라진다.
    이 시도의 예약이 합산 칸 잠금을 걸었다면 그 잠금도 푼다. 0 이 된 합산 칸은 지운다(정상 사용자 흔적을 남기지 않는다).
    """
    own = db.execute(
        delete(LoginThrottle)
        .where(_throttle_key(username, ip_key))
        .returning(LoginThrottle.failed_count)
        .execution_options(synchronize_session=False)
    ).first()
    own_count = max(1, int(own[0])) if own is not None else 1
    remaining = LoginThrottle.failed_count - own_count
    values: dict = {"failed_count": case((remaining > 0, remaining), else_=0)}
    if global_locked_by_me:
        values["locked_until"] = None
    db.execute(
        update(LoginThrottle)
        .where(_throttle_key(username, GLOBAL_THROTTLE_KEY))
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(LoginThrottle).where(
            _throttle_key(username, GLOBAL_THROTTLE_KEY),
            LoginThrottle.failed_count <= 0,
            LoginThrottle.locked_until.is_(None),
        )
    )
    db.commit()


def clear_login_throttles(db: Session, username: str, *, commit: bool = True) -> int:
    """username 의 모든 칸(IP 칸 + 전체 합산 칸)을 지우고 지운 행 수를 돌려준다(잠금 해제)."""
    result = db.execute(
        delete(LoginThrottle).where(LoginThrottle.username == username).execution_options(synchronize_session=False)
    )
    if commit:
        db.commit()
    return int(result.rowcount or 0)


def purge_stale_login_throttles(db: Session, *, dry_run: bool = False) -> int:
    """잠금 중이 아니고 마지막 실패가 오래된 칸을 지운다(운영 CLI cleanup-auth). dry_run 이면 세기만 한다.

    기준은 LOGIN_THROTTLE_RETENTION 과 잠금 시간 중 긴 쪽이다 — 그보다 오래된 칸은 다음 시도에서 어차피
    처음부터 세므로 지워도 동작이 바뀌지 않는다. 미존재 아이디로 시도해도 행이 생기므로 주기적으로 정리한다.
    """
    _, _, window = _throttle_limits()
    ts = now()
    stale = and_(
        or_(LoginThrottle.locked_until.is_(None), LoginThrottle.locked_until <= ts),
        LoginThrottle.last_failed_at < ts - max(LOGIN_THROTTLE_RETENTION, window),
    )
    if dry_run:
        return int(db.scalar(select(func.count()).select_from(LoginThrottle).where(stale)) or 0)
    result = db.execute(delete(LoginThrottle).where(stale).execution_options(synchronize_session=False))
    db.commit()
    return int(result.rowcount or 0)


def authenticate(db: Session, username: str, password: str, *, client_ip: str | None = None) -> User:
    """성공 시 User, 실패 시 ServiceError("invalid_credentials" | "too_many_attempts").

    실패 사유(자격증명 불일치/비활성 계정)는 응답 메시지로 구분하지 않고
    서버 로그로만 구분한다. 계정이 없어도 더미 해시로 항상 1회 검증해 응답 시간으로도
    존재 여부가 드러나지 않게 한다. 연속 실패는 (username, client_ip) 칸과 username 전체 합산 칸으로
    제한한다(위 「로그인 시도 제한」) — 잠긴 칸이 있으면 비밀번호 검증 전에 "too_many_attempts" 로 끝낸다(429).

    client_ip 는 웹 계층이 신뢰하는 프록시 설정을 반영해 얻은 접속 IP 다.
    None 이면 고정 칸(UNKNOWN_CLIENT_IP_KEY)을 쓴다.
    로그에는 사용자 입력을 %r 로 남긴다 — 개행·제어 문자가 이스케이프돼 로그 줄을 위조할 수 없다.
    """
    ip_key = client_ip_key(client_ip)
    global_locked_by_me = _reserve_or_raise(db, username, ip_key)
    user = get_by_username(db, username)
    hashed = user.hashed_password if user is not None else dummy_password_hash()
    password_ok = verify_password(password, hashed)
    if user is None or not password_ok:
        logger.info("로그인 실패(자격증명 불일치): username=%r client_ip=%r", username, ip_key)
        audit.info("로그인 실패: username=%r client_ip=%r", username, ip_key)
        raise ServiceError("invalid_credentials", INVALID_CREDENTIALS_MESSAGE)
    if not user.is_active:
        logger.info("로그인 실패(비활성 계정): username=%r client_ip=%r", username, ip_key)
        audit.info("로그인 실패: username=%r user_id=%s client_ip=%r", username, user.id, ip_key)
        raise ServiceError("invalid_credentials", INVALID_CREDENTIALS_MESSAGE)
    _release_on_success(db, username, ip_key, global_locked_by_me=global_locked_by_me)
    audit.info("로그인 성공: username=%r user_id=%s client_ip=%r", username, user.id, ip_key)
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
    잠금 상태(login_throttles 의 그 username 칸 전부)도 함께 지워 새 비밀번호로 바로 로그인할 수 있게 한다.
    """
    from app.services import session_service  # 순환 import 방지(session_service → user 모델)

    validate_new_password(password)
    user = get_by_username(db, username)
    if user is None:
        raise ServiceError("not_found", "사용자를 찾을 수 없습니다.")
    user.hashed_password = hash_password(password)
    session_service.revoke_all_for_user(db, user.id, commit=False)
    clear_login_throttles(db, username, commit=False)
    db.commit()
    db.refresh(user)
    audit.info("비밀번호 재설정(CLI) — 세션 전체 폐기: username=%r user_id=%s", username, user.id)
    return user
