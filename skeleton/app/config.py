"""애플리케이션 설정 (ARCHITECTURE.md §5).

설정은 OS 무관하게 .env 로 주입한다. 접근은 항상 get_settings() 로 한다.
"""
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_ROOT / ".env"

# 공개된 기본 서명키 — 개발·alembic 편의용이다. 이 값이 그대로 쓰이면 main.py 가 개발에서는 경고하고
# APP_ENV=production 에서는 기동을 거부한다(운영 키는 32 bytes 이상이어야 한다).
DEFAULT_SECRET_KEY = "change-me-in-production-use-32-bytes"
MIN_PRODUCTION_SECRET_BYTES = 32
MIN_PRODUCTION_BCRYPT_ROUNDS = 12


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 실행 환경 — "production" 이면 안전하지 않은 기본값으로 기동하지 않는다 (main.py 의 fail-fast).
    # 허용 값 외(예: "prod" 오타)는 설정 검증에서 기동을 거부한다 — 오타로 운영 보호 장치가
    # 조용히 꺼지는 경로(fail-open)를 막는다.
    app_env: Literal["development", "test", "production"] = "development"

    # 로그 수준 — app.* 로거(감사 로그 app.audit 포함)에 적용한다 (app/core/logging.py).
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # DB
    database_url: str | None = None

    # JWT / 세션 — access 는 짧게(탈취 창 축소), 갱신은 DB 세션 기반 refresh 토큰이 담당한다.
    secret_key: str = DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    # bcrypt 비용 — 운영 하한은 12 다(APP_ENV=production 에서 미만이면 기동 거부). 테스트만 낮춘다.
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    # 로그인 시도 제한 — (아이디, 접속 IP)별 실패가 max 이상이면 lockout 분 동안 429 로 거부한다.
    # 아이디 전체(모든 IP 합산) 상한은 max × user_service.GLOBAL_FAILURE_MULTIPLIER 다.
    login_max_failures: int = 5
    login_lockout_minutes: int = 15

    # refresh 토큰 전달 방식 (§9) — 같은 백엔드 코드가 두 종류의 프론트엔드를 섬긴다.
    # - "cookie": 백엔드가 httpOnly 쿠키(path=/api/v1/auth)로 직접 심는다. 브라우저 SPA 용이며
    #             refresh 토큰이 JS 에 노출되지 않는다. 안전한 쪽이 기본값이다.
    # - "body":   요청/응답 JSON 본문으로 주고받는다. BFF(예: Next.js 서버)가 받아 자기 httpOnly 쿠키에
    #             보관하는 구조 전용 — 브라우저 JS 가 직접 받는 구성에서는 쓰지 않는다.
    refresh_token_transport: Literal["cookie", "body"] = "cookie"
    # refresh 쿠키의 Secure 속성 — HTTPS 운영에서는 반드시 true. production + cookie 모드에서
    # false 면 main.py 가 기동을 거부한다(평문 HTTP 로 refresh 토큰이 새는 구성을 막는다).
    cookie_secure: bool = False

    # 시각대 (ARCHITECTURE.md §10 KST 단일 기준)
    tz: str = "Asia/Seoul"

    # 초기 시드 — 기본은 꺼져 있다. 개발 환경에서만 .env 로 켠다(스캐폴드가 무작위 비밀번호와 함께 켜준다).
    # ⛔ 비밀번호에 기본값을 두지 않는다. 두면 설정을 빠뜨린 모든 배포가 같은 자격증명을 갖게 된다.
    seed_default_admin: bool = False
    default_admin_password: str | None = None

    # CORS
    cors_origins: str = "http://localhost:3000"

    # URL
    frontend_url: str = "http://localhost:3000"
    backend_public_url: str = "http://localhost:8000"

    # 업로드 저장소 (app/core/storage.py) — 상대 경로는 backend 디렉터리 기준이다.
    # public/ 아래만 /uploads/public 으로 정적 서빙되고, private/(공지 첨부)는 API 로만 내려간다.
    upload_dir: Path = BACKEND_ROOT / "uploads"
    # 공개 파일 URL 접두사. 비우면 응답 URL 이 루트 상대 경로(/uploads/public/...)다 — 프론트엔드가
    # 백엔드와 같은 오리진(또는 /uploads 프록시)일 때. 브라우저가 백엔드를 다른 오리진으로 직접 부르거나
    # BFF 뒤에 있으면 백엔드의 공개 주소(예: http://localhost:8000)를 넣는다.
    public_files_base_url: str = ""
    # 업로드 크기 상한(MB) — 이미지(에디터·배너)와 공지 첨부.
    max_image_upload_mb: int = 5
    max_attachment_upload_mb: int = 20

    @field_validator("upload_dir")
    @classmethod
    def _resolve_upload_dir(cls, v: Path) -> Path:
        # 실행 디렉터리(cwd)에 따라 저장 위치가 달라지지 않게 backend 기준 절대 경로로 고정한다.
        return v if v.is_absolute() else BACKEND_ROOT / v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def _apply_timezone(tz: str) -> None:
    """프로세스 시각대를 맞춘다 (§10). 앱 시각(core.security.now)과 로그 시각은 이 함수와 무관하게 KST 다.

    - Unix: .env 의 TZ 를 프로세스에 적용한다(tzset) — 외부 라이브러리·하위 프로세스의 로컬 시각도 맞춘다.
      .env 의 TZ 가 셸 환경변수보다 우선한다(§5 셸 환경변수 의존 금지) — setdefault 가 아니라 대입이다.
    - Windows(tzset 없음): C 런타임(MSVC CRT)이 IANA 이름(Asia/Seoul)을 해석하지 못해 UTC 로 보므로
      프로세스 환경에 넣지 않는다. 넣으면 OS 시각대가 서울이어도 로컬 시각이 UTC 로 바뀐다.
    """
    if not hasattr(time, "tzset"):
        return
    os.environ["TZ"] = tz
    time.tzset()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _apply_timezone(settings.tz)
    return settings
