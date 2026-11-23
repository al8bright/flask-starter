"""앱 생성 시 설정 검사·기본 관리자 시드·보안 헤더 (ARCHITECTURE.md §9, §21)."""

import pytest

from app.config import DEFAULT_SECRET_KEY, get_settings
from app.main import create_app
from app.services import user_service
from app.web.security_headers import CONTENT_SECURITY_POLICY

STRONG_KEY = "x" * 40


def _production(monkeypatch, **env):
    values = {
        "APP_ENV": "production",
        "SECRET_KEY": STRONG_KEY,
        "COOKIE_SECURE": "true",
        "BCRYPT_ROUNDS": "12",
        "SEED_DEFAULT_ADMIN": "false",
        **env,
    }
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def test_production_with_safe_settings_starts(monkeypatch, db_session_factory):
    _production(monkeypatch)
    create_app(session_factory=db_session_factory)


@pytest.mark.parametrize(
    "env",
    [
        {"SECRET_KEY": DEFAULT_SECRET_KEY},
        {"SECRET_KEY": "short"},
        {"COOKIE_SECURE": "false"},
        {"BCRYPT_ROUNDS": "4"},
        {"SEED_DEFAULT_ADMIN": "true"},
    ],
)
def test_production_refuses_unsafe_settings(monkeypatch, db_session_factory, env):
    _production(monkeypatch, **env)
    with pytest.raises(RuntimeError):
        create_app(session_factory=db_session_factory)


def test_seed_default_admin(monkeypatch, db_session_factory, db_session):
    monkeypatch.setenv("SEED_DEFAULT_ADMIN", "true")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    get_settings.cache_clear()
    create_app(session_factory=db_session_factory)
    assert user_service.get_by_username(db_session, "admin") is not None


def test_seed_skips_without_password(monkeypatch, db_session_factory, db_session):
    monkeypatch.setenv("SEED_DEFAULT_ADMIN", "true")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "")
    get_settings.cache_clear()
    create_app(session_factory=db_session_factory)
    assert user_service.get_by_username(db_session, "admin") is None


def test_security_headers(client):
    res = client.get("/")
    assert res.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Cache-Control"] == "private, no-store"
    assert "Strict-Transport-Security" not in res.headers


def test_hsts_when_cookie_secure(monkeypatch, client):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    get_settings.cache_clear()
    assert client.get("/api/v1/health").headers["Strict-Transport-Security"] == "max-age=31536000"
