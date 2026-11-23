#!/usr/bin/env bash
# Tailwind CSS 빌드 (macOS/Linux) — Node 없이 standalone CLI 를 쓴다 (ARCHITECTURE.md §15).
# Windows 는 scripts/tailwind.ps1 을 사용한다. 동작은 동일하다.
#
# 사용 (프로젝트 루트에서):
#   ./scripts/tailwind.sh            최소화 빌드 (배포·커밋 전)
#   ./scripts/tailwind.sh --watch    개발 중 변경 감시
#
# CLI 는 처음 한 번 .tools/ 에 내려받고, scripts/tailwind-sha256sums.txt 의 SHA-256 과 맞을 때만 쓴다.
# 입력: app/static/css/input.css → 출력: app/static/css/app.css (.gitignore 대상)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
VERSION="$(sed -n 's/^TAILWIND_VERSION=//p' "$ROOT/scripts/versions.env" | tr -d '\r')"
[ -n "$VERSION" ] || { echo "scripts/versions.env 에 TAILWIND_VERSION 이 없습니다." >&2; exit 1; }

case "$(uname -s)" in
  Linux)  os=linux ;;
  Darwin) os=macos ;;
  *) echo "지원하지 않는 OS 입니다: $(uname -s) (Windows 는 scripts/tailwind.ps1)" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64)  arch=x64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) echo "지원하지 않는 CPU 입니다: $(uname -m)" >&2; exit 1 ;;
esac
suffix=""
if [ "$os" = linux ] && ldd --version 2>&1 | grep -qi musl; then suffix="-musl"; fi
ASSET="tailwindcss-${os}-${arch}${suffix}"
BIN="$ROOT/.tools/tailwindcss-${VERSION}-${os}-${arch}${suffix}"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

if [ ! -x "$BIN" ]; then
  expected="$(awk -v a="$ASSET" '$2 == a { print $1 }' "$ROOT/scripts/tailwind-sha256sums.txt")"
  [ -n "$expected" ] || { echo "tailwind-sha256sums.txt 에 $ASSET 항목이 없습니다." >&2; exit 1; }
  mkdir -p "$ROOT/.tools"
  tmp="$BIN.download"
  echo "Tailwind CSS v$VERSION ($ASSET) 내려받는 중…"
  curl -fsSL -o "$tmp" "https://github.com/tailwindlabs/tailwindcss/releases/download/v${VERSION}/${ASSET}"
  actual="$(sha256_of "$tmp")"
  if [ "$actual" != "$expected" ]; then
    rm -f "$tmp"
    echo "⛔ SHA-256 불일치 — 내려받은 파일을 쓰지 않습니다 (기대 $expected, 실제 $actual)." >&2
    exit 1
  fi
  chmod +x "$tmp"
  mv "$tmp" "$BIN"
fi

args=(-i "$ROOT/app/static/css/input.css" -o "$ROOT/app/static/css/app.css")
if [ "${1:-}" = "--watch" ]; then
  exec "$BIN" "${args[@]}" --watch
fi
exec "$BIN" "${args[@]}" --minify
