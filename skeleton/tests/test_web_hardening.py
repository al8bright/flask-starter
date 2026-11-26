"""웹 계층 보안 강화 — 본문 상한·쿠키 접두사·권한 정책 헤더·정수 쿼리 파싱·프록시 설정 검사."""

import io

import pytest

from app.config import get_settings
from app.main import DEFAULT_BODY_LIMIT_BYTES, create_app
from app.web.body_limit import UPLOAD_ENDPOINTS
from tests.conftest import csrf_token, post_form

# 기본 상한을 넘지만 업로드 상한보다는 작은 본문.
OVER_DEFAULT = b"x" * (DEFAULT_BODY_LIMIT_BYTES + 1024)


def _multipart(client, url: str, payload: bytes):
    token = csrf_token(client)
    return client.post(
        url,
        data={"csrf_token": token, "file": (io.BytesIO(payload), "big.pdf")},
        content_type="multipart/form-data",
    )


# ---------------------------------------------------------------------------
# 요청 본문 상한 (app/web/body_limit.py)
# ---------------------------------------------------------------------------


def test_upload_endpoints_exist(flask_app):
    endpoints = {rule.endpoint for rule in flask_app.url_map.iter_rules()}
    assert UPLOAD_ENDPOINTS <= endpoints


def test_anonymous_large_body_is_rejected_on_login(client):
    res = _multipart(client, "/login", OVER_DEFAULT)
    assert res.status_code == 413


def test_anonymous_large_body_is_rejected_on_upload_route(client):
    res = _multipart(client, "/admin/editor/images", OVER_DEFAULT)
    assert res.status_code == 413


def test_normal_user_cannot_use_upload_limit(user_client):
    res = _multipart(user_client, "/admin/editor/images", OVER_DEFAULT)
    assert res.status_code == 413


def test_admin_upload_route_allows_upload_limit(admin_client, db_session):
    post_form(admin_client, "/admin/notices/new", {"title": "첨부", "body_html": "<p>a</p>"})
    from app.models.notice import Notice

    notice = db_session.query(Notice).one()
    res = _multipart(admin_client, f"/admin/notices/{notice.id}/attachments", b"%PDF-1.4\n" + OVER_DEFAULT)
    assert res.status_code != 413


def test_admin_non_upload_route_keeps_default_limit(admin_client):
    res = _multipart(admin_client, "/admin/notices/new", OVER_DEFAULT)
    assert res.status_code == 413


# ---------------------------------------------------------------------------
# __Host- 쿠키 접두사
# ---------------------------------------------------------------------------


def test_cookie_names_without_https_have_no_prefix(flask_app):
    from app.dependencies import AUTH_COOKIE, auth_cookie_name

    assert auth_cookie_name() == AUTH_COOKIE
    assert not flask_app.config["SESSION_COOKIE_NAME"].startswith("__Host-")


def test_cookie_names_with_https_use_host_prefix(monkeypatch, db_session_factory):
    from app.dependencies import AUTH_COOKIE, auth_cookie_name

    monkeypatch.setenv("COOKIE_SECURE", "true")
    get_settings.cache_clear()
    app = create_app(session_factory=db_session_factory)
    assert auth_cookie_name() == "__Host-" + AUTH_COOKIE
    assert app.config["SESSION_COOKIE_NAME"].startswith("__Host-")
    assert app.config["SESSION_COOKIE_PATH"] in (None, "/")
    assert app.config["SESSION_COOKIE_DOMAIN"] in (None, False)


# ---------------------------------------------------------------------------
# 헤더·쿼리 파싱
# ---------------------------------------------------------------------------


def test_permissions_policy_header(client):
    policy = client.get("/").headers["Permissions-Policy"]
    assert "camera=()" in policy and "geolocation=()" in policy
    assert "fullscreen" not in policy


@pytest.mark.parametrize("raw", ["²", "١", "9" * 5000, "99999999999999999999", "0", "-1", "1.5"])
def test_bad_page_values_fall_back_to_first_page(client, raw):
    assert client.get("/notices", query_string={"page": raw}).status_code == 200


@pytest.mark.parametrize("raw", ["²", "9" * 5000, "abc"])
def test_bad_session_filter_is_ignored(admin_client, raw):
    assert admin_client.get("/admin/sessions", query_string={"user_id": raw}).status_code == 200


# ---------------------------------------------------------------------------
# 프록시 신뢰와 APP_ENV
# ---------------------------------------------------------------------------


def test_proxy_trust_in_development_refuses_start(monkeypatch, db_session_factory):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="APP_ENV"):
        create_app(session_factory=db_session_factory)


# ---------------------------------------------------------------------------
# 로그인 잠금(아이디, IP)·조회수 집계·잠금 해제 경로
# ---------------------------------------------------------------------------


def _fail_login(client, username: str, ip: str):
    return post_form(
        client, "/login", {"username": username, "password": "wrong-password"}, environ_base={"REMOTE_ADDR": ip}
    )


def test_lockout_from_one_ip_does_not_block_another(client, admin_user):
    from app.config import get_settings as settings

    for _ in range(settings().login_max_failures):
        _fail_login(client, admin_user.username, "203.0.113.10")
    assert _fail_login(client, admin_user.username, "203.0.113.10").status_code == 429
    assert _fail_login(client, admin_user.username, "198.51.100.20").status_code == 401


def test_admin_can_clear_throttle_by_form_value(admin_client, client, normal_user):
    _fail_login(admin_client, normal_user.username, "203.0.113.10")
    page = admin_client.get("/admin/sessions").get_data(as_text=True)
    assert "203.0.113.10" in page and "전체 합산" in page
    res = post_form(admin_client, "/admin/login-throttles/clear", {"username": normal_user.username})
    assert res.status_code == 302
    assert "203.0.113.10" not in admin_client.get("/admin/sessions").get_data(as_text=True)


def _published_notice(admin_client, db_session):
    post_form(admin_client, "/admin/notices/new", {"title": "공지", "body_html": "<p>a</p>", "is_published": "on"})
    from app.models.notice import Notice

    return db_session.query(Notice).one()


@pytest.mark.parametrize(
    ("method", "headers", "counted"),
    [
        ("GET", {}, True),
        ("GET", {"Sec-Fetch-Dest": "document"}, True),
        ("GET", {"Sec-Fetch-Dest": "image"}, False),
        ("GET", {"Sec-Purpose": "prefetch"}, False),
        ("HEAD", {}, False),
    ],
)
def test_view_count_only_for_document_requests(admin_client, db_session, method, headers, counted):
    notice = _published_notice(admin_client, db_session)
    before = notice.view_count
    res = admin_client.open(f"/notices/{notice.id}", method=method, headers=headers)
    assert res.status_code == 200
    db_session.refresh(notice)
    assert notice.view_count == before + (1 if counted else 0)


def test_db_health_exposes_status_only(client):
    assert client.get("/api/v1/health/db").get_json() == {"db": "ok"}
