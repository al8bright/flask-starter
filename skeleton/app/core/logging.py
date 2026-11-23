"""애플리케이션 로깅 설정 (ARCHITECTURE.md §9 감사 로그).

uvicorn 은 자기 로거(uvicorn.*)만 설정하므로, 별도 설정이 없으면 app.* 로거의 INFO 기록
(로그인 성공·세션 폐기 등 감사 로그 app.audit)은 출력되지 않고 사라진다. 여기서 app 로거에
표준 출력 핸들러를 한 번만 붙인다. 루트 로거는 건드리지 않는다 — uvicorn·pytest(caplog)의
로깅 구성과 충돌하지 않게 하고, 수집 시스템 연동은 이 함수만 바꾸면 되게 한다.
"""
import logging
import sys

APP_LOGGER = "app"
_HANDLER_NAME = "app-stdout"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str) -> None:
    """app 로거의 수준을 정하고 표준 출력 핸들러를 붙인다. 여러 번 호출해도 핸들러는 하나다."""
    logger = logging.getLogger(APP_LOGGER)
    logger.setLevel(level)
    if any(h.get_name() == _HANDLER_NAME for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
