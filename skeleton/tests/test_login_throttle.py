"""로그인 시도 제한 서비스 테스트 — (username, IP) 칸·전체 합산 칸·예약 원자성 (ARCHITECTURE.md §9).

웹 프레임워크와 무관하게 서비스(user_service.authenticate)만 호출한다. 필요한 픽스처는
db_session·db_session_factory 뿐이다.
"""
import logging
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.core.security import now
from app.models.auth_session import LoginThrottle
from app.services import user_service
from app.services.exceptions import ServiceError
from app.services.user_service import GLOBAL_THROTTLE_KEY, UNKNOWN_CLIENT_IP_KEY, client_ip_key

PASSWORD = "pw123456"
WRONG = "wrong-password"
IP_A = "203.0.113.10"
IP_B = "198.51.100.20"


def _user(db_session, username: str = "alice"):
    return user_service.create_user(db_session, username=username, password=PASSWORD)


def _attempt(db, username: str, password: str, ip: str | None) -> str:
    """로그인 1회 — 결과 코드("ok" | "invalid_credentials" | "too_many_attempts")."""
    try:
        user_service.authenticate(db, username, password, client_ip=ip)
    except ServiceError as e:
        return e.code
    return "ok"


def _row(db_session, username: str, key: str) -> LoginThrottle | None:
    db_session.expire_all()
    return db_session.execute(
        select(LoginThrottle).where(LoginThrottle.username == username, LoginThrottle.client_ip == key)
    ).scalar_one_or_none()


def _limit() -> int:
    return get_settings().login_max_failures


# ---------------------------------------------------------------------------
# 접속 IP 정규화
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("203.0.113.10", "203.0.113.10"),
        (" 203.0.113.10 ", "203.0.113.10"),
        ("::ffff:203.0.113.10", "203.0.113.10"),  # IPv4 매핑 IPv6 는 IPv4 로 본다
        ("2001:db8:1:2:aaaa::1", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:ffff", "2001:db8:1:2::/64"),  # 같은 /64 는 같은 칸
        (None, UNKNOWN_CLIENT_IP_KEY),
        ("", UNKNOWN_CLIENT_IP_KEY),
        ("testclient", UNKNOWN_CLIENT_IP_KEY),
        ("*", UNKNOWN_CLIENT_IP_KEY),  # 전체 합산 칸 키로 둔갑할 수 없다
        ("1.2.3.4\nforged", UNKNOWN_CLIENT_IP_KEY),
        ("9" * 5000, UNKNOWN_CLIENT_IP_KEY),
    ],
)
def test_client_ip_key_normalizes(raw, expected):
    assert client_ip_key(raw) == expected


# ---------------------------------------------------------------------------
# IP 칸 · 전체 합산 칸
# ---------------------------------------------------------------------------


def test_lock_is_per_ip_so_other_ip_can_still_log_in(db_session):
    # 계정 단위 잠금이면 누구나 관리자를 잠글 수 있다 — 공격 IP 만 잠기고 정상 사용자 IP 는 로그인된다.
    _user(db_session)
    for _ in range(_limit()):
        assert _attempt(db_session, "alice", WRONG, IP_A) == "invalid_credentials"
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "too_many_attempts"
    assert _attempt(db_session, "alice", PASSWORD, IP_B) == "ok"
    # 다른 IP 의 성공은 공격 IP 칸을 풀지 않는다.
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "too_many_attempts"


def test_locked_ip_does_not_feed_global_counter(db_session):
    # 잠긴 IP 의 시도는 IP 칸에서 막힌다 — 전체 합산 칸을 계속 올려 계정 전체를 잠그지 못한다.
    for _ in range(_limit() * 3):
        _attempt(db_session, "alice", WRONG, IP_A)
    assert _row(db_session, "alice", GLOBAL_THROTTLE_KEY).failed_count == _limit()
    assert _row(db_session, "alice", GLOBAL_THROTTLE_KEY).locked_until is None


def test_global_cap_locks_account_across_ips(db_session):
    _user(db_session)
    global_limit = _limit() * user_service.GLOBAL_FAILURE_MULTIPLIER
    for i in range(user_service.GLOBAL_FAILURE_MULTIPLIER):
        for _ in range(_limit()):
            assert _attempt(db_session, "alice", WRONG, f"192.0.2.{i + 1}") == "invalid_credentials"
    row = _row(db_session, "alice", GLOBAL_THROTTLE_KEY)
    assert row.failed_count == global_limit
    assert row.locked_until is not None
    # 처음 보는 IP 도, 올바른 비밀번호도 잠금 동안은 429 다(분산 대입의 상한).
    with pytest.raises(ServiceError) as exc_info:
        user_service.authenticate(db_session, "alice", PASSWORD, client_ip=IP_B)
    assert exc_info.value.code == "too_many_attempts"
    assert 1 <= exc_info.value.retry_after <= get_settings().login_lockout_minutes * 60


def test_none_client_ip_uses_fixed_bucket(db_session):
    _user(db_session)
    for _ in range(_limit()):
        _attempt(db_session, "alice", WRONG, None)
    assert _row(db_session, "alice", UNKNOWN_CLIENT_IP_KEY).locked_until is not None
    assert _attempt(db_session, "alice", PASSWORD, None) == "too_many_attempts"
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "ok"


def test_unknown_username_follows_same_rules(db_session):
    # 미존재 계정도 같은 칸·같은 잠금 — 429 유무로 존재 여부가 드러나지 않는다.
    for _ in range(_limit()):
        assert _attempt(db_session, "ghost", WRONG, IP_A) == "invalid_credentials"
    assert _attempt(db_session, "ghost", WRONG, IP_A) == "too_many_attempts"


def test_failures_restart_after_window_without_lock(db_session):
    _user(db_session)
    for _ in range(_limit() - 1):
        _attempt(db_session, "alice", WRONG, IP_A)
    row = _row(db_session, "alice", IP_A)
    row.last_failed_at = now() - timedelta(minutes=get_settings().login_lockout_minutes, seconds=1)
    db_session.commit()
    assert _attempt(db_session, "alice", WRONG, IP_A) == "invalid_credentials"
    assert _row(db_session, "alice", IP_A).failed_count == 1


def test_expired_lock_restarts_counting(db_session):
    # 잠금이 풀린 뒤의 실패는 처음부터 다시 센다 — 풀리자마자 1회 실패로 재잠금되면 영구 잠금이다.
    _user(db_session)
    db_session.add(
        LoginThrottle(
            username="alice", client_ip=IP_A, failed_count=_limit(), locked_until=now() - timedelta(seconds=1)
        )
    )
    db_session.commit()
    assert _attempt(db_session, "alice", WRONG, IP_A) == "invalid_credentials"  # 429 아님
    row = _row(db_session, "alice", IP_A)
    assert (row.failed_count, row.locked_until) == (1, None)


# ---------------------------------------------------------------------------
# 성공 시 되돌리기
# ---------------------------------------------------------------------------


def test_success_clears_own_ip_and_its_share_of_global(db_session):
    _user(db_session)
    for _ in range(3):
        _attempt(db_session, "alice", WRONG, IP_B)  # 다른 IP 의 실패(공격 진행 중)
    for _ in range(_limit() - 1):
        _attempt(db_session, "alice", WRONG, IP_A)
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "ok"
    assert _row(db_session, "alice", IP_A) is None
    # 합산 칸에는 다른 IP 의 실패(3)만 남는다 — 정상 로그인 한 번이 분산 대입 횟수를 지우지 않는다.
    assert _row(db_session, "alice", GLOBAL_THROTTLE_KEY).failed_count == 3
    assert _row(db_session, "alice", IP_B).failed_count == 3


def test_success_without_other_failures_leaves_no_rows(db_session):
    _user(db_session)
    for _ in range(_limit() - 1):
        _attempt(db_session, "alice", WRONG, IP_A)
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "ok"
    assert db_session.execute(select(LoginThrottle)).scalars().all() == []


def test_success_that_reached_global_cap_releases_its_own_lock(db_session):
    _user(db_session)
    global_limit = _limit() * user_service.GLOBAL_FAILURE_MULTIPLIER
    db_session.add(LoginThrottle(username="alice", client_ip=GLOBAL_THROTTLE_KEY, failed_count=global_limit - 1))
    db_session.commit()
    # 이 시도의 예약이 합산 칸을 상한에 닿게 해 잠금이 걸리지만, 비밀번호가 맞으면 그 잠금을 되돌린다.
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "ok"
    row = _row(db_session, "alice", GLOBAL_THROTTLE_KEY)
    assert (row.failed_count, row.locked_until) == (global_limit - 1, None)
    assert _attempt(db_session, "alice", PASSWORD, IP_B) == "ok"


# ---------------------------------------------------------------------------
# 예약 원자성 (TOCTOU)
# ---------------------------------------------------------------------------


def test_attempt_is_reserved_and_committed_before_password_check(db_session_factory, db_session, monkeypatch):
    # 확인과 기록을 따로 하면 병렬 요청이 모두 확인을 통과한다. bcrypt 검증 시점에 이 시도는 이미
    # 다른 연결에서 보이는 카운트로 반영돼 있어야 한다.
    _user(db_session)
    seen: list[tuple[int, int]] = []
    real_verify = user_service.verify_password

    def spying_verify(plain: str, hashed: str) -> bool:
        with db_session_factory() as other:
            counts = dict(
                other.execute(
                    select(LoginThrottle.client_ip, LoginThrottle.failed_count).where(LoginThrottle.username == "alice")
                ).all()
            )
        seen.append((counts.get(IP_A, 0), counts.get(GLOBAL_THROTTLE_KEY, 0)))
        return real_verify(plain, hashed)

    monkeypatch.setattr(user_service, "verify_password", spying_verify)
    _attempt(db_session, "alice", WRONG, IP_A)
    _attempt(db_session, "alice", WRONG, IP_A)
    assert seen == [(1, 1), (2, 2)]


def test_concurrent_reservations_cannot_exceed_limit(db_session_factory, db_session, monkeypatch):
    # 다른 연결들이 상한까지 예약해 두면(아직 검증 중인 병렬 요청) 다음 시도는 bcrypt 없이 429 다.
    _user(db_session)
    _, _, window = user_service._throttle_limits()
    sessions = [db_session_factory() for _ in range(_limit())]
    try:
        for s in sessions:
            user_service._insert_throttle_if_missing(s, "alice", IP_A)
            assert user_service._reserve_attempt(s, "alice", IP_A, _limit(), window) is not None
            s.commit()
    finally:
        for s in sessions:
            s.close()
    calls: list[str] = []
    monkeypatch.setattr(user_service, "verify_password", lambda plain, hashed: calls.append(hashed) or True)
    assert _attempt(db_session, "alice", PASSWORD, IP_A) == "too_many_attempts"
    assert calls == []
    assert _row(db_session, "alice", IP_A).failed_count == _limit()


def test_reservation_counts_are_atomic_across_sessions(db_session_factory, db_session):
    # 낡은 identity map 을 든 세션이 예약해도 증가분이 사라지지 않는다(읽고-고치고-쓰기 금지).
    _, _, window = user_service._throttle_limits()
    user_service._insert_throttle_if_missing(db_session, "alice", IP_A)
    user_service._reserve_attempt(db_session, "alice", IP_A, _limit(), window)
    db_session.commit()
    a, b = db_session_factory(), db_session_factory()
    try:
        b.execute(select(LoginThrottle)).scalar_one()  # B 의 identity map 에 count=1 상태를 올린다
        b.commit()
        for s in (a, b):
            user_service._reserve_attempt(s, "alice", IP_A, _limit(), window)
            s.commit()
    finally:
        a.close()
        b.close()
    assert _row(db_session, "alice", IP_A).failed_count == 3


# ---------------------------------------------------------------------------
# 감사 로그 주입 방지
# ---------------------------------------------------------------------------


def test_audit_log_escapes_user_supplied_values(db_session, caplog):
    forged = "alice\n2026-01-01 INFO app.audit 로그인 성공: username='admin'"
    with caplog.at_level(logging.INFO, logger="app.audit"):
        _attempt(db_session, forged, WRONG, IP_A)
    messages = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert messages
    assert all("\n" not in m for m in messages)
    assert any("\\n" in m for m in messages)


# ---------------------------------------------------------------------------
# 정리·해제
# ---------------------------------------------------------------------------


def test_purge_stale_login_throttles_keeps_recent_and_locked(db_session):
    old = now() - user_service.LOGIN_THROTTLE_RETENTION - timedelta(minutes=1)
    db_session.add_all(
        [
            LoginThrottle(username="stale", client_ip=IP_A, failed_count=1, last_failed_at=old),
            LoginThrottle(
                username="expired-lock",
                client_ip=IP_A,
                failed_count=5,
                last_failed_at=old,
                locked_until=now() - timedelta(hours=1),
            ),
            LoginThrottle(username="recent", client_ip=IP_A, failed_count=1, last_failed_at=now()),
            LoginThrottle(
                username="locked",
                client_ip=IP_A,
                failed_count=5,
                last_failed_at=old,
                locked_until=now() + timedelta(minutes=5),
            ),
        ]
    )
    db_session.commit()
    assert user_service.purge_stale_login_throttles(db_session, dry_run=True) == 2
    assert len(db_session.execute(select(LoginThrottle)).scalars().all()) == 4
    assert user_service.purge_stale_login_throttles(db_session) == 2
    db_session.expire_all()
    left = {t.username for t in db_session.execute(select(LoginThrottle)).scalars()}
    assert left == {"recent", "locked"}


def test_clear_login_throttles_removes_every_bucket_of_username(db_session):
    for _ in range(_limit()):
        _attempt(db_session, "alice", WRONG, IP_A)
    _attempt(db_session, "alice", WRONG, IP_B)
    _attempt(db_session, "bob", WRONG, IP_A)
    assert user_service.clear_login_throttles(db_session, "alice") == 3  # IP_A·IP_B·합산 칸
    db_session.expire_all()
    assert {t.username for t in db_session.execute(select(LoginThrottle)).scalars()} == {"bob"}
