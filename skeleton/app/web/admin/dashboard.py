"""관리자 — 대시보드."""

from flask import render_template

from app.dependencies import get_db
from app.services import admin_service
from app.web.admin import bp


@bp.get("/")
def dashboard() -> str:
    return render_template("admin/dashboard.html", stats=admin_service.dashboard(get_db()))
