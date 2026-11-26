"""헬스 체크 서비스 (ARCHITECTURE.md §8).

DB 연결 및 테이블 접근이 정상인지 확인한다.
응답은 최소 상태({"db": "ok"})만 담는다 — 공개 경로이므로 테이블 이름·행 수 같은 내부 정보를 내보내지 않는다.
실패는 SQLAlchemyError 로 그대로 올리고, 웹 계층이 503 으로 바꾼다.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_meta import AppMeta


def db_health(db: Session) -> dict:
    """app_meta 테이블을 한 행만 조회해 DB/테이블 접근을 검증한다(전체 집계는 하지 않는다)."""
    db.execute(select(AppMeta.id).limit(1)).first()
    return {"db": "ok"}
