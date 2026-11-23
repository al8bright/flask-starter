"""Flask 진입점 — 앱 팩토리 (ARCHITECTURE.md §4).

- 화면은 Jinja 전체 페이지 렌더링이 기본이고, htmx 요청에는 partial 만 돌려준다 (§13).
- JSON 은 /api/v1 아래(헬스 체크·첨부 다운로드)에만 둔다.
- 업로드 공개 파일: UPLOAD_DIR/public → /uploads/public (private 은 절대 정적 서빙하지 않는다).
- DB 스키마는 Alembic 으로만 관리한다 (§11). 여기서 create_all 을 호출하지 않는다.

실행:
    flask --app app.main run --debug              (개발)
    waitress-serve --call app.main:create_app      (운영 — Windows·Linux 공통)
    gunicorn "app.main:create_app()"               (운영 — Linux)
"""

import logging

from flask import Flask
from flask_wtf.csrf import CSRFProtect, generate_csrf
from markupsafe import Markup
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  모델 메타데이터 등록
from app import dependencies
from app.config import (
    DEFAULT_SECRET_KEY,
    MIN_PRODUCTION_BCRYPT_ROUNDS,
    MIN_PRODUCTION_SECRET_BYTES,
    Settings,
    get_settings,
)
from app.core import storage
from app.core.logging import configure_logging
from app.web import register_blueprints
from app.web.errors import register_error_handlers
from app.web.security_headers import register_security_headers

logger = logging.getLogger(__name__)

PROJECT_NAME = "__PROJECT_NAME__"

MB = 1024 * 1024
# 요청 본문 전체 상한 = 가장 큰 업로드 상한 + 폼 필드 여유. 넘으면 Werkzeug 가 413 을 낸다.
# 파일별 상한(이미지·첨부)은 app/web/files.py 의 read_upload 가 따로 검사한다.
REQUEST_BODY_MARGIN_BYTES = 2 * MB
# 파일이 아닌 폼 필드 합계 상한 — Werkzeug 기본(500 KB)으로는 공지 본문 상한(20만 자, 한글 3 bytes)을 받지 못한다.
MAX_FORM_MEMORY_BYTES = 1 * MB

csrf = CSRFProtect()


def csrf_field() -> Markup:
    """폼에 넣는 CSRF 숨은 필드 — 템플릿에서 {{ csrf_field() }} 로 쓴다 (§9)."""
    return Markup('<input type="hidden" name="csrf_token" value="{}">').format(generate_csrf())


def check_startup_settings(settings: Settings) -> None:
    """안전하지 않은 설정이면 운영에서 기동을 막고, 개발에서는 경고한다 (§9, §21).

    공개된 서명키는 누구나 CSRF 토큰·flash 쿠키를 위조할 수 있다는 뜻이다.
    """
    is_production = settings.app_env == "production"

    if settings.secret_key == DEFAULT_SECRET_KEY:
        if is_production:
            raise RuntimeError(
                "APP_ENV=production 인데 SECRET_KEY 가 공개된 기본값입니다. "
                ".env 에 무작위 키를 설정하세요 (예: openssl rand -hex 32)."
            )
        logger.warning("SECRET_KEY 가 공개된 기본값입니다. 서명 위조가 가능하므로 .env 에 무작위 키를 설정하세요.")
    elif len(settings.secret_key.encode("utf-8")) < MIN_PRODUCTION_SECRET_BYTES:
        if is_production:
            raise RuntimeError(
                f"APP_ENV=production 인데 SECRET_KEY 가 {MIN_PRODUCTION_SECRET_BYTES} bytes 미만입니다. "
                ".env 에 무작위 키를 설정하세요 (예: openssl rand -hex 32)."
            )
        logger.warning("SECRET_KEY 가 %s bytes 미만입니다. 무작위 키를 설정하세요.", MIN_PRODUCTION_SECRET_BYTES)

    # bcrypt 비용을 낮추는 것은 테스트 전용이다 — 운영에서 낮으면 해시 유출 시 대입 공격 비용이 줄어든다.
    if is_production and settings.bcrypt_rounds < MIN_PRODUCTION_BCRYPT_ROUNDS:
        raise RuntimeError(f"APP_ENV=production 인데 BCRYPT_ROUNDS 가 {MIN_PRODUCTION_BCRYPT_ROUNDS} 미만입니다.")

    # 인증 쿠키가 Secure 없이 나가면 HTTP 구간에서 평문으로 노출된다.
    if is_production and not settings.cookie_secure:
        raise RuntimeError(
            "APP_ENV=production 인데 COOKIE_SECURE=false 입니다. "
            "HTTPS 로 서비스하고 .env 에 COOKIE_SECURE=true 를 설정하세요."
        )

    if settings.seed_default_admin and is_production:
        raise RuntimeError(
            "APP_ENV=production 에서는 기본 관리자 시드를 켤 수 없습니다. "
            "SEED_DEFAULT_ADMIN=false 로 두고 관리자 계정을 직접 만드세요 (python -m app.cli create-admin)."
        )


def seed_default_admin(settings: Settings, session_factory: sessionmaker[Session]) -> None:
    """기본 관리자 시드(SEED_DEFAULT_ADMIN). 실패해도 기동을 막지 않는다."""
    from app.services import user_service

    if not settings.seed_default_admin:
        return
    if not settings.default_admin_password:
        logger.error(
            "SEED_DEFAULT_ADMIN=true 인데 DEFAULT_ADMIN_PASSWORD 가 비어 있습니다 — "
            "기본 관리자 시드를 건너뜁니다. .env 에 초기 비밀번호를 설정하세요."
        )
        return
    try:
        with session_factory() as db:
            user_service.ensure_admin(db, password=settings.default_admin_password)
    except ValueError:
        logger.error(
            "기본 관리자 시드에 실패했습니다. DEFAULT_ADMIN_PASSWORD 가 UTF-8 기준 72 bytes 이하인지 확인하세요.",
            exc_info=True,
        )
    except (OperationalError, ProgrammingError):
        logger.warning(
            "기본 관리자 시드를 건너뜁니다 (테이블 없음/DB 미연결 — alembic upgrade head 필요).", exc_info=True
        )
    except Exception:  # noqa: BLE001  시드 실패가 서버 기동을 막지 않게 한다.
        logger.error("기본 관리자 시드 중 예상하지 못한 오류가 발생했습니다.", exc_info=True)


def create_app(*, session_factory: sessionmaker[Session] | None = None) -> Flask:
    """앱을 만든다. session_factory 는 테스트가 임시 DB 로 바꿀 때만 넘긴다(기본: app.db.session.SessionLocal)."""
    # §5 ⛔ 모듈 전역 settings 싱글톤 금지 — 생성 시점에 get_settings() 로 읽는다.
    settings = get_settings()
    configure_logging(settings.log_level)
    check_startup_settings(settings)
    storage.ensure_dirs()

    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal

    flask_app = Flask(__name__)
    flask_app.config.update(
        # Flask 서명 쿠키(session)는 flash 메시지와 CSRF 토큰에만 쓴다 — 인증은 DB 세션 쿠키다 (§9).
        SECRET_KEY=settings.secret_key,
        SESSION_COOKIE_NAME="__PROJECT_SNAKE___flash",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.cookie_secure,
        MAX_CONTENT_LENGTH=max(settings.max_image_upload_mb, settings.max_attachment_upload_mb) * MB
        + REQUEST_BODY_MARGIN_BYTES,
        MAX_FORM_MEMORY_SIZE=MAX_FORM_MEMORY_BYTES,
        # CSRF 토큰 만료를 Flask 세션 수명에 맡긴다 — 기본 1시간이면 긴 글 작성 중 저장이 실패한다.
        WTF_CSRF_TIME_LIMIT=None,
        WTF_CSRF_SSL_STRICT=settings.cookie_secure,
        TEMPLATES_AUTO_RELOAD=settings.app_env == "development",
    )
    flask_app.jinja_env.globals["project_name"] = PROJECT_NAME
    flask_app.jinja_env.globals["csrf_field"] = csrf_field

    csrf.init_app(flask_app)
    dependencies.init_app(flask_app, session_factory)
    register_security_headers(flask_app)
    register_error_handlers(flask_app)
    register_blueprints(flask_app)

    seed_default_admin(settings, session_factory)
    return flask_app
