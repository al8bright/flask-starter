"""Health-check response schemas."""

from pydantic import BaseModel


class DbHealth(BaseModel):
    """공개 DB 헬스 응답 — 상태만 담는다(테이블 이름·행 수 등 내부 정보는 내보내지 않는다)."""

    db: str
