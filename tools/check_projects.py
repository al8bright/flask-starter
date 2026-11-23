"""생성 프로젝트 점검 — 이 스타터로 만든 프로젝트들의 버전·공통 파일·보안 감사를 한 화면에 모은다.

여러 프로젝트를 함께 관리할 때 같은 보안 업데이트를 따로 하거나, 한쪽만 스타터 수정을 놓치는 일을 줄이려는 도구다.
저장소도 프로젝트도 고치지 않는다(읽기 전용). 표준 라이브러리만 쓰므로 설치 없이 Python 3.13 으로 실행한다.
형제 템플릿(fastapi-react-pg-starter)의 tools/check_projects.py 를 평면 구조(app/·alembic/·tests/ 가 루트)에
맞춘 판이다.

    python tools/check_projects.py ../project-a ../project-b
    python tools/check_projects.py --audit --files --output 점검.md

경로를 주지 않으면 tools/projects.local.txt(커밋하지 않는 개인 목록, 한 줄에 경로 하나)를 읽는다.

출력(마크다운):
  1. 런타임·도구 — scripts/versions.env · .python-version · 벤더링한 htmx.min.js 의 실제 버전
  2. Python 핀 — requirements.txt
  3. 스타터 대비 공통 파일 — skeleton/ 과 같은 경로 파일의 같음·다름·없음(치환 토큰은 프로젝트 값으로 바꿔 비교)
  4. 보안 감사(--audit) — OSV(api.osv.dev). 취약점이 하나라도 있으면 종료 코드 1 로 끝난다.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKELETON = ROOT / "skeleton"
LOCAL_LIST = Path(__file__).resolve().parent / "projects.local.txt"
STARTER_LABEL = "스타터"
KST = timezone(timedelta(hours=9), "KST")  # zoneinfo 는 Windows 에서 tzdata 설치가 필요해 고정 오프셋을 쓴다

# 공통 파일 비교에서 빼는 것 — 설치·빌드 산출물과 개인 설정.
SKIP_NAMES = {".env", "app.css"}
SKIP_DIRS = {".venv", "venv", ".tools", "uploads", "logs", "__pycache__", ".ruff_cache", ".pytest_cache", ".git"}

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"

# 3절에서 기본으로 숨기는 파일 — 화면 템플릿과 프로젝트 문서는 프로젝트마다 다시 쓰는 게 정상이라
# 공통 인프라(스킬·스크립트·CI·앱 코드·설정)의 차이를 가린다. --files 로 함께 본다.
SCREEN_PREFIXES = ("app/templates/",)
PROJECT_DOCS = {"README.md", "PLAN.md"}

# 스캐폴드가 치환한 값을 생성물에서 다시 읽는 자리 — 스캐폴드는 이 두 줄에 토큰을 넣는다.
NAME_SOURCE = ("app/main.py", re.compile(r'^PROJECT_NAME = "(.*)"$', re.M))
SNAKE_SOURCE = ("app/dependencies.py", re.compile(r'^AUTH_COOKIE = "(.*)_session"$', re.M))
HTMX_FILE = "app/static/js/htmx.min.js"


# ── 파서 ────────────────────────────────────────────────────────────────────


def normalize_package(name: str) -> str:
    """PEP 503 이름 정규화 — PyJWT·pyjwt, pydantic_settings·pydantic-settings 를 같게 본다."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text: str) -> dict[str, str]:
    """requirements.txt → {정규화 이름: 버전}. `==` 핀은 버전만, 그 밖의 조건식은 식 그대로 둔다(환경 마커는 뗀다)."""
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)", line)
        if not match:
            continue
        name, spec = normalize_package(match.group(1)), match.group(3).strip()
        result[name] = spec[2:].strip() if spec.startswith("==") else spec
    return result


def parse_versions_env(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.split("#", 1)[0].strip().strip("'\"")
    return result


def htmx_version(text: str) -> str:
    """벤더링한 htmx.min.js 안의 `version:"x.y.z"` — 파일을 바꾸고 versions.env 를 빠뜨린 경우를 드러낸다."""
    match = re.search(r'version:"([0-9][^"]*)"', text)
    return match.group(1) if match else ""


def summarize_osv(packages: list[tuple[str, str]], response: dict) -> list[str]:
    """OSV querybatch 응답(요청 순서와 같은 results) → 취약 패키지 줄 목록."""
    lines = []
    for (name, version), result in zip(packages, response.get("results", []), strict=False):
        ids = [v["id"] for v in result.get("vulns", [])]
        if ids:
            lines.append(f"{name} {version} — {', '.join(ids)}")
    return lines


# ── 비교 ────────────────────────────────────────────────────────────────────


def diff_line_count(a: str, b: str) -> int:
    """줄바꿈(CRLF/LF)을 무시한 diff 의 지운 줄 + 더한 줄 수."""
    diff = difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
    return sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))


@dataclass(frozen=True)
class ProjectNames:
    """스캐폴드가 치환한 두 값 — 표시 이름(__PROJECT_NAME__)과 snake 이름(__PROJECT_SNAKE__)."""

    name: str
    snake: str


def substitute_tokens(text: str, names: ProjectNames) -> str:
    """스캐폴드 치환을 재현한다. __PROJECT_SNAKE__ 를 먼저 바꿔야 __PROJECT_NAME__ 과 겹치지 않는다."""
    return text.replace("__PROJECT_SNAKE__", names.snake).replace("__PROJECT_NAME__", names.name)


def is_infra_file(rel: str) -> bool:
    return not rel.startswith(SCREEN_PREFIXES) and rel not in PROJECT_DOCS


@dataclass
class FileComparison:
    same: list[str] = field(default_factory=list)
    different: dict[str, int] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def skeleton_files(skeleton: Path) -> list[str]:
    files = []
    for path in skeleton.rglob("*"):
        rel = path.relative_to(skeleton)
        if path.is_file() and path.name not in SKIP_NAMES and not SKIP_DIRS.intersection(rel.parts):
            files.append(rel.as_posix())
    return sorted(files)


def compare_files(skeleton: Path, project: Path, names: ProjectNames) -> FileComparison:
    result = FileComparison()
    for rel in skeleton_files(skeleton):
        target = project / rel
        if not target.is_file():
            result.missing.append(rel)
            continue
        base, mine = _read_text(skeleton / rel), _read_text(target)
        if base is None or mine is None:  # 이진 파일 — 바이트로 비교
            if (skeleton / rel).read_bytes() == target.read_bytes():
                result.same.append(rel)
            else:
                result.different[rel] = -1
            continue
        count = diff_line_count(substitute_tokens(base, names), mine)
        if count:
            result.different[rel] = count
        else:
            result.same.append(rel)
    return result


def version_rows(columns: dict[str, dict[str, str]]) -> list[list[str]]:
    """{열 이름: {패키지: 버전}} → 표 행. 두 곳 이상에 있고 값이 다를 때만 마지막 칸에 ≠ 를 단다."""
    names = sorted({name for values in columns.values() for name in values})
    rows = []
    for name in names:
        cells = [values.get(name, "-") for values in columns.values()]
        present = {c for c in cells if c != "-"}
        rows.append([name, *cells, "≠" if len(present) > 1 else ""])
    return rows


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(value: str) -> str:
        return str(value).replace("|", "\\|")

    lines = ["| " + " | ".join(cell(h) for h in headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


# ── 프로젝트 읽기 ───────────────────────────────────────────────────────────


def read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def project_names(root: Path) -> ProjectNames:
    """생성물에서 치환된 이름을 읽는다. 찾지 못하면 폴더 이름으로 대신한다(공통 파일 차이가 늘어날 수 있다)."""
    found = []
    for rel, pattern in (NAME_SOURCE, SNAKE_SOURCE):
        match = pattern.search(read_optional(root / rel))
        found.append(match.group(1) if match else "")
    name, snake = found
    return ProjectNames(name or root.name, snake or root.name)


def resolve_project_paths(args: list[str], listing: Path) -> list[Path]:
    if args:
        return [Path(a) for a in args]
    if listing.is_file():
        lines = listing.read_text(encoding="utf-8").splitlines()
        paths = [Path(line.strip()) for line in lines if line.strip() and not line.lstrip().startswith("#")]
        if paths:
            return paths
    raise SystemExit(
        "점검할 프로젝트 경로를 인자로 주거나 tools/projects.local.txt 에 한 줄에 하나씩 적는다"
        "(이 파일은 커밋하지 않는다)."
    )


def runtime_values(root: Path) -> dict[str, str]:
    values = parse_versions_env(read_optional(root / "scripts" / "versions.env"))
    values[".python-version"] = read_optional(root / ".python-version").strip()
    values["htmx.min.js"] = htmx_version(read_optional(root / HTMX_FILE))
    return {k: v for k, v in values.items() if v}


# ── 보안 감사(네트워크) ─────────────────────────────────────────────────────


def venv_python(root: Path) -> Path | None:
    for candidate in (root / ".venv/Scripts/python.exe", root / ".venv/bin/python"):
        if candidate.is_file():
            return candidate
    return None


def python_packages(root: Path) -> tuple[list[tuple[str, str]], str]:
    """감사할 Python 패키지 — 프로젝트 venv 가 있으면 설치된 전체(전이 의존성 포함), 없으면 requirements 핀."""
    python = venv_python(root)
    if python:
        out = subprocess.run(
            [str(python), "-m", "pip", "list", "--format=json", "--disable-pip-version-check"],
            capture_output=True,
            check=False,
        )
        if out.returncode == 0:
            items = json.loads(out.stdout.decode("utf-8"))
            return sorted((normalize_package(i["name"]), i["version"]) for i in items), "venv 설치 목록"
    pins = parse_requirements(read_optional(root / "requirements.txt"))
    return sorted((n, v) for n, v in pins.items() if re.fullmatch(r"[0-9][0-9A-Za-z.+!-]*", v)), "requirements 핀"


def osv_audit(packages: list[tuple[str, str]]) -> list[str]:
    queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in packages]
    request = urllib.request.Request(
        OSV_BATCH_URL, data=json.dumps({"queries": queries}).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return summarize_osv(packages, json.load(response))


# ── 보고서 ──────────────────────────────────────────────────────────────────


def build_report(projects: list[Path], *, audit: bool, list_files: bool) -> tuple[str, int]:
    names = [project_names(p) for p in projects]
    labels = [n.snake for n in names]
    columns = [STARTER_LABEL, *labels]
    roots = [SKELETON, *projects]
    out: list[str] = [f"# 생성 프로젝트 점검 — {datetime.now(KST):%Y-%m-%d %H:%M} KST", ""]
    out += [f"- {STARTER_LABEL}: `{SKELETON}`"]
    out += [f"- {lb}: `{p.resolve()}`" for lb, p in zip(labels, projects, strict=True)] + [""]
    out += ["`≠` 는 두 곳 이상에 있는 값이 서로 다르다는 뜻이다. `-` 는 그 프로젝트에 없다는 뜻이다.", ""]

    out += ["## 1. 런타임·도구", ""]
    rows = version_rows(dict(zip(columns, (runtime_values(r) for r in roots), strict=True)))
    out += [markdown_table(["항목", *columns, "차이"], rows), ""]

    out += ["## 2. Python 핀 (`requirements.txt`)", ""]
    reqs = (parse_requirements(read_optional(r / "requirements.txt")) for r in roots)
    rows = version_rows(dict(zip(columns, reqs, strict=True)))
    out += [markdown_table(["패키지", *columns, "차이"], rows), ""]

    out += ["## 3. 스타터 대비 공통 파일 (`skeleton/` 기준)", ""]
    comparisons = [compare_files(SKELETON, p, n) for p, n in zip(projects, names, strict=True)]
    summary = [
        [lb, str(len(c.same)), str(len(c.different)), str(len(c.missing))]
        for lb, c in zip(labels, comparisons, strict=True)
    ]
    out += [markdown_table(["프로젝트", "같음", "다름", "없음"], summary), ""]
    differing = sorted({f for c in comparisons for f in c.different})

    def cell(c: FileComparison, f: str) -> str:
        if f in c.different:
            return "이진" if c.different[f] < 0 else str(c.different[f])
        return "없음" if f in c.missing else "같음"

    def file_table(files: list[str]) -> list[str]:
        return [markdown_table(["파일", *labels], [[f, *(cell(c, f) for c in comparisons)] for f in files]), ""]

    infra = [f for f in differing if is_infra_file(f)]
    screen = [f for f in differing if not is_infra_file(f)]
    out += ["숫자는 바뀐 줄 수(지운 줄 + 더한 줄, 줄바꿈 무시)다. `이진` 은 바이트가 다른 파일이다.", ""]
    if infra:
        out += ["### 공통 인프라 — 스킬 · 스크립트 · CI · 앱 코드 · 설정", ""] + file_table(infra)
    if screen and list_files:
        out += ["### 화면 템플릿 · 프로젝트 문서", ""] + file_table(screen)
    elif screen:
        out += [
            (
                f"화면 템플릿(`{'`·`'.join(SCREEN_PREFIXES)}`)·프로젝트 문서({'·'.join(sorted(PROJECT_DOCS))}) "
                f"{len(screen)}개는 프로젝트마다 다른 게 정상이라 생략하였다(`--files` 로 출력)."
            ),
            "",
        ]
    if list_files:
        for lb, c in zip(labels, comparisons, strict=True):
            if c.missing:
                out += [f"**{lb}** 에 없는 스타터 파일 {len(c.missing)}개:", ""]
                out += [f"- `{f}`" for f in c.missing] + [""]

    findings = 0
    if audit:
        out += ["## 4. 보안 감사", ""]
        for lb, root in zip(labels, projects, strict=True):
            packages, source = python_packages(root)
            out += [f"### {lb}", ""]
            try:
                py_lines = osv_audit(packages)
                findings += len(py_lines)
                out.append(
                    f"- Python ({source} {len(packages)}개, OSV): "
                    + (f"취약 {len(py_lines)}건" if py_lines else "없음")
                )
                out += [f"  - {line}" for line in py_lines]
            except OSError as exc:
                out.append(f"- Python: 미실행 — OSV 조회 실패({exc})")
            out.append("")
    return "\n".join(out).rstrip() + "\n", findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="이 스타터로 만든 프로젝트들의 버전·공통 파일·보안 감사를 한 화면에 모은다."
    )
    parser.add_argument("projects", nargs="*", help="프로젝트 루트 경로(없으면 tools/projects.local.txt)")
    parser.add_argument(
        "--audit", action="store_true", help="보안 감사(OSV, 네트워크 사용). 취약점이 있으면 종료 코드 1"
    )
    parser.add_argument(
        "--files",
        action="store_true",
        help="화면 템플릿·프로젝트 문서의 차이와 프로젝트에 없는 스타터 파일 목록도 출력",
    )
    parser.add_argument("--output", type=Path, help="보고서를 UTF-8 파일로 저장")
    args = parser.parse_args(argv)
    # Windows 콘솔 기본 인코딩(cp949)으로는 한국어 보고서·안내가 깨진다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    projects = resolve_project_paths(args.projects, LOCAL_LIST)
    for path in projects:
        if not path.is_dir():
            raise SystemExit(f"프로젝트 폴더가 없다: {path}")
    report, findings = build_report(projects, audit=args.audit, list_files=args.files)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"저장: {args.output}")
    else:
        sys.stdout.write(report)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
