"""응답 형식 협상 — fetch 가 JSON 을 요청했는지 판단한다 (ARCHITECTURE.md §13).

화면은 HTML 이 기본이다. 편집기 이미지 업로드처럼 스크립트가 `Accept: application/json` 으로 부르는
경로만 JSON 으로 답한다(성공·오류·로그인 만료 모두). 브라우저 이동(text/html 우선)과 htmx(`*/*`)는 해당하지 않는다.
"""

from flask import request


def wants_json() -> bool:
    """Accept 에서 application/json 이 text/html 보다 우선인가."""
    accept = request.accept_mimetypes
    return accept.quality("application/json") > accept.quality("text/html")
