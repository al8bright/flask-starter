"""관리자 화면 (ARCHITECTURE.md §4) — /admin 아래 전체가 관리자 전용이다.

Blueprint 의 before_request 가 모든 관리자 경로를 막는다 — 뷰마다 데코레이터를 빠뜨려도 열리지 않는다.
"""

from flask import Blueprint

from app.dependencies import admin_required

bp = Blueprint("admin", __name__)


@bp.before_request
@admin_required
def _require_admin() -> None:
    return None


from app.web.admin import banners, dashboard, notices, users  # noqa: E402,F401  라우트 등록
