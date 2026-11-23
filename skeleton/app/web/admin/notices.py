"""관리자 — 공지 작성·수정·삭제, 첨부, 본문 이미지 업로드.

본문은 HTML 이다. 저장 직전에 서비스 계층이 nh3 로 정화한다(core/sanitize.py) — 화면은 정화된 값만 |safe 로 출력한다.
본문은 편집기(static/js/editor/)가 쓰고, 이미지는 편집기가 /admin/editor/images 로 올린다(JSON).
JS 가 없으면 textarea 에 HTML 을 직접 쓰고, 이미지는 같은 경로로 올려 돌려받은 <img> 코드를 붙여 넣는다.
"""

from flask import Response, flash, jsonify, make_response, redirect, render_template, request, url_for

from app.config import get_settings
from app.dependencies import current_user, get_db
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_QUERY_LENGTH
from app.schemas.notice import NoticeWrite
from app.services import notice_service, upload_service
from app.services.exceptions import ServiceError
from app.web.accept import wants_json
from app.web.admin import bp
from app.web.files import attachment_response, read_upload
from app.web.forms import checkbox, parse_form
from app.web.htmx import is_htmx
from app.web.pagination import page_arg, page_links


def _form_values() -> dict:
    return {
        "title": request.form.get("title", ""),
        "body_html": request.form.get("body_html", ""),
        "is_pinned": checkbox(request.form.get("is_pinned")),
        "is_published": checkbox(request.form.get("is_published")),
    }


def _render_form(*, notice=None, form: dict, errors: dict, status: int = 200) -> Response:
    html = render_template(
        "admin/notice_form.html",
        notice=notice,
        form=form,
        errors=errors,
        max_image_mb=get_settings().max_image_upload_mb,
    )
    return make_response(html, status)


@bp.get("/notices")
def notices() -> str:
    q = (request.args.get("q") or "").strip()[:MAX_QUERY_LENGTH] or None
    result = notice_service.admin_list(get_db(), page=page_arg(), size=DEFAULT_PAGE_SIZE, q=q)
    return render_template(
        "admin/notices.html", result=result, q=q or "", pages=page_links(result, "admin.notices", q=q)
    )


@bp.get("/notices/new")
def new_notice() -> Response:
    return _render_form(form={"title": "", "body_html": "", "is_pinned": False, "is_published": False}, errors={})


@bp.post("/notices/new")
def create_notice() -> Response:
    form = _form_values()
    data, errors = parse_form(NoticeWrite, **form)
    if errors:
        return _render_form(form=form, errors=errors, status=422)
    actor = current_user()
    try:
        notice = notice_service.create(get_db(), author_id=actor.id, data=data)
    except ServiceError as e:
        return _render_form(form=form, errors={"body_html": e.message}, status=422)
    flash("공지를 만들었습니다. 첨부 파일은 아래에서 올리세요.", "success")
    return redirect(url_for("admin.edit_notice", notice_id=notice.id))


@bp.get("/notices/<int:notice_id>")
def edit_notice(notice_id: int) -> Response:
    notice = notice_service.admin_get(get_db(), notice_id)
    form = {
        "title": notice.title,
        "body_html": notice.body_html,
        "is_pinned": notice.is_pinned,
        "is_published": notice.is_published,
    }
    return _render_form(notice=notice, form=form, errors={})


@bp.post("/notices/<int:notice_id>")
def update_notice(notice_id: int) -> Response:
    db = get_db()
    form = _form_values()
    data, errors = parse_form(NoticeWrite, **form)
    if errors:
        return _render_form(notice=notice_service.admin_get(db, notice_id), form=form, errors=errors, status=422)
    try:
        notice_service.update_notice(db, notice_id, data)
    except ServiceError as e:
        if e.code != "empty_body":
            raise
        return _render_form(
            notice=notice_service.admin_get(db, notice_id), form=form, errors={"body_html": e.message}, status=422
        )
    flash("공지를 저장했습니다.", "success")
    return redirect(url_for("admin.edit_notice", notice_id=notice_id))


@bp.post("/notices/<int:notice_id>/delete")
def delete_notice(notice_id: int) -> Response:
    notice_service.delete(get_db(), notice_id)
    flash("공지를 삭제했습니다.", "success")
    return redirect(url_for("admin.notices"))


@bp.post("/notices/<int:notice_id>/attachments")
def add_attachment(notice_id: int) -> Response:
    data, filename = read_upload(request.files.get("file"), max_mb=get_settings().max_attachment_upload_mb)
    att = notice_service.add_attachment(get_db(), notice_id, data=data, filename=filename)
    flash(f"{att.original_name} 을(를) 첨부했습니다.", "success")
    return redirect(url_for("admin.edit_notice", notice_id=notice_id))


@bp.get("/notices/<int:notice_id>/attachments/<int:attachment_id>")
def download_attachment(notice_id: int, attachment_id: int) -> Response:
    """관리자 다운로드 — 게시 전(초안) 공지의 첨부도 받을 수 있다."""
    att, path = notice_service.attachment_file(get_db(), notice_id, attachment_id, published_only=False)
    return attachment_response(path, filename=att.original_name, content_type=att.content_type)


@bp.post("/notices/<int:notice_id>/attachments/<int:attachment_id>/delete")
def delete_attachment(notice_id: int, attachment_id: int) -> Response:
    notice_service.delete_attachment(get_db(), notice_id, attachment_id)
    flash("첨부를 삭제했습니다.", "success")
    return redirect(url_for("admin.edit_notice", notice_id=notice_id))


@bp.post("/editor/images")
def upload_editor_image() -> Response | str:
    data, _ = read_upload(request.files.get("file"), max_mb=get_settings().max_image_upload_mb)
    image = upload_service.save_image(data, category="editor")
    if wants_json():
        # 편집기(static/js/editor/upload.js) — 본문에 넣을 공개 URL 과 서버가 재인코딩한 실제 크기.
        response = jsonify(key=image.key, url=image.url, width=image.width, height=image.height)
        response.status_code = 201
        return response
    if is_htmx():
        return render_template("partials/editor_image.html", image=image)
    flash(f'본문에 붙여 넣을 코드: <img src="{image.url}" alt="">', "success")
    return redirect(url_for("admin.notices"))
