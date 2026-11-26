"""공개 화면 (ARCHITECTURE.md §4) — 홈(배너·최근 공지), 공지 목록·상세, /favicon.ico·/robots.txt. 인증 불요.

공지 목록은 htmx 예제다 — 검색어 입력이 목록 partial(partials/notice_list.html)만 바꾸고 URL 도 갱신한다.
htmx 가 없어도 같은 URL 의 검색 폼(GET)으로 똑같이 동작한다.
"""

from flask import Blueprint, Response, current_app, render_template, request

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


def _counts_as_view() -> bool:
    """사람이 문서를 여는 요청인지 — 조회수 집계 대상.

    HEAD·미리 가져오기(prefetch)·다른 페이지의 <img>·<iframe> 같은 하위 리소스 요청은 세지 않는다.
    Sec-Fetch-Dest 를 보내지 않는 클라이언트(오래된 브라우저·curl)는 문서 요청으로 본다.
    """
    if request.method != "GET":
        return False
    purpose = (request.headers.get("Sec-Purpose") or request.headers.get("Purpose") or "").lower()
    if "prefetch" in purpose:
        return False
    return request.headers.get("Sec-Fetch-Dest", "document") in ("document", "iframe")


@bp.get("/notices/<int:notice_id>")
def notice_detail(notice_id: int) -> str:
    db = get_db()
    if _counts_as_view():
        notice_service.increment_view(db, notice_id)
    notice = notice_service.get_published(db, notice_id)
    return render_template("public/notice_detail.html", notice=notice)


@bp.get("/favicon.ico")
def favicon() -> Response:
    """브라우저가 링크와 무관하게 요청하는 주소 — static/img/favicon.ico 를 준다(없으면 404 가 로그에 쌓인다)."""
    return current_app.send_static_file("img/favicon.ico")


# 검색엔진 수집 규칙 — 모두 허용한다. ⛔ 관리자·로그인 같은 경로를 Disallow 로 적지 않는다:
# robots.txt 는 누구나 읽는 파일이라 경로 목록이 공격 단서가 된다. 색인 제외는 응답 헤더
# X-Robots-Tag: noindex(app/web/security_headers.py)로 한다. 공개 화면의 sitemap 이 생기면 Sitemap 줄을 더한다.
ROBOTS_TXT = "User-agent: *\nDisallow:\n"


@bp.get("/robots.txt")
def robots() -> Response:
    return Response(ROBOTS_TXT, mimetype="text/plain")
