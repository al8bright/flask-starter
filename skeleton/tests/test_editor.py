"""공지 본문 편집기 (ARCHITECTURE.md §13) — 서버 계약과 정적 스크립트 점검.

편집기는 app/static/js/editor/ 의 ES 모듈이다(빌드 없음). JS 동작 자체는 브라우저에서 확인하고,
여기서는 서버가 지켜야 할 계약을 고정한다.
- 이미지 업로드: Accept: application/json 이면 JSON 으로 답한다(성공·오류·로그인 만료 모두).
- 출력 계약: 편집기가 만드는 마크업은 정화(core/sanitize.py) 후에도 그대로 남아야 한다.
- 정적 점검: 모듈 import 경로가 실제 파일을 가리키고, CSP 를 깨는 코드(eval·style 속성)가 없다.
"""

import io
import re
from pathlib import Path

import pytest

from app.core.sanitize import sanitize_html
from app.web.security_headers import CONTENT_SECURITY_POLICY
from tests.conftest import csrf_token, post_form
from tests.media_factory import image_bytes

EDITOR_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "js" / "editor"
JSON = {"Accept": "application/json"}


def upload_json(client, data: bytes, name: str = "a.png"):
    return post_form(
        client,
        "/admin/editor/images",
        {"file": (io.BytesIO(data), name)},
        content_type="multipart/form-data",
        headers=dict(JSON),
    )


# ---------------------------------------------------------------------------
# 이미지 업로드 JSON 계약


def test_editor_image_upload_json_returns_url_and_size(admin_client):
    res = upload_json(admin_client, image_bytes("PNG", (40, 20)))
    assert res.status_code == 201
    body = res.get_json()
    assert body["url"].startswith("/uploads/public/editor/")
    assert (body["width"], body["height"]) == (40, 20)
    assert body["key"].startswith("public/editor/")


def test_editor_image_upload_json_error_is_json(admin_client):
    res = upload_json(admin_client, b"not an image")
    assert res.status_code == 422
    assert res.is_json
    assert res.get_json()["detail"]


def test_editor_image_upload_json_without_login_is_401_json(client):
    res = upload_json(client, image_bytes())
    assert res.status_code == 401
    assert res.is_json
    assert res.get_json()["code"] == "http_401"


def test_editor_image_upload_json_without_csrf_is_400_json(admin_client):
    res = admin_client.post(
        "/admin/editor/images",
        data={"file": (io.BytesIO(image_bytes()), "a.png")},
        content_type="multipart/form-data",
        headers=dict(JSON),
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == "csrf_failed"


def test_editor_image_upload_accepts_csrf_header(admin_client):
    # 편집기는 폼 필드가 아니라 X-CSRFToken 헤더로 토큰을 보낸다.
    token = csrf_token(admin_client)
    res = admin_client.post(
        "/admin/editor/images",
        data={"file": (io.BytesIO(image_bytes()), "a.png")},
        content_type="multipart/form-data",
        headers={**JSON, "X-CSRFToken": token},
    )
    assert res.status_code == 201


def test_browser_navigation_still_gets_html_error(admin_client):
    # Accept 가 text/html 우선(일반 폼 제출)이면 기존처럼 HTML 오류 페이지다.
    res = post_form(
        admin_client,
        "/admin/editor/images",
        {"file": (io.BytesIO(b"not an image"), "a.png")},
        content_type="multipart/form-data",
        headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
    )
    assert res.status_code == 422
    assert res.mimetype == "text/html"


# ---------------------------------------------------------------------------
# 화면 연결


def test_notice_form_mounts_editor_on_textarea(admin_client):
    html = admin_client.get("/admin/notices/new").get_data(as_text=True)
    # JS 가 없으면 textarea 그대로 쓰고, 있으면 편집기가 이 textarea 를 숨기고 대신한다.
    assert re.search(r"<textarea[^>]*name=\"body_html\"[^>]*data-rich-editor", html)
    assert 'data-upload-url="/admin/editor/images"' in html
    assert 'type="module" src="/static/js/editor/editor.js"' in html
    assert re.search(r'<meta name="csrf-token" content="[^"]+">', html)


def test_csp_allows_blob_images_for_upload_preview():
    # 업로드 중 자리표시와 자르기 미리보기는 blob: 주소를 쓴다.
    img_src = next(d for d in CONTENT_SECURITY_POLICY.split("; ") if d.startswith("img-src"))
    assert "blob:" in img_src.split()
    assert "script-src 'self'" in CONTENT_SECURITY_POLICY
    assert "style-src 'self'" in CONTENT_SECURITY_POLICY


# ---------------------------------------------------------------------------
# 출력 계약 — 편집기(media-html.js·editor-dom.js)가 만드는 마크업은 정화 후에도 같아야 한다

EDITOR_OUTPUT = [
    '<p class="align-center">가운데 <strong>굵게</strong> <em>기울임</em> <u>밑줄</u></p>',
    "<p><s>취소</s> <mark>형광</mark></p>",
    "<h2>제목 2</h2><h3>제목 3</h3>",
    "<ul><li>하나</li></ul><ol><li>둘</li></ol><blockquote><p>인용</p></blockquote><hr>",
    '<p><img src="/uploads/public/editor/2026/11/23/a.webp" alt="설명" width="640" height="360"></p>',
    '<p class="align-right"><img src="/uploads/public/editor/2026/11/23/b.png" alt="" width="80" height="45"></p>',
]


@pytest.mark.parametrize("html", EDITOR_OUTPUT)
def test_editor_markup_survives_sanitizer(html):
    assert sanitize_html(html) == html


def test_editor_link_markup_gets_forced_rel():
    out = sanitize_html('<p><a href="https://example.com/a">링크</a></p>')
    assert 'href="https://example.com/a"' in out
    assert 'rel="noopener noreferrer"' in out


def test_editor_youtube_markup_survives_sanitizer():
    html = (
        '<div class="video" data-youtube-video="">'
        '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" width="640" height="360" '
        'title="YouTube 영상" allowfullscreen=""></iframe></div>'
    )
    out = sanitize_html(html)
    assert 'class="video"' in out
    assert "data-youtube-video" in out
    assert 'src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"' in out
    assert 'width="640" height="360"' in out


# ---------------------------------------------------------------------------
# 정적 점검 — 빌드 단계가 없으므로 import 경로 오류·CSP 위반 코드를 여기서 막는다

IMPORT_RE = re.compile(r"""^\s*import\s[^;]*?from\s+["']([^"']+)["']""", re.MULTILINE | re.DOTALL)
FORBIDDEN = {
    "eval(": "eval 은 CSP(unsafe-eval 없음)에 막힌다",
    "new Function": "문자열 코드 실행은 CSP 에 막힌다",
    'setAttribute("style"': "style 속성은 CSP 에 막힌다 — el.style.<속성> 을 쓴다",
    "style=": "HTML 문자열의 style 속성은 CSP 에 막힌다",
    "cssText": "cssText 대신 개별 속성을 쓴다(의도 명확화)",
    "document.write": "document.write 금지",
    "jquery": "DOM 유틸리티 라이브러리 금지(★MUST #1)",
}


def editor_files() -> list[Path]:
    files = sorted(EDITOR_DIR.glob("*.js"))
    assert files, "편집기 모듈이 없습니다."
    return files


def test_editor_module_imports_resolve():
    for path in editor_files():
        for spec in IMPORT_RE.findall(path.read_text(encoding="utf-8")):
            assert spec.startswith("./") and spec.endswith(".js"), f"{path.name}: 상대 경로 .js 만 import 한다 — {spec}"
            assert (path.parent / spec).is_file(), f"{path.name}: {spec} 파일이 없다"


def test_editor_modules_avoid_csp_breaking_code():
    for path in editor_files():
        text = path.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(("//", "*", "/*")))
        for needle, reason in FORBIDDEN.items():
            assert needle.lower() not in code.lower(), f"{path.name}: {needle} — {reason}"
