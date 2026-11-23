"""파일 다운로드·업로드 공통 HTTP 처리 + 공개 업로드 파일 서빙.

- /uploads/public/<key>  UPLOAD_DIR/public 아래만 서빙한다. private/(공지 첨부)는 어떤 경로로도 닿지 않는다
  — 서빙 루트가 public/ 이고 send_from_directory 가 루트 밖 경로(../ 포함)를 거부한다.
- 첨부 다운로드는 항상 attachment 로 내려 브라우저가 인라인 렌더링하지 않게 한다.
"""

import re
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, Response, send_file, send_from_directory
from werkzeug.datastructures import FileStorage

from app.core import storage

MB = 1024 * 1024

# 공개 파일 이름이 무작위(uuid)이고 내용이 바뀌지 않으므로 길게 캐시한다.
PUBLIC_UPLOADS_CACHE_CONTROL = "public, max-age=31536000, immutable"

bp = Blueprint("files", __name__)


@bp.get("/uploads/public/<path:key>")
def public_upload(key: str) -> Response:
    response = send_from_directory(storage.public_root(), key, max_age=None, conditional=True)
    response.headers["Cache-Control"] = PUBLIC_UPLOADS_CACHE_CONTROL
    return response


def content_disposition(filename: str) -> str:
    """attachment + ASCII 대체 filename + RFC 5987 filename* (한글 등 비ASCII 파일명용)."""
    fallback = re.sub(r'[^\x20-\x7e]|["\\]', "_", filename).strip() or "download"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


def attachment_response(path: Path, *, filename: str, content_type: str | None) -> Response:
    response = send_file(path, mimetype=content_type or "application/octet-stream", conditional=False)
    response.headers["Content-Disposition"] = content_disposition(filename)
    response.headers["Cache-Control"] = "private, no-store"
    return response


def read_upload(file: FileStorage | None, *, max_mb: int) -> tuple[bytes, str]:
    """업로드 파일을 상한(MB)까지만 읽어 (내용, 원래 파일명)을 돌려준다.

    파일이 없으면 StorageError("invalid_filename"), 상한을 넘으면 StorageError("file_too_large") → 413.
    """
    if file is None or not file.filename:
        raise storage.StorageError("invalid_filename", "업로드할 파일을 선택하세요.")
    return storage.read_limited(file.stream, max_mb * MB), file.filename
