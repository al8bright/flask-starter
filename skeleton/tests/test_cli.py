"""운영 관리 CLI 테스트 (app/cli.py)."""
import io

from sqlalchemy import select

from app import cli
from app.core.security import verify_password
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
    db_session.add(LoginThrottle(username="alice", failed_count=5))
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
