# Changelog

스캐폴드 템플릿 `flask-starter` 의 변경 이력.
형식은 [Keep a Changelog](https://keepachangelog.com/)를 느슨히 따른다.

오래된 항목은 `docs/archive/changelog/` 에 연도별로 보관한다(규칙은 `AGENTS.md` 「문서 갱신」).

---

## 2026-11-23 — 비밀번호 경계 테스트

### Added (추가)

- `skeleton/tests/test_passwords.py`: 형제 템플릿의 FastAPI 테스트에만 있던 비밀번호 검증을 Flask 폼 POST 기준으로 옮겼다 — 로그인 비밀번호 72 bytes 초과 422(한글 25자), 72 bytes 경계값의 저장·로그인 왕복, `hash_password`·`create_user`·`ensure_admin` 의 초과·최소 길이 거부, `verify_password` 초과 시 `False`, 미존재 계정과 틀린 비밀번호의 응답 동일, 미존재 계정의 더미 해시 1회 검증과 비용 일치.

### 검증

- 임시 스캐폴드(Python 3.13.14): `pip check` 통과, `ruff check` 경고 0, `pytest -W error::DeprecationWarning` 172건 통과.

## 2026-11-23 — 생성 프로젝트 아키텍처 문서

### Added (추가)

- **`skeleton/ARCHITECTURE.md`**: 생성 프로젝트의 아키텍처 기준(SSOT). 형제 템플릿 문서의 절 번호(§0~§22)와 ★핵심 MUST 요약 구조를 유지하고 Flask 판으로 다시 작성하였다 — 공통 계층 코드 주석이 § 번호를 참조하기 때문이다.
  - 공통 계층 절(§5 설정·§7 DB·§8 모델/스키마/서비스·§10 KST·§11 Alembic)은 같은 규칙을 두고, FastAPI 전용 설정 키를 이 템플릿이 읽지 않는다는 점을 밝혔다.
  - Flask 절: §4 앱 구조(`create_app`·블루프린트), §6 `dependencies.py`(요청 훅·데코레이터), §9 DB 세션 쿠키 인증·CSRF·CSP, §12 테스트 픽스처, §13 화면 구조(Jinja·htmx), §14 화면 인증 흐름, §15 Tailwind standalone, §17 환경변수(`.env.example` 과 같은 키), §20 CI, §21 생성 직후 확인·배포 전 체크리스트.
- 루트 `README.md` 구조도와 「기준이 바뀌면」, `AGENTS.md` 「저장소 구조」, `skeleton/README.md` 「상세 문서」에 문서 링크를 넣고 「작성 예정」 표기를 지웠다. `add-screen` 스킬의 CSP 절 참조를 §9·§13 으로 고쳤다.

### 검증

- 문서의 경로·설정 키·라우트·헤더 값·htmx 설정·픽스처 이름을 `skeleton/` 코드와 대조하였다. 코드 주석·스킬·스크립트의 `ARCHITECTURE.md §N` 참조가 해당 절 주제와 맞는지 확인하였다.
- 미검증: 문서가 서술하는 브라우저 동작(htmx 교체·CSP 위반 없음)과 PostgreSQL 마이그레이션 왕복은 이전 항목과 같이 미검증이다.

## 2026-11-23 — 검증 자동화: CI·점검 도구

### Added (추가)

- **생성 프로젝트 CI** `skeleton/.github/workflows/ci.yml`: `app`(Ubuntu·Windows, `pip check`·`ruff check`·`pytest -W error::DeprecationWarning`), `css`(Ubuntu `tailwind.sh`·Windows PowerShell 5.1 `tailwind.ps1`), `migrations`(`postgres:16` Alembic 왕복), `powershell-syntax`, `audit`(`pip-audit`, 경고성). PR 템플릿과 PS 5.1 구문 검사 스크립트(`check-ps1-syntax.ps1`, 형제 템플릿과 같은 검사)를 함께 넣었다.
- **템플릿 CI** `.github/workflows/template-ci.yml`: PS·bash 구문 검사(ShellCheck 게이트, `tailwind.sh` 포함), `versions.env` 와 벤더링 자산(htmx·Tailwind 해시 파일)의 버전 정합, Ubuntu·macOS 스캐폴드 실행과 생성물 pytest·CSS 빌드, Windows 에서 두 스캐폴드 생성물 동일성·생성물 pytest·`tailwind.ps1`, PostgreSQL 마이그레이션 왕복, `pip-audit`(차단), 점검 도구 단위 테스트.
- **점검 도구** `tools/`: `check_projects.py`(형제 템플릿 도구를 평면 구조에 맞춘 판 — 런타임·htmx 실제 버전, Python 핀, 공통 파일, OSV 감사)와 `check_common_layer.py`(공통 계층이 원본과 같은지 — 원본이 비공개 저장소라 CI 대신 로컬에서 실행). AGENTS.md 의 diff 반복문을 이 도구로 대체하였다.

### 검증

- 점검 도구 단위 테스트 28건 통과(Python 3.13), 도구 코드 ruff(`E·F·I·B`) 경고 0, `check_common_layer.py` 동일.
- 임시 스캐폴드(`Demo App`)에 `check_projects.py` → 공통 파일 119개 모두 같음(토큰 치환 재현 확인). `scaffold.ps1`·`scaffold.sh` 생성물은 `.github/` 를 포함해 비밀값을 빼고 같음.
- `check-ps1-syntax.ps1` 을 저장소(5개)와 생성물(3개)에서 PowerShell 5.1 로 실행해 통과. ShellCheck 0.11.0(`-S warning -e SC2088`)과 `bash -n` 이 세 `.sh` 에서 통과. 벤더링 자산 정합 스크립트를 로컬에서 실행해 통과.
- 미검증: 두 워크플로의 GitHub Actions 실제 실행(push 전), PostgreSQL 마이그레이션 왕복(로컬 PostgreSQL 접속 정보 없음 — CI `migrations` 잡이 처음 확인한다).

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
