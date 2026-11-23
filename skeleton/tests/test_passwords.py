"""비밀번호 정책·bcrypt 72 bytes 경계·계정 존재 비노출 (ARCHITECTURE.md §9).

형제 FastAPI 템플릿의 test_auth.py·test_security.py·test_auth_sessions.py 에 있는 같은 검증을
Flask 화면(폼 POST) 기준으로 옮겼다. 서비스 함수는 공통 계층이라 그대로 호출한다.
"""

import pytest

from app.config import get_settings
from app.core.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    PASSWORD_MIN_LENGTH,
    dummy_password_hash,
    hash_password,
    validate_new_password,
    verify_password,
)
from app.dependencies import AUTH_COOKIE
from app.services import user_service
from app.services.exceptions import ServiceError
from tests.conftest import post_form

# 한글 25자 = UTF-8 75 bytes — 문자 수(25)는 작아도 bcrypt 상한(72 bytes)을 넘는다.
OVER_LIMIT_KOREAN = "비" * 25


def test_login_password_over_72_bytes_is_422(client):
    assert len(OVER_LIMIT_KOREAN.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES
    res = post_form(client, "/login", {"username": "admin", "password": OVER_LIMIT_KOREAN})
    assert res.status_code == 422
    assert f"{BCRYPT_MAX_PASSWORD_BYTES} bytes 이하" in res.get_data(as_text=True)
    assert client.get_cookie(AUTH_COOKIE) is None


def test_password_at_byte_limit_roundtrips_through_login(client, db_session):
    # 상한(72 bytes) 경계값은 저장도 되고 그 비밀번호로 로그인도 되어야 한다 — 쓰기/읽기 경로 일치.
    password = "a" * BCRYPT_MAX_PASSWORD_BYTES
    user_service.ensure_admin(db_session, password=password)
    res = post_form(client, "/login", {"username": "admin", "password": password})
    assert res.status_code == 302
    assert client.get_cookie(AUTH_COOKIE) is not None


def test_hash_password_rejects_over_72_bytes(db_session):
    # 저장 경로에서 거부하지 않으면 시드는 성공하고 로그인은 영구 422 가 되어 관리자가 잠긴다.
    with pytest.raises(ValueError):
        hash_password(OVER_LIMIT_KOREAN)
    with pytest.raises(ValueError):
        user_service.create_user(db_session, username="toolong", password=OVER_LIMIT_KOREAN)
    with pytest.raises(ValueError):
        user_service.ensure_admin(db_session, password=OVER_LIMIT_KOREAN)
    assert user_service.get_by_username(db_session, "toolong") is None


def test_verify_password_over_72_bytes_returns_false():
    # bcrypt 5 의 checkpw 는 72 bytes 초과에 ValueError — verify_password 는 예외 없이 False.
    limit = BCRYPT_MAX_PASSWORD_BYTES
    hashed = hash_password("a" * limit)
    assert verify_password("a" * limit, hashed) is True
    assert verify_password("a" * (limit + 1), hashed) is False


def test_validate_new_password_enforces_min_length():
    with pytest.raises(ValueError):
        validate_new_password("a" * (PASSWORD_MIN_LENGTH - 1))
    validate_new_password("a" * PASSWORD_MIN_LENGTH)  # 경계값은 통과


def test_create_user_and_ensure_admin_reject_short_password(db_session):
    short = "a" * (PASSWORD_MIN_LENGTH - 1)
    with pytest.raises(ValueError):
        user_service.create_user(db_session, username="shorty", password=short)
    with pytest.raises(ValueError):
        user_service.ensure_admin(db_session, password=short)
    assert user_service.get_by_username(db_session, "shorty") is None
    assert user_service.get_by_username(db_session, "admin") is None


def test_unknown_username_gets_same_response_as_wrong_password(client, normal_user):
    missing = post_form(client, "/login", {"username": "missing-user", "password": "pw123456"})
    wrong = post_form(client, "/login", {"username": normal_user.username, "password": "wrong-password"})
    assert missing.status_code == wrong.status_code == 401
    message = "아이디 또는 비밀번호가 올바르지 않습니다."
    assert message in missing.get_data(as_text=True)
    assert message in wrong.get_data(as_text=True)


def test_authenticate_verifies_password_once_for_unknown_user(db_session, monkeypatch):
    # 미존재 계정에서 bcrypt 검증을 건너뛰면 응답 시간으로 계정 존재 여부가 드러난다.
    real_verify = user_service.verify_password
    used_hashes: list[str] = []

    def counting_verify(plain: str, hashed: str) -> bool:
        used_hashes.append(hashed)
        return real_verify(plain, hashed)

    monkeypatch.setattr(user_service, "verify_password", counting_verify)
    with pytest.raises(ServiceError):
        user_service.authenticate(db_session, "ghost", "pw123456")
    assert used_hashes == [dummy_password_hash()]


def test_dummy_password_hash_uses_same_cost_as_real_hash():
    # 비용(rounds)이 실제 해시와 다르면 응답 시간 차이로 계정 존재가 드러난다 — 해시의 비용 필드로 고정한다.
    dummy = dummy_password_hash()
    real = hash_password("pw123456")
    assert dummy.split("$")[2] == real.split("$")[2] == f"{get_settings().bcrypt_rounds:02d}"
    assert verify_password("pw123456", dummy) is False
