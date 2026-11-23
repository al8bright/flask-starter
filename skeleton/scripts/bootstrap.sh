#!/usr/bin/env bash
# 신규 개발 환경 부트스트랩 (macOS / Linux) — 최소 버전 검사 후 부족할 때만 설치.
#
# 정책:
#   - Python : pyenv 로 버전 격리 관리. pyenv 자체가 없으면 brew 로 설치.
#              MIN_PYTHON 계열 최신 패치를 pyenv install 후 .python-version 고정.
#   - PostgreSQL : 있으면 유지, --with-postgres 옵션 시에만 설치.
#   Node·pnpm 은 쓰지 않는다 — CSS 는 Tailwind standalone CLI(scripts/tailwind.*)로 빌드한다.
#   설치·활성화 실패는 경고로 넘기지 않고 원인을 보인 뒤 종료 코드 1 로 끝낸다(bootstrap.ps1 과 동일).
#
# 사용:
#   ./scripts/bootstrap.sh                  # 런타임만
#   ./scripts/bootstrap.sh --with-postgres  # PostgreSQL 까지
set -euo pipefail

WITH_PG=0
# 버전 고정 파일(.python-version)을 쓸 위치. 미지정 시 이 스크립트의 상위 폴더.
# scaffold.sh 는 템플릿 리포(skeleton/) 오염을 막기 위해 임시 폴더를 넘긴다.
PROJECT_ROOT_ARG=""
usage(){
  cat <<'EOF'
Usage: ./scripts/bootstrap.sh [--with-postgres] [--project-root <경로>]

Options:
  --with-postgres        PostgreSQL도 함께 설치합니다.
  --project-root <경로>  .python-version 을 기록할 위치.
                         (기본: 이 스크립트의 상위 폴더)
  -h, --help             이 도움말을 표시합니다.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --with-postgres) WITH_PG=1 ;;
    --project-root)
      if [ $# -lt 2 ]; then
        printf '옵션 --project-root 에 경로 인자가 필요합니다\n' >&2
        usage >&2
        exit 2
      fi
      PROJECT_ROOT_ARG="$2"
      shift
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      printf '알 수 없는 옵션: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

info(){ printf '  [i]  %s\n' "$1"; }
ok(){   printf '  [OK] %s\n' "$1"; }
warn(){ printf '  [!]  %s\n' "$1"; }

# psql 활성화 — 설치 방식에 따라 psql 이 PATH 에 없을 수 있다(macOS Postgres.app,
# Debian/Ubuntu 의 /usr/lib/postgresql/<ver>/bin, keg-only Homebrew formula).
# 설치돼 있는데도 "없음"으로 판정해 중복 설치하는 일을 막는다. 여러 버전이면 최고 버전을 쓴다.
enable_psql(){
  command -v psql >/dev/null 2>&1 && return 0
  _best=""; _best_ver=-1
  for _d in /Applications/Postgres.app/Contents/Versions/*/bin \
            /usr/lib/postgresql/*/bin \
            /usr/pgsql-*/bin \
            /opt/homebrew/opt/postgresql@*/bin \
            /usr/local/opt/postgresql@*/bin \
            "/c/Program Files/PostgreSQL/"*/bin; do   # 마지막은 Git Bash(Windows) 설치 경로
    [ -x "$_d/psql" ] || continue
    _v=$(printf '%s' "$_d" | grep -oE '[0-9]+' | head -n1); [ -n "$_v" ] || _v=0
    if [ "$_v" -gt "$_best_ver" ]; then _best_ver="$_v"; _best="$_d"; fi
  done
  if [ -n "$_best" ]; then
    PATH="$_best:$PATH"; export PATH
    info "psql 을 PATH 에서 찾지 못해 설치 경로를 사용합니다: $_best"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "$PROJECT_ROOT_ARG" ]; then
  mkdir -p "$PROJECT_ROOT_ARG" || { warn "--project-root 폴더를 만들 수 없습니다: $PROJECT_ROOT_ARG"; exit 1; }
  PROJECT_ROOT="$(cd "$PROJECT_ROOT_ARG" && pwd)"
else
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# 최소 버전 로드 (단일 출처)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/versions.env"
: "${MIN_PYTHON:?versions.env 에서 MIN_PYTHON 누락}"

extract_ver(){ printf '%s' "$1" | grep -oE '[0-9]+(\.[0-9]+){0,2}' | head -n1 || true; }
# meets MIN HAVE  -> HAVE >= MIN 이면 0(true)
meets(){
  [ -n "$2" ] || return 1
  awk -v min="$1" -v have="$2" 'BEGIN {
    min_n = split(min, min_parts, ".")
    have_n = split(have, have_parts, ".")
    n = min_n > have_n ? min_n : have_n
    for (i = 1; i <= n; i++) {
      min_part = (i <= min_n ? min_parts[i] : 0) + 0
      have_part = (i <= have_n ? have_parts[i] : 0) + 0
      if (have_part > min_part) exit 0
      if (have_part < min_part) exit 1
    }
    exit 0
  }'
}

echo "=== 개발 환경 부트스트랩 ($(uname -s)) ==="

PY_PIN_FILE="$PROJECT_ROOT/.python-version"

# 핀 파일과 실제 런타임이 어긋나면 알린다 — CI 는 핀 파일을 읽으므로 로컬만 통과하고
# CI 에서 깨지는 상황이 생긴다. pyenv 없이 기존 런타임을 재사용할 때만 발생한다.
warn_pin_mismatch(){
  _pf="$1"; _actual="$2"; _label="$3"
  [ -f "$_pf" ] || return 0
  _pin="$(head -n1 "$_pf" | tr -d '[:space:]' | sed 's/^v//')"
  [ -n "$_pin" ] && [ -n "$_actual" ] || return 0
  case "$_actual" in
    "$_pin"|"$_pin".*) return 0 ;;
  esac
  warn "$_label 핀($_pin)과 설치본($_actual)이 다릅니다 — CI 는 핀 파일을 읽으므로 로컬과 다른 버전을 씁니다."
  printf '  일치시키려면 관리자를 설치해 핀 버전을 쓰거나, 핀 파일을 설치본에 맞추세요.\n'
}

# ── 1·2. Python ─────────────────────────────────────────────────────────────
# 정책(versions.env): 하한 이상이면 기존 설치본을 재사용한다.
#   - pyenv 가 있으면 그것으로 관리한다(핀 존중).
#   - 없어도 Python 이 하한을 충족하면 그대로 쓴다. ⛔ 관리자가 없다는 이유만으로 중단하지 않는다.
#   - 둘 다 아닐 때만 brew 로 pyenv 설치를 시도한다.
HAS_PYENV=0
command -v pyenv >/dev/null 2>&1 && HAS_PYENV=1
PY_HAVE="$(extract_ver "$(python3 --version 2>/dev/null || true)")"
PY_MEETS_MIN=0
meets "$MIN_PYTHON" "$PY_HAVE" && PY_MEETS_MIN=1

if [ "$HAS_PYENV" = "0" ] && [ "$PY_MEETS_MIN" = "0" ]; then
  info "Python $MIN_PYTHON 이상이 없습니다. pyenv 를 brew 로 설치합니다 …"
  if command -v brew >/dev/null 2>&1; then
    brew install pyenv
    command -v pyenv >/dev/null 2>&1 && HAS_PYENV=1
  else
    warn "Homebrew 없음 — pyenv 를 수동으로 설치하세요: https://github.com/pyenv/pyenv"
    warn "또는 Python $MIN_PYTHON 이상을 직접 설치해도 됩니다."
    exit 1
  fi
fi

if [ "$HAS_PYENV" = "0" ]; then
  ok "Python $PY_HAVE 재사용 (>= $MIN_PYTHON) — pyenv 없이 진행"
  warn_pin_mismatch "$PY_PIN_FILE" "$PY_HAVE" "Python"
else
  ok "pyenv $(extract_ver "$(pyenv --version 2>/dev/null)") 발견"

  # 현재 셸 세션에서 pyenv 활성화
  export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
  export PATH="$PYENV_ROOT/bin:$PATH"
  # init 출력이 셸 코드가 아닐 수 있다(예: Git Bash 의 pyenv-win 은 "no such command" 를 stdout 으로 낸다).
  # 그대로 eval 하면 127 로 죽으므로(set -e) 실패를 무시한다 — 버전 선택은 PYENV_VERSION 으로 따로 한다.
  eval "$(pyenv init --path 2>/dev/null || true)" 2>/dev/null || true
  eval "$(pyenv init - 2>/dev/null || true)" 2>/dev/null || true

  # 기존 .python-version 핀이 있으면(예: 템플릿의 체크인 파일) 그 값을 존중해 설치하고,
  # 없을 때만 MIN_PYTHON(예: 3.13) 계열의 최신 패치 버전을 pyenv 목록에서 선택해 새로 핀한다.
  PYENV_PYTHON=""
  if [ -f "$PY_PIN_FILE" ]; then
    PYENV_PYTHON="$(head -n1 "$PY_PIN_FILE" | tr -d '[:space:]')"
    if [ -n "$PYENV_PYTHON" ]; then
      ok "기존 .python-version 핀 존중: $PYENV_PYTHON"
    fi
  fi

  if [ -z "$PYENV_PYTHON" ]; then
    # || true: 목록에 없으면 grep 이 실패해 set -e·pipefail 로 아래 안내 없이 죽는다
    # Git Bash 의 pyenv-win 은 목록을 CRLF·들여쓰기 없이 내보낸다 — \r 을 지우고 앞 공백은 선택으로 둔다.
    PYENV_PYTHON="$(pyenv install --list 2>/dev/null \
      | tr -d '\r' \
      | grep -E "^[[:space:]]*${MIN_PYTHON//./\\.}\.[0-9]+$" \
      | tail -1 \
      | tr -d ' ' || true)"
    if [ -z "$PYENV_PYTHON" ]; then
      warn "pyenv 목록에서 Python ${MIN_PYTHON}.x 를 찾지 못했습니다. 'pyenv update' 후 재시도하세요."
      PYENV_PYTHON="$MIN_PYTHON"
    fi
  fi

  if pyenv versions --bare 2>/dev/null | tr -d '\r' | grep -qx "$PYENV_PYTHON"; then
    ok "Python $PYENV_PYTHON 이미 pyenv 에 설치됨 — 재사용"
  else
    info "Python $PYENV_PYTHON 설치 (pyenv) …"
    # 핀 버전이 pyenv 목록에 없을 수 있다(버전 DB 가 오래됨). 하한을 충족하는 Python 이
    # 이미 있으면 그것으로 진행한다 — 설치 가능한 핀이 없다는 이유로 환경을 막지 않는다.
    if ! pyenv install "$PYENV_PYTHON"; then
      if [ "$PY_MEETS_MIN" = "1" ]; then
        warn "Python $PYENV_PYTHON 설치 실패 — pyenv 목록에 없거나 내려받지 못했습니다."
        ok "기존 Python $PY_HAVE 로 진행합니다 (>= $MIN_PYTHON)."
        warn_pin_mismatch "$PY_PIN_FILE" "$PY_HAVE" "Python"
        printf "  핀을 쓰려면 'pyenv update' 후 다시 실행하거나, .python-version 을 설치 가능한 버전으로 바꾸세요.\n"
        HAS_PYENV=0
      else
        exit 1
      fi
    fi
  fi

  if [ "$HAS_PYENV" = "1" ]; then
    # 이 프로세스 안에서만 방금 고른 버전을 쓴다 — 핀 파일이 현재 폴더에 없으면(--project-root 가
    # 임시 폴더일 때) pyenv shim 이 global(대개 system)로 풀려 아래 최종 확인이 헛되게 실패한다.
    export PYENV_VERSION="$PYENV_PYTHON"
    # 핀 파일이 없을 때만 프로젝트 루트에 .python-version 기록 (기존 핀은 덮어쓰지 않음)
    if [ ! -f "$PY_PIN_FILE" ]; then
      echo "$PYENV_PYTHON" > "$PY_PIN_FILE"
      ok "Python $PYENV_PYTHON → $PY_PIN_FILE 고정"
    fi
  fi
fi

# ── 3. PostgreSQL (선택, 있으면 유지) ───────────────────────────────────────
if [ "$WITH_PG" = "1" ]; then
  enable_psql
  if command -v psql >/dev/null 2>&1; then
    ok "PostgreSQL 이미 설치됨 (psql 발견) — 유지"
  else
    info "PostgreSQL 설치 …"
    _pg_ok=1
    if command -v brew >/dev/null 2>&1; then
      { brew install postgresql@16 && brew services start postgresql@16; } || _pg_ok=0
    elif command -v apt-get >/dev/null 2>&1; then
      { sudo apt-get update && sudo apt-get install -y postgresql; } || _pg_ok=0
    elif command -v dnf >/dev/null 2>&1; then
      { sudo dnf install -y postgresql-server && sudo postgresql-setup --initdb && sudo systemctl enable --now postgresql; } || _pg_ok=0
    else
      warn "지원되는 패키지 매니저(brew·apt-get·dnf)를 못 찾음 — PostgreSQL 을 수동 설치한 뒤 다시 실행하세요."
      exit 1
    fi
    if [ "$_pg_ok" = "0" ]; then
      warn "PostgreSQL 설치 실패 — 위 로그를 확인하세요."
      exit 1
    fi
    enable_psql   # keg-only formula 등은 PATH 에 넣지 않으므로 표준 경로를 직접 찾는다
    if ! command -v psql >/dev/null 2>&1; then
      warn "PostgreSQL 설치 명령은 끝났지만 psql 을 찾을 수 없습니다. 새 셸에서 PATH 를 반영하거나 PostgreSQL bin 디렉터리를 PATH 에 추가하세요."
      exit 1
    fi
    ok "PostgreSQL 설치 완료 — superuser 비밀번호/포트(5432)를 .env 의 DATABASE_URL 에 반영하세요."
  fi
else
  warn "PostgreSQL 은 건너뜀. 필요하면 '--with-postgres' 또는 원격 DB 를 사용하세요."
fi

# 설치/활성화가 실제 현재 프로세스에 반영됐는지 최종 확인한다 (bootstrap.ps1 과 동일).
_final_ok=1
PY_FINAL="$(extract_ver "$(python3 --version 2>/dev/null || true)")"
meets "$MIN_PYTHON" "$PY_FINAL" || { warn "최종 확인 실패: Python 이 $MIN_PYTHON 이상이 아닙니다 (현재: ${PY_FINAL:-없음})."; _final_ok=0; }
[ "$_final_ok" = "1" ] || exit 1
ok "최종 확인 완료: Python $PY_FINAL"

cat <<'EOF'

=== 다음 단계 ===
1) pyenv 를 새로 설치했다면 ~/.zshrc (또는 ~/.bashrc) 에 아래 줄을 추가하고 새 셸을 여세요:
     export PYENV_ROOT="$HOME/.pyenv"
     export PATH="$PYENV_ROOT/bin:$PATH"
     eval "$(pyenv init -)"
2) 의존성:        python3 -m venv .venv && ./.venv/bin/python -m pip install -r requirements.txt
3) CSS 빌드:      ./scripts/tailwind.sh
4) DB 마이그레이션: .env 의 DATABASE_URL 확인 후  ./.venv/bin/python -m alembic upgrade head
자세한 내용은 README.md 참조.
EOF
