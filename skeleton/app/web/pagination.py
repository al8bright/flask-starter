"""목록 페이지 번호 처리 — schemas.common.Page 를 화면용 링크로 바꾼다."""

from dataclasses import dataclass
from math import ceil

from flask import request, url_for

from app.schemas.common import Page

# 현재 페이지 앞뒤로 보여 줄 번호 개수.
PAGE_WINDOW = 2
# 쿼리 문자열 정수의 최대 자릿수 — OFFSET 이 DB 정수 범위를 넘거나 int() 가 큰 수에서 실패하지 않게 한다.
MAX_INT_ARG_DIGITS = 9


@dataclass(frozen=True)
class PageLink:
    number: int
    url: str
    current: bool


@dataclass(frozen=True)
class PageLinks:
    pages: list[PageLink]
    prev_url: str | None
    next_url: str | None
    total_pages: int


def int_arg(name: str) -> int | None:
    """쿼리 문자열의 양의 정수. ASCII 숫자가 아니거나 너무 길거나 1 미만이면 None.

    str.isdigit() 는 "²" 같은 문자도 참이라 int() 가 실패한다 — ASCII 십진수만 받는다.
    """
    raw = request.args.get(name, "")
    if not (raw.isascii() and raw.isdecimal()) or len(raw) > MAX_INT_ARG_DIGITS:
        return None
    value = int(raw)
    return value if value >= 1 else None


def page_arg(name: str = "page") -> int:
    """?page= 값. 정수가 아니거나 범위를 벗어나면 1."""
    return int_arg(name) or 1


def page_links(result: Page, endpoint: str, **params) -> PageLinks:
    """현재 페이지 주변 번호와 이전·다음 링크. None 인 params 는 URL 에 넣지 않는다."""
    params = {k: v for k, v in params.items() if v not in (None, "")}
    total_pages = max(1, ceil(result.total / result.size)) if result.size else 1

    def link(n: int) -> str:
        return url_for(endpoint, page=n, **params)

    start = max(1, result.page - PAGE_WINDOW)
    end = min(total_pages, result.page + PAGE_WINDOW)
    return PageLinks(
        pages=[PageLink(n, link(n), n == result.page) for n in range(start, end + 1)],
        prev_url=link(result.page - 1) if result.page > 1 else None,
        next_url=link(result.page + 1) if result.page < total_pages else None,
        total_pages=total_pages,
    )
