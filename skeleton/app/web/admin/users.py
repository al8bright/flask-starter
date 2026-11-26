"""관리자 — 사용자·세션·로그인 잠금.

사용자 행의 권한·활성 변경은 htmx 예제다 — 행 하나(partials/admin_user_row.html)만 다시 그린다.
htmx 가 없으면 같은 폼이 POST → redirect 로 목록 전체를 다시 그린다.
"""

from flask import Response, flash, redirect, render_template, request, url_for

from app.dependencies import current_user, get_db
from app.schemas.admin import AdminUserUpdate
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_QUERY_LENGTH
from app.services import admin_service
from app.web.admin import bp
from app.web.forms import checkbox, parse_form
from app.web.htmx import is_htmx
from app.web.pagination import int_arg, page_arg, page_links

ROLE_FILTERS = ("user", "admin")


@bp.get("/users")
def users() -> str:
    q = (request.args.get("q") or "").strip()[:MAX_QUERY_LENGTH] or None
    role = request.args.get("role") if request.args.get("role") in ROLE_FILTERS else None
    result = admin_service.list_users(get_db(), q=q, role=role, page=page_arg(), size=DEFAULT_PAGE_SIZE)
    return render_template(
        "admin/users.html",
        result=result,
        q=q or "",
        role=role or "",
        pages=page_links(result, "admin.users", q=q, role=role),
    )


@bp.post("/users/<int:user_id>")
def update_user(user_id: int) -> Response | str:
    data, errors = parse_form(
        AdminUserUpdate, role=request.form.get("role"), is_active=checkbox(request.form.get("is_active"))
    )
    if errors:
        flash(next(iter(errors.values())), "error")
        return redirect(url_for("admin.users"))
    actor = current_user()
    user = admin_service.update_user(
        get_db(), actor_id=actor.id if actor else None, user_id=user_id, role=data.role, is_active=data.is_active
    )
    if is_htmx():
        return render_template("partials/admin_user_row.html", user=user, saved=True)
    flash(f"{user.username} 사용자를 저장했습니다.", "success")
    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/sessions/revoke")
def revoke_user_sessions(user_id: int) -> Response:
    revoked = admin_service.revoke_user_sessions(get_db(), user_id)
    flash(f"세션 {revoked}개를 폐기했습니다.", "success")
    return redirect(url_for("admin.users"))


@bp.get("/sessions")
def sessions() -> str:
    user_id = int_arg("user_id")
    result = admin_service.list_sessions(get_db(), user_id=user_id, page=page_arg(), size=DEFAULT_PAGE_SIZE)
    return render_template(
        "admin/sessions.html",
        result=result,
        pages=page_links(result, "admin.sessions", user_id=user_id),
        throttles=admin_service.list_login_throttles(get_db()),
    )


@bp.post("/sessions/<int:session_id>/revoke")
def revoke_session(session_id: int) -> Response:
    admin_service.revoke_session(get_db(), session_id)
    flash("세션을 폐기했습니다.", "success")
    return redirect(url_for("admin.sessions"))


@bp.post("/login-throttles/clear")
def clear_login_throttle() -> Response:
    # 아이디는 URL 이 아니라 폼 값으로 받는다 — 공격자가 만든 아이디(../ 등)가 경로를 바꾸지 못한다.
    username = request.form.get("username", "")
    admin_service.clear_login_throttle(get_db(), username)
    flash(f"{username} 의 로그인 잠금을 해제했습니다.", "success")
    return redirect(url_for("admin.sessions"))
