"""리버스 프록시 신뢰 (ARCHITECTURE.md §5, §17) — Flask 웹 계층 전용 설정.

앞단 프록시(nginx 등)가 HTTPS 를 끝내면 앱에는 HTTP 로 들어온다. 설정한 단계 수만큼 X-Forwarded-* 를 믿어
request.is_secure·host·remote_addr 가 원래 요청을 가리키게 한다(werkzeug ProxyFix).
Flask-WTF 의 HTTPS Referer 엄격 검사(WTF_CSRF_SSL_STRICT)는 request.is_secure 일 때만 동작하므로,
프록시 뒤에서 이 값이 0 이면 그 검사가 꺼진다.

기본 0 은 헤더를 따르지 않는다 — 프록시 없이 앱을 바로 노출할 때 클라이언트가 헤더를 위조할 수 있기 때문이다.

이 키는 공통 계층(app/config.py — 형제 템플릿과 같은 파일)에 두지 않는다. 같은 .env 를 읽는 웹 계층 전용 설정이다.
"""

import logging

from flask import Flask
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import ENV_FILE

logger = logging.getLogger(__name__)

MAX_PROXY_HOPS = 3


class ProxySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # 앞단 리버스 프록시 단계 수. nginx 한 겹이면 1.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=MAX_PROXY_HOPS)


def apply_proxy_fix(app: Flask, *, cookie_secure: bool) -> int:
    """설정한 단계 수만큼 X-Forwarded-For·Proto·Host 를 믿는다. 적용한 단계 수를 돌려준다.

    값이 범위를 벗어나면 pydantic ValidationError 로 기동을 막는다.
    """
    hops = ProxySettings().trusted_proxy_hops
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)  # type: ignore[method-assign]
    elif cookie_secure:
        logger.warning(
            "COOKIE_SECURE=true 인데 TRUSTED_PROXY_HOPS=0 입니다. HTTPS 를 끝내는 프록시 뒤라면 "
            ".env 에 TRUSTED_PROXY_HOPS=1 을 두세요 — 아니면 CSRF 의 HTTPS Referer 검사가 동작하지 않습니다."
        )
    return hops
