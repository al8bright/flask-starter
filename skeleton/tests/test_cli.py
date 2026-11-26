"""운영 관리 CLI 테스트 (app/cli.py)."""
import io
from datetime import timedelta

import pytest
from sqlalchemy import select

from app import cli
from app.core.security import now, verify_password
from app.models.auth_session import AuthSession, LoginThrottle
from app.models.user import UserRole
from app.services import session_service, user_service


def _stdin(monkeypatch, text: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


def test_create_admin_from_stdin(db_session_factory, db_session, monkeypatch):
    _stdin(monkeypatch, "strong-pass-123\n")
    code = cli.main(
        ["create-admin", "--username", "ops", "--password-stdin"], session_factory=db_session_factory
    )
    assert code == 0
    user = user_service.get_by_username(db_session, "ops")
    assert user.role == UserRole.ADMIN.value
    assert verify_password("strong-pass-123", user.hashed_password)


def test_create_admin_rejects_short_password(db_session_factory, db_session, monkeypatch):
    _stdin(monkeypatch, "short\n")
    code = cli.main(
        ["create-admin", "--username", "ops", "--password-stdin"], session_factory=db_session_factory
    )
    assert code == 1
    assert user_service.get_by_username(db_session, "ops") is None


def test_set_password_revokes_sessions_and_clears_lock(db_session_factory, db_session, monkeypatch):
    user = user_service.create_user(db_session, username="alice", password="old-pass-123")
    session_service.create_session(db_session, user_id=user.id)
    db_session.add(LoginThrottle(username="alice", client_ip="203.0.113.1", failed_count=5))
    db_session.add(LoginThrottle(username="alice", client_ip="*", failed_count=5))
    db_session.commit()
    _stdin(monkeypatch, "new-pass-456\n")
    code = cli.main(
        ["set-password", "--username", "alice", "--password-stdin"], session_factory=db_session_factory
    )
    assert code == 0
    db_session.expire_all()
    assert verify_password("new-pass-456", user_service.get_by_username(db_session, "alice").hashed_password)
    assert all(s.revoked_at is not None for s in db_session.execute(select(AuthSession)).scalars())
    assert db_session.execute(select(LoginThrottle)).scalar_one_or_none() is None


def test_set_password_unknown_user_fails(db_session_factory, monkeypatch):
    _stdin(monkeypatch, "new-pass-456\n")
    code = cli.main(
        ["set-password", "--username", "ghost", "--password-stdin"], session_factory=db_session_factory
    )
    assert code == 1


def _seed_auth_records(db_session):
    """만료 1·폐기 1·활성 1 세션과 오래된 실패 칸 1·최근 실패 칸 1."""
    user = user_service.create_user(db_session, username="alice", password="old-pass-123")
    expired, _ = session_service.create_session(db_session, user_id=user.id)
    revoked, _ = session_service.create_session(db_session, user_id=user.id)
    session_service.create_session(db_session, user_id=user.id)
    expired.expires_at = now() - timedelta(days=1)
    revoked.revoked_at = now() - timedelta(days=1)
    old = now() - user_service.LOGIN_THROTTLE_RETENTION - timedelta(minutes=1)
    db_session.add(LoginThrottle(username="ghost", client_ip="203.0.113.1", failed_count=2, last_failed_at=old))
    db_session.add(LoginThrottle(username="recent", client_ip="203.0.113.1", failed_count=1, last_failed_at=now()))
    db_session.commit()


def _counts(db_session) -> tuple[int, int]:
    db_session.expire_all()
    return (
        len(db_session.execute(select(AuthSession)).scalars().all()),
        len(db_session.execute(select(LoginThrottle)).scalars().all()),
    )


def test_cleanup_auth_dry_run_only_counts(db_session_factory, db_session, capsys):
    _seed_auth_records(db_session)
    code = cli.main(["cleanup-auth", "--dry-run"], session_factory=db_session_factory)
    assert code == 0
    assert "세션 2건, 로그인 실패 기록 1건" in capsys.readouterr().out
    assert _counts(db_session) == (3, 2)


def test_cleanup_auth_deletes_expired_revoked_and_stale(db_session_factory, db_session, capsys):
    _seed_auth_records(db_session)
    code = cli.main(["cleanup-auth"], session_factory=db_session_factory)
    assert code == 0
    assert "삭제했습니다: 세션 2건, 로그인 실패 기록 1건" in capsys.readouterr().out
    assert _counts(db_session) == (1, 1)
    remaining = db_session.execute(select(AuthSession)).scalar_one()
    assert remaining.revoked_at is None and remaining.expires_at > now()


def test_cleanup_auth_retention_keeps_recently_ended_sessions(db_session_factory, db_session, capsys):
    _seed_auth_records(db_session)
    code = cli.main(["cleanup-auth", "--retention-days", "7"], session_factory=db_session_factory)
    assert code == 0
    assert "세션 0건" in capsys.readouterr().out
    assert _counts(db_session)[0] == 3


def test_cleanup_auth_rejects_negative_retention(db_session_factory):
    with pytest.raises(SystemExit):
        cli.main(["cleanup-auth", "--retention-days", "-1"], session_factory=db_session_factory)
