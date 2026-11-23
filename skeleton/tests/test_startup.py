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


# ---------------------------------------------------------------------------
# 리버스 프록시 신뢰 — TRUSTED_PROXY_HOPS (app/web/proxy.py)

FORWARDED = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": "app.example.com", "X-Forwarded-For": "203.0.113.7"}


def _probe_client(monkeypatch, db_session_factory, hops: str):
    """요청이 앱에 어떻게 보이는지(scheme·host·IP) 돌려주는 시험용 경로를 붙인 클라이언트."""
    from flask import request

    monkeypatch.setenv("TRUSTED_PROXY_HOPS", hops)
    get_settings.cache_clear()
    app = create_app(session_factory=db_session_factory)
    app.add_url_rule("/__probe", "probe", lambda: f"{request.scheme} {request.host} {request.remote_addr}")
    return app.test_client()


def test_forwarded_headers_ignored_without_trusted_proxy(monkeypatch, db_session_factory):
    """기본(0)은 클라이언트가 보낸 X-Forwarded-* 를 따르지 않는다(위조 방지)."""
    client = _probe_client(monkeypatch, db_session_factory, "0")
    assert client.get("/__probe", headers=FORWARDED).get_data(as_text=True) == "http localhost 127.0.0.1"


def test_forwarded_headers_trusted_behind_one_proxy(monkeypatch, db_session_factory):
    """nginx 한 겹 뒤(1)에서는 HTTPS·원래 호스트·클라이언트 IP 를 앱이 그대로 본다.

    request.is_secure 가 참이어야 Flask-WTF 의 HTTPS Referer 엄격 검사(WTF_CSRF_SSL_STRICT)가 동작한다.
    """
    client = _probe_client(monkeypatch, db_session_factory, "1")
    assert client.get("/__probe", headers=FORWARDED).get_data(as_text=True) == "https app.example.com 203.0.113.7"


@pytest.mark.parametrize("hops", ["-1", "4", "abc"])
def test_invalid_proxy_hops_refuses_start(monkeypatch, db_session_factory, hops):
    from pydantic import ValidationError

    monkeypatch.setenv("TRUSTED_PROXY_HOPS", hops)
    with pytest.raises(ValidationError):
        create_app(session_factory=db_session_factory)


def test_warns_when_secure_cookie_without_proxy_trust(monkeypatch, db_session_factory, caplog):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")
    get_settings.cache_clear()
    with caplog.at_level("WARNING", logger="app.web.proxy"):
        create_app(session_factory=db_session_factory)
    assert "TRUSTED_PROXY_HOPS" in caplog.text
