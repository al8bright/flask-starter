# flask-starter 에이전트 지침 (템플릿 저장소용)

> 이 파일은 **스타터 템플릿 저장소 자체**를 작업할 때의 공통 지침이다. Claude Code 는 루트 `CLAUDE.md` 가 이 파일을 import 해 읽는다.
> 생성 프로젝트가 받는 지침의 원본은 `skeleton/AGENTS.md`·`skeleton/CLAUDE.md` 다 — 이 저장소 작업 규칙과 섞지 않는다.

## 언어

- 사용자에게 보내는 답변·진행 보고·질문(선택지 포함)은 **항상 한국어**로 쓴다. 세션 첫 답변부터 적용한다.
- 패키지명·명령어·파일 경로·코드 식별자·에러 원문처럼 바꿀 수 없는 이름만 원문으로 두고, 전문용어는 처음 나올 때 한국어 설명을 붙인다.
- 저장소 문서와 커밋 메시지는 한국어 평서체(`~한다`)로 쓴다. 영어 문장·영어 위주 표를 섞지 않는다.
- 명령 예시는 현재 OS 에 맞춘다(Windows 는 PowerShell).

## 저장소 구조

| 경로 | 역할 |
|---|---|
| `scaffold.ps1` · `scaffold.sh` | 새 프로젝트 생성 스크립트(Windows · macOS/Linux/Git Bash) — **두 판의 동작을 항상 같게** 유지한다 |
| `skeleton/` | 새 프로젝트가 받는 골격 전체(Flask + Jinja + htmx + PostgreSQL, Tailwind standalone). 스캐폴드는 이 폴더만 복사한다 |
| `skeleton/ARCHITECTURE.md` | 생성 프로젝트의 아키텍처 기준(SSOT)과 ★핵심 MUST 요약. 공통 코드 주석이 형제 템플릿의 § 번호를 참조하므로 절 번호를 형제와 같게 둔다 |
| `skeleton/app/` 의 공통 계층 | `config.py`·`cli.py`·`core/`·`db/`·`models/`·`schemas/`·`services/` 와 `skeleton/alembic/` — `fastapi-react-pg-starter` 의 `skeleton/backend/` 에서 **파일 그대로 복사**한 것(아래 「공통 계층」) |
| `skeleton/.claude/skills/` | 생성 프로젝트용 작업 스킬 — 이 저장소에서도 `skeleton/` 을 고칠 때 참고한다(특히 `stack-versions`) |
| `skeleton/.github/` | 생성 프로젝트 CI(`workflows/ci.yml`)·PS 5.1 구문 검사 스크립트·PR 템플릿 |
| `.github/` | 이 템플릿 저장소의 CI(`workflows/template-ci.yml`)와 같은 PS 5.1 구문 검사 스크립트 |
| `tools/` | 점검 도구(`check_projects.py` 생성 프로젝트 점검, `check_common_layer.py` 공통 계층 동일성)와 단위 테스트. 스캐폴드 시 복사되지 않는다 |
| `docs/` | 템플릿 문서 — 검토 기록(`reviews/`)·보관 기록(`archive/`). 스캐폴드 시 복사되지 않는다. 작성 규칙은 [`docs/README.md`](docs/README.md) |
| `TODO.md` | 재개발 작업 계획(작업 중에만 둔다 — 아래 「문서 갱신」) |
| `CHANGELOG.md` | 템플릿 변경 이력 |
| `LICENSE` · `SECURITY.md` | 템플릿 라이선스(MIT — 생성 프로젝트는 README 「라이선스」의 MIT-0) · 보안 정책(비공개 취약점 제보) |
| `README.md` | 템플릿 사용법·버전 고정 정책·검증 상태 |

템플릿 CI(`template-ci.yml`)는 push 이후 도는 사후 안전망이다. 커밋 전 게이트는 아래 「검증 절차」다.
공통 계층 동일성은 원본 저장소가 비공개라 CI 에서 검사하지 않는다 — 로컬에서 `tools/check_common_layer.py` 로 확인한다.

## 지침 적용 범위

- **템플릿 운영**(스캐폴드 스크립트, 검증 절차, 문서 배치, 커밋)은 이 파일을 따른다.
- **`skeleton/` 안의 코드·설정을 고칠 때**는 `skeleton/AGENTS.md` 「반드시 지킨다」를 그대로 적용한다
  — 스택 고정(Node 빌드 없음, htmx 는 선택적 보강), Alembic 전용 DB 관리, KST 단일 기준, 계층 분리, DB 세션 쿠키 인증, CSRF·CSP 등. 작업별 절차는 `skeleton/.claude/skills/<이름>/SKILL.md` 를 직접 읽는다.
- `skeleton/AGENTS.md` 의 「프로젝트 개요 (작성)」·`<…>` 자리표시와 `__PROJECT_NAME__` 은 생성 후 사용자가 채우는 부분이다. 템플릿에서 채우지 않는다.
- 두 지침이 충돌하면 저장소 운영(검증·커밋·push·문서 위치)은 이 파일이 우선한다.
- 실제 비밀번호·토큰·접속 문자열을 명령 인자·문서·대화에 평문으로 쓰지 않는다. 환경변수나 `.pgpass` 를 쓰고 DB 도구는 읽기 전용으로 연결한다(검증용 임시 컨테이너의 기본값은 예외).
- 요청 범위 밖에서 찾은 문제는 고치지 않고 보고 끝에 후속 항목으로 남긴다.

## skeleton/ 수정 규칙

- ⛔ **치환 토큰 보존**: `__PROJECT_NAME__` · `__PROJECT_SNAKE__` 를 실제 값으로 바꾸거나 지우지 않는다(스캐폴드가 치환한다).
  토큰을 추가·변경하면 두 스캐폴드 스크립트의 치환 처리를 같은 변경에서 고친다. 치환 대상 확장자(`TOKEN_EXTENSIONS`) 밖의 파일에 토큰을 두지 않는다.
- ⛔ **템플릿 비오염**: 저장소 안에서 설치·실행하지 않는다. `skeleton/` 안에 `.venv`·`.tools`·`uploads`·`.env`·`app/static/css/app.css` 가 생기거나 `.python-version` 이 바뀌면 저장소가 오염된다. 검증은 항상 **임시 스캐폴드**로 한다(아래).
- 규칙(기준)이 바뀌면 `skeleton/ARCHITECTURE.md`(+ 필요 시 `skeleton/AGENTS.md`)를 고치고, ★핵심 MUST 요약을 최신으로 유지한다.
- 기능·설정을 제거하면 관련 이름을 저장소 전체에서 검색해 코드 주석·env 선언·문서 서술까지 함께 정리한다.
- htmx·Tailwind CLI 처럼 저장소에 들이는 외부 바이너리·스크립트는 버전을 `skeleton/scripts/versions.env` 에 기록하고 무결성(SHA-256·npm integrity)을 확인한 것만 쓴다(`stack-versions` 스킬 §5-2).
  `skeleton/` 에 벤더링하는 외부 코드는 생성 프로젝트에 고지 의무를 지우지 않는 라이선스(0BSD·MIT-0 등)인지 확인하고, 고지가 필요하면 루트 README 「라이선스」 표와 생성 프로젝트 README 에 함께 기록한다.

### 공통 계층

- `fastapi-react-pg-starter/skeleton/backend/` → 이 저장소 `skeleton/` 으로 **단방향 추적**한다. ⛔ 이 저장소에서 공통 파일을 고치지 않는다 — 버그를 찾으면 원본 저장소에서 고치도록 보고하고, 원본이 바뀌면 파일을 다시 복사한다.
- 대상: `app/__init__.py`·`app/config.py`·`app/cli.py`·`app/core/`·`app/db/`·`app/models/`·`app/schemas/`·`app/services/`·`alembic/`·`alembic.ini`, 테스트 `media_factory.py`·`test_cli.py`·`test_config.py`·`test_login_throttle.py`·`test_sanitize.py`·`test_storage.py`. 프레임워크(FastAPI·Flask)에 묶인 코드는 공통 계층에 없다.
- 원본에서 다시 복사하면 이 저장소 웹 계층(`app/web/`·`app/dependencies.py`·`app/main.py`)과 테스트가 새 서비스 시그니처에 맞는지 확인한다. 설정 키가 바뀌었으면 `.env.example` 과 두 스캐폴드의 `.env` 생성 블록도 고친다.
- 동일성 확인(저장소 루트) — 원본 기본 위치는 이 저장소 옆 `../fastapi-react-pg-starter` 다. 종료 코드 0 같음, 1 차이, 2 원본 없음.
  대상 목록은 `tools/check_common_layer.py` 의 `COMMON_PATHS` 에 있으며, 위 「대상」을 바꾸면 함께 고친다.

```powershell
python -B tools\check_common_layer.py                 # 다른 위치면 --source <원본 저장소 루트>
```

## 검증 절차

`skeleton/` 이나 스캐폴드 스크립트를 바꾸면 임시 스캐폴드로 생성물 전체를 검증한다.

```powershell
# 1) 임시 스캐폴드 — 저장소 밖 짧은 경로(세션 스크래치 등). -SkipInstall 이면 CSS 빌드도 건너뛴다
.\scaffold.ps1 -Name tmp -Target <임시 경로> -SkipDb -SkipInstall
git status --short   # 출력이 없어야 한다(템플릿 비오염)

# 2) 생성물(<임시 경로>) — .python-version 의 Python 3.13 으로 venv 생성
py -3.13 -m venv .venv   # py 런처가 없으면 pyenv 의 python.exe 를 직접 지정
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python -m pip check
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q -W error::DeprecationWarning
.\scripts\tailwind.ps1   # CSS 빌드(내려받기·SHA-256 검증 포함)
```

macOS / Linux: `./scaffold.sh --name tmp --target <임시 경로> --skip-db --skip-install` → `python3.13 -m venv .venv` 후 같은 순서 → `./scripts/tailwind.sh`.

- 시스템 기본 `python` 이 더 새 버전(예: 3.14)일 수 있다. `python --version` 을 먼저 확인하고, 대상 런타임이 아닌 venv 로 얻은 결과는 검증으로 인정하지 않는다.
- 생성물에서 잔여 토큰이 없어야 한다: `grep -rIl --exclude-dir=.venv --exclude-dir=.tools '__PROJECT_' <임시 경로>` 출력 없음.
- 생성 `.env` 의 키 집합이 `.env.example` 과 같아야 한다.
- 화면·htmx·CSP 를 바꾸면 생성물에서 `flask --app app.main run` 으로 띄워 브라우저로 확인한다(콘솔에 CSP 위반 없음). 확인하지 못했으면 **미검증**으로 남긴다.
- 검증을 마치면 `git status --short --ignored` 로 저장소 안에 새 산출물이 없는지 확인한다(작업 전부터 있던 무시 파일은 제외).
- DB 가 바뀌면 PostgreSQL 상대로 `alembic upgrade head` → `alembic check` → `alembic downgrade base` → `alembic upgrade head` 를 실행한다
  (Docker 예: `docker run --rm -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:16` + 임시 프로젝트 `.env` 의 `DATABASE_URL` 수정).
- `.ps1` 을 고치면 `powershell -NoProfile -ExecutionPolicy Bypass -File .\.github\scripts\check-ps1-syntax.ps1`(Windows PowerShell 5.1 파싱 + PS7 전용 토큰 검사)을, `.sh` 를 고치면 `bash -n` 과 ShellCheck(`shellcheck -S warning -e SC2088 scaffold.sh skeleton/scripts/bootstrap.sh skeleton/scripts/tailwind.sh skeleton/deploy/deploy.sh`)를 실행한다. 새 `.sh` 는 실행 권한(`git add --chmod=+x`)으로 기록한다. ShellCheck 가 없으면 스크래치 venv 에 `pip install shellcheck-py` 로 받는다. 스캐폴드는 두 판 모두 실제로 실행해 결과물이 같은지(비밀값 제외) 비교한다.
- `tools/` 를 고치면 `python -B -m unittest discover -s tools` 를 실행한다(표준 라이브러리만 쓴다).
- 실행하지 못한 검증은 생략하지 않고 **미검증**으로 명시한다(사유 포함 — README 검증 상태·CHANGELOG·보고). 통과한 것처럼 서술하지 않는다.

### 버전 상향

- `skeleton/.claude/skills/stack-versions/SKILL.md` §5 절차를 따른다.
- **배포 24시간 규칙**: 배포 후 24시간이 지난 버전만 선정한다. pip 은 `pip install --uploaded-prior-to P1D`(pip 26.3 이상, 정수 일 단위)로 강제할 수 있다.
  lock 은 `skeleton/scripts/versions.env` 의 `LOCK_EXCLUDE_NEWER`(UTC)로 같은 기준을 건다 — 재생성 시점보다 24시간 이상 전으로 옮긴다.
- 동작을 좌우하는 전이 의존성(현재 `werkzeug`·`jinja2`·`markupsafe`·`itsdangerous`)은 `requirements.txt` 에 직접 핀한다.
- **lock**: 사람이 고치는 입력은 `skeleton/requirements.txt`·`skeleton/.github/requirements-ci.txt` 이고, 해시 lock(`requirements.lock`·`.github/requirements-ci.lock`)은 `skeleton/` 에서 `python -B scripts/lock.py` 로 다시 만든다(⛔ 손으로 고치지 않는다).
  uv 는 저장소 밖 스크래치 venv 에 `requirements-ci.lock` 으로 설치한다(`lock.py` 는 uv 버전이 핀과 다르면 멈춘다). 입력을 고치면 같은 커밋에서 lock 도 바꾼다 — 템플릿 CI `lock-check` 가 다시 만들어 비교한다.
- 설치는 어디서나 `pip install --require-hashes -r requirements.lock` 이다. ⛔ `pip install --upgrade pip` 같은 미고정 설치를 스크립트·CI 에 들이지 않는다.
- **Dependabot**(`.github/dependabot.yml`, 매주·cooldown 1일): pip PR 은 `requirements*.txt` 만 바꿔 `lock-check` 가 실패한다 — 그 PR 에서 lock 을 다시 만들어 함께 올린 뒤 검증 절차를 거친다. 액션 PR 은 SHA 와 `# vX.Y.Z` 주석을 함께 바꾼다. CI 의 `postgres` 이미지 digest 는 대상이 아니므로 손으로 옮긴다(`stack-versions` §5-1).
- 공통 계층이 쓰는 패키지(sqlalchemy·alembic·psycopg2-binary·pydantic·pydantic-settings·PyJWT·bcrypt·nh3·pillow)는 원본 저장소와 같은 핀을 유지한다. 원본보다 먼저 올리지 않는다 — Dependabot 의 `common-layer` 묶음 PR 도 원본이 같은 버전으로 올린 뒤에만 병합한다.
- 검토 결과는 `docs/reviews/YYYY-MM-DD-dependency-upgrade.md` 로 남긴다.

## 스크립트 작성 규칙

- `.ps1` 은 **Windows PowerShell 5.1 에서 파싱되어야 한다** — ⛔ PS7 전용 문법(`??`, `?:`, `&&`/`||`, `?.`).
- `.ps1` 은 **UTF-8 BOM** 으로 저장한다. BOM 이 없으면 5.1 이 ANSI(한국어 Windows 는 CP949)로 읽어 한글이 깨진다.
  대상은 `scaffold.ps1`·`skeleton/scripts/bootstrap.ps1`·`skeleton/scripts/tailwind.ps1` 과 두 `check-ps1-syntax.ps1`(`.github/scripts/`·`skeleton/.github/scripts/`, 같은 내용으로 유지)이며, 편집 도구가 BOM 을 지우지 않았는지 커밋 전에 확인한다.
- 줄바꿈은 `.gitattributes` 가 강제한다 — `.sh` 는 LF(CRLF 면 셰뱅이 깨진다), `.ps1` 은 CRLF. 루트와 `skeleton/` 의 `.gitattributes` 를 함께 유지한다.
- `scaffold.ps1` ↔ `scaffold.sh`, `bootstrap.ps1` ↔ `bootstrap.sh`, `tailwind.ps1` ↔ `tailwind.sh` 는 한쪽을 고치면 다른 쪽도 같은 변경에서 고친다(`skeleton/deploy/deploy.sh` 는 Linux 서버 전용이라 짝이 없다). 옵션 이름은 각 셸 관례를 따른다(`-SkipDb` ↔ `--skip-db`).
- 생성되는 `.env` 의 키 집합은 `skeleton/.env.example` 과 같아야 한다. 키를 추가·삭제하면 두 스캐폴드 스크립트의 `.env` 생성 블록을 같은 변경에서 고친다.
- 골격 복사는 산출물(`.venv`·`venv`·`.ruff_cache`·`.pytest_cache`·`__pycache__`·`.tools`·`uploads`·`logs`·`app.css`·`.DS_Store`·`.env`)을 원천 제외한다. 제외 목록은 두 스크립트 맨 위 「템플릿 설정」 블록에 있으며, 바꾸면 두 스크립트를 함께 고친다.
- 스크립트의 설치 단계(pyenv·PostgreSQL)는 기존 설치본이 하한을 충족하면 재사용한다. 형제 템플릿 스크립트에서 가져온 동작을 바꾸면 이유를 CHANGELOG 에 남긴다.

## 문서 갱신

- 버전·동작이 바뀌면 함께 고친다 — 루트 `README.md` 「버전 고정 정책」·검증 상태, `skeleton/README.md` 버전 표, `skeleton/ARCHITECTURE.md` §2, 관련 스킬(`stack-versions` §3), 루트 `CHANGELOG.md`.
- 루트 `README.md` 「검증 상태」는 특정 시점의 기록이다. 새 검증 결과는 CHANGELOG 또는 `docs/reviews/` 에 남긴다.
- 기술 선택을 검토했으면 `docs/reviews/YYYY-MM-DD-<영문-주제>.md` 로 남기고 `docs/README.md` 목차에 추가한다(작성 규칙은 `docs/README.md`).
- 파일·폴더 구조가 바뀌면 루트 `README.md` 의 저장소 구조와 이 파일의 「저장소 구조」 표를 고친다.
- 문서·스킬 서술은 해당 코드·스크립트를 읽어 확인한 뒤 쓴다. 확인할 수 없는 서술은 고치지 않고 보고에 남긴다.
- 지침·스킬에 테스트 건수·줄 번호처럼 자주 바뀌는 값을 쓰지 않는다(검증 기록·CHANGELOG 는 시점 기록이라 예외).
- 템플릿 작업 계획 문서(`TODO.md`)는 작업 중에만 둔다. 끝나면 결과를 CHANGELOG·검토 기록에 옮기고 삭제한다(생성 프로젝트의 `PLAN.md` 는 대상이 아니다).
- `CHANGELOG.md` 는 200줄 이하로 유지한다. 새 항목을 추가한 뒤 넘으면 최신 3개 항목을 남기고 오래된 항목부터 `docs/archive/changelog/CHANGELOG-YYYY.md`(항목 연도)로 옮긴다. 옮긴 항목은 날짜 내림차순을 지키고 내용을 고치지 않는다.

## 커밋

- 제목: `[Structural]` 또는 `[Behavioral]` + conventional type(`feat`·`fix`·`chore`·`docs` 등) + 한국어 요약.
  예) `[Behavioral] fix: ...`, `[Structural] docs: ...`. 의존성 상향은 런타임 동작이 바뀌므로 `[Behavioral] chore:` 로 한다.
- 한 커밋에는 Structural·Behavioral 중 하나만 담는다(Tidy First). 버전 상향에 딸린 문서 갱신은 같은 커밋에 둘 수 있다.
- `main` 에 직접 커밋·push 하는 것이 기본이다. 커밋 전에 변경 범위에 해당하는 검증을 통과시킨다. **커밋·push 는 사용자가 요청할 때만** 한다.
- 커밋 작성자 이메일은 GitHub noreply 주소를 쓴다(저장소 로컬 `user.email`). 공개 이력에 실제 주소·연락처·실명을 남기지 않는다.

### 보안 수정

- 공개 순서는 [`SECURITY.md`](SECURITY.md) 「보안 수정 공개 절차」를 따른다 — 관리자가 운영하는 생성 프로젝트에 먼저 반영한 뒤 이 저장소에 push 한다. 사용자가 push 를 요청했는데 운영 프로젝트 반영 여부가 확인되지 않으면 push 전에 묻는다.
- 커밋 메시지·CHANGELOG 보안 항목에는 영향 범위와 조치만 쓴다. 재현 절차·공격 입력값·우회 방법은 쓰지 않는다(검토 기록 `docs/reviews/` 도 같다).
- 이력에 비밀값·개인정보가 들어간 것을 발견하면 파일 삭제 커밋으로 끝내지 않는다. 사용자에게 보고하고 이력 재작성(`git filter-repo`)·강제 push·GitHub 캐시 삭제 요청 여부를 정한다. `main` 은 강제 push·삭제 차단 규칙(ruleset)이 켜져 있어 재작성 때만 잠시 끈다.

## 템플릿 고유 사항

- 형제 FastAPI 템플릿과 달리 프론트엔드 빌드 체인(Node·pnpm)이 없다. CSS 는 Tailwind standalone CLI(`skeleton/scripts/tailwind.*`), 스크립트는 벤더링한 htmx, `app/static/js/app.js`, 공지 편집기 `app/static/js/editor/`(빌드 없는 ES 모듈)뿐이다. ⛔ Node 의존 단계를 들이지 않는다.
- 인증은 DB 세션 불투명 토큰 쿠키다(JWT 미사용). 공통 설정 키 `REFRESH_TOKEN_EXPIRE_DAYS` 를 로그인 세션 수명으로 쓴다. FastAPI 전용 키(`ACCESS_TOKEN_EXPIRE_MINUTES`·`REFRESH_TOKEN_TRANSPORT`·`CORS_ORIGINS`·`FRONTEND_URL`·`BACKEND_PUBLIC_URL`)는 `.env.example` 에 두지 않는다.
- 공지 첨부 다운로드 경로 `/api/v1/notices/<id>/attachments/<aid>` 는 공통 `notice_service.download_url` 이 만드는 URL 과 같아야 한다 — 바꾸지 않는다.
- 생성 프로젝트는 평면 구조(`app/`·`alembic/`·`tests/` 가 루트)다. 공통 `config.py` 의 `BACKEND_ROOT` 는 이 구조에서 프로젝트 루트를 가리킨다.
