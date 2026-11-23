"""관리자 — 배너 작성·수정·삭제·순서 변경.

이미지는 폼과 함께 올린다(multipart). 새 파일이 있으면 저장 후 그 key 로, 없으면 기존 image_key 를 그대로 쓴다.
순서 변경(위·아래)은 htmx 예제다 — 목록 partial(partials/admin_banner_rows.html)만 다시 그린다.
"""

from flask import Response, flash, make_response, redirect, render_template, request, url_for

from app.config import get_settings
from app.core import storage
from app.dependencies import get_db
from app.schemas.banner import BannerOrder, BannerWrite
from app.services import banner_service, upload_service
from app.services.exceptions import ServiceError
from app.web.admin import bp
from app.web.files import read_upload
from app.web.forms import checkbox, optional_datetime, optional_text, parse_form
from app.web.htmx import is_htmx

# 검증 단계에서 image_key 자리에 넣는 값 — 새 파일은 다른 필드가 모두 통과한 뒤에만 저장한다(고아 파일 방지).
PENDING_IMAGE_KEY = "pending-upload"


def _form_values(existing_key: str | None) -> dict:
    return {
        "title": request.form.get("title", ""),
        "image_key": existing_key or "",
        "link_url": optional_text(request.form.get("link_url")),
        "alt_text": request.form.get("alt_text", ""),
        "starts_at": optional_datetime(request.form.get("starts_at")),
        "ends_at": optional_datetime(request.form.get("ends_at")),
        "is_active": checkbox(request.form.get("is_active")),
    }


def _render_form(*, banner=None, form: dict, errors: dict, status: int = 200) -> Response:
    return make_response(render_template("admin/banner_form.html", banner=banner, form=form, errors=errors), status)


def _save(banner_id: int | None) -> Response:
    db = get_db()
    banner = banner_service.admin_get(db, banner_id) if banner_id is not None else None
    file = request.files.get("image")
    has_new_image = file is not None and bool(file.filename)
    form = _form_values(banner.image_key if banner else None)
    if has_new_image:
        form["image_key"] = PENDING_IMAGE_KEY
    elif not form["image_key"]:
        return _render_form(banner=banner, form=form, errors={"image_key": "배너 이미지를 선택하세요."}, status=422)

    _, errors = parse_form(BannerWrite, **form)
    if errors:
        return _render_form(banner=banner, form=form, errors=errors, status=422)

    new_key = None
    if has_new_image:
        data, _ = read_upload(file, max_mb=get_settings().max_image_upload_mb)
        new_key = upload_service.save_image(data, category="banners").key
        form["image_key"] = new_key
    data = BannerWrite(**form)
    try:
        if banner is None:
            saved = banner_service.create(db, data)
        else:
            saved = banner_service.update_banner(db, banner.id, data)
    except ServiceError:
        if new_key:
            storage.delete(new_key)
        raise
    flash("배너를 저장했습니다.", "success")
    return redirect(url_for("admin.edit_banner", banner_id=saved.id))


@bp.get("/banners")
def banners() -> str:
    return render_template("admin/banners.html", banners=banner_service.admin_list(get_db()))


@bp.get("/banners/new")
def new_banner() -> Response:
    form = {"title": "", "image_key": "", "link_url": "", "alt_text": "", "starts_at": None, "ends_at": None}
    form["is_active"] = True
    return _render_form(form=form, errors={})


@bp.post("/banners/new")
def create_banner() -> Response:
    return _save(None)


@bp.get("/banners/<int:banner_id>")
def edit_banner(banner_id: int) -> Response:
    banner = banner_service.admin_get(get_db(), banner_id)
    return _render_form(banner=banner, form=banner.model_dump(), errors={})


@bp.post("/banners/<int:banner_id>")
def update_banner(banner_id: int) -> Response:
    return _save(banner_id)


@bp.post("/banners/<int:banner_id>/delete")
def delete_banner(banner_id: int) -> Response:
    banner_service.delete(get_db(), banner_id)
    flash("배너를 삭제했습니다.", "success")
    return redirect(url_for("admin.banners"))


@bp.post("/banners/<int:banner_id>/move")
def move_banner(banner_id: int) -> Response | str:
    db = get_db()
    ids = [b.id for b in banner_service.admin_list(db)]
    if banner_id not in ids:
        raise ServiceError("not_found", "배너를 찾을 수 없습니다.")
    i = ids.index(banner_id)
    j = i - 1 if request.form.get("direction") == "up" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
        banner_service.reorder(db, BannerOrder(ids=ids))
    if is_htmx():
        return render_template("partials/admin_banner_rows.html", banners=banner_service.admin_list(db))
    return redirect(url_for("admin.banners"))
