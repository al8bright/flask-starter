"""공개 화면·첨부 다운로드·공개 업로드 서빙 (ARCHITECTURE.md §4, §13)."""

import pytest

from app.core import storage
from app.schemas.notice import NoticeWrite
from app.services import notice_service
from tests.media_factory import image_bytes


@pytest.fixture
def notices(db_session, admin_user):
    published = notice_service.create(
        db_session,
        author_id=admin_user.id,
        data=NoticeWrite(
            title="서버 점검 안내", body_html="<p>점검합니다</p><script>alert(1)</script>", is_published=True
        ),
    )
    draft = notice_service.create(
        db_session, author_id=admin_user.id, data=NoticeWrite(title="초안 공지", body_html="<p>비공개</p>")
    )
    return published, draft


def test_home_lists_published_notices(client, notices):
    html = client.get("/").get_data(as_text=True)
    assert "서버 점검 안내" in html and "초안 공지" not in html


def test_notice_list_full_page_and_htmx_partial(client, notices):
    full = client.get("/notices?q=점검")
    assert full.status_code == 200
    assert "<html" in full.get_data(as_text=True)

    partial = client.get("/notices?q=점검", headers={"HX-Request": "true"})
    body = partial.get_data(as_text=True)
    assert "<html" not in body and 'id="notice-list"' in body
    assert "서버 점검 안내" in body
    assert "HX-Request" in partial.headers["Vary"]


def test_htmx_history_restore_gets_full_page(client, notices):
    res = client.get("/notices", headers={"HX-Request": "true", "HX-History-Restore-Request": "true"})
    assert "<html" in res.get_data(as_text=True)


def test_notice_list_ignores_bad_page(client, notices):
    assert client.get("/notices?page=abc").status_code == 200


def test_notice_detail_renders_sanitized_body(client, notices):
    published, _ = notices
    html = client.get(f"/notices/{published.id}").get_data(as_text=True)
    assert "<p>점검합니다</p>" in html
    assert "alert(1)" not in html


def test_draft_notice_is_404(client, notices):
    _, draft = notices
    res = client.get(f"/notices/{draft.id}")
    assert res.status_code == 404
    assert "<html" in res.get_data(as_text=True)


def test_attachment_download_published_only(client, db_session, notices):
    published, draft = notices
    att = notice_service.add_attachment(db_session, published.id, data=b"hello", filename="안내문.txt")
    res = client.get(att.download_url)
    assert res.status_code == 200 and res.data == b"hello"
    assert res.headers["Content-Disposition"].startswith("attachment;")
    assert "filename*=UTF-8''" in res.headers["Content-Disposition"]
    assert res.headers["Cache-Control"] == "private, no-store"

    draft_att = notice_service.add_attachment(db_session, draft.id, data=b"secret", filename="a.txt")
    missing = client.get(draft_att.download_url)
    assert missing.status_code == 404
    assert missing.get_json()["code"] == "not_found"


def test_public_upload_is_served_and_private_is_not(client):
    stored = storage.save_image(image_bytes("PNG"), category="editor")
    res = client.get(storage.public_url(stored.key))
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "public, max-age=31536000, immutable"

    attachment = storage.save_attachment(b"secret", "a.txt")
    assert client.get(f"/uploads/{attachment.key}").status_code == 404
    assert client.get(f"/uploads/public/../{attachment.key}").status_code == 404


def test_health(client):
    assert client.get("/api/v1/health").get_json() == {"status": "ok"}


def test_unknown_api_path_is_json_404(client):
    res = client.get("/api/v1/nope")
    assert res.status_code == 404 and res.get_json()["code"] == "http_404"


def test_unknown_page_is_html_404(client):
    res = client.get("/nope")
    assert res.status_code == 404 and "페이지를 찾을 수 없습니다." in res.get_data(as_text=True)


def test_method_not_allowed_keeps_allow_header(client):
    res = client.put("/notices")
    assert res.status_code == 405
    assert "GET" in res.headers["Allow"]
