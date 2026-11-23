"""웹 계층 (ARCHITECTURE.md §4) — 얇은 HTTP 계층. 도메인 로직은 services/ 에 둔다.

| Blueprint | URL            | 내용 |
|-----------|----------------|------|
| public    | /              | 홈(배너·최근 공지), 공지 목록·상세 |
| auth      | /login /logout | 로그인·로그아웃 |
| admin     | /admin         | 대시보드·사용자·세션·공지·배너 (관리자 전용) |
| api       | /api/v1        | 헬스 체크(JSON)·공지 첨부 다운로드 |
| files     | /uploads/public| 공개 업로드 파일(에디터·배너 이미지) |
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.web.admin import bp as admin_bp
    from app.web.api import bp as api_bp
    from app.web.auth import bp as auth_bp
    from app.web.files import bp as files_bp
    from app.web.public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(files_bp)
