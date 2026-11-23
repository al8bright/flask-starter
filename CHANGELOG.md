# Changelog

스캐폴드 템플릿 `flask-starter` 의 변경 이력.
형식은 [Keep a Changelog](https://keepachangelog.com/)를 느슨히 따른다.

오래된 항목은 `docs/archive/changelog/` 에 연도별로 보관한다(규칙은 `AGENTS.md` 「문서 갱신」).

---

## 2026-11-23 — 재개발: FastAPI 형제 템플릿 구조로 전환

진행 계획과 남은 단계는 [`TODO.md`](TODO.md) 에 있다. 재개발 전 상태(코드 생성기 방식)는 `legacy-scaffolder` 태그에 있다.
저장소 이름은 `flask-starter` 를 유지한다(`flask-pg-starter` 로 바꾸려던 계획은 철회하였다).

### Removed (제거)

- 기존 Flask 프로젝트 생성기(CLI·i18n·게시판 예제)를 제거하였다(`d724356`).

### Added (추가)

- **`skeleton/`**: Flask 3 + Jinja + htmx + PostgreSQL 골격(`b5d6081`).
  - 공통 계층(`config`·`cli`·`core`·`db`·`models`·`schemas`·`services`·`alembic` 과 테스트 5개)을 `fastapi-react-pg-starter` 의 `skeleton/backend/` 에서 파일 그대로 복사하였다. 원본과 파일 단위로 같음을 diff 로 확인하였다.
  - 웹 계층: 앱 팩토리(`app/main.py`), 요청별 DB 세션·현재 사용자·권한 데코레이터(`app/dependencies.py`), 블루프린트(`public`·`auth`·`admin`·`api`·`files`), 오류 응답(JSON·htmx alert·오류 페이지), 보안 헤더(CSP `script-src 'self'`·`style-src 'self'`).
  - 인증: `auth_sessions` 불투명 토큰을 httpOnly·SameSite=Lax 쿠키로 보내고 요청마다 DB 에서 확인한다. CSRF 는 Flask-WTF `CSRFProtect` 전역.
  - 화면: 공개 홈·공지 목록/상세, 로그인, 관리자 대시보드·사용자·세션·공지(첨부·본문 이미지)·배너. htmx 예제 3곳(공지 검색·사용자 행 저장·배너 순서 변경), htmx 2.0.11 벤더링.
  - Tailwind CSS v4.3.5 standalone CLI 빌드 스크립트(`scripts/tailwind.*`) — SHA-256 을 확인한 바이너리만 쓴다.
- **`scaffold.sh`·`scaffold.ps1`**, **`skeleton/scripts/bootstrap.*`**: 형제 템플릿 스크립트를 바탕으로 프론트엔드(pnpm)·DESIGN.md 테마 단계를 빼고, `.env` 를 프로젝트 루트에 만들고, Tailwind 빌드 단계를 넣었다. bootstrap 은 Python·PostgreSQL 만 다룬다(`3cc11cb`).
- **문서**: 루트 `README.md`·`AGENTS.md`·`CLAUDE.md`·`CHANGELOG.md`·`docs/README.md`·`.gitignore`, 생성 프로젝트용 `skeleton/README.md`·`AGENTS.md`·`CLAUDE.md`·`PLAN.md`·`docs/README.md` 와 스킬 5종(`add-domain`·`db-migration`·`add-screen`·`pr-workflow`·`stack-versions`). `skeleton/scripts/versions.env` 에 벤더링한 htmx 버전(`HTMX_VERSION`)을 기록하였다.

### Fixed (수정)

- `bootstrap.sh`: Git Bash + pyenv-win 에서 `pyenv install --list` 출력이 CRLF·들여쓰기 없이 나와 `3.13.x` 를 찾지 못하고 `3.13` 으로 핀하던 문제를 고쳤다(`tr -d '\r'`, 앞 공백 선택). 형제 템플릿에서 가져온 버그이며, 형제 저장소에는 반영하지 않았다.

### 검증

- 생성물(Python 3.13.14): pytest 163건 통과, `ruff check` 경고 0.
- `scaffold.ps1`(PowerShell 5.1)·`scaffold.sh`(Git Bash) `-SkipDb` 생성 → 두 결과물이 비밀값을 빼고 같음, 잔여 토큰 없음, `.env` 키 집합 = `.env.example`, Tailwind 내려받기·검증·빌드 성공. 잘못된 이름·템플릿 안 대상·비어 있지 않은 대상(비대화형)은 종료 코드 1.
- `bootstrap.sh`·`bootstrap.ps1` 을 빈 핀 폴더로 실행해 `3.13.14` 선택·최종 확인 통과.
- 임시 프로젝트에서 SQLite `alembic upgrade head`, waitress 기동 후 공개·관리자 화면 HTTP 200·로그인·CSP 헤더 확인.
- 미검증: PostgreSQL 대상 마이그레이션 왕복과 스캐폴드 DB 단계(PostgreSQL 미기동), 브라우저 실동작(htmx·CSP), macOS/Linux 실행, ShellCheck(로컬 미설치), 템플릿 CI(아직 없음).
