"""폼 → pydantic 스키마 검증 (ARCHITECTURE.md §8).

폼 검증은 WTForms 가 아니라 schemas/ 의 pydantic 모델로 한다 — 검증 규칙을 한 벌로 유지한다.
Flask-WTF 는 CSRF 보호(CSRFProtect)에만 쓴다.

    data, errors = parse_form(NoticeWrite, title=..., body_html=...)
    if errors:
        return render_template("...", errors=errors, form=request.form), 422
"""

from datetime import datetime

from pydantic import BaseModel, ValidationError

# 필드 이름이 없는 오류(model_validator 등)를 담는 키.
FORM_ERROR_KEY = "_form"


def parse_form[M: BaseModel](model: type[M], **values) -> tuple[M | None, dict[str, str]]:
    """값으로 모델을 만든다. 실패하면 (None, {필드: 첫 오류 메시지})."""
    try:
        return model(**values), {}
    except ValidationError as e:
        errors: dict[str, str] = {}
        for err in e.errors(include_url=False):
            field = str(err["loc"][0]) if err["loc"] else FORM_ERROR_KEY
            message = err["msg"].removeprefix("Value error, ")
            errors.setdefault(field, message)
        return None, errors


def checkbox(value: str | None) -> bool:
    """HTML 체크박스 — 체크되면 값이 오고(기본 "on"), 아니면 필드 자체가 없다."""
    return value is not None


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def optional_datetime(value: str | None) -> datetime | str | None:
    """<input type="datetime-local"> 값(KST naive, "YYYY-MM-DDTHH:MM"). 형식 오류는 pydantic 이 메시지를 만든다."""
    value = optional_text(value)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value
