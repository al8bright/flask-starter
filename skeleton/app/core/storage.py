"""로컬 업로드 저장소 (UPLOAD_DIR).

키(key)는 UPLOAD_DIR 기준 상대 경로이며 **항상 서버가 만든다** — 사용자 입력(파일명 등)은 경로에 쓰지 않는다.

    public/editor/YYYY/MM/DD/<uuid>.<ext>        에디터 본문 이미지   → /uploads/public/... 로 정적 서빙
    public/banners/YYYY/MM/DD/<uuid>.<ext>       배너 이미지          → 〃
    private/attachments/YYYY/MM/DD/<uuid>.<ext>  공지 첨부(원본 파일명은 DB) → API 로만 내려간다(정적 서빙 금지)

이미지는 클라이언트를 믿지 않는다: 시그니처 + Pillow 로 실제 이미지인지 확인하고(PNG·JPEG·WebP·GIF 만),
EXIF 방향을 반영한 뒤 재인코딩해 EXIF·XMP·ICC·주석(JPEG COM·PNG 텍스트) 등 메타데이터를 지우며,
긴 변이 MAX_LONG_EDGE 를 넘으면 줄인다.
GIF 는 프레임 수·전 프레임 픽셀 합을 제한한 뒤 Pillow 로 다시 저장한다 — 애니메이션(프레임별 표시 시간·
반복·disposal)은 유지하고 주석·XMP 등 확장 블록과 파일 끝 뒤에 덧붙은 데이터는 버린다. 크기는 줄이지 않는다.
"""

import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError

from app.config import get_settings
from app.core.security import now

# 서버 재인코딩 시 긴 변 상한(px). 에디터는 업로드 전에 1600px 로 줄이지만 서버가 최종 방어선이다.
MAX_LONG_EDGE = 2000
# 디코딩 전에 거르는 픽셀 수 상한 — 작은 파일로 거대한 캔버스를 선언하는 압축 폭탄 방어.
MAX_IMAGE_PIXELS = 40_000_000
JPEG_QUALITY = 85
WEBP_QUALITY = 85
# 애니메이션 GIF 상한 — 디코딩·재저장 비용은 (프레임 수 × 캔버스 픽셀)에 비례하므로 둘 다 막는다.
# 전 프레임 픽셀 합 상한은 정지 이미지 한 장의 상한(MAX_IMAGE_PIXELS)과 같은 예산이다.
MAX_GIF_FRAMES = 300
MAX_GIF_TOTAL_PIXELS = MAX_IMAGE_PIXELS

# 재인코딩 때 원본 info 에서 넘겨도 되는 키 — 화면 표시에 필요한 값만. 그 밖의 키(comment·exif·xmp·
# icc_profile·dpi 와 PNG tEXt 등)는 Pillow 가 저장 시 im.info 에서 기본값으로 다시 쓰는 경우가 있어
# (예: JPEG 은 im.info["comment"] 를 COM 세그먼트로, PNG 는 icc_profile 을 그대로 쓴다) 저장 전에 지운다.
_KEEP_INFO_KEYS = frozenset({"transparency"})

PUBLIC_PREFIX = "public/"
IMAGE_CATEGORIES = frozenset({"editor", "banners"})
ATTACHMENT_CATEGORY = "attachments"

# Pillow 포맷 → (저장 확장자, Content-Type)
IMAGE_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
    "GIF": ("gif", "image/gif"),
}

# 첨부 허용 확장자 → Content-Type (클라이언트가 보낸 Content-Type 은 쓰지 않는다).
ATTACHMENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "hwp": "application/x-hwp",
    "hwpx": "application/hwp+zip",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "csv": "text/csv",
    "zip": "application/zip",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

ORIGINAL_NAME_MAX_LENGTH = 255

# 서버가 만드는 키의 유일한 형식. 이 형식이 아니면 해석하지 않는다(경로 탈출·임의 파일 접근 차단).
KEY_RE = re.compile(
    r"^(?:public/(?:editor|banners)|private/attachments)/\d{4}/\d{2}/\d{2}/[0-9a-f]{32}\.[a-z0-9]{1,5}$"
)


class StorageError(Exception):
    """저장소 오류. code: invalid_image | unsupported_file_type | file_too_large | invalid_filename | invalid_key."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class StoredImage:
    key: str
    width: int
    height: int
    content_type: str


@dataclass(frozen=True)
class StoredFile:
    key: str
    size_bytes: int
    content_type: str


def upload_root() -> Path:
    return get_settings().upload_dir


def public_root() -> Path:
    return upload_root() / "public"


def ensure_dirs() -> None:
    """기동 시 public/·private/ 디렉터리를 만든다 (정적 서빙 대상이 없으면 404 만 나도록)."""
    (upload_root() / "public").mkdir(parents=True, exist_ok=True)
    (upload_root() / "private").mkdir(parents=True, exist_ok=True)


def _new_key(prefix: str, ext: str) -> str:
    return f"{prefix}/{now():%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"


def resolve_key(key: str) -> Path:
    """키를 실제 경로로 바꾼다. 서버가 만든 형식이 아니거나 UPLOAD_DIR 밖이면 StorageError("invalid_key")."""
    if not isinstance(key, str) or not KEY_RE.fullmatch(key):
        raise StorageError("invalid_key", "잘못된 파일 키입니다.")
    root = upload_root().resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise StorageError("invalid_key", "잘못된 파일 키입니다.")
    return path


def exists(key: str) -> bool:
    try:
        return resolve_key(key).is_file()
    except StorageError:
        return False


def delete(key: str) -> None:
    """파일 삭제. 없거나 잘못된 키면 조용히 넘어간다(DB 행 삭제 뒤 정리용)."""
    try:
        resolve_key(key).unlink(missing_ok=True)
    except StorageError:
        return


def public_url(key: str) -> str:
    """공개 키의 URL = PUBLIC_FILES_BASE_URL + "/uploads/" + key. private 키는 거부한다."""
    if not key.startswith(PUBLIC_PREFIX):
        raise ValueError("공개 파일만 URL 을 만들 수 있습니다.")
    return f"{get_settings().public_files_base_url.rstrip('/')}/uploads/{key}"


def read_limited(fileobj: BinaryIO, max_bytes: int) -> bytes:
    """최대 max_bytes 까지만 읽는다. 넘으면 StorageError("file_too_large")."""
    data = fileobj.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise StorageError("file_too_large", f"파일이 너무 큽니다(최대 {max_bytes // (1024 * 1024)}MB).")
    return data


def _write(key: str, data: bytes) -> None:
    path = resolve_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# 이미지
# ---------------------------------------------------------------------------


def _sniff_image_format(data: bytes) -> str | None:
    """매직 바이트로 형식을 판별한다 — 확장자·Content-Type 은 믿지 않는다."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def _invalid_image() -> StorageError:
    return StorageError("invalid_image", "PNG·JPEG·WebP·GIF 이미지만 올릴 수 있습니다.")


def _open_verified(data: bytes, fmt: str) -> Image.Image:
    """Pillow 로 열어 형식·크기·무결성을 확인한 이미지(아직 디코드 전)를 돌려준다."""
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format != fmt or probe.width * probe.height > MAX_IMAGE_PIXELS:
                raise _invalid_image()
            probe.verify()
        img = Image.open(BytesIO(data))
        img.load()
    except StorageError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as e:
        raise _invalid_image() from e
    return img


def _strip_info(img: Image.Image) -> None:
    """저장에 쓰일 메타데이터를 지운다 — 표시에 필요한 키(_KEEP_INFO_KEYS)만 남긴다."""
    img.info = {k: v for k, v in img.info.items() if k in _KEEP_INFO_KEYS}


def _reencode(img: Image.Image, fmt: str) -> tuple[bytes, int, int]:
    """EXIF 방향 반영 → 긴 변 축소 → 메타데이터 없이 재인코딩."""
    img = ImageOps.exif_transpose(img)
    if max(img.size) > MAX_LONG_EDGE:
        img.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.Resampling.LANCZOS)
    _strip_info(img)
    out = BytesIO()
    if fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    elif fmt == "WEBP":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.save(out, format="WEBP", quality=WEBP_QUALITY)
    else:  # PNG
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA")
        img.save(out, format="PNG", optimize=True)
    # exif=·pnginfo=·icc_profile=·comment= 를 넘기지 않고 info 도 비웠으므로(_strip_info) 원본 메타데이터는
    # 따라오지 않는다. convert() 결과도 비운 info 를 물려받는다.
    return out.getvalue(), img.width, img.height


def _gif_too_large() -> StorageError:
    return StorageError(
        "invalid_image",
        f"GIF 가 너무 큽니다(최대 {MAX_GIF_FRAMES}프레임, 전체 프레임 합 {MAX_GIF_TOTAL_PIXELS:,}픽셀).",
    )


def _reencode_gif(img: Image.Image) -> tuple[bytes, int, int]:
    """GIF 를 프레임 단위로 다시 저장한다 — 표시 시간·반복·disposal 만 넘기고 나머지 확장 블록은 버린다.

    프레임 수는 디코딩 전에 센다(n_frames 는 블록 헤더만 훑는다). 상한을 넘으면 StorageError.
    """
    n_frames = getattr(img, "n_frames", 1)
    if n_frames > MAX_GIF_FRAMES or n_frames * img.width * img.height > MAX_GIF_TOTAL_PIXELS:
        raise _gif_too_large()
    loop = img.info.get("loop")
    frames: list[Image.Image] = []
    durations: list[int] = []
    disposals: list[int] = []
    for frame in ImageSequence.Iterator(img):
        durations.append(int(frame.info.get("duration", 0)))
        disposals.append(int(getattr(frame, "disposal_method", 0)))
        copy = frame.copy()
        _strip_info(copy)
        frames.append(copy)
    out = BytesIO()
    params: dict = {"format": "GIF", "save_all": True, "append_images": frames[1:]}
    if len(frames) > 1:
        params.update(duration=durations, disposal=disposals)
    elif durations[0]:
        params["duration"] = durations[0]
    if loop is not None:
        params["loop"] = loop
    frames[0].save(out, **params)
    return out.getvalue(), img.width, img.height


def save_image(data: bytes, *, category: str) -> StoredImage:
    """이미지를 검증·재인코딩해 public/<category>/ 아래에 저장한다. 실패 시 StorageError("invalid_image")."""
    if category not in IMAGE_CATEGORIES:
        raise ValueError(f"알 수 없는 이미지 분류입니다: {category}")
    fmt = _sniff_image_format(data)
    if fmt is None:
        raise _invalid_image()
    img = _open_verified(data, fmt)
    ext, content_type = IMAGE_FORMATS[fmt]
    try:
        payload, width, height = _reencode_gif(img) if fmt == "GIF" else _reencode(img, fmt)
    except StorageError:
        raise
    except (OSError, ValueError, EOFError) as e:
        raise _invalid_image() from e
    key = _new_key(f"public/{category}", ext)
    _write(key, payload)
    return StoredImage(key=key, width=width, height=height, content_type=content_type)


def image_size(key: str) -> tuple[int, int]:
    """저장된 이미지의 (폭, 높이) — 헤더만 읽는다. 없거나 이미지가 아니면 StorageError."""
    path = resolve_key(key)
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except FileNotFoundError as e:
        raise StorageError("invalid_key", "파일을 찾을 수 없습니다.") from e
    except (UnidentifiedImageError, OSError) as e:
        raise _invalid_image() from e


# ---------------------------------------------------------------------------
# 첨부
# ---------------------------------------------------------------------------


def clean_original_name(raw: str) -> str:
    """표시·다운로드용 원본 파일명 정리 — 경로 성분·제어 문자를 지우고 확장자를 살려 255자로 자른다."""
    name = unicodedata.normalize("NFC", raw or "")
    name = re.split(r"[\\/]", name)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip().strip(".")
    if len(name) > ORIGINAL_NAME_MAX_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) < 16:
            name = stem[: ORIGINAL_NAME_MAX_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:ORIGINAL_NAME_MAX_LENGTH]
    return name


def attachment_extension(filename: str) -> str:
    """허용 목록 확장자(소문자)를 돌려준다. 아니면 StorageError("unsupported_file_type")."""
    stem, dot, ext = (filename or "").rpartition(".")
    ext = ext.lower()
    if not dot or not stem or ext not in ATTACHMENT_TYPES:
        allowed = ", ".join(sorted(ATTACHMENT_TYPES))
        raise StorageError("unsupported_file_type", f"첨부할 수 없는 파일 형식입니다. 허용: {allowed}")
    return ext


def save_attachment(data: bytes, filename: str) -> StoredFile:
    """첨부를 private/attachments/ 아래 무작위 이름으로 저장한다. 원본 파일명은 호출자가 DB 에 둔다."""
    ext = attachment_extension(filename)
    key = _new_key(f"private/{ATTACHMENT_CATEGORY}", ext)
    _write(key, data)
    return StoredFile(key=key, size_bytes=len(data), content_type=ATTACHMENT_TYPES[ext])
