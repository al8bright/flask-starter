# TODO — flask-pg-starter 재개발

> 작업 중에만 두는 계획 문서다. 끝나면 결과를 CHANGELOG·검토 기록으로 옮기고 이 파일을 삭제한다.
> 재개발 전 상태(코드 생성기 방식)는 `legacy-scaffolder` 태그에 있다.

## 나중에 할 일 — 저장소 이름 변경 (`flask-starter` → `flask-pg-starter`)

재개발이 어느 정도 자리 잡은 뒤 한 번에 처리한다.

- [ ] GitHub 저장소 이름 변경: `gh repo rename flask-pg-starter` (공개 저장소 — 옛 URL 은 GitHub 가 리다이렉트한다)
- [ ] 로컬 remote 갱신: `git remote set-url origin git@github.com:al8bright/flask-pg-starter.git`
- [ ] 로컬 폴더 이름 변경: `C:\Personal\flask-starter` → `C:\Personal\flask-pg-starter`
  - 이 폴더에서 실행 중인 에디터·터미널·Claude Code 세션을 모두 닫은 뒤 실행한다(Windows 폴더 잠금).
  - `Rename-Item C:\Personal\flask-starter flask-pg-starter`
- [ ] 저장소 안의 옛 이름 검색·정리: `git grep -n "flask-starter"`
- [ ] 형제 템플릿 문서에서 이 저장소를 가리키는 경로가 있으면 함께 고친다

## 결정 사항 (2026-11-23)

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

- [ ] 1. 저장소 틀 — AGENTS·CLAUDE·README·CHANGELOG, 루트 `.gitignore`, scaffold 쌍, bootstrap
  - [x] `LICENSE`·`.gitattributes`(루트·skeleton) 복사
  - [ ] `scaffold.ps1`·`scaffold.sh` — 형제 것을 기준으로 프론트(pnpm) 단계 제거, `.env` 를 루트에 생성, Tailwind 빌드 단계 추가
  - [ ] `skeleton/scripts/bootstrap.*` — Python 만 확인·설치(Node·pnpm 제거)
  - [ ] skeleton 문서 — `README.md`·`AGENTS.md`·`CLAUDE.md`·`PLAN.md`·`docs/README.md`·`.claude/skills/`
- [x] 2. 공통 계층 복사 + 서비스 단위 테스트 통과 — 원본과 파일 단위 동일 확인(2026-11-23)
- [x] 3. 웹 계층 — `app/main.py`(create_app)·`app/dependencies.py`·`app/web/`(auth·public·api·files·errors·htmx·admin)
- [x] 4. 화면 — Jinja 템플릿, htmx 예제 3곳(공지 검색·사용자 행 저장·배너 순서), Tailwind standalone 빌드(`scripts/tailwind.*`)
- [ ] 5. 검증 자동화
  - [x] 웹 테스트(Flask `test_client`) — 전체 163건 통과, ruff 통과
  - [ ] `skeleton/.github/workflows/ci.yml`(생성 프로젝트 CI), 루트 `template-ci.yml`
  - [ ] `tools/check_projects.py` 경로 대응 + 공통 계층 동일성 검사(원본 `fastapi-react-pg-starter`)
- [ ] 6. `skeleton/ARCHITECTURE.md` — 형제 문서 기준으로 §4·§6·§9·§13~15 재작성(절 번호는 유지 — 공통 코드 주석이 § 번호를 참조한다)

## 미검증·확인할 것

- [ ] PostgreSQL 마이그레이션(`upgrade → check → downgrade base → upgrade`) — Docker 미기동으로 미검증. SQLite 에서는 `upgrade head` 통과
- [ ] SQLite `alembic check` 가 `banners.alt_text` 기본값 차이를 보고한다 — 공통 마이그레이션(원본 저장소) 쪽 문제인지 PostgreSQL 에서 확인
- [ ] 브라우저 실동작(htmx 검색·행 저장·배너 이동이 CSP 아래에서 동작하는지, 콘솔 CSP 위반 없음) — Chrome 확장 미연결로 미검증. HTTP 수준(waitress 실행, 로그인, 관리자 화면 200)은 확인
- [ ] 공지 본문 편집기 — 지금은 HTML textarea + 이미지 업로드 후 코드 붙여 넣기. 리치 텍스트 편집기 도입 여부 결정
- [ ] `requirements.txt` 핀 검토 — 직접 의존성만 고정(전이 의존성 jinja2·markupsafe·itsdangerous·click·blinker 는 미고정)
