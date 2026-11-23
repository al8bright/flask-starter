"""JSON·파일 API (ARCHITECTURE.md §4) — /api/v1.

- /api/v1/health, /api/v1/health/db   배포·모니터링용 헬스 체크
- /api/v1/notices/<id>/attachments/<aid>   공지 첨부 다운로드(게시된 공지만)
  경로는 공통 계층(notice_service.download_url)이 만드는 URL 과 같아야 한다 — 형제 FastAPI 템플릿과 같은 경로다.

상태 변경 API 는 두지 않는다 — 화면의 변경은 폼 POST(CSRF 보호)로만 한다.
"""

import logging

from flask import Blueprint, Response, jsonify
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import get_db
from app.schemas.health import DbHealth
from app.services import health_service, notice_service
from app.web.files import attachment_response

logger = logging.getLogger(__name__)

bp = Blueprint("api", __name__)


@bp.get("/health")
def health() -> Response:
    return jsonify(status="ok")


@bp.get("/health/db")
def health_db() -> Response | tuple[Response, int]:
    # DB 연결 불가/테이블 없음은 unhandled 500 이 아니라 구조화된 503 으로 응답한다.
    try:
        return jsonify(DbHealth(**health_service.db_health(get_db())).model_dump())
    except SQLAlchemyError:
        logger.exception("DB 헬스 체크 실패")
        return jsonify(db="error", detail="데이터베이스에 접근할 수 없습니다."), 503


@bp.get("/notices/<int:notice_id>/attachments/<int:attachment_id>")
def download_attachment(notice_id: int, attachment_id: int) -> Response:
    att, path = notice_service.attachment_file(get_db(), notice_id, attachment_id, published_only=True)
    return attachment_response(path, filename=att.original_name, content_type=att.content_type)
