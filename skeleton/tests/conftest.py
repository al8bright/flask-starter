"""테스트 공통 픽스처 (ARCHITECTURE.md §12).

DB 는 테스트마다 임시 SQLite 파일을 쓰고, 앱은 create_app(session_factory=...) 로 그 DB 에 붙인다.
create_all 은 테스트에서만 허용된다 (§11 예외).

요청은 운영과 같이 **요청마다 새 세션**을 열고 닫는다. 테스트의 db_session 을 요청에 그대로 넘기면
커밋하지 않은 변경도 다음 요청·단언에서 보여 commit() 누락을 잡지 못한다. 요청 전에는 db_session 의
열린 트랜잭션(SQLite 쓰기 잠금)을 닫고, 요청 뒤에는 캐시를 만료해 단언이 실제로 커밋된 값을 읽게 한다.

CSRF 보호는 테스트에서도 켜 둔다 — 폼 POST 는 post_form() 으로 토큰을 실어 보낸다.
"""

import os
import re

# app 모듈 임포트 전에 주입한다.
# - DATABASE_URL: 엔진이 fail-fast 하므로(app/db/engine.py) 임포트용 최소값. 실제 쿼리는 테스트 세션 팩토리가 담당.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-0123456789abcdef")

# 아래는 setdefault 가 아니라 대입이다 — 개발자의 .env 값이 새어 들어와 테스트가 흔들리지 않게 한다.
os.environ["APP_ENV"] = "test"
# 기본 관리자 시드는 끈다 — 시드 동작은 test_startup.py 가 명시적으로 켜서 검증한다.
os.environ["SEED_DEFAULT_ADMIN"] = "false"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "admin123"
os.environ["COOKIE_SECURE"] = "false"
os.environ["PUBLIC_FILES_BASE_URL"] = ""
os.environ["MAX_IMAGE_UPLOAD_MB"] = "5"
os.environ["MAX_ATTACHMENT_UPLOAD_MB"] = "20"
# bcrypt 비용을 최소(4)로 낮춘다 — 운영 비용(12)이면 로그인 픽스처가 실행 시간의 대부분을 차지한다.
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from flask import Flask  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SESSION_OPTIONS  # noqa: E402
from app.main import create_app  # noqa: E402

CSRF_RE = re.compile(r'"X-CSRFToken": "([^"]+)"')

ADMIN_PASSWORD = "admin-pass-123"
USER_PASSWORD = "user-pass-123"


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    """업로드 저장소를 테스트별 임시 디렉터리로 돌린다 — 테스트가 저장소(uploads/)에 파일을 남기지 않는다."""
    path = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(path))
    get_settings.cache_clear()
    return path


@pytest.fixture
def db_session_factory(tmp_path):
    """테스트 엔진에 바인딩된 세션 팩토리 (운영 SessionLocal 의 테스트 대역).

    in-memory(StaticPool)는 연결 하나를 모든 세션이 공유해 트랜잭션 경계가 운영과 달라진다.
    세션 옵션은 운영과 같아야 한다(SESSION_OPTIONS).
    """
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield sessionmaker(bind=engine, **SESSION_OPTIONS)
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session(db_session_factory):
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def flask_app(db_session_factory, db_session) -> Flask:
    flask_app = create_app(session_factory=db_session_factory)
    flask_app.config["TESTING"] = True

    # 등록 순서상 앱의 before_request(현재 사용자 로드)보다 먼저 돌도록 맨 앞에 넣는다.
    flask_app.before_request_funcs.setdefault(None, []).insert(0, db_session.commit)

    @flask_app.teardown_request
    def _expire_test_session(_exc):
        db_session.expire_all()

    return flask_app


@pytest.fixture
def client(flask_app) -> FlaskClient:
    return flask_app.test_client()


def csrf_token(client: FlaskClient) -> str:
    """현재 클라이언트 세션의 CSRF 토큰 — 모든 페이지 <body hx-headers> 에 들어 있다."""
    res = client.get("/")
    match = CSRF_RE.search(res.get_data(as_text=True))
    assert match, "CSRF 토큰을 찾지 못했습니다."
    return match.group(1)


def post_form(client: FlaskClient, url: str, data: dict | None = None, *, htmx: bool = False, **kwargs):
    """CSRF 토큰을 실은 폼 POST. htmx=True 면 htmx 요청 헤더를 붙인다."""
    payload = {"csrf_token": csrf_token(client), **(data or {})}
    headers = kwargs.pop("headers", {})
    if htmx:
        headers["HX-Request"] = "true"
    return client.post(url, data=payload, headers=headers, **kwargs)


def login(client: FlaskClient, username: str, password: str):
    res = post_form(client, "/login", {"username": username, "password": password})
    assert res.status_code == 302, res.get_data(as_text=True)
    return res


@pytest.fixture
def admin_user(db_session):
    from app.models.user import UserRole
    from app.services import user_service

    return user_service.create_user(db_session, username="root", password=ADMIN_PASSWORD, role=UserRole.ADMIN)


@pytest.fixture
def normal_user(db_session):
    from app.services import user_service

    return user_service.create_user(db_session, username="member", password=USER_PASSWORD)


@pytest.fixture
def admin_client(client, admin_user) -> FlaskClient:
    """관리자로 로그인한 클라이언트 (실제 로그인 — 세션 쿠키 검사까지 그대로 탄다)."""
    login(client, admin_user.username, ADMIN_PASSWORD)
    return client


@pytest.fixture
def user_client(client, normal_user) -> FlaskClient:
    login(client, normal_user.username, USER_PASSWORD)
    return client
