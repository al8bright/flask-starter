#!/usr/bin/env bash
# 갱신 배포 — 서버(Linux)에서 프로젝트 루트의 배포 계정으로 실행한다:  ./deploy/deploy.sh
# 소스 최신화 → 패키지 → CSS 빌드 → DB 마이그레이션 → 재기동 → 상태 확인. 한 단계라도 실패하면 멈춘다.
# 최초 설치(실행 계정·서비스·nginx·인증서·운영 .env·마이그레이션 접속 정보)는 deploy/README.md 를 따른다.
# ⛔ root 로 실행하지 않는다 — 코드·.venv 가 root 소유가 되면 배포 계정이 다시 고칠 수 없다.
# sudo 가 필요한 단계는 재기동(systemctl restart)과 상태 확인(nginx 계정으로 소켓 접속)뿐이다.
# 서비스 이름·소켓 경로를 바꾸면 deploy/app.service·deploy/nginx.conf 와 같이 고친다.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SERVICE=__PROJECT_SNAKE__
SOCKET=/run/__PROJECT_SNAKE__/gunicorn.sock
HEALTH_PATH=/api/v1/health/db
# 마이그레이션 전용 접속 정보(DB 소유 계정) — root:배포 계정 0640, 앱 실행 계정은 읽지 못한다.
MIGRATE_ENV=/etc/__PROJECT_SNAKE__/migrate.env

die() { echo "$1" >&2; exit 1; }
step() { printf '\n== %s\n' "$1"; }

# KEY=VALUE 파일에서 마지막 KEY 값을 읽는다(셸로 source 하지 않는다). 감싼 따옴표와 CR 은 벗긴다.
read_env_value() {
  local key="$1" file="$2" value
  value=$(sed -n "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//p" "$file" | tail -n 1 | tr -d '\r')
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

[ "$(id -u)" -ne 0 ] || die "root 로 실행하지 않습니다 — 코드 폴더를 소유한 배포 계정으로 실행하세요."

cd "$APP_DIR"
# 새 파일을 앱 실행 계정(다른 사용자)이 읽을 수 있게 하고, 그룹 쓰기는 주지 않는다.
umask 0022

[ -x .venv/bin/python ] || die ".venv 가 없습니다 — deploy/README.md 「최초 설치」를 먼저 따르세요."
[ -f .env ] || die ".env 가 없습니다 — 운영 .env 를 먼저 만드세요(deploy/README.md)."
[ -r .env ] || die ".env 를 읽을 수 없습니다 — 배포 계정이 $SERVICE 그룹에 속하는지 확인하세요(deploy/README.md)."
app_env=$(read_env_value APP_ENV .env)
[ "$app_env" = production ] || die ".env 의 APP_ENV 가 production 이 아닙니다(현재: '${app_env}') — 운영 .env 를 확인하세요."
[ -r "$MIGRATE_ENV" ] || die "$MIGRATE_ENV 를 읽을 수 없습니다 — 마이그레이션 접속 정보를 먼저 만드세요(deploy/README.md)."
migrate_url=$(read_env_value DATABASE_URL "$MIGRATE_ENV")
[ -n "$migrate_url" ] || die "$MIGRATE_ENV 에 DATABASE_URL 이 없습니다."

step "소스"
before=$(git rev-parse --short HEAD)
git pull --ff-only
after=$(git rev-parse --short HEAD)
echo "$before -> $after"

step "패키지"
[ -f requirements.lock ] || die "requirements.lock 이 없습니다."
.venv/bin/python -m pip install --require-hashes -r requirements.lock

step "CSS"
./scripts/tailwind.sh

step "DB 마이그레이션"
# 프로세스 환경변수가 .env 의 DATABASE_URL 보다 우선한다(pydantic-settings) — 이 두 명령에만 소유 계정을 쓴다.
DATABASE_URL="$migrate_url" .venv/bin/alembic upgrade head
DATABASE_URL="$migrate_url" .venv/bin/alembic current
unset migrate_url

step "재기동"
sudo systemctl restart "$SERVICE"

step "상태 확인"
# nginx 는 /api/v1/health/db 를 외부에 막는다 — 소켓에 접근할 수 있는 nginx 계정(www-data)으로 직접 묻는다.
for _ in $(seq 1 20); do
  if body=$(sudo -u www-data curl -fsS -m 3 --unix-socket "$SOCKET" "http://localhost${HEALTH_PATH}" 2>/dev/null); then
    echo "$body"
    echo "배포 완료: $after"
    exit 0
  fi
  sleep 1
done
die "상태 확인 실패 — journalctl -u $SERVICE -n 50 --no-pager"
