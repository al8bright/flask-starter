"""htmx 보조 (ARCHITECTURE.md §13) — HX-Request 확인은 이 모듈 한 곳에서만 한다.

규칙:
- 모든 화면은 htmx 없이도 동작해야 한다(전체 페이지 렌더링 + 폼 POST → redirect).
- htmx 요청에는 같은 데이터로 partial(templates/partials/)만 돌려준다 — render_page_or_partial.
- 클라이언트 상태(모달·드래그 등)가 필요해지면 JS 를 덧대지 말고 SPA 스타터를 검토한다.
"""

from flask import Response, make_response, render_template, request


def is_htmx() -> bool:
    """htmx 가 보낸 요청인가. 히스토리 복원 요청(HX-History-Restore-Request)은 전체 페이지가 필요하다."""
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"


def render_page_or_partial(page: str, partial: str, status: int = 200, **context) -> Response:
    """htmx 요청이면 partial, 아니면 전체 페이지를 렌더링한다. 두 템플릿은 같은 context 를 받는다."""
    template = partial if is_htmx() else page
    response = make_response(render_template(template, **context), status)
    # 같은 URL 이 요청 헤더에 따라 다른 본문을 내므로 캐시가 섞이지 않게 한다.
    response.vary.add("HX-Request")
    return response


def htmx_redirect(location: str) -> Response:
    """htmx 요청에 전체 페이지 이동을 지시한다 (302 는 partial 자리에 끼워지므로 쓰지 않는다)."""
    return Response(status=204, headers={"HX-Redirect": location})
