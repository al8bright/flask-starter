"""요청 본문 상한 (ARCHITECTURE.md §8, §9).

전역 상한(MAX_CONTENT_LENGTH)은 폼 필드 수준으로 낮게 두고, 관리자 업로드 경로에 관리자가 보낸 요청일 때만
업로드 상한으로 올린다. CSRF 검사(Flask-WTF)가 request.form 을 읽는 순간 Werkzeug 가 본문 전체를 받아
파일 부분을 임시 파일로 쓰므로, 로그인하지 않은 요청이 큰 본문으로 디스크·워커를 점유하지 못하게 한다.

이 훅은 현재 사용자를 읽은 뒤(dependencies.init_app), CSRF 보다 먼저 등록해야 한다(app/main.py).
배포 예시의 nginx client_max_body_size 도 같은 경로에만 업로드 상한을 연다(deploy/nginx.conf).
"""

from flask import Flask, request

from app.dependencies import current_user, is_admin

# 파일을 받는 관리자 엔드포인트 — 경로를 바꾸면 deploy/nginx.conf 의 업로드 location 도 함께 고친다.
UPLOAD_ENDPOINTS = frozenset(
    {
        "admin.create_banner",
        "admin.update_banner",
        "admin.add_attachment",
        "admin.upload_editor_image",
    }
)


def register_body_limit(app: Flask, *, upload_limit_bytes: int) -> None:
    @app.before_request
    def _raise_limit_for_admin_upload() -> None:
        if request.endpoint in UPLOAD_ENDPOINTS and is_admin(current_user()):
            request.max_content_length = upload_limit_bytes
