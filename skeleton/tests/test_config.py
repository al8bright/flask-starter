"""설정/시각대 테스트 (ARCHITECTURE.md §5, §10)."""
import logging
import os
import time
from datetime import UTC, datetime, timedelta

from app import config
from app.core.security import KST, now


def _utc_naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_now_is_kst_regardless_of_process_timezone(monkeypatch):
    # §10 KST 는 OS·프로세스 시각대와 무관하다 — 프로세스를 UTC 로 돌려도 now() 는 UTC+9 다.
    # Unix 는 tzset 으로 프로세스 시각대를 실제로 UTC 로 바꿔 본다. Windows 는 실행 중에 바꿀 수 없으므로
    # OS 시각대 그대로 검사한다(CI 의 Ubuntu·macOS 는 기본 시각대가 UTC 다).
    if hasattr(time, "tzset"):
        monkeypatch.setenv("TZ", "UTC")
        time.tzset()
    try:
        before = _utc_naive_now() + timedelta(hours=9)
        value = now()
        after = _utc_naive_now() + timedelta(hours=9)
    finally:
        monkeypatch.undo()
        if hasattr(time, "tzset"):
            time.tzset()
    assert value.tzinfo is None
    assert before <= value <= after


def test_kst_is_fixed_utc_plus_9():
    assert KST.utcoffset(None) == timedelta(hours=9)
    assert datetime(2026, 10, 2, tzinfo=UTC).astimezone(KST).replace(tzinfo=None) == datetime(2026, 10, 2, 9, 0)


def test_apply_timezone_overwrites_preexisting_tz_on_unix(monkeypatch):
    # .env 의 TZ 가 셸 환경변수보다 우선해야 한다 (§5 셸 환경변수 의존 금지) — setdefault 가 아니다.
    calls: list[str] = []
    monkeypatch.setenv("TZ", "America/New_York")
    monkeypatch.setattr(time, "tzset", lambda: calls.append(os.environ["TZ"]), raising=False)
    config._apply_timezone("Asia/Seoul")
    assert os.environ["TZ"] == "Asia/Seoul"
    assert calls == ["Asia/Seoul"]


def test_apply_timezone_does_not_inject_iana_name_on_windows(monkeypatch):
    # Windows(tzset 없음)의 C 런타임은 IANA 이름을 해석하지 못해 TZ=Asia/Seoul 을 UTC 로 본다 —
    # 프로세스 환경에 넣으면 OS 시각대가 서울이어도 로컬 시각이 UTC 로 바뀐다.
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.delattr(time, "tzset", raising=False)
    config._apply_timezone("Asia/Seoul")
    assert "TZ" not in os.environ


def test_log_timestamps_are_kst():
    from app.core.logging import kst_formatter

    record = logging.makeLogRecord({"created": 0, "msecs": 0})
    assert kst_formatter().formatTime(record).startswith("1970-01-01 09:00:00")


def test_app_env_rejects_unknown_value(monkeypatch):
    # "prod" 같은 오타가 development 로 취급되면 운영 보호 장치(기동 거부)가 조용히 꺼진다 — fail-closed.
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("APP_ENV", "prod")
    with pytest.raises(ValidationError):
        config.Settings(_env_file=None)


def test_configure_logging_attaches_single_handler_to_app_logger():
    from app.core.logging import APP_LOGGER, configure_logging

    configure_logging("INFO")
    configure_logging("INFO")
    logger = logging.getLogger(APP_LOGGER)
    assert logger.level == logging.INFO
    assert sum(1 for h in logger.handlers if h.get_name() == "app-stdout") == 1
    # 감사 로그(app.audit)의 INFO 가 출력 대상이 된다.
    assert logging.getLogger("app.audit").isEnabledFor(logging.INFO)
