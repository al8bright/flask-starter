"""도메인 예외·HTTP 오류 → 응답 변환 (ARCHITECTURE.md §8).

코드별 상태는 STATUS_BY_CODE 한 곳에서 정한다(형제 FastAPI 템플릿의 app/api/errors.py 와 같은 표). 표에 없는 코드는 400.
응답 형식은 요청에 따라 고른다.

- /api/v1/*      JSON {"detail", "code"}
- Accept 가 JSON 우선(web/accept.py — 편집기 이미지 업로드 fetch) 도 같은 JSON
- htmx 요청      partials/alert.html 을 #alerts 영역에 끼운다(HX-Retarget).
                 base.html 의 htmx-config 가 4xx·5xx 응답도 swap 하게 해 둔다.
- 그 밖          errors/error.html 전체 페이지

폼 검증 오류(pydantic ValidationError)는 여기까지 오지 않는다 — 각 화면이 폼과 함께 422 로 다시 그린다.
"""

import logging

from flask import Flask, Response, jsonify, make_response, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException, MethodNotAllowed

from app.core.storage import StorageError
from app.services.exceptions import ServiceError
from app.web.accept import wants_json
from app.web.htmx import is_htmx

logger = logging.getLogger(__name__)

STATUS_BY_CODE: dict[str, int] = {
    "not_found": 404,
    "self_modification": 409,
    "last_admin": 409,
    "too_many_attachments": 409,
    "file_too_large": 413,
    "empty_body": 422,
    "invalid_image": 422,
    "invalid_image_key": 422,
    "unsupported_file_type": 422,
    "invalid_filename": 422,
    "invalid_reorder": 422,
    "invalid_key": 422,
}

HTTP_MESSAGES: dict[int, str] = {
    400: "잘못된 요청입니다.",
    401: "로그인이 필요합니다.",
    403: "접근 권한이 없습니다.",
    404: "페이지를 찾을 수 없습니다.",
    405: "허용되지 않은 요청 방식입니다.",
    413: "업로드 용량이 너무 큽니다.",
    429: "요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
    500: "서버 오류가 발생했습니다.",
}

CSRF_MESSAGE = "보안 토큰이 만료되었거나 올바르지 않습니다. 페이지를 새로 고친 뒤 다시 시도하세요."


def _is_api() -> bool:
    return request.path.startswith("/api/")


def error_response(status: int, message: str, code: str) -> Response:
    if _is_api() or wants_json():
        response = jsonify(detail=message, code=code)
        response.status_code = status
        return response
    if is_htmx():
        response = make_response(render_template("partials/alert.html", level="error", message=message), status)
        response.headers["HX-Retarget"] = "#alerts"
        response.headers["HX-Reswap"] = "innerHTML"
        return response
    return make_response(render_template("errors/error.html", status=status, message=message), status)


def status_for_code(code: str) -> int:
    return STATUS_BY_CODE.get(code, 400)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ServiceError)
    def _service_error(exc: ServiceError) -> Response:
        response = error_response(status_for_code(exc.code), exc.message, exc.code)
        if exc.retry_after:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

    @app.errorhandler(StorageError)
    def _storage_error(exc: StorageError) -> Response:
        return error_response(status_for_code(exc.code), exc.message, exc.code)

    @app.errorhandler(CSRFError)
    def _csrf_error(_exc: CSRFError) -> Response:
        return error_response(400, CSRF_MESSAGE, "csrf_failed")

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException) -> Response:
        status = exc.code or 500
        message = HTTP_MESSAGES.get(status) or exc.description or "요청을 처리하지 못했습니다."
        response = error_response(status, message, f"http_{status}")
        if isinstance(exc, MethodNotAllowed) and exc.valid_methods:
            response.headers["Allow"] = ", ".join(exc.valid_methods)
        return response

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception) -> Response:
        # 내부 정보(예외 메시지·스택)는 응답에 내보내지 않고 서버 로그에만 남긴다.
        logger.exception("처리되지 않은 예외: %s %s", request.method, request.path, exc_info=exc)
        return error_response(500, HTTP_MESSAGES[500], "internal_error")
