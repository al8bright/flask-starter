"""정적 스크립트 점검 (ARCHITECTURE.md §13, ★MUST 1·5) — 빌드 단계가 없으므로 CSP 를 깨는 코드를 여기서 막는다.

대상은 app/static/js/ 아래 모든 .js 다(하위 폴더 포함). 스크립트를 새로 추가해도 자동으로 검사된다.
벤더링한 라이브러리(VENDORED)는 무결성(SHA-256)으로 관리하므로 제외한다.
"""

from pathlib import Path

import pytest

JS_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "js"
VENDORED = {"htmx.min.js"}

FORBIDDEN = {
    "eval(": "eval 은 CSP(unsafe-eval 없음)에 막힌다",
    "new Function": "문자열 코드 실행은 CSP 에 막힌다",
    'setAttribute("style"': "style 속성은 CSP 에 막힌다 — el.style.<속성> 을 쓴다",
    "style=": "HTML 문자열의 style 속성은 CSP 에 막힌다",
    "cssText": "cssText 대신 개별 속성을 쓴다(의도 명확화)",
    "document.write": "document.write 금지",
    "jquery": "DOM 유틸리티 라이브러리 금지(★MUST 1)",
}


def own_scripts() -> list[Path]:
    files = sorted(p for p in JS_DIR.rglob("*.js") if p.name not in VENDORED)
    assert files, "검사할 스크립트가 없습니다."
    return files


def _code_lines(text: str) -> str:
    """주석 줄은 뺀다 — 금지 이유를 설명하는 주석이 걸리지 않게 한다."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(("//", "*", "/*")))


@pytest.mark.parametrize("path", own_scripts(), ids=lambda p: p.relative_to(JS_DIR).as_posix())
def test_scripts_avoid_csp_breaking_code(path):
    code = _code_lines(path.read_text(encoding="utf-8")).lower()
    for needle, reason in FORBIDDEN.items():
        assert needle.lower() not in code, f"{path.relative_to(JS_DIR).as_posix()}: {needle} — {reason}"


def test_vendored_scripts_exist():
    """제외 목록이 실제 파일을 가리킨다 — 이름이 바뀌면 검사에서 빠진 채로 남지 않게 한다."""
    for name in VENDORED:
        assert (JS_DIR / name).is_file(), name
