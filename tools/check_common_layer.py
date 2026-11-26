"""공통 계층 동일성 검사 — skeleton/ 의 공통 파일이 원본(fastapi-react-pg-starter)과 바이트 단위로 같은지 확인한다.

공통 계층은 원본 → 이 저장소로 단방향 추적한다(AGENTS.md 「공통 계층」). 이 저장소에서 공통 파일을 고쳤거나
원본이 바뀌었는데 다시 복사하지 않았으면 차이가 난다. 원본이 비공개 저장소라 Template CI 에서는 돌리지 않는다.
읽기 전용이며 표준 라이브러리만 쓴다.

    python tools/check_common_layer.py                      # 원본 기본 위치: 이 저장소 옆 ../fastapi-react-pg-starter
    python tools/check_common_layer.py --source <원본 저장소>

종료 코드: 0 같음, 1 차이 있음, 2 원본을 찾지 못함.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKELETON = ROOT / "skeleton"
DEFAULT_SOURCE = ROOT.parent / "fastapi-react-pg-starter"
SOURCE_SUBDIR = Path("skeleton") / "backend"

# 원본 skeleton/backend/ 와 이 저장소 skeleton/ 에서 같은 상대 경로를 갖는 공통 계층.
# AGENTS.md 「공통 계층」의 대상 목록과 같게 유지한다.
COMMON_PATHS = (
    "app/__init__.py",
    "app/config.py",
    "app/cli.py",
    "app/core",
    "app/db",
    "app/models",
    "app/schemas",
    "app/services",
    "alembic",
    "alembic.ini",
    "tests/media_factory.py",
    "tests/test_cli.py",
    "tests/test_config.py",
    "tests/test_login_throttle.py",
    "tests/test_sanitize.py",
    "tests/test_storage.py",
)
SKIP_DIRS = {"__pycache__"}


def list_files(base: Path, rel: str) -> set[str]:
    """base/rel 이 파일이면 그 하나, 폴더면 아래 모든 파일의 base 기준 상대 경로(캐시 폴더 제외)."""
    target = base / rel
    if target.is_file():
        return {rel}
    if not target.is_dir():
        return set()
    return {
        p.relative_to(base).as_posix()
        for p in target.rglob("*")
        if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(base).parts)
    }


def read_normalized(path: Path) -> bytes:
    """줄바꿈만 LF 로 맞춘 바이트 — Windows 작업 트리의 CRLF 변환을 차이로 세지 않는다."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def compare(skeleton: Path, source: Path, paths: tuple[str, ...] = COMMON_PATHS) -> dict[str, list[str]]:
    """{"different": [...], "only_here": [...], "only_source": [...]} — 모두 비면 동일하다."""
    result: dict[str, list[str]] = {"different": [], "only_here": [], "only_source": []}
    for rel in paths:
        here, there = list_files(skeleton, rel), list_files(source, rel)
        result["only_here"] += sorted(here - there)
        result["only_source"] += sorted(there - here)
        same_paths = here & there
        result["different"] += sorted(
            f for f in same_paths if read_normalized(skeleton / f) != read_normalized(source / f)
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="skeleton/ 의 공통 계층이 원본 저장소와 같은지 검사한다.")
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE, help="원본 저장소 루트(fastapi-react-pg-starter)"
    )
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    source = args.source / SOURCE_SUBDIR
    if not source.is_dir():
        print(f"원본을 찾지 못하였다: {source} — --source 로 원본 저장소 루트를 지정한다.", file=sys.stderr)
        return 2
    result = compare(SKELETON, source)
    labels = {"different": "내용 다름", "only_here": "이 저장소에만 있음", "only_source": "원본에만 있음"}
    total = 0
    for key, label in labels.items():
        for rel in result[key]:
            print(f"{label}: {rel}")
            total += 1
    if total:
        print(f"\n공통 계층 차이 {total}건 — 원본에서 다시 복사하거나 원본 저장소에서 고친다(AGENTS.md 「공통 계층」).")
        return 1
    print(f"공통 계층 동일 (원본: {source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
