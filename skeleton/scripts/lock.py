"""requirements.lock 생성·검사 — 전이 의존성까지 정확한 버전과 해시로 고정한다(stack-versions 스킬 §5-1).

사람이 고치는 입력은 requirements.txt(직접 의존성 핀)와 .github/requirements-ci.txt(CI 도구 핀)다.
이 스크립트는 uv pip compile 로 두 입력을 Windows·macOS·Linux 공용(--universal) 해시 lock 으로 바꾼다.

사용 (프로젝트 루트에서, uv 를 설치한 Python 으로 — uv 는 .github/requirements-ci.lock 으로 설치한다):
  python scripts/lock.py           requirements.lock · .github/requirements-ci.lock 을 다시 만든다
  python scripts/lock.py --check   다시 만든 결과가 저장소의 lock 과 같은지 검사한다(CI — 다르면 종료 코드 1)

해석 기준은 scripts/versions.env 의 MIN_PYTHON(Python 계열)·LOCK_EXCLUDE_NEWER(이 시각 뒤 배포본 제외)다.
⛔ 결과가 uv 버전에 따라 달라질 수 있어 .github/requirements-ci.txt 에 핀한 uv 버전으로만 실행한다.
"""

import argparse
import difflib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# (입력, lock) — 경로는 프로젝트 루트 기준 상대 경로다(lock 의 "via" 주석에 그대로 적힌다).
LOCKS = (
    ("requirements.txt", "requirements.lock"),
    (".github/requirements-ci.txt", ".github/requirements-ci.lock"),
)
# lock 머리말에 적는 재생성 명령 — 실행 위치·임시 파일 경로가 lock 에 섞이지 않게 고정한다.
HEADER_COMMAND = "python scripts/lock.py"


def read_versions_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / "scripts" / "versions.env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z_]+)=(\S+)", line)
        if m:
            values[m[1]] = m[2]
    return values


def pinned_uv_version() -> str:
    text = (ROOT / ".github" / "requirements-ci.txt").read_text(encoding="utf-8")
    m = re.search(r"^uv==(\S+)", text, re.MULTILINE)
    if not m:
        sys.exit(".github/requirements-ci.txt 에 uv==<버전> 핀이 없습니다.")
    return m[1]


def check_uv_version() -> None:
    want = pinned_uv_version()
    try:
        out = subprocess.run(
            [sys.executable, "-m", "uv", "--version"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        sys.exit(
            "이 Python 에 uv 가 없습니다 — 별도 venv 에서 "
            "'python -m pip install --require-hashes -r .github/requirements-ci.lock' 후 "
            "그 venv 의 python 으로 실행하세요."
        )
    have = out.split()[1] if len(out.split()) > 1 else out.strip()
    if have != want:
        sys.exit(f"uv 버전이 핀과 다릅니다(설치 {have}, 핀 {want}) — lock 결과가 달라질 수 있어 중단합니다.")


def compile_lock(src: str, python_version: str, exclude_newer: str, out_dir: Path) -> str:
    out = out_dir / "out.lock"
    cmd = [
        sys.executable, "-m", "uv", "pip", "compile", src,
        "--output-file", str(out),
        "--universal",
        "--python-version", python_version,
        "--generate-hashes",
        "--exclude-newer", exclude_newer,
        # 기존 lock 을 선호 버전으로 쓰지 않는다 — 결과가 (입력, 기준 시각, uv 버전)만으로 정해져야 --check 가 성립한다.
        "--upgrade",
        "--no-config",
        "--custom-compile-command", HEADER_COMMAND,
        "--quiet",
    ]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"uv pip compile 실패: {src}")
    # 줄바꿈은 LF 로 통일한다(.gitattributes 와 같다).
    return out.read_text(encoding="utf-8").replace("\r\n", "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="requirements.lock 생성·검사")
    parser.add_argument("--check", action="store_true", help="다시 만든 결과가 저장소의 lock 과 같은지만 검사한다")
    args = parser.parse_args()

    env = read_versions_env()
    python_version = env.get("MIN_PYTHON")
    exclude_newer = env.get("LOCK_EXCLUDE_NEWER")
    if not python_version or not exclude_newer:
        sys.exit("scripts/versions.env 에 MIN_PYTHON · LOCK_EXCLUDE_NEWER 가 있어야 합니다.")
    check_uv_version()

    failed = False
    for src, lock in LOCKS:
        with tempfile.TemporaryDirectory() as tmp:
            new = compile_lock(src, python_version, exclude_newer, Path(tmp))
        lock_path = ROOT / lock
        if args.check:
            old = lock_path.read_text(encoding="utf-8").replace("\r\n", "\n") if lock_path.exists() else ""
            if old != new:
                failed = True
                diff = difflib.unified_diff(
                    old.splitlines(True), new.splitlines(True), f"{lock} (저장소)", f"{lock} (재생성)"
                )
                sys.stdout.writelines(diff)
                print(f"\n[X] {lock} 이 {src} 와 맞지 않습니다 — 'python scripts/lock.py' 로 다시 만든 뒤 커밋하세요.")
            else:
                print(f"[OK] {lock} = {src}")
        else:
            lock_path.write_text(new, encoding="utf-8", newline="\n")
            print(f"[OK] {lock} 생성 ({src}, exclude-newer {exclude_newer})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
