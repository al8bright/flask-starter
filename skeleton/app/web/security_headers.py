"""보안 응답 헤더 (ARCHITECTURE.md §9).

이 앱은 HTML 을 직접 내므로 CSP 도 여기서 붙인다.
- 스크립트·스타일은 같은 출처 파일만(인라인 금지). htmx 는 static/js 에 버전을 고정해 둔다.
  htmx 의 인라인 indicator 스타일은 base.html 의 htmx-config 로 끈다(includeIndicatorStyles=false).
- hx-on·hx-vals="js:" 처럼 문자열을 eval 하는 htmx 기능은 쓰지 않는다(unsafe-eval 을 열지 않는다).
- 이미지: 공지 본문은 외부 http(s) 이미지를 허용하므로(core/sanitize.py) img-src 에 https: 를 둔다.
  blob: 은 편집기의 업로드 중 자리표시·자르기 미리보기용이다(같은 페이지가 만든 주소만 해당).
- iframe: 공지 본문의 유튜브 임베드만(core/sanitize.py 의 YOUTUBE_EMBED_RE 와 한 쌍).
- 로그인·관리자·API 응답은 X-Robots-Tag: noindex 로 색인에서 뺀다. robots.txt 에 경로를 적지 않는다 —
  누구나 읽는 파일이라 관리자 경로 목록이 공격 단서가 된다(app/web/public.py).
"""

from flask import Flask, Response, request

from app.config import get_settings

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: blob: https:",
        "frame-src https://www.youtube-nocookie.com https://www.youtube.com",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

# 쓰지 않는 브라우저 기능을 문서 단위로 끈다 — 스크립트가 주입되더라도 권한 요청을 띄우지 못한다.
# fullscreen 은 공지 본문의 유튜브 임베드가 쓰므로 기본값(같은 출처 + 위임)으로 둔다.
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=()"
# 인증 상태에 따라 내용이 달라지는 HTML 은 공유 캐시에 남기지 않는다.
PRIVATE_NO_STORE = "private, no-store"
# 검색엔진 색인에서 빼는 블루프린트 — 로그인·관리자 화면과 JSON·첨부 다운로드.
NOINDEX_BLUEPRINTS = frozenset({"auth", "admin", "api"})


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        settings = get_settings()
        # HSTS 는 HTTPS 배포에서만 — 개발(http://localhost)이 HTTPS 로 고정되는 사고를 막는다.
        if settings.cookie_secure or settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if response.mimetype == "text/html" and "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = PRIVATE_NO_STORE
        if request.path.startswith("/admin") or request.path in ("/login", "/logout"):
            response.headers["Cache-Control"] = PRIVATE_NO_STORE
        if request.blueprint in NOINDEX_BLUEPRINTS:
            response.headers["X-Robots-Tag"] = "noindex"
        return response
