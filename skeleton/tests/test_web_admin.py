"""관리자 화면 — 공지·첨부·배너·사용자 (ARCHITECTURE.md §4, §13)."""

import io

from sqlalchemy import select

from app.models.banner import Banner
from app.models.notice import Notice
from app.schemas.banner import BannerWrite
from app.services import banner_service, upload_service
from tests.conftest import post_form
from tests.media_factory import image_bytes


def test_dashboard(admin_client):
    res = admin_client.get("/admin/")
    assert res.status_code == 200
    assert "대시보드" in res.get_data(as_text=True)
    assert res.headers["Cache-Control"] == "private, no-store"


def test_admin_pages_render(admin_client):
    for path in (
        "/admin/users",
        "/admin/sessions",
        "/admin/notices",
        "/admin/notices/new",
        "/admin/banners",
        "/admin/banners/new",
    ):
        assert admin_client.get(path).status_code == 200, path


# ---------------------------------------------------------------------------
# 공지
# ---------------------------------------------------------------------------


def test_create_notice_sanitizes_and_redirects(admin_client, db_session):
    res = post_form(
        admin_client,
        "/admin/notices/new",
        {"title": "  새 소식  ", "body_html": '<p onclick="x()">본문</p>', "is_published": "on"},
    )
    assert res.status_code == 302
    notice = db_session.execute(select(Notice)).scalar_one()
    assert notice.title == "새 소식" and notice.is_published and not notice.is_pinned
    assert notice.body_html == "<p>본문</p>"
    assert res.headers["Location"] == f"/admin/notices/{notice.id}"


def test_create_notice_validation_errors_rerender_form(admin_client, db_session):
    res = post_form(admin_client, "/admin/notices/new", {"title": " ", "body_html": "<p>x</p>"})
    assert res.status_code == 422
    assert "제목을 입력하세요." in res.get_data(as_text=True)
    assert db_session.execute(select(Notice)).first() is None


def test_create_notice_empty_body_is_form_error(admin_client):
    res = post_form(admin_client, "/admin/notices/new", {"title": "제목", "body_html": "<script>x</script>"})
    assert res.status_code == 422
    assert "본문을 입력하세요." in res.get_data(as_text=True)


def test_update_and_delete_notice_with_attachment(admin_client, db_session):
    post_form(admin_client, "/admin/notices/new", {"title": "원래", "body_html": "<p>a</p>"})
    notice = db_session.execute(select(Notice)).scalar_one()

    res = post_form(
        admin_client, f"/admin/notices/{notice.id}", {"title": "바뀜", "body_html": "<p>b</p>", "is_pinned": "on"}
    )
    assert res.status_code == 302
    db_session.refresh(notice)
    assert notice.title == "바뀜" and notice.is_pinned and not notice.is_published

    res = post_form(
        admin_client,
        f"/admin/notices/{notice.id}/attachments",
        {"file": (io.BytesIO(b"pdf-bytes"), "계획서.pdf")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 302
    db_session.refresh(notice)
    att = notice.attachments[0]
    # 초안 공지의 첨부도 관리자 경로로는 받을 수 있다.
    assert admin_client.get(f"/admin/notices/{notice.id}/attachments/{att.id}").data == b"pdf-bytes"

    assert post_form(admin_client, f"/admin/notices/{notice.id}/delete").status_code == 302
    assert db_session.execute(select(Notice)).first() is None


def test_attachment_rejects_unsupported_type(admin_client, db_session):
    post_form(admin_client, "/admin/notices/new", {"title": "t", "body_html": "<p>a</p>"})
    notice = db_session.execute(select(Notice)).scalar_one()
    res = post_form(
        admin_client,
        f"/admin/notices/{notice.id}/attachments",
        {"file": (io.BytesIO(b"MZ"), "run.exe")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 422


def test_editor_image_upload_htmx_returns_snippet(admin_client):
    res = post_form(
        admin_client,
        "/admin/editor/images",
        {"file": (io.BytesIO(image_bytes("PNG")), "a.png")},
        content_type="multipart/form-data",
        htmx=True,
    )
    assert res.status_code == 200
    assert '&lt;img src="/uploads/public/editor/' in res.get_data(as_text=True)


def test_htmx_service_error_is_retargeted_to_alerts(admin_client):
    res = post_form(
        admin_client,
        "/admin/editor/images",
        {"file": (io.BytesIO(b"not an image"), "a.png")},
        content_type="multipart/form-data",
        htmx=True,
    )
    assert res.status_code == 422
    assert res.headers["HX-Retarget"] == "#alerts"
    assert 'role="alert"' in res.get_data(as_text=True)


# ---------------------------------------------------------------------------
# 배너
# ---------------------------------------------------------------------------


def _banner_form(**overrides):
    data = {
        "title": "봄 이벤트",
        "alt_text": "봄",
        "link_url": "/notices",
        "is_active": "on",
        "starts_at": "",
        "ends_at": "",
    }
    data.update(overrides)
    return data


def test_create_banner_with_image(admin_client, db_session):
    data = _banner_form(image=(io.BytesIO(image_bytes("PNG")), "b.png"))
    res = post_form(admin_client, "/admin/banners/new", data, content_type="multipart/form-data")
    assert res.status_code == 302, res.get_data(as_text=True)
    banner = db_session.execute(select(Banner)).scalar_one()
    assert banner.title == "봄 이벤트" and banner.image_key.startswith("public/banners/")


def test_create_banner_requires_image(admin_client):
    res = post_form(admin_client, "/admin/banners/new", _banner_form(), content_type="multipart/form-data")
    assert res.status_code == 422
    assert "배너 이미지를 선택하세요." in res.get_data(as_text=True)


def test_banner_validation_error_does_not_store_image(admin_client, upload_dir):
    data = _banner_form(link_url="javascript:alert(1)", image=(io.BytesIO(image_bytes("PNG")), "b.png"))
    res = post_form(admin_client, "/admin/banners/new", data, content_type="multipart/form-data")
    assert res.status_code == 422
    assert not list((upload_dir / "public").rglob("*.png"))


def test_banner_window_validation(admin_client):
    data = _banner_form(
        starts_at="2026-05-02T10:00", ends_at="2026-05-01T10:00", image=(io.BytesIO(image_bytes("PNG")), "b.png")
    )
    res = post_form(admin_client, "/admin/banners/new", data, content_type="multipart/form-data")
    assert res.status_code == 422
    assert "종료 시각은 시작 시각보다 뒤여야 합니다." in res.get_data(as_text=True)


def test_update_banner_keeps_existing_image(admin_client, db_session):
    key = upload_service.save_image(image_bytes("PNG"), category="banners").key
    banner = banner_service.create(db_session, BannerWrite(title="a", image_key=key))
    res = post_form(
        admin_client, f"/admin/banners/{banner.id}", _banner_form(title="b"), content_type="multipart/form-data"
    )
    assert res.status_code == 302
    row = db_session.get(Banner, banner.id)
    assert row.title == "b" and row.image_key == key


def test_move_banner_htmx_returns_rows(admin_client, db_session):
    ids = []
    for title in ("first", "second"):
        key = upload_service.save_image(image_bytes("PNG"), category="banners").key
        ids.append(banner_service.create(db_session, BannerWrite(title=title, image_key=key)).id)
    res = post_form(admin_client, f"/admin/banners/{ids[1]}/move", {"direction": "up"}, htmx=True)
    body = res.get_data(as_text=True)
    assert res.status_code == 200 and body.lstrip().startswith("{#") is False and 'id="banner-rows"' in body
    assert body.index("second") < body.index("first")
    assert [b.id for b in banner_service.admin_list(db_session)] == [ids[1], ids[0]]


# ---------------------------------------------------------------------------
# 사용자
# ---------------------------------------------------------------------------


def test_update_user_htmx_returns_row(admin_client, normal_user):
    res = post_form(admin_client, f"/admin/users/{normal_user.id}", {"role": "admin", "is_active": "on"}, htmx=True)
    body = res.get_data(as_text=True)
    assert res.status_code == 200
    assert body.strip().startswith(f'<tr id="user-{normal_user.id}"') and "저장됨" in body


def test_update_user_without_htmx_redirects(admin_client, db_session, normal_user):
    res = post_form(admin_client, f"/admin/users/{normal_user.id}", {"role": "user"})
    assert res.status_code == 302
    db_session.refresh(normal_user)
    assert normal_user.is_active is False  # 체크박스가 없으면 비활성


def test_cannot_demote_self(admin_client, admin_user):
    res = post_form(admin_client, f"/admin/users/{admin_user.id}", {"role": "user", "is_active": "on"}, htmx=True)
    assert res.status_code == 409
    assert res.headers["HX-Retarget"] == "#alerts"


def test_csrf_required_for_admin_post(admin_client, normal_user):
    res = admin_client.post(f"/admin/users/{normal_user.id}", data={"role": "admin"})
    assert res.status_code == 400
