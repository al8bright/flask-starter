"""공개 화면 (ARCHITECTURE.md §4) — 홈(배너·최근 공지), 공지 목록·상세. 인증 불요.

공지 목록은 htmx 예제다 — 검색어 입력이 목록 partial(partials/notice_list.html)만 바꾸고 URL 도 갱신한다.
htmx 가 없어도 같은 URL 의 검색 폼(GET)으로 똑같이 동작한다.
"""

from flask import Blueprint, Response, render_template, request

from app.dependencies import get_db
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_QUERY_LENGTH
from app.services import banner_service, notice_service
from app.web.htmx import render_page_or_partial
from app.web.pagination import page_arg, page_links

bp = Blueprint("public", __name__)

HOME_NOTICE_COUNT = 5


@bp.get("/")
def home() -> str:
    db = get_db()
    banners = banner_service.list_live(db)
    notices = notice_service.list_published(db, page=1, size=HOME_NOTICE_COUNT, q=None)
    return render_template("public/home.html", banners=banners, notices=notices.items)


@bp.get("/notices")
def notices() -> Response:
    q = (request.args.get("q") or "").strip()[:MAX_QUERY_LENGTH] or None
    page = page_arg()
    result = notice_service.list_published(get_db(), page=page, size=DEFAULT_PAGE_SIZE, q=q)
    return render_page_or_partial(
        "public/notices.html",
        "partials/notice_list.html",
        result=result,
        q=q or "",
        pages=page_links(result, "public.notices", q=q),
    )


@bp.get("/notices/<int:notice_id>")
def notice_detail(notice_id: int) -> str:
    notice = notice_service.view_published(get_db(), notice_id)
    return render_template("public/notice_detail.html", notice=notice)
