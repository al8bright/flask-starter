"""Flask 공통 의존성 (ARCHITECTURE.md §6) — 단일 파일.

Flask 에는 FastAPI 의 Depends 가 없으므로 같은 역할을 요청 훅과 데코레이터로 둔다.

- get_db()            요청 단위 DB 세션 (요청이 끝나면 닫힌다)
- current_user()      DB 세션 쿠키로 확인한 현재 사용자 (없으면 None)
- login_required      로그인 사용자만 — 아니면 로그인 화면으로 보낸다
- admin_required      활성 관리자만 — 로그인했지만 관리자가 아니면 403

인증은 auth_sessions 행 하나 = 로그인 하나다 (§9). 쿠키에는 불투명 토큰("<session_id>.<secret>")만
담고 DB 에는 SHA-256 해시만 둔다. 요청마다 세션 행(존재·미폐기·미만료)과 사용자(활성)를 DB 에서
다시 읽으므로, 로그아웃·관리자 강제 폐기·비활성화·강등이 다음 요청부터 바로 반영된다.
"""

import hmac
from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, Response, abort, current_app, g, jsonify, redirect, request, url_for
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.security import hash_refresh_token, parse_session_id
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole
from app.services import session_service, user_service
from app.web.accept import wants_json

# 인증 쿠키 기본 이름. HTTPS(COOKIE_SECURE=true)에서는 __Host- 접두사를 붙인다 — auth_cookie_name().
AUTH_COOKIE = "__PROJECT_SNAKE___session"
AUTH_COOKIE_PATH = "/"
SECONDS_PER_DAY = 86400

_SESSION_FACTORY_KEY = "db_session_factory"


def auth_cookie_name() -> str:
    """실제 인증 쿠키 이름. __Host- 는 Secure·Path=/·Domain 없음 쿠키만 허용돼 형제 서브도메인의 쿠키 심기를 막는다."""
    return ("__Host-" if get_settings().cookie_secure else "") + AUTH_COOKIE


def init_app(app: Flask, session_factory: sessionmaker[Session]) -> None:
    app.extensions[_SESSION_FACTORY_KEY] = session_factory
    app.before_request(_load_current_user)
    app.teardown_appcontext(_close_db)
    app.context_processor(lambda: {"current_user": current_user()})


# ---------------------------------------------------------------------------
# DB 세션
# ---------------------------------------------------------------------------


def get_db() -> Session:
    """요청 단위 DB 세션. 같은 요청 안에서는 같은 세션을 돌려준다."""
    if "db" not in g:
        g.db = current_app.extensions[_SESSION_FACTORY_KEY]()
    return g.db


def _close_db(_exc: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# 현재 사용자
# ---------------------------------------------------------------------------


def find_active_session(db: Session, token: str | None) -> AuthSession | None:
    """쿠키 토큰으로 살아 있는 세션 행을 찾는다. 형식 오류·미존재·해시 불일치·폐기·만료면 None."""
    if not token:
        return None
    session_id = parse_session_id(token)
    if session_id is None:
        return None
    session = db.get(AuthSession, session_id)
    if session is None or session.revoked_at is not None or session_service.is_expired(session):
        return None
    if not hmac.compare_digest(session.refresh_token_hash, hash_refresh_token(token)):
        return None
    return session


def _load_current_user() -> None:
    g.current_user = None
    g.auth_session_id = None
    # 정적 파일·헬스 체크는 DB 를 열지 않는다.
    if request.endpoint in (None, "static") or request.path.startswith("/api/v1/health"):
        return
    token = request.cookies.get(auth_cookie_name())
    if not token:
        return
    db = get_db()
    session = find_active_session(db, token)
    if session is None:
        return
    user = user_service.get_by_id(db, session.user_id)
    if user is None or not user.is_active:
        return
    g.current_user = user
    g.auth_session_id = session.id


def current_user() -> User | None:
    return g.get("current_user")


def is_admin(user: User | None) -> bool:
    return user is not None and user.is_active and user.role == UserRole.ADMIN.value


def safe_next_path(raw: str | None) -> str | None:
    """로그인 후 돌아갈 경로 — 같은 사이트의 "/" 경로만 허용한다(열린 리다이렉트 차단)."""
    if not raw or not raw.startswith("/") or raw.startswith(("//", "/\\")):
        return None
    if any(ch.isspace() or ord(ch) < 0x20 for ch in raw):
        return None
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc:
        return None
    return raw


def _login_redirect() -> Response:
    target = url_for("auth.login", next=request.full_path.rstrip("?"))
    if request.headers.get("HX-Request") == "true":
        # htmx 요청에 302 를 주면 로그인 화면이 partial 자리에 끼워진다 — 전체 페이지 이동을 지시한다.
        return Response(status=401, headers={"HX-Redirect": target})
    if wants_json():
        # fetch(편집기 업로드)는 302 를 따라가 로그인 HTML 을 받게 된다 — JSON 401 로 알린다.
        response = jsonify(detail="로그인이 필요합니다.", code="http_401")
        response.status_code = 401
        return response
    return redirect(target)


def login_required[F: Callable[..., Any]](view: F) -> F:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if current_user() is None:
            return _login_redirect()
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def admin_required[F: Callable[..., Any]](view: F) -> F:
    """역할은 쿠키가 아니라 요청마다 DB 에서 읽는다 — 강등되면 다음 요청부터 바로 403 이다."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if user is None:
            return _login_redirect()
        if not is_admin(user):
            abort(403)
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 인증 쿠키
# ---------------------------------------------------------------------------


def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        auth_cookie_name(),
        token,
        max_age=settings.refresh_token_expire_days * SECONDS_PER_DAY,
        path=AUTH_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="Lax",
    )


def clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        auth_cookie_name(), path=AUTH_COOKIE_PATH, secure=settings.cookie_secure, httponly=True, samesite="Lax"
    )
