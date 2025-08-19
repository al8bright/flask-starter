"""
유틸리티 헬퍼 함수들
"""
import getpass
from pathlib import Path

HERE = Path.cwd()


def info(msg: str) -> None:
    """정보 메시지 출력"""
    print(f"\033[96m[INFO]\033[0m {msg}")


def warn(msg: str) -> None:
    """경고 메시지 출력"""
    print(f"\033[93m[WARN]\033[0m {msg}")


def err(msg: str) -> None:
    """에러 메시지 출력"""
    print(f"\033[91m[ERROR]\033[0m {msg}")


def ask(prompt: str, default: str | None = None) -> str:
    """사용자 입력 요청"""
    p = f"{prompt.strip()}" + (f" [{default}]" if default else "") + ": "
    s = input(p).strip()
    return s or (default or "")


def ask_secret(prompt_text: str) -> str:
    """비밀번호 입력 요청"""
    return getpass.getpass(prompt_text + ": ")


def choose(title: str, options: list[str], default_index: int = 0) -> str:
    """선택 옵션 제공"""
    print(title)
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    while True:
        raw = input(f"Select 1-{len(options)} [{default_index+1}]: ").strip()
        if not raw:
            return options[default_index]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        print("Invalid selection. Try again.")
