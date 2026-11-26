---
name: stack-versions
description: __PROJECT_NAME__ 의 고정 스택 버전과 버전별 주의사항(gotcha)을 정의한다. 의존성 추가·업그레이드, Tailwind CLI·htmx 교체, 또는 버전에 따라 동작이 달라지는 코드를 작성·디버깅할 때 사용. 정확한 버전의 출처 파일과 Flask 3.1/Werkzeug 폼 크기 상한, Flask-WTF CSRF, htmx 2 설정, Tailwind standalone SHA-256 검증, bcrypt 5 72-byte 등 버전별 함정, 업그레이드 검증 절차를 안내한다.
---

# 스택 버전 & 버전별 주의

## 1. 정확한 버전의 출처 (SSOT) — 항상 여기서 확인
- **런타임 하한·도구 버전**: `scripts/versions.env` (`MIN_PYTHON`·`TAILWIND_VERSION`·`HTMX_VERSION`, lock 기준 시각 `LOCK_EXCLUDE_NEWER`)
- **Python 설치 핀**: `.python-version`
- **Python 패키지**: `requirements.txt` (직접 의존성 `==` 정확 핀 — 사람이 고치는 입력)
- **설치 lock**: `requirements.lock` (전이 의존성까지 정확 버전 + SHA-256 해시 — `scripts/lock.py` 가 만든다. ⛔ 손으로 고치지 않는다)
- **CI·lock 도구**: `.github/requirements-ci.txt` (pip-audit·uv 핀) → `.github/requirements-ci.lock`
- **GitHub Actions·CI 이미지**: `.github/workflows/ci.yml` 의 커밋 SHA(`# vX.Y.Z` 주석)·`postgres@sha256:` digest
- **Tailwind CLI 무결성**: `scripts/tailwind-sha256sums.txt`
- **htmx 본체**: `app/static/js/htmx.min.js` (벤더링)

> ⛔ **패키지 버전을 이 파일에 복사해 두지 않는다.** 값을 여러 곳(SSOT·README·이 스킬)에 두면 반드시 드리프트가 난다. 값이 필요하면 위 파일을 읽는다.

## 2. 영역별 고정 방식

| 영역 | 방식 | 출처 |
|---|---|---|
| Python 하한 | 이상이면 기존 설치본 재사용 | `scripts/versions.env` |
| Python 설치 핀 | pyenv 가 설치·활성화(정확 버전) | `.python-version` |
| Python 패키지 | `==` **정확 고정** — 재현성 우선. 동작을 좌우하는 전이 의존성 werkzeug·jinja2·markupsafe·itsdangerous 포함 | `requirements.txt` |
| Python 설치 | 전이 의존성까지 정확 버전 + 해시. 설치는 **언제나** `pip install --require-hashes -r requirements.lock`(로컬·CI·배포). ⛔ `pip install --upgrade pip` 같은 미고정 설치를 하지 않는다 | `requirements.lock` |
| CI 도구(pip-audit·uv) | 정확 핀 + 해시 lock(pip 자체도 lock 에 들어 있다) | `.github/requirements-ci.txt` → `.lock` |
| GitHub Actions | 전체 커밋 SHA + `# vX.Y.Z` 주석, `persist-credentials: false` | `.github/workflows/ci.yml` |
| Tailwind CSS | standalone CLI 정확 버전 + SHA-256 검증(실행마다). Node 불필요 | `versions.env` + `tailwind-sha256sums.txt` |
| htmx | 파일 벤더링(CDN 금지 — CSP `script-src 'self'`) | `app/static/js/htmx.min.js` + `versions.env` |
| PostgreSQL | 고정 없음 | 16+ 권장(CI 는 `postgres:16` 을 digest 로 고정) |

패키지별 전체 목록은 **`README.md` 의 「기술 스택과 버전」** 절에 표로 있다.

## 3. ⚠️ 버전별 함정 (코드·설정 작성 시 반드시)

### Flask 3.1 · Werkzeug 3.1
- ⚠️ **Werkzeug 는 Flask 의 전이 의존성이지만 `requirements.txt` 에 직접 `==` 로 고정한다.** Flask 는 `werkzeug>=3.1.0` 처럼 상한 없이 선언하므로, 고정하지 않으면 설치 시점의 최신 Werkzeug 가 들어온다. Flask 를 올릴 때 두 핀을 **같은 변경에서** 검토한다(§5 의 `pip check`).
- 같은 이유로 **Jinja2(템플릿 렌더링·자동 이스케이프)·MarkupSafe(`app/main.py` 가 직접 import)·itsdangerous(flash·CSRF 서명 쿠키 형식)** 도 직접 고정한다. Flask 를 올리면 네 핀을 함께 검토한다. click·blinker 는 화면 동작에 관여하지 않아 고정하지 않는다.
- 요청 크기 상한은 두 겹이다 — `MAX_CONTENT_LENGTH`(전체 본문, 업로드 상한 + 여유)와 `MAX_FORM_MEMORY_SIZE`(파일이 아닌 폼 필드 하나의 최대 크기, Flask 3.1 에서 생긴 설정). 공지 본문처럼 큰 텍스트 필드가 이 값을 넘으면 **413** 이다. 값은 `app/main.py` 에 있다.
- 앱은 팩토리(`create_app()`)로만 만든다. 실행은 `flask --app app.main run`(개발), `waitress-serve --call app.main:create_app`·`gunicorn "app.main:create_app()"`(운영). 모듈 전역 `app = create_app()` 을 두지 않는다 — import 만으로 DB 시드가 돈다.

### Flask-WTF 1.3 (CSRF 만 사용)
- `CSRFProtect` 를 전역으로 켜고 WTForms 폼 클래스는 쓰지 않는다(폼 검증은 pydantic — `app/web/forms.py`). Flask-WTF 를 올리면 WTForms 핀도 함께 본다.
- `WTF_CSRF_TIME_LIMIT=None` — 토큰은 시간 만료 없이 Flask 서명 쿠키(`__PROJECT_SNAKE___flash`) 수명을 따른다. 로그인 시 `session.clear()` 로 새 토큰을 받는다.
- `WTF_CSRF_SSL_STRICT` 는 `COOKIE_SECURE` 와 같다 — HTTPS 에서는 `Referer` 가 같은 호스트여야 한다. 이 검사는 `request.is_secure` 일 때만 돌므로, 프록시 뒤라면 `X-Forwarded-*` 가 전달되고 `TRUSTED_PROXY_HOPS` 가 프록시 단계 수여야 한다(werkzeug `ProxyFix` — `app/web/proxy.py`). Flask-WTF·Werkzeug 를 올리면 `tests/test_startup.py` 의 프록시 테스트로 확인한다.
- htmx 요청은 `X-CSRFToken` 헤더로 토큰을 보낸다(`base.html` 의 `hx-headers`). fetch 로 POST 하는 편집기 업로드(`app/static/js/editor/upload.js`)도 `<meta name="csrf-token">` 값을 같은 헤더로 보낸다. 헤더 이름을 바꾸면 `WTF_CSRF_HEADERS`·`base.html`·`upload.js` 를 함께 수정한다.

### htmx 2 (벤더링)
- 설정은 `base.html` 의 `<meta name="htmx-config">` 다. `allowEval:false`(CSP — `hx-on`·`hx-vars`·`js:` 불가), `includeIndicatorStyles:false`(인라인 스타일 금지 — indicator 스타일은 `input.css` 의 `.htmx-request`), `historyCacheSize:0`, `responseHandling` 으로 4xx·5xx 도 swap 한다(오류 알림이 `HX-Retarget: #alerts` 로 온다).
- ⚠️ htmx 는 메이저마다 기본값이 바뀐다(1 → 2: `DELETE` 파라미터가 쿼리 문자열로 이동, `selfRequestsOnly` 기본 true, 확장 분리 등). 메이저를 올릴 때는 공식 마이그레이션 가이드를 읽고 위 설정을 다시 검토한다.
- 교체 절차는 §5-2.

### Tailwind CSS v4 standalone CLI
- 설정 파일(`tailwind.config.js`) 없이 `app/static/css/input.css` 의 `@import "tailwindcss"`·`@source`·`@theme` 로 설정한다. 클래스를 찾는 범위는 `@source` 가 정한다 — 템플릿 폴더를 옮기면 함께 고친다.
- `scripts/tailwind.*` 는 `.tools/tailwindcss-<버전>-<OS>-<아키텍처>` 가 없을 때만 내려받는다. **SHA-256 은 실행할 때마다** `tailwind-sha256sums.txt` 와 비교한다 — 내려받아 둔 파일이 다르면 지우고 다시 내려받고, 새로 받은 파일도 다르면 쓰지 않고 중단한다. Windows 는 x64 바이너리만 있다.
- 출력 `app/static/css/app.css` 는 빌드 결과라 커밋하지 않는다(`.gitignore`). 배포 산출물을 만들 때 다시 빌드한다.

### SQLAlchemy 2.x / Alembic
- 2.0 스타일(`Mapped`/`mapped_column`, `select()` + `db.execute(...).scalar_one_or_none()`)을 쓴다. ⛔ 1.x 레거시 `session.query()` 패턴을 새로 들이지 않는다.
- ⚠️ Alembic 1.16+ 는 `alembic.ini` 에 `path_separator` 가 없으면 `DeprecationWarning` 을 낸다(Windows 경로의 `C:` 와도 충돌). → **`path_separator = os`** 를 지우지 않는다.
- ⛔ `alembic.ini` 는 **ASCII 전용**이다 — configparser 가 OS 로캘 인코딩으로 읽어 Windows(cp949)에서 한글 주석이 있으면 `UnicodeDecodeError` 로 alembic 이 뜨지 않는다.
- 마이그레이션 검증은 SQLite 가 아니라 **실제 PostgreSQL** 에서 `alembic upgrade head` + `alembic check` 로 한다([db-migration]).

### Pillow
- `core/storage.py` 가 **신뢰할 수 없는 업로드를 디코딩**한다 → Pillow 보안 릴리스는 늦추지 않는다.
- Pillow 13 부터 `thumbnail()` 의 축소 결과 픽셀이 조금 달라질 수 있다 → 테스트에서 이미지 **바이트·해시·픽셀 값을 비교하지 말고** 크기·포맷·메타데이터 제거 여부로 검증한다(현재 테스트가 그렇다).

### Pydantic 2.x
- v2 API(`model_config`, `@field_validator`, `@model_validator`, `SettingsConfigDict`). ⛔ v1 패턴(`class Config`, `@validator`) 금지.
- 폼 오류 메시지는 `parse_form` 이 pydantic 의 `"Value error, "` 접두어를 떼고 화면에 보여 준다. pydantic 을 올린 뒤 오류 문구 테스트(`test_web_*`)가 깨지면 이 접두어 형식부터 확인한다.

### bcrypt 5 · 인증
- 자체 계정 비밀번호는 **bcrypt** 해시(`core/security` 의 `hash_password`/`verify_password`). 새로 저장하는 비밀번호는 `validate_new_password()`(최소 8자 + UTF-8 72 bytes 상한)를 거친다.
- ⚠️ **bcrypt 5** 는 72 bytes 초과 입력에 `hashpw`/`checkpw` 모두 **`ValueError`** 를 던진다(4.x 는 조용히 절단). 그래서 72-byte 상한은 ① 스키마(`LoginRequest` → 422) ② `hash_password`(저장 거부) ③ `verify_password`(`ValueError` → `False` → 401) 세 겹으로 막는다. ⛔ 이 가드를 지우면 긴 비밀번호 한 번으로 500 이 난다.
- PyJWT 는 인증에 쓰지 않지만 공통 `core/security.py` 가 import 하므로 남겨 둔다(형제 FastAPI 템플릿과 공유하는 파일).

### WSGI 서버
- `gunicorn` 은 Windows 를 지원하지 않아 `requirements.txt` 에 `; sys_platform != "win32"` 마커가 있다. Windows 운영은 `waitress` 다.

### ruff (린트)
- 설정은 `pyproject.toml`: `alembic/` 제외, line-length 120, `select = E·F·I·B·UP`.
- `UP042`: `class X(str, enum.Enum)` → **`enum.StrEnum`** 을 쓴다(`UserRole`).
- 검사는 `ruff check .` 만 한다. `ruff format` 은 강제하지 않는다(공통 계층 코드가 format 기준과 다르다).

## 4. 핀 정책
- `requirements.txt` 는 **`==` 정확 핀, 재현성 우선**(ARCHITECTURE.md §2).
- 원칙은 직접 의존성만 핀하지만, **동작을 좌우하는데 상위가 범위를 넓게 열어 둔 전이 의존성은 예외로 직접 핀**한다. 현재 대상: **`werkzeug`·`jinja2`·`markupsafe`·`itsdangerous`**(§3 Flask).
- 런타임 하한을 올린다고 핀을 자동으로 올리지 않는다 — **호환되면 유지**한다.
- 핀 상향은 보안·기능 목적의 **의식적 결정**으로 한다.
- 후보 버전은 **배포 후 24시간이 지난 것**만 고른다(당일 배포본은 회수·핫픽스 위험) — §5 의 `--uploaded-prior-to P1D`. Tailwind CLI·htmx·uv·pip-audit·GitHub Actions 도 같은 기준이다.
- 전이 의존성은 `requirements.lock` 이 고정한다. lock 은 `scripts/versions.env` 의 `LOCK_EXCLUDE_NEWER`(UTC) 뒤에 올라온 배포본을 넣지 않으므로(`uv --exclude-newer`), 이 값은 **lock 을 다시 만드는 시점의 24시간 전**으로 옮긴다. 값을 옮기면 직접 핀이 아닌 전이 의존성도 그 시각의 최신으로 바뀐다 — lock diff 를 보고 의도하지 않은 변경이 없는지 확인한다.
- ⛔ `requirements.txt` 만 바꾸고 lock 을 다시 만들지 않으면 CI `lock` 잡이 실패한다(설치는 lock 만 쓴다).

## 5. 업그레이드 검증 절차 (필수)

버전을 올릴 땐 추측하지 않는다 — **이 프로젝트에서 실제로 설치·검증한 뒤** 핀을 고정한다. 의존성을 한꺼번에 올리면 브랜치에서 진행하는 편이 안전하다([pr-workflow]).
명령은 프로젝트 루트에서 실행한다. **각 명령의 종료 코드를 확인하고, 실패하면 다음 단계로 가지 않는다.**

### 5-1. Python 패키지

사람이 고치는 파일은 `requirements.txt`(직접 의존성)와 `.github/requirements-ci.txt`(CI 도구)뿐이다. 두 lock 은 `scripts/lock.py` 가 다시 만든다.
lock 도구(uv)·pip 는 프로젝트 `.venv` 가 아니라 **프로젝트 밖의 도구 venv** 에 `.github/requirements-ci.lock` 으로 설치한다(프로젝트 venv 에 도구가 섞이지 않게).

1. **venv 는 `.python-version` 의 Python 으로 만든다.** 시스템 기본 `python` 이 더 새 버전(예: 3.14)일 수 있으니 버전을 먼저 확인한다.
2. 도구 venv 에서 `pip install --dry-run --uploaded-prior-to P1D <패키지>` 로 배포 후 24시간이 지난 후보 버전을 확인하고(`Would install …`), `requirements.txt` 에 `==` 로 적는다. Flask 를 올리면 Werkzeug 핀도 함께 본다(§3).
3. `scripts/versions.env` 의 `LOCK_EXCLUDE_NEWER` 를 **지금보다 24시간 이상 전의 UTC 시각**(`YYYY-MM-DDT00:00:00Z` 형식)으로 옮기고, 도구 venv 의 python 으로 `scripts/lock.py` 를 실행해 두 lock 을 다시 만든다. lock diff 에서 전이 의존성 변경을 확인한다(§4).
4. 프로젝트 `.venv` 를 `--clear` 로 다시 만들어 `pip install --require-hashes -r requirements.lock` 으로 설치하고 `pip check` → `ruff check .` → `pytest -q -W error::DeprecationWarning` 을 통과시킨다.
5. `scripts/lock.py --check`(CI `lock` 잡과 같다)와 `pip-audit -r requirements.lock --require-hashes --disable-pip` 로 마무리한다.
6. 모델·마이그레이션·DB 드라이버가 바뀌었으면 실제 PostgreSQL 에서 `alembic upgrade head` → `alembic check` 까지 확인한다([db-migration]).

```powershell
# Windows (PowerShell 5.1) — py 런처로 .python-version 과 같은 버전을 지정한다(기존 venv 는 --clear 로 다시 만든다)
# py 런처가 없으면(pyenv-win 등) 핀 버전 python.exe 경로로 만든다 — 예: & (pyenv which python) -m venv --clear .venv
$tools = Join-Path $env:TEMP 'lock-tools'                 # 도구 venv — 프로젝트 밖에 둔다
py -3.13 -m venv --clear $tools;                          if ($LASTEXITCODE) { throw "도구 venv 생성 실패" }
& "$tools\Scripts\python" -m pip install --require-hashes -r .github\requirements-ci.lock; if ($LASTEXITCODE) { throw "도구 설치 실패" }
& "$tools\Scripts\python" -m pip install --dry-run --ignore-installed --no-deps --uploaded-prior-to P1D <패키지>  # 후보 확인
# → requirements.txt 의 핀과 versions.env 의 LOCK_EXCLUDE_NEWER 를 고친다
& "$tools\Scripts\python" -B scripts\lock.py;             if ($LASTEXITCODE) { throw "lock 생성 실패" }
py -3.13 -m venv --clear .venv;                           if ($LASTEXITCODE) { throw "venv 생성 실패" }
.\.venv\Scripts\python --version                          # .python-version 과 같은 3.13.x 인지 확인
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock; if ($LASTEXITCODE) { throw "설치 실패" }
.\.venv\Scripts\python -m pip check;                      if ($LASTEXITCODE) { throw "pip check 실패" }
.\.venv\Scripts\python -m ruff check .;                   if ($LASTEXITCODE) { throw "ruff 실패" }
.\.venv\Scripts\python -m pytest -q -W error::DeprecationWarning; if ($LASTEXITCODE) { throw "pytest 실패" }
& "$tools\Scripts\python" -B scripts\lock.py --check;     if ($LASTEXITCODE) { throw "lock 불일치" }
& "$tools\Scripts\python" -m pip_audit -r requirements.lock --require-hashes --disable-pip; if ($LASTEXITCODE) { throw "취약점 발견" }
```

```bash
# macOS / Linux — pyenv 를 쓰면 python 이 .python-version 을 따른다. && 는 실패한 곳에서 멈춘다
# (⛔ 대화형 셸에 set -e 를 걸지 않는다 — 명령 하나가 실패하면 셸이 닫힌다)
python --version                                          # .python-version 과 같은 3.13.x 인지 확인
tools="${TMPDIR:-/tmp}/lock-tools"                        # 도구 venv — 프로젝트 밖에 둔다
python -m venv --clear "$tools" \
  && "$tools/bin/python" -m pip install --require-hashes -r .github/requirements-ci.lock \
  && "$tools/bin/python" -m pip install --dry-run --ignore-installed --no-deps --uploaded-prior-to P1D <패키지>
# → requirements.txt 의 핀과 versions.env 의 LOCK_EXCLUDE_NEWER 를 고친다
"$tools/bin/python" -B scripts/lock.py \
  && python -m venv --clear .venv \
  && ./.venv/bin/python -m pip install --require-hashes -r requirements.lock \
  && ./.venv/bin/python -m pip check \
  && ./.venv/bin/python -m ruff check . \
  && ./.venv/bin/python -m pytest -q -W error::DeprecationWarning \
  && "$tools/bin/python" -B scripts/lock.py --check \
  && "$tools/bin/python" -m pip_audit -r requirements.lock --require-hashes --disable-pip
```

- **CI 도구(pip-audit·uv)를 올릴 때**: `.github/requirements-ci.txt` 의 핀을 고친다. `scripts/lock.py` 는 설치된 uv 가 이 핀과 다르면 멈추므로(uv 버전마다 lock 결과가 달라질 수 있다), 도구 venv 에 새 uv 를 먼저 `pip install --uploaded-prior-to P1D uv==<새 버전>` 으로 넣고 lock 을 다시 만든 뒤, 도구 venv 를 새 `.github/requirements-ci.lock` 으로 다시 만들어 `--check` 가 통과하는지 본다.
- **Dependabot PR**(`.github/dependabot.yml`, 매주): pip PR 은 `requirements.txt`·`.github/requirements-ci.txt` 의 핀만 바꾸고 lock 은 바꾸지 않는다 → CI `lock` 잡이 **실패하는 것이 정상**이다. 그 PR 브랜치에서 위 3~5단계(기준 시각 이동 → `scripts/lock.py` → 설치·테스트 → `--check`)를 거쳐 lock 을 함께 커밋한 뒤 병합한다. Dependabot 은 배포 후 1일이 지난 버전만 올리지만(cooldown) 그 버전이 `LOCK_EXCLUDE_NEWER` 보다 새로우면 기준 시각을 옮겨야 lock 이 만들어진다.
- **GitHub Actions**: Dependabot 이 SHA 와 `# vX.Y.Z` 주석을 함께 올린다. 손으로 올릴 때는 `gh api repos/<소유자>/<액션>/git/ref/tags/<태그>` 로 SHA 를 확인하고, 그 커밋이 공식 저장소의 릴리스 태그인지 본다. **PostgreSQL 이미지 digest** 는 Dependabot 대상이 아니다 — `docker buildx imagetools inspect postgres:16` 의 `Digest` 로 손으로 옮기고 주석의 버전·빌드 날짜를 함께 고친다.
### 5-2. Tailwind CLI · htmx

- **Tailwind**: 새 릴리스의 자산별 SHA-256 을 GitHub 자산 digest 로 확인한다 — `gh api repos/tailwindlabs/tailwindcss/releases/tags/v<버전> --jq '.assets[] | select(.name | startswith("tailwindcss-")) | "\(.digest | ltrimstr("sha256:"))  \(.name)"'`. 그 결과로 `scripts/tailwind-sha256sums.txt` 의 해시 줄을 모두 바꾸고(첫 줄 주석의 버전도), `versions.env` 의 `TAILWIND_VERSION` 을 같은 버전으로 바꾼다. `.tools/` 를 지우고 `scripts/tailwind.*` 를 실행해 내려받기·검증·빌드가 통과하는지, 화면 스타일이 그대로인지 확인한다.
- **htmx**: npm 레지스트리의 `htmx.org@<버전>` 패키지 정보에서 `dist.tarball`·`dist.integrity`(sha512)를 확인하고, 내려받은 tarball 의 sha512 가 integrity 와 같을 때만 `package/dist/htmx.min.js` 를 `app/static/js/htmx.min.js` 로 복사한다. 파일 안의 `version:"<버전>"` 을 확인하고 `versions.env` 의 `HTMX_VERSION` 을 바꾼다. 릴리스 노트에서 설정 기본값 변경을 확인하고(§3 htmx), 브라우저에서 htmx 예제 세 곳(공지 검색·사용자 행 저장·배너 순서)과 CSP 위반 없음까지 확인한다.

### 5-3. 반영
- 통과하면 SSOT 파일과 `README.md` 의 버전 표를 갱신하고, 새로 알게 된 버전별 함정이 있으면 **이 스킬의 §3** 에 적는다(필요하면 `ARCHITECTURE.md` 도). 이력(언제 몇 버전으로 올렸는지)은 커밋 메시지에 남기고 이 스킬에는 적지 않는다.
- 커밋은 [pr-workflow] 를 따른다(의존성 상향은 보통 `[Behavioral] chore:`).
