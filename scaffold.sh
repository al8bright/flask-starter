#!/usr/bin/env bash
# flask-starter 신규 프로젝트 스캐폴드 (macOS/Linux, Git Bash).
# Windows PowerShell 은 scaffold.ps1 을 사용한다. 동작은 동일하다.
#
# 사용:
#   ./scaffold.sh --name project_test --target ~/work/project_test
#   ./scaffold.sh --name Demo --target ./Demo --skip-db --skip-install
#
# 옵션:
#   --name <이름>          프로젝트 이름 (없으면 묻는다)
#   --target <경로>        생성 위치 (기본: 템플릿 폴더의 부모/<이름>)
#   --skip-db              psql DB 생성 + alembic 마이그레이션 생략
#   --skip-install         venv/pip 설치 + alembic + Tailwind CSS 빌드 생략
#   --db-host/--db-port/--db-user/--db-password/--db-name
#                          DB 접속 정보 기본값 (대화형이면 Enter 로 수락, 비밀번호는 지정하면 묻지 않는다)
#                          값 규칙: DB 이름은 영문자·숫자·'_'(63자 이하), 호스트는 호스트 이름·IPv4
#                          (영문자·숫자·'.'·'-'·'_') 또는 [IPv6], 사용자는 제어 문자·큰따옴표 금지,
#                          포트는 1~65535. 어기면 중단한다(scaffold.ps1 과 같다).
#   -h, --help             이 도움말
#
# 환경변수:
#   SCAFFOLD_DB_PASSWORD   DB 비밀번호 (권장). ⚠️ --db-password 는 프로세스 목록·셸 기록에 남아 경고를 내며
#                          호환용으로만 남긴다. 둘 다 있으면 인자가 우선한다. 대화형이면 지정하지 않고 프롬프트로 넣는다.
#
# 사전 요구: python3. Node·pnpm 은 필요 없다(CSS 는 Tailwind standalone CLI 로 빌드한다).
#            psql 은 PATH 에 없어도 표준 설치 경로를 탐색한다. 찾지 못하면 DB 단계만 건너뛴다.
# 이름 규칙: ASCII 영문자·숫자로 시작하고 영문자·숫자·공백·'_'·'-' 만 쓴다(최대 64자).
# 대상 폴더: 비어 있지 않으면 대화형은 y/N 확인, 비대화형은 중단한다.
#            템플릿 저장소 자신·그 하위·그 상위 폴더는 항상 거부한다.
# 종료 코드: 0 = 모든 단계 완료
#            1 = 중단(입력 오류, 대상 폴더 거부, 런타임 미충족, 복사·치환 실패, .env 생성·권한 제한 실패)
#            2 = 골격은 생성됐지만 일부 단계(pip·DB·alembic·CSS 빌드 등)가 미완료 — 마지막 요약 참고

# ---------- 템플릿 설정 ----------
# 토큰을 치환할 파일 확장자 (대소문자 구분, scaffold.ps1 과 동일)
TOKEN_EXTENSIONS=".py .html .css .js .md .ini .mako .example .txt .toml .sh .conf .service"
APP_PORT=5000
# 골격 복사·토큰 치환에서 제외하는 산출물 (scaffold.ps1 과 동일)
#   .tools = 내려받은 Tailwind CLI, uploads·logs = 실행 산출물, app.css = Tailwind 빌드 결과
COPY_EXCLUDES=".venv venv .ruff_cache .pytest_cache __pycache__ .tools uploads logs app.css .DS_Store .env"
PRUNE_DIRS=".venv venv .ruff_cache .pytest_cache __pycache__ .git .tools uploads logs"
# 완료 안내의 배포 전 주의
DEPLOY_NOTE='  ⛔ 배포 전 이 계정의 비밀번호를 바꾸고 SEED_DEFAULT_ADMIN=false, APP_ENV=production,
     COOKIE_SECURE=true(HTTPS) 로 설정하세요.'
# ---------- 템플릿 설정 끝 ----------

# ---------- 기본값 / 인자 ----------
NAME=""
TARGET=""
SKIP_DB=0
SKIP_INSTALL=0
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"
DB_PASSWORD=""
_DB_PW_ARG=0
DB_NAME=""

# 값이 필요한 옵션의 값 누락 검사 (누락 시 무한 루프 방지)
_need_val() { [ "$2" -ge 2 ] || { echo "옵션 $1 에 값이 필요합니다" >&2; exit 1; }; }

while [ $# -gt 0 ]; do
  case "$1" in
    --name)         _need_val "$1" $#; NAME="$2"; shift 2 ;;
    --target)       _need_val "$1" $#; TARGET="$2"; shift 2 ;;
    --skip-db)      SKIP_DB=1; shift ;;
    --skip-install) SKIP_INSTALL=1; shift ;;
    --db-host)      _need_val "$1" $#; DB_HOST="$2"; shift 2 ;;
    --db-port)      _need_val "$1" $#; DB_PORT="$2"; shift 2 ;;
    --db-user)      _need_val "$1" $#; DB_USER="$2"; shift 2 ;;
    --db-password)  _need_val "$1" $#; DB_PASSWORD="$2"; _DB_PW_ARG=1; shift 2 ;;
    --db-name)      _need_val "$1" $#; DB_NAME="$2"; shift 2 ;;
    -h|--help)      sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
  esac
done

# 물리 경로(pwd -P) — 아래 "대상이 템플릿 안인가" 비교를 심볼릭 링크에 속지 않게 한다
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SKELETON_DIR="$SCRIPT_DIR/skeleton"

c_cyan='\033[36m'; c_green='\033[32m'; c_yellow='\033[33m'; c_red='\033[31m'; c_reset='\033[0m'
step() { printf "\n${c_cyan}=== %s ===${c_reset}\n" "$1"; }
ok()   { printf "  ${c_green}[OK]${c_reset} %s\n" "$1"; }
warn() { printf "  ${c_yellow}[!]${c_reset}  %s\n" "$1"; }
die()  { printf "  ${c_red}[X]${c_reset}  %s\n" "$1" >&2; exit 1; }
# 포트는 숫자만 받는다 (scaffold.ps1 의 [int] 매개변수·TryParse 와 같게) — 대화형 입력이 숫자가 아니면 기존 값을 유지한다.
_set_port() {
  case "$1" in
    ''|*[!0-9]*) warn "포트가 숫자가 아닙니다: '$1' — 기존 값 $DB_PORT 유지" ;;
    *) DB_PORT="$1" ;;
  esac
}
case "$DB_PORT" in ''|*[!0-9]*) die "--db-port 는 숫자여야 합니다: $DB_PORT" ;; esac

# 미완료 단계 모음 — 마지막에 요약하고, 하나라도 있으면 종료 코드 2 로 끝낸다 (scaffold.ps1 과 동일).
_INCOMPLETE=""
_INCOMPLETE_N=0
_incomplete() { _INCOMPLETE="${_INCOMPLETE}${1}
"; _INCOMPLETE_N=$((_INCOMPLETE_N + 1)); }

# 경로 정규화 — 존재하는 가장 가까운 상위를 pwd -P 로 풀고, 나머지(아직 없는 부분)의 . / .. 를 처리한다.
# (realpath -m 은 macOS 기본 도구에 없다)
_canon_path() {
  local p="$1" rest="" base out part
  while [ ! -d "$p" ]; do
    base="${p##*/}"
    rest="$base${rest:+/$rest}"
    case "$p" in */*) p="${p%/*}" ;; *) p="." ;; esac
    [ -n "$p" ] || p="/"
  done
  out="$(cd "$p" && pwd -P)" || return 1
  local IFS=/
  # shellcheck disable=SC2086  # / 로 나눠 순회한다 (경로 조각에 glob 문자가 있어도 set -f 로 막는다)
  set -f; set -- $rest; set +f
  for part in "$@"; do
    case "$part" in
      ""|.) ;;
      ..) out="${out%/*}"; [ -n "$out" ] || out="/" ;;
      *)  out="${out%/}/$part" ;;
    esac
  done
  printf '%s\n' "$out"
}
_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
# $1 이 $2 와 같거나 그 하위인가 (대소문자 무시 — macOS·Windows 기본 파일 시스템 기준)
_path_within() {
  local c p
  c="$(_lower "${1%/}")"; p="$(_lower "${2%/}")"
  [ -n "$c" ] || c="/"; [ -n "$p" ] || p="/"
  [ "$c" = "$p" ] && return 0
  [ "$p" = "/" ] && return 0
  case "$c" in "$p"/*) return 0 ;; esac
  return 1
}

# ---------- 1. 이름·생성 위치 (런타임 설치보다 먼저 검증해 잘못된 입력이면 아무것도 하지 않고 끝낸다) ----------
step "신규 프로젝트 스캐폴드"
# DB 비밀번호 — ⚠️ 명령줄 인자는 프로세스 목록·셸 기록에 남는다. 환경변수 SCAFFOLD_DB_PASSWORD 를 권장하고,
# 인자는 호환용으로만 받는다(둘 다 있으면 인자 우선, 빈 값은 지정하지 않은 것으로 본다 — scaffold.ps1 과 같다).
if [ "$_DB_PW_ARG" = "1" ] && [ -n "$DB_PASSWORD" ]; then
  warn "--db-password 인자는 프로세스 목록·셸 기록에 남습니다 — 환경변수 SCAFFOLD_DB_PASSWORD 를 쓰세요."
elif [ -n "${SCAFFOLD_DB_PASSWORD:-}" ]; then
  DB_PASSWORD="$SCAFFOLD_DB_PASSWORD"
fi
[ -z "$NAME" ] && read -r -p "프로젝트 이름 (예: project_test): " NAME
[ -z "$NAME" ] && die "프로젝트 이름이 필요합니다."
# ⛔ 이름은 Python 문자열 리터럴(app/main.py)·HTML 제목과 기본 생성 위치(부모/<이름>)에 그대로 들어간다.
#    " \ ../ 같은 문자는 코드를 깨거나 경로를 벗어나므로 허용 목록으로만 받는다 (scaffold.ps1 과 같은 규칙).
#    로케일에 따라 A-Z 범위가 다른 문자를 포함할 수 있어 문자 집합을 명시한다.
_alnum='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
_name_re="^[${_alnum}]([${_alnum} _-]{0,62}[${_alnum}_-])?\$"
if ! [[ "$NAME" =~ $_name_re ]]; then
  printf "  ${c_red}[X]${c_reset}  사용할 수 없는 프로젝트 이름입니다: %s\n" "$NAME" >&2
  echo "        ASCII 영문자·숫자로 시작하고 영문자·숫자·공백·'_'·'-' 만 쓸 수 있습니다(최대 64자, 공백으로 끝나면 안 됨)." >&2
  exit 1
fi
SNAKE=$(printf '%s' "$NAME" | sed -E 's/([a-z0-9])([A-Z])/\1_\2/g' | tr 'A-Z' 'a-z' | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//')
# ⛔ 식별자가 비면 DATABASE_URL 에 DB 이름이 없고 쿠키 이름이 "_session" 이 된다.
#    위 허용 목록이 영숫자 시작을 강제하므로 정상 경로에서는 오지 않지만, 방어로 남긴다.
if [ -z "$SNAKE" ]; then
  echo "프로젝트 이름에서 식별자를 만들 수 없습니다: $NAME" >&2
  echo "  ASCII 영문자·숫자를 1자 이상 포함하세요 (DB 이름·쿠키 이름에 쓰입니다)." >&2
  exit 1
fi
[ -z "$DB_NAME" ] && DB_NAME="$SNAKE"

# --target 미지정 시 기본값: 템플릿 저장소의 부모 폴더에 <이름> 으로 생성
if [ -z "$TARGET" ]; then
  DEFAULT_TARGET="$(dirname "$SCRIPT_DIR")/$NAME"
  [ -t 0 ] && read -r -p "생성 위치 [$DEFAULT_TARGET]: " TARGET
  [ -z "$TARGET" ] && TARGET="$DEFAULT_TARGET"
fi

# ~ 확장 + 상대경로는 현재 위치 기준 절대경로화 (드라이브 문자 경로도 절대로 인식)
# '~' 단독 / '~/...' 만 확장한다 ('~user' 를 $HOME+user 로 오확장하지 않도록)
case "$TARGET" in
  "~")   TARGET="$HOME" ;;
  "~/"*) TARGET="$HOME${TARGET#\~}" ;;
  "~"*)  die "'~사용자' 형태 경로는 지원하지 않습니다 — 절대 경로를 사용하세요: $TARGET" ;;
esac
case "$TARGET" in
  /*) ;;                                                    # unix 절대경로
  [A-Za-z]:[\\/]*) TARGET="$(printf '%s' "$TARGET" | tr '\\' '/')" ;;  # windows 드라이브 경로 (git-bash)
  *) TARGET="$PWD/$TARGET" ;;
esac
TARGET="$(_canon_path "$TARGET")" || die "생성 위치를 해석할 수 없습니다: $TARGET"

# ⛔ 대상이 템플릿 저장소 자신·그 하위면 골격·문서가 덮이거나 토큰이 치환돼 템플릿이 망가진다.
#    대상이 템플릿의 상위면 토큰 치환이 템플릿 저장소까지 훑는다. 어느 경우든 무조건 중단한다.
if _path_within "$TARGET" "$SCRIPT_DIR"; then
  die "생성 위치가 템플릿 저장소 안입니다 — 템플릿 밖의 경로를 지정하세요: $TARGET"
fi
if _path_within "$SCRIPT_DIR" "$TARGET"; then
  die "생성 위치가 템플릿 저장소를 포함합니다 — 템플릿 밖의 별도 폴더를 지정하세요: $TARGET"
fi
if [ -e "$TARGET" ] && [ ! -d "$TARGET" ]; then
  die "생성 위치가 이미 파일로 존재합니다: $TARGET"
fi
# ⛔ 비어 있지 않은 폴더 위 재실행은 파괴적이다(사용자가 고친 골격 파일이 원본으로 되돌아간다).
#    대화형이면 확인을 받고, 비대화형(CI·스크립트)이면 중단한다 (scaffold.ps1 과 동일).
if [ -d "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  warn "대상 디렉토리가 비어있지 않습니다: $TARGET"
  if [ -t 0 ]; then
    read -r -p "  계속할까요? 기존 파일 위에 골격을 덮어씁니다 (y/N): " _overwrite_ans
    case "$_overwrite_ans" in
      [Yy]*) : ;;
      *) echo "중단합니다." >&2; exit 1 ;;
    esac
  else
    die "비대화형 실행이므로 중단합니다. 덮어쓰려면 대상 디렉터리를 비우거나 대화형으로 실행하세요."
  fi
fi
ok "이름=$NAME  snake=$SNAKE  위치=$TARGET"

# ---------- 2. 런타임 확인 (미달이면 bootstrap.sh 자동 실행) ----------
# 최소 버전 로드 (단일 출처 versions.env — _activate_version_managers 에서도 쓰므로 먼저 읽는다)
_BOOTSTRAP="$SCRIPT_DIR/skeleton/scripts/bootstrap.sh"
_VERSIONS_ENV="$SCRIPT_DIR/skeleton/scripts/versions.env"
if [ -f "$_VERSIONS_ENV" ]; then
  # shellcheck disable=SC1090
  . "$_VERSIONS_ENV"
fi

_ext_ver(){ printf '%s' "$1" | grep -oE '[0-9]+(\.[0-9]+){0,2}' | head -n1 || true; }
# _meets MIN HAVE -> HAVE >= MIN 이면 0(true). (sort -V 는 BSD·busybox 마다 달라 쓰지 않는다)
_meets(){
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

# 런타임 핀 로드 — ⚠️ 반드시 _activate_version_managers 보다 먼저 읽어야 한다.
# pyenv 는 "shim 이 PATH 에 있다"와 "어떤 버전을 쓴다"가 별개라, 활성화 시점에 핀 값이 필요하다.
_PY_PIN_FILE="$SKELETON_DIR/.python-version"
_PY_PIN=""
[ -f "$_PY_PIN_FILE" ] && _PY_PIN="$(head -n1 "$_PY_PIN_FILE" | tr -d '[:space:]')"

# pyenv 가 설치돼 있으면 셸 세션에 활성화 (시스템 Python 대신 버전 관리 도구 우선)
_activate_version_managers() {
  if command -v pyenv >/dev/null 2>&1; then
    export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
    export PATH="$PYENV_ROOT/bin:$PATH"
    # init 출력이 셸 코드가 아닐 수 있다(예: Git Bash 의 pyenv-win 은 "no such command" 를 stdout 으로 낸다).
    # 그대로 eval 하면 오류 출력이 섞이므로 실패를 무시한다 — 버전 선택은 PYENV_VERSION 으로 따로 한다.
    eval "$(pyenv init --path 2>/dev/null || true)" 2>/dev/null || true
    eval "$(pyenv init - 2>/dev/null || true)" 2>/dev/null || true
    # ⛔ pyenv init 은 shim 을 PATH 에 올릴 뿐 버전을 고르지 않는다.
    #    pyenv global 이 system(예: 3.9.6)이거나 비어 있으면 python3 는 system 을 가리키거나 실패해
    #    bootstrap 이 3.13 을 설치·재사용한 뒤에도 검증 단계에서 실패한다.
    #    ⚠️ 설치돼 있지 않은 버전을 지정하면 모든 shim 호출이 깨지므로 반드시 설치 여부를 확인한다.
    local _installed _v _pv=""
    _installed="$(pyenv versions --bare 2>/dev/null | tr -d '\r')"
    if [ -n "${_PY_PIN:-}" ] && printf '%s\n' "$_installed" | grep -qx "$_PY_PIN"; then
      export PYENV_VERSION="$_PY_PIN"
    else
      # 핀이 설치돼 있지 않으면 하한 계열(MIN_PYTHON.x) 설치본 중 가장 높은 것을 고른다 (system 폴백 방지)
      for _v in $_installed; do
        case "$_v" in "${MIN_PYTHON:-3.13}".*) ;; *) continue ;; esac
        printf '%s' "$_v" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || continue
        if [ -z "$_pv" ] || _meets "$_pv" "$_v"; then _pv="$_v"; fi
      done
      [ -n "$_pv" ] && export PYENV_VERSION="$_pv"
    fi
  fi
}
_activate_version_managers

# bootstrap 이 필요한 기준은 "런타임이 하한 미달"이다 (versions.env 정책: 이상이면 재사용).
# ⛔ pyenv 가 없다는 이유만으로 bootstrap 을 강제하지 않는다 — 이미 조건을 만족한 환경까지
# 골격 생성 전에 막아버린다.
_need_bootstrap=0
_bootstrap_reason=""
_PY="$(_ext_ver "$(python3 --version 2>/dev/null || true)")"
_meets "${MIN_PYTHON:-3.13}" "$_PY" || { _need_bootstrap=1; _bootstrap_reason="Python 하한(${MIN_PYTHON:-3.13}) 미달"; }
# skeleton/.python-version 핀 처리
#  - pyenv 가 있으면: 핀된 정확한 버전이 실제 설치돼 있어야 한다(없으면 bootstrap 이 설치 시도).
#  - pyenv 가 없으면: 핀을 강제할 수단이 없다. 하한을 충족하는 Python 을 쓰되 CI 와의 차이만 경고한다.
if [ -n "$_PY_PIN" ]; then
  if command -v pyenv >/dev/null 2>&1; then
    if [ "$_need_bootstrap" = "0" ] && ! pyenv versions --bare 2>/dev/null | tr -d '\r' | grep -qx "$_PY_PIN"; then
      _need_bootstrap=1
      _bootstrap_reason="pyenv 에 Python 핀($_PY_PIN) 미설치"
    fi
  elif [ "$_need_bootstrap" = "0" ]; then
    case "$_PY" in
      "$_PY_PIN"|"$_PY_PIN".*) : ;;
      *)
        warn "Python 핀($_PY_PIN)과 설치본($_PY)이 다릅니다 — CI 는 .python-version 을 읽으므로 로컬과 다른 버전을 씁니다."
        printf '        일치시키려면 pyenv 를 설치해 핀 버전을 쓰거나, 생성 후 프로젝트의 .python-version 을 설치본에 맞추세요.\n'
        ;;
    esac
  fi
fi

if [ "$_need_bootstrap" = "1" ]; then
  [ -f "$_BOOTSTRAP" ] || die "bootstrap.sh 를 찾을 수 없습니다 ($_BOOTSTRAP). 수동으로 먼저 실행하세요."
  warn "$_bootstrap_reason — bootstrap.sh 를 먼저 실행합니다 …"
  # ⛔ --project-root 없이 실행하면 bootstrap 이 핀 파일이 없을 때 템플릿의 skeleton/ 에 핀을 기록해
  #    리포를 오염시킬 수 있다. 템플릿 오염 방지용 임시 폴더를 넘기고, 끝나면 지운다.
  #    골격의 핀을 미리 심어 bootstrap 이 "기존 핀 존중" 경로를 타게 한다 — 빈 폴더면 bootstrap 이
  #    임의의 최신 패치를 골라 설치해, 생성 프로젝트의 핀(골격 값)과 다른 버전이 깔린다.
  #    bootstrap 은 핀이 이미 있으면 기록하지 않으므로, 생성 프로젝트의 핀은 언제나 골격 값이다.
  _PIN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/scaffold-pin.XXXXXX")" || die "임시 폴더를 만들 수 없습니다."
  [ -f "$_PY_PIN_FILE" ] && cp "$_PY_PIN_FILE" "$_PIN_DIR/.python-version"
  bash "$_BOOTSTRAP" --project-root "$_PIN_DIR" --skip-next-steps
  _rc=$?
  rm -rf "$_PIN_DIR"
  # 실패 문구는 scaffold.ps1 과 같은 두 갈래다.
  if [ "$_rc" -ne 0 ]; then
    warn "bootstrap.sh 종료 코드 $_rc"
    die "bootstrap 실패 — 스캐폴드를 중단합니다. 위 로그의 오류를 해결한 뒤 다시 실행하세요."
  fi
  _activate_version_managers                                    # bootstrap 후 현재 프로세스에 재적용

  # 검증 기준은 "런타임이 하한을 충족하는가"이지 "pyenv 가 설치됐는가"가 아니다 —
  # 관리자 없이 기존 설치본을 재사용하는 경로가 정상 경로이기 때문이다.
  _bootstrap_ok=1
  _PY="$(_ext_ver "$(python3 --version 2>/dev/null || true)")"
  _meets "${MIN_PYTHON:-3.13}" "$_PY" || _bootstrap_ok=0
  # 핀이 pyenv 에 설치됐는지는 경고 대상이지 중단 사유가 아니다. bootstrap 이 핀을 설치하지
  # 못해도 하한을 충족하는 Python 으로 폴백했을 수 있고, 위 런타임 검증을 이미 통과했다.
  if [ "$_bootstrap_ok" = "1" ] && [ -n "$_PY_PIN" ] && command -v pyenv >/dev/null 2>&1; then
    if ! pyenv versions --bare 2>/dev/null | tr -d '\r' | grep -qx "$_PY_PIN"; then
      warn "Python 핀 $_PY_PIN 이 pyenv 에 없습니다 — 하한을 충족하는 설치본으로 진행합니다. CI 는 핀을 사용합니다."
    fi
  fi
  [ "$_bootstrap_ok" = "1" ] || die "bootstrap 후에도 Python ${MIN_PYTHON:-3.13} 이상을 찾지 못했습니다 — 스캐폴드를 중단합니다."
fi

# ---------- 3. DB 접속 정보 ----------
# DB 접속 값 검사 — 값은 psql 인자·SQL 식별자·.env 의 DATABASE_URL 에 들어간다. 규칙은 scaffold.ps1 의 Assert-DbValues 와 같다.
#  - 이름: 영문자·숫자·'_' 1~63자(PostgreSQL 식별자 한도 — 넘으면 서버가 조용히 잘라 URL 과 어긋난다)
#  - 호스트: URL 에 인코딩 없이 들어가므로 허용 목록 — 호스트 이름·IPv4(영문자·숫자·'.'·'-'·'_') 또는 [IPv6]
#  - 사용자: 제어 문자·큰따옴표 금지(URL 에는 인코딩해 넣는다), 포트: 1~65535
#  - 비밀번호: URL 에는 인코딩해 넣으므로(%0A 등) 제한하지 않는다. ⛔ 그래서 .env 에 줄바꿈이 들어갈 수 없다.
#  로케일에 따라 A-Z 범위가 다른 문자를 포함할 수 있어 문자 집합을 명시한다(위 _alnum).
_check_db_values() {
  local _db_name_re="^[${_alnum}_]{1,63}\$"
  local _db_host_re="^([${_alnum}._-]{1,253}|\\[[0123456789ABCDEFabcdef:.]{2,45}\\])\$"
  [[ "$DB_NAME" =~ $_db_name_re ]] || die "DB 이름은 영문자·숫자·'_' 1~63자만 쓸 수 있습니다: $DB_NAME"
  [[ "$DB_HOST" =~ $_db_host_re ]] \
    || die "DB 호스트는 호스트 이름·IPv4(영문자·숫자·'.'·'-'·'_') 또는 [IPv6] 만 쓸 수 있습니다: $DB_HOST"
  case "$DB_USER" in
    ''|*[[:cntrl:]]*|*'"'*) die "DB 사용자는 1~63자이고 제어 문자·큰따옴표(\")를 쓸 수 없습니다." ;;
  esac
  [ "${#DB_USER}" -le 63 ] || die "DB 사용자는 1~63자이고 제어 문자·큰따옴표(\")를 쓸 수 없습니다."
  case "$DB_PORT" in
    ''|*[!0-9]*) die "DB 포트는 1~65535 여야 합니다: $DB_PORT" ;;
  esac
  { [ "${#DB_PORT}" -le 5 ] && [ "$DB_PORT" -ge 1 ] && [ "$DB_PORT" -le 65535 ]; } \
    || die "DB 포트는 1~65535 여야 합니다: $DB_PORT"
}
if [ $SKIP_DB -eq 0 ]; then
  step "PostgreSQL 접속 정보 (psql 로 DB 생성)"
  if [ -t 0 ]; then
    read -r -p "DB host [$DB_HOST]: " i; [ -n "$i" ] && DB_HOST="$i"
    read -r -p "DB port [$DB_PORT]: " i; [ -n "$i" ] && _set_port "$i"
    read -r -p "DB user [$DB_USER]: " i; [ -n "$i" ] && DB_USER="$i"
    [ -z "$DB_PASSWORD" ] && { read -r -s -p "DB password: " DB_PASSWORD; echo; }
    read -r -p "DB name [$DB_NAME]: " i; [ -n "$i" ] && DB_NAME="$i"
  fi
fi
# --skip-db 여도 값은 .env 의 DATABASE_URL 에 들어가므로 항상 검사한다.
_check_db_values

# psql 활성화 — 배포판·설치 방식에 따라 psql 이 PATH 에 없을 수 있다
# (macOS Postgres.app, Debian/Ubuntu 의 /usr/lib/postgresql/<ver>/bin, keg-only Homebrew formula).
# 설치돼 있는데도 DB 단계를 건너뛰지 않도록 표준 경로를 탐색해 PATH 에 추가한다.
enable_psql(){
  command -v psql >/dev/null 2>&1 && return 0
  _best=""; _best_ver=-1
  # Git Bash(Windows): %LOCALAPPDATA% 를 POSIX 경로로 바꾼다(없으면 빈 값 → 아래 경로는 존재하지 않아 건너뛴다).
  _lad=""
  if [ -n "${LOCALAPPDATA:-}" ] && command -v cygpath >/dev/null 2>&1; then _lad="$(cygpath -u "$LOCALAPPDATA")"; fi
  for _d in /Applications/Postgres.app/Contents/Versions/*/bin \
            /usr/lib/postgresql/*/bin \
            /usr/pgsql-*/bin \
            /opt/homebrew/opt/postgresql@*/bin \
            /usr/local/opt/postgresql@*/bin \
            "/c/Program Files/PostgreSQL/"*/bin \
            "/c/Program Files (x86)/PostgreSQL/"*/bin \
            "$_lad/Programs/PostgreSQL/"*/bin; do   # 마지막 세 줄은 Git Bash(Windows) 설치 경로
    [ -x "$_d/psql" ] || [ -x "$_d/psql.exe" ] || continue
    # bin 바로 위 폴더 이름의 첫 숫자 덩어리를 메이저 버전으로 본다 (없으면 0, scaffold.ps1 과 같다).
    # ⛔ 경로 전체에서 찾지 않는다 — "Program Files (x86)" 의 86 이나 사용자 이름의 숫자를 버전으로 오인한다.
    _v=$(printf '%s' "${_d%/bin}" | sed 's|.*/||' | grep -oE '[0-9]+' | head -n1)
    [ -n "$_v" ] || _v=0
    if [ "$_v" -gt "$_best_ver" ]; then _best_ver="$_v"; _best="$_d"; fi
  done
  if [ -n "$_best" ]; then
    PATH="$_best:$PATH"; export PATH
    ok "psql 을 PATH 에서 찾지 못해 설치 경로를 사용합니다: $_best"
  fi
}

# DB 사전 접속 검사 (psql 로 SELECT 1) — 접속 정보 입력 직후 1회 가볍게 확인한다.
# 실패하면 접속 실패 요지를 경고하고, 대화형이면 1회 재입력, 비대화형이면 DB 단계 전체를 건너뛴다.
# 여기서 DB_UNREACHABLE=1 이면 아래 DB 단계에서 CREATE DATABASE·alembic 을 모두 생략한다.
# psql 이 없으면 검사 불가 → 아래 DB 단계에서 'psql 없음' 으로 안내한다.
DB_UNREACHABLE=0
[ $SKIP_DB -eq 0 ] && enable_psql
if [ $SKIP_DB -eq 0 ] && command -v psql >/dev/null 2>&1; then
  _db_retried=0
  while :; do
    export PGPASSWORD="$DB_PASSWORD"
    # stderr 만 캡처(2>&1 >/dev/null): 성공 출력은 버리고 실패 메시지 요지만 취한다.
    _pc_err=$(psql -w -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1" 2>&1 >/dev/null)
    _pc_rc=$?
    unset PGPASSWORD
    [ "$_pc_rc" -eq 0 ] && break
    _pc_summary=$(printf '%s\n' "$_pc_err" | grep -v '^[[:space:]]*$' | tail -n1)
    warn "접속 실패: ${_pc_summary:-psql 연결에 실패했습니다}"
    if [ -t 0 ] && [ "$_db_retried" -eq 0 ]; then
      _db_retried=1
      printf "  ${c_yellow}[!]${c_reset}  접속정보를 다시 입력하세요 (1회 재시도, Enter 는 기존값 유지)\n"
      read -r -p "DB host [$DB_HOST]: " i; [ -n "$i" ] && DB_HOST="$i"
      read -r -p "DB port [$DB_PORT]: " i; [ -n "$i" ] && _set_port "$i"
      read -r -p "DB user [$DB_USER]: " i; [ -n "$i" ] && DB_USER="$i"
      read -r -s -p "DB password [기존값 유지]: " i; echo; [ -n "$i" ] && DB_PASSWORD="$i"
      read -r -p "DB name [$DB_NAME]: " i; [ -n "$i" ] && DB_NAME="$i"
      _check_db_values
      continue
    fi
    warn "DB 접속 불가로 판단 — DB 생성/마이그레이션 단계를 건너뜁니다"
    DB_UNREACHABLE=1
    break
  done
fi

# 사용자·비밀번호는 URL 인코딩해 DATABASE_URL 에 넣는다 (@ : / # ? % 줄바꿈 등 특수문자 안전).
# 호스트·이름은 위 _check_db_values 의 허용 목록을 통과한 값이라 인코딩이 필요 없다.
# ⛔ 인코딩 실패 시 원문 폴백을 두지 않는다 — 특수문자 비밀번호가 인코딩 없이 URL 에 들어가면
#    "생성은 성공했는데 DB 접속만 조용히 실패"하는 프로젝트가 나온다. 런타임 사전 검사(위)가
#    python3 를 보장하므로 이 실패는 비정상 상황이고, 즉시 중단이 맞다.
# 값은 인자가 아니라 환경변수로 넘긴다 — Git Bash 의 pyenv-win shim(.bat)은 인자의 & % 를 cmd 가
# 해석해 비밀번호가 잘린다(예: 'a&b' → 'a'). 환경변수는 셸·cmd 해석을 거치지 않는다.
_urlenc() {
  SCAFFOLD_URLENC="$1" python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["SCAFFOLD_URLENC"], safe=""))'
}
DB_USER_ENC="$(_urlenc "$DB_USER")" \
  || die "DB 사용자 URL 인코딩에 실패했습니다 (python3 확인) — 중단합니다."
DB_PASSWORD_ENC="$(_urlenc "$DB_PASSWORD")" \
  || die "DB 비밀번호 URL 인코딩에 실패했습니다 (python3 확인) — 중단합니다."
DATABASE_URL="postgresql+psycopg2://${DB_USER_ENC}:${DB_PASSWORD_ENC}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
# ⛔ 방어 이중화 — 제어 문자(줄바꿈 등)가 남아 있으면 .env 에 다른 키를 끼워 넣을 수 있다. 쓰기 전에 중단한다.
case "$DATABASE_URL" in *[[:cntrl:]]*) die "DATABASE_URL 에 제어 문자가 있습니다 — 중단합니다." ;; esac
# SECRET_KEY 는 Flask 서명 쿠키(flash·CSRF 토큰)의 서명키이므로 반드시 암호학적 난수여야 한다.
# ⛔ 타임스탬프 폴백(change-me-<epoch>)은 생성 시각만 추측하면 서명키가 복원되어 쿠키 위조로
#    직결된다 — 난수를 만들 수 없으면 약한 키로 진행하지 말고 즉시 중단한다.
#    32 bytes(64 hex) — 앱의 운영 하한(32 bytes)을 넉넉히 넘는다.
if command -v openssl >/dev/null 2>&1; then SECRET=$(openssl rand -hex 32)
elif command -v python3 >/dev/null 2>&1; then SECRET=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
else
  echo "SECRET_KEY 를 생성할 수 없습니다: openssl 또는 python3 가 필요합니다." >&2
  echo "  둘 중 하나를 설치한 뒤 다시 실행하세요 (서명키는 암호학적 난수여야 합니다)." >&2
  exit 1
fi

# 초기 관리자 비밀번호도 무작위로 생성한다.
# ⛔ 하드코딩된 기본값(admin123)을 쓰면 이 템플릿으로 만든 모든 프로젝트가 같은 자격증명을 갖는다.
#    타임스탬프 폴백(admin-<epoch>)도 같은 이유로 두지 않는다 — 위 SECRET 생성에서 openssl/python3
#    부재 시 이미 중단했으므로 여기서는 둘 중 하나가 반드시 존재한다.
if command -v openssl >/dev/null 2>&1; then SEED_ADMIN_PW=$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-16)
else SEED_ADMIN_PW=$(python3 -c 'import secrets;print(secrets.token_urlsafe(12))'); fi

# ---------- 4. 복사 ----------
step "골격 복사 → $TARGET"
mkdir -p "$TARGET" || die "대상 디렉토리 생성 실패: $TARGET"
# ⛔ cp -R 로 통째 복사하지 않는다 — 템플릿 저장소에서 개발/검증을 하면 skeleton/ 안에
#    .venv·.tools(Tailwind CLI 실행 파일, 100MB 이상)·업로드 같은 gitignore 산출물이 남는데,
#    그대로 복사되면 생성 프로젝트가 부풀고 아래 토큰 치환이 산출물을 붙잡는다.
#    실제 .env 가 복사되면 템플릿의 SECRET_KEY 가 새 프로젝트로 새는 보안 문제도 된다.
#    tar 는 GNU/bsdtar 모두 --exclude 를 지원하므로 산출물·비밀을 원천 제외하고 복사한다.
_tar_ex=""
for _e in $COPY_EXCLUDES; do _tar_ex="$_tar_ex --exclude $_e"; done
# shellcheck disable=SC2086  # $_tar_ex 는 공백으로 나뉘어야 하는 옵션 나열이다
if ! (cd "$SKELETON_DIR" && tar cf - $_tar_ex .) | (cd "$TARGET" && tar xf -); then
  die "골격 복사 실패 (권한/디스크 확인) — 중단합니다"
fi
ok "복사 완료"

# 생성 기준 기록 — 템플릿의 이후 수정은 생성 프로젝트에 자동으로 반영되지 않는다. 어떤 수정을 옮길지
# flask-starter CHANGELOG 와 비교하는 기준으로 커밋을 남긴다(git 이 없거나 zip 으로 받았으면 unknown,
# 커밋하지 않은 변경이 있으면 -dirty). 내용은 scaffold.ps1 과 같다(LF, BOM 없음).
STARTER_REV="unknown"
if command -v git >/dev/null 2>&1 && _rev=$(git -C "$SCRIPT_DIR" rev-parse --short=7 HEAD 2>/dev/null) && [ -n "$_rev" ]; then
  STARTER_REV="$_rev"
  git -C "$SCRIPT_DIR" diff --quiet HEAD -- 2>/dev/null || STARTER_REV="$STARTER_REV-dirty"
fi
cat > "$TARGET/.flask-starter" <<EOF || die ".flask-starter 생성 실패 — 중단합니다"
# 이 프로젝트를 생성한 flask-starter 커밋 — 템플릿의 이후 수정은 자동으로 반영되지 않는다.
# 옮길 변경은 flask-starter 의 CHANGELOG.md 에서 이 커밋 이후 항목을 보고 고른다(README 「템플릿 수정 반영」).
commit=$STARTER_REV
EOF
ok "생성 기준 기록: .flask-starter (commit=$STARTER_REV)"

# ---------- 5. 토큰 치환 ----------
step "토큰 치환"
# ⛔ bash 의 ${var//…} 로 치환하지 않는다 — macOS 기본 bash 3.2 의 패턴 치환은 문자열 길이에
#    사실상 제곱으로 느려져(특히 UTF-8 한국어 문서, LC_ALL=C 로도 부족) 큰 문서 하나에
#    수십 초가 걸린다. python3 는 이 스크립트의 사전 요구이므로 단일 프로세스로 처리한다.
#    바이트 치환(토큰은 ASCII)이라 인코딩·줄바꿈이 원본 그대로 보존된다(scaffold.ps1 의 Latin-1 치환과 동일).
# 복사 단계가 산출물을 제외하지만, 기존 디렉토리 위에 덮어쓴 재실행(이미 install/build 된
# 프로젝트)에서는 .venv·.tools 가 남아 있다 — 디렉터리 이름으로 가지치기해 산출물을
# 붙잡지 않는다(방어 이중화). 대상 아래만 걸으므로 대상 경로 자체에 같은 이름이 있어도 무관하다.
# 변경된 파일만 재기록한다(재실행 시 불필요한 mtime 변경 방지 — scaffold.ps1 과 동일).
# 값은 환경변수로 넘긴다(위 _urlenc 와 같은 이유). Git Bash(Windows python)에서는 경로를 cygpath 로
# C:/… 형태로 바꿔 넘긴다 — MSYS 자동 경로 변환은 환경변수·[ ] 가 든 인자에 적용되지 않는다.
_TARGET_NATIVE="$TARGET"
command -v cygpath >/dev/null 2>&1 && _TARGET_NATIVE="$(cygpath -m "$TARGET")"
SCAFFOLD_NAME="$NAME" SCAFFOLD_SNAKE="$SNAKE" SCAFFOLD_TARGET="$_TARGET_NATIVE" \
SCAFFOLD_PRUNE="$PRUNE_DIRS" SCAFFOLD_EXTS="$TOKEN_EXTENSIONS" python3 - <<'PYEOF' \
  || die "토큰 치환 실패 — 중단합니다"
import os
import sys

env = os.environ
target = env["SCAFFOLD_TARGET"]
prune, exts = set(env["SCAFFOLD_PRUNE"].split()), set(env["SCAFFOLD_EXTS"].split())
# 경로를 못 찾으면 os.walk 가 조용히 0건으로 끝나 토큰이 남는다 — 실패로 알린다
if not os.path.isdir(target):
    sys.exit(f"치환 대상 폴더를 찾을 수 없습니다: {target}")
tokens = [
    (b"__PROJECT_NAME__", os.fsencode(env["SCAFFOLD_NAME"])),
    (b"__PROJECT_SNAKE__", os.fsencode(env["SCAFFOLD_SNAKE"])),
]

# os.walk 는 기본값(followlinks=False)으로 링크 폴더를 따라가지 않는다. 링크 파일도 건너뛴다 —
# 쓰기가 링크 너머의 대상 밖 원본에 닿는다(scaffold.ps1 의 ReparsePoint 건너뛰기와 같다).
for root, dirs, files in os.walk(target):
    dirs[:] = [d for d in dirs if d not in prune]
    for fn in files:
        if os.path.splitext(fn)[1] not in exts:
            continue
        path = os.path.join(root, fn)
        if os.path.islink(path):
            continue
        with open(path, "rb") as fh:
            content = fh.read()
        new = content
        for token, value in tokens:
            new = new.replace(token, value)
        if new != content:
            with open(path, "wb") as fh:
                fh.write(new)
PYEOF
ok "치환 완료"

# ---------- 6. .env ----------
step ".env 생성 (OS 무관 주입 — ARCHITECTURE.md §5)"
# ⛔ 기존 .env 를 덮어쓰면 SECRET_KEY 가 재발급되어 flash·CSRF 쿠키가 전부 무효가 되고,
#    손으로 채운 DB 비밀번호도 사라진다. 백업을 남긴 뒤 새로 쓴다.
#    cp 는 umask 기준 권한(보통 644)으로 새 파일을 만들어 비밀이 다른 사용자에게 읽힐 수 있다 —
#    mv(권한 유지) 후 chmod 600 으로 백업도 소유자 전용으로 둔다.
if [ -f "$TARGET/.env" ]; then
  _env_bak="$TARGET/.env.bak.$(date +%Y%m%d%H%M%S)"
  mv "$TARGET/.env" "$_env_bak" || die "기존 .env 백업 실패 — 중단합니다"
  if ! chmod 600 "$_env_bak" 2>/dev/null; then
    warn "백업 파일 권한 제한 실패 — 직접 chmod 600 하거나 삭제하세요: $_env_bak"
    _incomplete ".env 백업 권한 제한"
  fi
  warn "기존 .env 를 백업했습니다: $(basename "$_env_bak")"
fi
# ⛔ .env 는 DB 비밀번호와 서명키를 담는다 — umask 077 로 처음부터 소유자 전용으로 만든다.
#    키 집합은 .env.example 과 같아야 한다(설명은 그 파일 참고, scaffold.ps1 과 동일).
( umask 077 && cat > "$TARGET/.env" ) <<EOF || die ".env 생성 실패 — 중단합니다"
DATABASE_URL=$DATABASE_URL
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=$SECRET
# 로그인 세션·시도 제한 (ARCHITECTURE.md §9) — 코드 기본값과 같지만, 운영자가 .env 만 보고도
# 조절 지점을 알 수 있도록 명시한다.
REFRESH_TOKEN_EXPIRE_DAYS=14
LOGIN_MAX_FAILURES=5
LOGIN_LOCKOUT_MINUTES=15
# 운영(HTTPS)에서는 true 로 바꾼다 (APP_ENV=production + false 면 기동 거부).
COOKIE_SECURE=false
# HTTPS 를 끝내는 리버스 프록시(nginx) 뒤에서 운영하면 1 로 바꾼다(앱을 바로 노출하면 0).
TRUSTED_PROXY_HOPS=0
# 업로드 저장소·크기 상한 — 값은 .env.example 과 같다(설명은 그 파일 참고).
UPLOAD_DIR=uploads
PUBLIC_FILES_BASE_URL=
MAX_IMAGE_UPLOAD_MB=5
MAX_ATTACHMENT_UPLOAD_MB=20
TZ=Asia/Seoul
# 초기 관리자 시드 — 코드 기본값은 꺼져 있고(app/config.py) 개발 편의를 위해 여기서만 켠다.
# ⛔ 배포 전 SEED_DEFAULT_ADMIN=false 로 끄고 APP_ENV=production 으로 바꾼다.
SEED_DEFAULT_ADMIN=true
DEFAULT_ADMIN_PASSWORD=$SEED_ADMIN_PW
EOF
if ! chmod 600 "$TARGET/.env" 2>/dev/null; then
  warn ".env 권한 설정 실패 — 수동으로 chmod 600 하세요"
  _incomplete ".env 권한 제한"
fi
ok ".env 생성 (DATABASE_URL, SECRET_KEY 주입)"

# venv 안의 python — macOS/Linux 는 bin/, Git Bash(Windows) 는 Scripts/
_venv_py() {
  if [ -x "$TARGET/.venv/bin/python" ]; then printf '%s' "$TARGET/.venv/bin/python"
  elif [ -x "$TARGET/.venv/Scripts/python.exe" ]; then printf '%s' "$TARGET/.venv/Scripts/python.exe"
  else return 1; fi
}
# 안내 문구용 venv python 경로 (Git Bash 는 Scripts/)
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) VPY_HINT=".venv/Scripts/python" ;;
  *) VPY_HINT=".venv/bin/python" ;;
esac

# ---------- 7. Python 의존성 설치 ----------
if [ $SKIP_INSTALL -eq 0 ]; then
  step "venv + 의존성 설치"
  if ! command -v python3 >/dev/null 2>&1; then
    warn "python3 없음 — 의존성 설치 건너뜀"
    _incomplete "venv·의존성 설치 (python3 없음)"
  elif ! ( cd "$TARGET" && python3 -m venv .venv ) || ! _VPY="$(_venv_py)"; then
    warn "venv 생성 실패 — 'python3 -m venv .venv' 로 직접 확인하세요"
    _incomplete "venv 생성"
  else
    # ⛔ pip 자체를 --upgrade 로 올리지 않는다(고정되지 않은 최신 pip 를 받는다). venv 에 딸린 pip 로
    #    전이 의존성까지 해시로 고정한 requirements.lock 을 설치한다 — 해시가 다른 파일은 설치하지 않는다(scaffold.ps1 과 같다).
    if ( cd "$TARGET" && "$_VPY" -m pip install --require-hashes -r requirements.lock ); then
      ok "의존성 설치 완료"
    else
      warn "pip install 미완료 — '$VPY_HINT -m pip install --require-hashes -r requirements.lock'"
      _incomplete "의존성 설치 (pip install)"
    fi
  fi
else warn "skip-install: 의존성 설치 건너뜀"; fi

# ---------- 8. DB + 테이블(Alembic) ----------
# DB 수동 실행 안내(한 블록만) — CREATE DATABASE·alembic 을 모두 건너뛸 때 보여준다(scaffold.ps1 과 같은 형식).
# 명령 인자 대신 "접속 후 실행할 SQL" 로 보여준다 — 셸마다 다른 따옴표 규칙 때문에 이름에 대문자·'-' 가 있으면
# -c 인자 한 줄로는 두 셸 모두에서 맞게 쓸 수 없다. 이름은 항상 큰따옴표 식별자로 인용한다.
_db_manual_guide() {
  warn "$1 — 다음을 수동 실행:"
  printf "        1) DB 생성·시각대: psql -h %s -p %s -U %s -d postgres 로 접속해 실행\n" "$DB_HOST" "$DB_PORT" "$DB_USER"
  printf "             CREATE DATABASE \"%s\";\n" "$DB_NAME"
  printf "             ALTER DATABASE \"%s\" SET timezone TO 'Asia/Seoul';\n" "$DB_NAME"
  printf "        2) 테이블 생성:    %s -m alembic upgrade head\n" "$VPY_HINT"
  _incomplete "$2"
}
_db_unreachable_guide() {
  _db_manual_guide "DB 접속 불가(접속정보 host/port/user/password 확인)" "DB 생성·마이그레이션 (접속 불가)"
}
# SQL 을 표준입력으로 psql 에 넘긴다 (PGPASSWORD 는 호출 동안만 설정).
# DB 이름은 -v dbname=… 변수로 넘기고 SQL 안에서 :"dbname"(식별자)·:'dbname'(문자열)로 인용한다
# (scaffold.ps1 과 동일 — 인자에 따옴표를 넣지 않아 셸마다 다른 인용 규칙을 피한다).
_psql_script() {
  local _tuples=""
  [ "${2:-}" = "tuples" ] && _tuples="-tA"
  # shellcheck disable=SC2086  # $_tuples 는 비어 있거나 옵션 하나다
  printf '%s\n' "$1" | PGPASSWORD="$DB_PASSWORD" psql -w -X -q -v ON_ERROR_STOP=1 -v "dbname=$DB_NAME" \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres $_tuples
}
# alembic upgrade — 실패해도 traceback 전체를 쏟지 않고 마지막 몇 줄(핵심 에러) + 임시 로그 경로만 안내.
_run_alembic() {
  if [ $SKIP_INSTALL -ne 0 ]; then
    warn "skip-install: alembic 미실행. '$VPY_HINT -m alembic upgrade head'"
    return
  fi
  if ! _VPY="$(_venv_py)"; then
    warn "venv 미설치 — '$VPY_HINT -m alembic upgrade head' 수동 실행"
    _incomplete "테이블 생성 (alembic — venv 없음)"
    return
  fi
  step "Alembic: 테이블 생성 (upgrade head) — DB는 항상 Alembic으로 관리 §11"
  _alembic_log="$(mktemp 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}/scaffold-alembic.$$.log")"
  if ( cd "$TARGET" && "$_VPY" -m alembic upgrade head ) >"$_alembic_log" 2>&1; then
    ok "테이블 생성 완료"
    rm -f "$_alembic_log"
  else
    warn "alembic 실패 — 핵심 오류(마지막 6줄):"
    tail -n 6 "$_alembic_log" 2>/dev/null | sed 's/^/        /'
    warn "전체 로그: $_alembic_log"
    warn "수동 재실행: $VPY_HINT -m alembic upgrade head"
    _incomplete "테이블 생성 (alembic upgrade head)"
  fi
}
if [ $SKIP_DB -eq 0 ]; then
  step "PostgreSQL: 데이터베이스 생성"
  enable_psql
  if ! command -v psql >/dev/null 2>&1; then
    warn "PostgreSQL 이 설치돼 있다면 bin 디렉터리를 PATH 에 추가하세요."
    _db_manual_guide "psql 없음(PATH·표준 설치 경로 모두)" "DB 생성·마이그레이션 (psql 없음)"
  elif [ "$DB_UNREACHABLE" = "1" ]; then
    # 사전 검사에서 이미 접속 불가로 판정 — 조회/생성/alembic 모두 생략하고 안내만.
    _db_unreachable_guide
  else
    exists=$(_psql_script "SELECT 1 FROM pg_database WHERE datname = :'dbname';" tuples 2>/dev/null)
    _q_rc=$?
    exists="$(printf '%s' "$exists" | tr -d '[:space:]')"
    if [ "$_q_rc" -ne 0 ]; then
      # 사전 검사 이후 접속이 끊긴 경우 — 접속 실패로 보고 CREATE·alembic 모두 건너뛴다.
      _db_unreachable_guide
    elif [ "$exists" = "1" ]; then
      warn "DB 이미 존재: $DB_NAME"
      _run_alembic
    elif _psql_script 'CREATE DATABASE :"dbname";'; then
      ok "DB 생성: $DB_NAME"
      # ⛔ 공통 계층은 세션 시각대 KST 를 전제한다(ARCHITECTURE.md KST 단일 기준). 앱 연결은 스스로
      #    맞추지만 psql·ETL 같은 외부 접속도 KST 로 보이도록 DB 기본값을 고정한다.
      if _psql_script "ALTER DATABASE :\"dbname\" SET timezone TO 'Asia/Seoul';"; then
        ok "DB 기본 시각대: Asia/Seoul"
      else
        warn "DB 시각대 설정 실패 — 수동: ALTER DATABASE \"$DB_NAME\" SET timezone TO 'Asia/Seoul'"
        _incomplete "DB 기본 시각대 설정 (ALTER DATABASE … timezone)"
      fi
      _run_alembic
    else
      warn "DB 생성 실패 — 접속정보 확인 후 수동으로 DB 생성/alembic 실행"
      _incomplete "DB 생성 (CREATE DATABASE)"
    fi
  fi
else warn "skip-db: DB 생성/마이그레이션 건너뜀"; fi

# ---------- 9. CSS 빌드 (Tailwind standalone CLI) ----------
# CLI 는 생성 프로젝트의 .tools/ 에 내려받고 scripts/tailwind-sha256sums.txt 로 검증한다(Node 불필요).
# Git Bash(Windows) 에서는 tailwind.sh 가 Windows 바이너리를 다루지 않으므로 tailwind.ps1 을 부른다.
if [ -n "${COMSPEC:-}" ] && command -v powershell.exe >/dev/null 2>&1; then
  _css_cmd=(powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$TARGET/scripts/tailwind.ps1" 2>/dev/null || printf '%s' "$TARGET/scripts/tailwind.ps1")")
  CSS_HINT='powershell -ExecutionPolicy Bypass -File .\scripts\tailwind.ps1'
  CSS_WATCH_HINT='powershell -ExecutionPolicy Bypass -File .\scripts\tailwind.ps1 -Watch'
else
  _css_cmd=(bash "$TARGET/scripts/tailwind.sh")
  CSS_HINT='./scripts/tailwind.sh'
  CSS_WATCH_HINT='./scripts/tailwind.sh --watch'
fi
if [ $SKIP_INSTALL -eq 0 ]; then
  step "CSS 빌드 (Tailwind standalone CLI)"
  if ( cd "$TARGET" && "${_css_cmd[@]}" ); then
    ok "app/static/css/app.css 빌드 완료"
  else
    warn "CSS 빌드 미완료 — 네트워크 확인 후 '$CSS_HINT' 로 다시 실행하세요"
    _incomplete "CSS 빌드 (Tailwind)"
  fi
else warn "skip-install: CSS 빌드 건너뜀"; fi

# ---------- 10. 안내 ----------
step "실행 방법"
# --skip-install 은 사용자가 고른 생략이라 미완료(종료 코드 2)로 세지 않는다. 대신 아래 [앱] 명령이 쓰는
# venv 가 없으므로 생략한 설치 단계를 먼저 안내한다(scaffold.ps1 과 같다).
if [ $SKIP_INSTALL -ne 0 ]; then
  printf '[설치]    --skip-install 로 생략한 단계를 먼저 실행 (Python %s 이상):\n' "${MIN_PYTHON:-3.13}"
  printf '  cd "%s"\n' "$TARGET"
  printf '  python3 -m venv .venv\n'
  printf '  %s -m pip install --require-hashes -r requirements.lock\n' "$VPY_HINT"
  [ $SKIP_DB -eq 0 ] && printf '  %s -m alembic upgrade head\n' "$VPY_HINT"
  printf '  %s\n\n' "$CSS_HINT"
fi
cat <<EOF
[앱]      새 터미널에서:
  cd "$TARGET"
  $VPY_HINT -m flask --app app.main run --debug --port $APP_PORT

[CSS]     템플릿을 고치는 동안 또 다른 터미널에서 (변경을 감시해 다시 빌드한다):
  cd "$TARGET"
  $CSS_WATCH_HINT

[로그인]  초기 관리자 계정 (.env 의 DEFAULT_ADMIN_PASSWORD):
  아이디: admin
  비밀번호: $SEED_ADMIN_PW
$DEPLOY_NOTE

[확인]    브라우저: http://localhost:$APP_PORT
          → 공개 홈 화면이 보이면 성공입니다. admin 으로 로그인한 뒤 관리자 대시보드에서
            'DB 정상'과 마이그레이션 리비전이 보이는지 확인하세요.

[DB 변경] 모델 수정 시 (ARCHITECTURE.md §11):
  cd "$TARGET"
  $VPY_HINT -m alembic revision --autogenerate -m "변경요약"
  $VPY_HINT -m alembic upgrade head
EOF

# ---------- 결과 요약 ----------
step "결과 요약"
if [ "$_INCOMPLETE_N" -gt 0 ]; then
  warn "골격은 생성됐지만 미완료 단계가 ${_INCOMPLETE_N}개 있습니다 — 위 안내대로 마무리하세요 (종료 코드 2):"
  printf '%s' "$_INCOMPLETE" | while IFS= read -r _m; do
    [ -n "$_m" ] && printf '        - %s\n' "$_m"
  done
  exit 2
fi
ok "모든 단계 완료"
exit 0
