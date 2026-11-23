#!/usr/bin/env bash
# 갱신 배포 — 서버(Linux)에서 프로젝트 루트의 배포 계정으로 실행한다:  ./deploy/deploy.sh
# 소스 최신화 → 패키지 → CSS 빌드 → DB 마이그레이션 → 재기동 → 상태 확인. 한 단계라도 실패하면 멈춘다.
# 최초 설치(서비스·nginx·인증서·운영 .env)는 deploy/README.md 를 따른다.
# 재기동에 sudo 가 필요하다(systemctl restart). 서비스 이름·포트를 바꾸면 deploy/app.service 와 같이 고친다.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SERVICE=__PROJECT_SNAKE__
HEALTH_URL=http://127.0.0.1:8000/api/v1/health/db

cd "$APP_DIR"
step() { printf '\n== %s\n' "$1"; }

[ -x .venv/bin/python ] || { echo ".venv 가 없습니다 — deploy/README.md 「최초 설치」를 먼저 따르세요." >&2; exit 1; }
[ -f .env ] || { echo ".env 가 없습니다 — 운영 .env 를 먼저 만드세요(deploy/README.md)." >&2; exit 1; }

step "소스"
before=$(git rev-parse --short HEAD)
git pull --ff-only
after=$(git rev-parse --short HEAD)
echo "$before -> $after"

step "패키지"
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -m pip check

step "CSS"
./scripts/tailwind.sh

step "DB 마이그레이션"
.venv/bin/alembic upgrade head
.venv/bin/alembic current

step "재기동"
sudo systemctl restart "$SERVICE"

step "상태 확인"
for _ in $(seq 1 20); do
  if body=$(curl -fsS -m 3 "$HEALTH_URL" 2>/dev/null); then
    echo "$body"
    echo "배포 완료: $after"
    exit 0
  fi
  sleep 1
done
echo "상태 확인 실패 — journalctl -u $SERVICE -n 50 --no-pager" >&2
exit 1
