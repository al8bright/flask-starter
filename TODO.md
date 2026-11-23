# TODO — flask-starter 재개발

> 작업 중에만 두는 계획 문서다. 끝나면 결과를 CHANGELOG·검토 기록으로 옮기고 이 파일을 삭제한다.
> 재개발 전 상태(코드 생성기 방식)는 `legacy-scaffolder` 태그에 있다.

## 결정 사항 (2026-11-23)

- 저장소 이름: `flask-starter` 를 유지한다(`flask-pg-starter` 로 바꾸는 계획은 철회)
- 구조: FastAPI 형제 템플릿과 같은 `skeleton/` + `scaffold.ps1`·`scaffold.sh` 방식
- 공통 계층: `fastapi-react-pg-starter/skeleton/backend/` 의 `config`·`core`·`db`·`models`·`schemas`·`services`·`alembic` 을
  **파일 그대로 복사**한다. 원본 → 이 저장소 **단방향 추적**이며 형제 저장소는 고치지 않는다. 동일성은 diff 검사로 확인한다.
- 생성 프로젝트 폴더: 루트 평면 구조(`app/`·`alembic/`·`tests/`) — `backend/`·`frontend/` 분리 없음
- 화면: Jinja 전체 페이지 렌더링이 기본, htmx 는 선택적 보강(예제 2~3곳), Alpine.js 미사용
- 스타일: Tailwind CSS v4 standalone CLI(Node 불필요)
- 인증: DB 세션(`auth_sessions`) 불투명 토큰을 httpOnly 쿠키로 — JWT·Flask-Login·Flask 기본 session 인증 미사용
- CSRF: Flask-WTF `CSRFProtect` 전역, 폼 검증은 기존 pydantic 스키마
- 기존 게시판(posts) 기능은 버리고 형제 템플릿 기능 구성(사용자·공지·배너·업로드·관리자)을 따른다

## 진행 단계

- [x] 1. 저장소 틀 — AGENTS·CLAUDE·README·CHANGELOG, 루트 `.gitignore`, scaffold 쌍, bootstrap
  - [x] `LICENSE`·`.gitattributes`(루트·skeleton) 복사
  - [x] `scaffold.ps1`·`scaffold.sh` — 형제 것을 기준으로 프론트(pnpm)·DESIGN.md 테마 단계 제거, `.env` 를 루트에 생성, Tailwind 빌드 단계 추가
    - 두 스크립트로 `-SkipDb` 생성 → 결과물 동일(.env 비밀값만 다름), 토큰 잔존 0, `.env` 키 = `.env.example`, pytest 163 통과, ruff check 통과(2026-11-23)
    - 거부 경로 확인: 잘못된 이름, 템플릿 안 대상, 비어 있지 않은 대상(비대화형)
  - [x] `skeleton/scripts/bootstrap.*` — Python 만 확인·설치(Node·pnpm 제거)
    - 형제 `bootstrap.sh` 버그 수정: Git Bash + pyenv-win 의 `pyenv install --list` 가 CRLF·들여쓰기 없이 나와 3.13.x 를 못 찾았다(`tr -d '\r'`, 앞 공백 선택). 형제 저장소에는 미반영
  - [x] skeleton 문서 — `README.md`·`AGENTS.md`·`CLAUDE.md`·`PLAN.md`·`docs/README.md`·`.claude/skills/`(5종)
  - [x] 루트 문서 — `README.md`·`AGENTS.md`·`CLAUDE.md`·`CHANGELOG.md`·`docs/README.md`·`.gitignore`
    - [x] 문서의 `ARCHITECTURE.md §N` 참조를 6단계 결과의 절 주제와 맞추었다
    - [x] CI 를 `pr-workflow` 스킬·README(루트·skeleton)·AGENTS 「저장소 구조」에 반영(5단계)
- [x] 2. 공통 계층 복사 + 서비스 단위 테스트 통과 — 원본과 파일 단위 동일 확인(2026-11-23)
- [x] 3. 웹 계층 — `app/main.py`(create_app)·`app/dependencies.py`·`app/web/`(auth·public·api·files·errors·htmx·admin)
- [x] 4. 화면 — Jinja 템플릿, htmx 예제 3곳(공지 검색·사용자 행 저장·배너 순서), Tailwind standalone 빌드(`scripts/tailwind.*`)
- [x] 5. 검증 자동화
  - [x] 웹 테스트(Flask `test_client`) — 전체 163건 통과, ruff 통과
  - [x] `skeleton/.github/workflows/ci.yml`(생성 프로젝트 CI), 루트 `template-ci.yml`, 두 `check-ps1-syntax.ps1`, PR 템플릿
  - [x] `tools/check_projects.py` 평면 구조 대응 + `tools/check_common_layer.py`(원본이 비공개라 CI 대신 로컬 실행) — 단위 테스트 28건 통과
  - [ ] 첫 push 후 GitHub Actions 결과 확인 — 특히 `migrations-postgres`(PostgreSQL 첫 검증)·`scaffold-posix` macOS·`scaffold-windows`
- [x] 6. `skeleton/ARCHITECTURE.md` — 형제 문서를 기준으로 §0~§22 절 번호를 유지하고 Flask 판으로 다시 작성하였다
  - §13(화면 구조 — Jinja·htmx)·§14(화면 인증 흐름 — 쿠키·CSRF·권한)는 형제 문서와 절 주제가 다르다
  - [ ] 서술이 코드와 어긋나지 않는지 화면·htmx 를 바꿀 때마다 확인한다(브라우저 미검증 항목은 아래 목록)

## 미검증·확인 항목

- [x] 공통 계층 Windows 시각대 버그 — 정책을 「OS 와 무관하게 KST」로 바꾸고 원본(`fastapi-react-pg-starter` `d93f04c`)에서 고친 뒤 다시 복사하였다(`now()` 를 고정 오프셋 UTC+9 로 계산, Windows 에서 `TZ` 미주입, 로그 시각 KST). `fastapi-nextjs-pg-starter`(`a94a56e`)에도 반영. nuxt·svelte 형제는 작업 환경에 없어 미반영
- [x] PostgreSQL 마이그레이션(`upgrade → check → downgrade base → upgrade`) — Docker `postgres:16`(16.15)에서 통과, `alembic check` 차이 없음. 앱 연결의 세션 시각대 `Asia/Seoul`, 헬스 체크·로그인·관리자 화면·공지 작성(본문 정화)·htmx 검색 partial 확인(2026-11-23)
- [x] SQLite `alembic check` 가 `banners.alt_text` 기본값 차이를 보고한다 — 원인 확인: 생성된 DDL 은 `DEFAULT ''` 로 정상이고, Alembic 1.20.1 `SQLiteImpl.compare_server_default` 의 따옴표 제거 정규식(`'(.+)'`)이 빈 문자열 `''` 을 벗기지 못해 DB 에서 읽은 값 `''` 과 모델의 빈 문자열이 다르다고 판정한다. 마이그레이션·모델 문제가 아니므로 고치지 않는다. PostgreSQL 에서는 `alembic check` 가 차이 없음으로 통과하였다
- [ ] 브라우저 실동작(htmx 검색·행 저장·배너 이동이 CSP 아래에서 동작하는지, 콘솔 CSP 위반 없음) — Chrome 확장 미연결로 미검증(2026-11-23 재시도도 미연결). HTTP 수준(waitress 실행, 로그인, 관리자 화면 200)과 템플릿 정적 검사(`style=` 속성·인라인 `<script>`·`on*=` 속성·`hx-on`·`js:`·`<style>` 없음)는 확인
- [ ] 공지 본문 편집기 — 검토 완료([`docs/reviews/2026-11-23-wysiwyg-editor.md`](docs/reviews/2026-11-23-wysiwyg-editor.md)): 형제 자체 편집기(contentEditable)를 바닐라 JS 로 이식하고 nh3 정화는 그대로 두는 안을 권장. 착수 여부·범위(1단계·2단계) 결정 대기
- [x] scaffold DB 단계(psql 사전 검사·CREATE DATABASE·시각대·alembic) — `scaffold.ps1`·`scaffold.sh` 를 설치 포함으로 실행해 두 DB 모두 시각대 `Asia/Seoul`·리비전 `0004_notices_banners`, 생성물 동일(`.env`·산출물 제외), `.env` 활성 키 = `.env.example`. 접속 불가(빈 포트)면 두 판 모두 DB 단계를 건너뛰고 수동 안내 후 종료 코드 2
  - [ ] 대화형 입력(접속 정보 재입력 1회)은 미검증 — 이 환경은 표준 입력이 터미널이 아니다
- [ ] scaffold·bootstrap·`tailwind.sh` 를 macOS/Linux 에서 실행 — Windows(Git Bash·PowerShell 5.1)에서만 확인(CI `scaffold-posix` 가 scaffold·`tailwind.sh` 를 다룬다). `bootstrap --with-postgres` 미검증
- [ ] `ruff format --check` 는 공통 파일 17개를 고치려 한다(원본 저장소 상태 그대로) — CI 는 형제와 같이 `ruff check` 만 돌린다
- [x] bcrypt 72-byte 가드 테스트 — `tests/test_passwords.py` 로 추가(로그인 422·72 bytes 경계 로그인·`hash_password` 거부·`verify_password` False·최소 길이·미존재 계정 응답 동일·더미 해시 비용). 생성물 pytest 172건 통과
- [x] `requirements.txt` 핀 검토 — 화면 동작을 좌우하는 전이 의존성 jinja2 3.1.6·markupsafe 3.0.4·itsdangerous 2.2.0 을 직접 고정(click·blinker 는 미고정 유지). `--uploaded-prior-to P1D` 설치·`pip check`·pytest 172건·`pip-audit` 통과
