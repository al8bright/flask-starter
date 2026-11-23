"""로그인·로그아웃·접근 제어 (ARCHITECTURE.md §9, §12)."""

from sqlalchemy import select

from app.dependencies import AUTH_COOKIE
from app.models.auth_session import AuthSession
from app.services import admin_service
from tests.conftest import ADMIN_PASSWORD, USER_PASSWORD, csrf_token, login, post_form


def _auth_cookie(client):
    return client.get_cookie(AUTH_COOKIE)


def test_login_sets_httponly_session_cookie(client, normal_user):
    res = login(client, normal_user.username, USER_PASSWORD)
    assert res.headers["Location"] == "/"
    cookie = _auth_cookie(client)
    assert cookie is not None and cookie.http_only and cookie.same_site == "Lax"
    set_cookie = res.headers["Set-Cookie"]
    assert "HttpOnly" in set_cookie and "Secure" not in set_cookie  # COOKIE_SECURE=false (개발)
    # 쿠키에는 불투명 토큰만 — DB 에는 해시만 있다.
    assert cookie.value.split(".")[0].isdigit()


def test_admin_login_goes_to_dashboard(client, admin_user):
    res = login(client, admin_user.username, ADMIN_PASSWORD)
    assert res.headers["Location"] == "/admin/"


def test_login_wrong_password_is_401_without_cookie(client, normal_user):
    res = post_form(client, "/login", {"username": normal_user.username, "password": "wrong-password"})
    assert res.status_code == 401
    assert "아이디 또는 비밀번호가 올바르지 않습니다." in res.get_data(as_text=True)
    assert _auth_cookie(client) is None


def test_login_validation_error_is_422(client):
    res = post_form(client, "/login", {"username": "", "password": ""})
    assert res.status_code == 422


def test_login_lockout_is_429_with_retry_after(client, normal_user):
    for _ in range(5):
        post_form(client, "/login", {"username": normal_user.username, "password": "wrong-password"})
    res = post_form(client, "/login", {"username": normal_user.username, "password": USER_PASSWORD})
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) >= 1


def test_login_without_csrf_token_is_rejected(client, normal_user):
    res = client.post("/login", data={"username": normal_user.username, "password": USER_PASSWORD})
    assert res.status_code == 400
    assert _auth_cookie(client) is None


def test_login_redirects_to_safe_next_only(client, normal_user):
    res = post_form(
        client, "/login", {"username": normal_user.username, "password": USER_PASSWORD, "next": "/notices?q=a"}
    )
    assert res.headers["Location"] == "/notices?q=a"


def test_login_ignores_external_next(client, normal_user):
    for bad in ("//evil.example", "/\\evil.example", "https://evil.example/", "/ok\nSet-Cookie:x"):
        client.delete_cookie(AUTH_COOKIE)
        res = post_form(client, "/login", {"username": normal_user.username, "password": USER_PASSWORD, "next": bad})
        assert res.headers["Location"] == "/", bad


def test_logout_revokes_session(client, db_session, normal_user):
    login(client, normal_user.username, USER_PASSWORD)
    token = _auth_cookie(client).value
    res = post_form(client, "/logout")
    assert res.status_code == 302
    session = db_session.execute(select(AuthSession).where(AuthSession.user_id == normal_user.id)).scalar_one()
    assert session.revoked_at is not None
    # 폐기된 토큰을 다시 실어 보내도 로그인 상태가 아니다.
    client.set_cookie(AUTH_COOKIE, token)
    assert "로그아웃" not in client.get("/").get_data(as_text=True)


def test_logout_requires_post(client):
    assert client.get("/logout").status_code == 405


def test_forged_cookie_is_anonymous(client, normal_user):
    login(client, normal_user.username, USER_PASSWORD)
    session_id = _auth_cookie(client).value.split(".")[0]
    client.set_cookie(AUTH_COOKIE, f"{session_id}.forged-secret")
    assert client.get("/admin/").status_code == 302


def test_admin_requires_login(client):
    res = client.get("/admin/notices?q=x")
    assert res.status_code == 302
    assert res.headers["Location"].startswith("/login?next=/admin/notices")


def test_admin_requires_admin_role(user_client):
    assert user_client.get("/admin/").status_code == 403


def test_htmx_request_without_login_gets_hx_redirect(client):
    res = client.get("/admin/users", headers={"HX-Request": "true"})
    assert res.status_code == 401
    assert res.headers["HX-Redirect"].startswith("/login")


def test_deactivated_user_loses_access_immediately(client, db_session, admin_user, normal_user):
    login(client, normal_user.username, USER_PASSWORD)
    assert "로그아웃" in client.get("/").get_data(as_text=True)
    admin_service.update_user(db_session, actor_id=admin_user.id, user_id=normal_user.id, role=None, is_active=False)
    assert "로그아웃" not in client.get("/").get_data(as_text=True)


def test_demoted_admin_gets_403_on_next_request(client, db_session, admin_user):
    from app.models.user import UserRole
    from app.services import user_service

    other = user_service.create_user(db_session, username="second", password=ADMIN_PASSWORD, role=UserRole.ADMIN)
    login(client, other.username, ADMIN_PASSWORD)
    assert client.get("/admin/").status_code == 200
    admin_service.update_user(db_session, actor_id=admin_user.id, user_id=other.id, role="user", is_active=None)
    assert client.get("/admin/").status_code == 403


def test_login_clears_previous_flask_session(client, normal_user):
    before = csrf_token(client)
    login(client, normal_user.username, USER_PASSWORD)
    assert csrf_token(client) != before
