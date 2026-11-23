"""로그인·로그아웃 (ARCHITECTURE.md §9) — 얇은 HTTP 계층.

로그인 성공 → auth_sessions 행 생성 → 불투명 토큰을 httpOnly 쿠키(AUTH_COOKIE)로 심는다.
로그아웃(POST) → 세션 폐기 + 쿠키 삭제. GET 으로는 로그아웃하지 않는다(링크·prefetch 로 끊기지 않게).
실패 사유는 응답으로 구분하지 않는다(user_service.authenticate). 잠금 중이면 429 + Retry-After.
"""

from flask import Blueprint, Response, make_response, redirect, render_template, request, session, url_for

from app.dependencies import (
    AUTH_COOKIE,
    clear_auth_cookie,
    current_user,
    get_db,
    is_admin,
    safe_next_path,
    set_auth_cookie,
)
from app.schemas.user import LoginRequest
from app.services import session_service, user_service
from app.services.exceptions import ServiceError
from app.web.errors import status_for_code
from app.web.forms import parse_form

bp = Blueprint("auth", __name__)

# ServiceError 코드 → 로그인 화면 응답 상태. 표(STATUS_BY_CODE)에 없는 인증 전용 코드다.
LOGIN_STATUS_BY_CODE = {"invalid_credentials": 401, "too_many_attempts": 429}


def _home_for_current_user() -> str:
    return url_for("admin.dashboard") if is_admin(current_user()) else url_for("public.home")


@bp.get("/login")
def login() -> Response | str:
    if current_user() is not None:
        return redirect(safe_next_path(request.args.get("next")) or _home_for_current_user())
    return render_template("auth/login.html", next=safe_next_path(request.args.get("next")), errors={}, username="")


@bp.post("/login")
def login_submit() -> Response:
    next_path = safe_next_path(request.form.get("next"))
    username = request.form.get("username", "")
    data, errors = parse_form(LoginRequest, username=username, password=request.form.get("password", ""))
    if errors:
        return make_response(render_template("auth/login.html", next=next_path, errors=errors, username=username), 422)

    db = get_db()
    try:
        user = user_service.authenticate(db, data.username, data.password)
    except ServiceError as e:
        status = LOGIN_STATUS_BY_CODE.get(e.code, status_for_code(e.code))
        response = make_response(
            render_template("auth/login.html", next=next_path, errors={"_form": e.message}, username=username),
            status,
        )
        if e.retry_after:
            response.headers["Retry-After"] = str(e.retry_after)
        return response

    _, token = session_service.create_session(db, user_id=user.id)
    # 로그인 전에 쌓인 flash·CSRF 토큰을 버린다(세션 고정 방지).
    session.clear()
    target = next_path or (url_for("admin.dashboard") if is_admin(user) else url_for("public.home"))
    response = redirect(target)
    set_auth_cookie(response, token)
    return response


@bp.post("/logout")
def logout() -> Response:
    token = request.cookies.get(AUTH_COOKIE)
    if token:
        session_service.revoke(get_db(), token)
    session.clear()
    response = redirect(url_for("public.home"))
    clear_auth_cookie(response)
    return response
