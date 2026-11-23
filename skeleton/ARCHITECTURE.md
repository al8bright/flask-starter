# flask-starter 아키텍처 가이드

> 본 문서는 **flask-starter 로 생성한 프로젝트**가 따르는 아키텍처 표준이다.
> 표준 스택은 **Flask(서버 렌더링 Jinja) + PostgreSQL** 이고, 화면 일부는 **htmx 로 선택적으로 보강**하며 CSS 는 **Tailwind CSS standalone CLI** 로 빌드한다(Node 불필요).
> 인증은 **DB 세션(`auth_sessions`) 불투명 토큰을 httpOnly 쿠키**로 두고(SSO 는 도입 시 확장 §9), 시각은 **KST 단일 기준**을 따른다.
> 모델·스키마·서비스·마이그레이션(공통 계층)은 형제 템플릿 `fastapi-react-pg-starter` 의 백엔드와 같은 코드다. 절 번호도 형제 문서와 같게 두므로(공통 코드 주석이 § 번호를 참조한다) 주제가 다른 절은 내용만 바뀐다(§13·§14).
> 이 템플릿을 사용하기로 했다면 아래 규칙을 프로젝트의 기본 계약으로 적용한다.

---

## ★ 핵심 MUST 요약 (반드시 고정)

> 아래 항목은 **프로젝트마다 바뀌지 않는 고정 규칙**이다. 어기려면 사용자와 합의한 뒤 §22 「프로젝트 고유 결정(예외)」에 사유를 남기되, ⛔ 표시 항목은 예외 없이 금지한다.
> 세부 내용은 각 섹션(§) 참조. 커밋·push 흐름(단독 개발 기본값: `main` 직접 커밋 + push 전 로컬 검증)은 MUST 가 아니라 [`pr-workflow` 스킬](.claude/skills/pr-workflow/SKILL.md)의 기본값이다(§20).

| # | 고정 규칙 (MUST) | § |
|---|------------------|---|
| 1 | **표준 스택 고정**: Flask 3 + Jinja + SQLAlchemy 2 + Alembic, DB 는 **PostgreSQL**. 화면 보강은 htmx(벤더링), 스타일은 Tailwind CSS standalone CLI. ⛔ Node·npm 빌드 단계, SPA 프레임워크, Alpine.js 금지 — 정확한 버전은 `requirements.txt`·`scripts/versions.env` | §2 |
| 2 | **DB는 항상 Alembic으로만 관리** — 모든 스키마 생성·변경은 마이그레이션. ⛔ dev/운영 런타임 `create_all`·자동 DDL·수동 `ALTER` 금지(테스트 임시 DB만 예외) | §11 |
| 3 | **설정은 OS 무관한 프로젝트 루트 `.env` 하나로 주입**. ⛔ 개발 중 `$env:`/`export`/`set` 셸 환경변수 의존 금지. ⛔ 실제 `.env` 커밋 금지(`.env.example`만) | §5, §17 |
| 4 | **시각은 KST 단일 기준 — OS·프로세스 시각대와 무관** — 저장·비교 기준은 KST naive(`now()` = 고정 오프셋 UTC+9 로 계산한 naive 값), PostgreSQL `connect_args`에 `timezone=Asia/Seoul`. ⛔ OS 시각대를 따르는 호출(naive `datetime.now()`·`date.today()`·인자 없는 `astimezone()`) 금지 — `now()`·`KST` 를 쓴다. ⛔ UTC 저장·aware 시각 비교 금지(외부 연동 값의 경계 변환과 표시용 `ZoneInfo` 변환은 허용) | §10, §7 |
| 5 | **화면은 블루프린트, JSON 은 `/api/v1`** — 화면(`/`·`/login`·`/admin`)은 HTML 을 렌더링하고, `/api/v1` 아래에는 헬스 체크·첨부 다운로드만 둔다. 블루프린트 등록은 `app/web/__init__.py` 한 곳 | §4 |
| 6 | **설정 접근은 `get_settings()` + `@lru_cache`** — ⛔ 모듈 전역 `settings` 싱글톤 금지 | §5 |
| 7 | **공통 의존성은 `app/dependencies.py` 단일 파일** (`get_db`, `current_user`, `login_required`, `admin_required`, 인증 쿠키) | §6 |
| 8 | **계층 분리** — 뷰(`app/web/`)는 HTTP 입출력·폼 해석·템플릿 선택만, 도메인 로직은 `services/`, 검증은 `schemas/`(pydantic). 도메인 오류는 `ServiceError` + `app/web/errors.py` 의 `STATUS_BY_CODE` | §4, §8 |
| 9 | **htmx 는 선택적 보강** — 모든 화면은 htmx 없이 일반 링크·폼으로 동작한다. `HX-Request` 분기는 `app/web/htmx.py` 헬퍼로만 한다 | §13 |
| 10 | **CSP `script-src 'self'`·`style-src 'self'`** — ⛔ 인라인 `<script>`·`style=` 속성·`on*=` 이벤트 속성·외부 CDN 스크립트 금지 | §9, §13 |
| 11 | **인증은 DB 세션 쿠키** — 로그인마다 `auth_sessions` 행 하나, 쿠키에는 불투명 토큰만, 요청마다 DB 에서 세션·사용자를 다시 확인한다. ⛔ JWT·Flask-Login·Flask 기본 `session` 으로 인증 상태를 들고 다니지 않는다(Flask `session` 은 flash·CSRF 토큰 전용) | §9, §14 |
| 12 | **CSRF** — 상태를 바꾸는 요청은 모두 POST 이고 Flask-WTF `CSRFProtect` 가 전역으로 검사한다. ⛔ `csrf.exempt` 금지 | §9, §14 |
| 13 | **테스트는 pytest + 임시 SQLite 파일** — `get_settings.cache_clear()` autouse, `create_app(session_factory=...)` 로 격리 | §12 |
| 14 | **TDD + Tidy First** — Red→Green→Refactor, 구조 변경과 동작 변경을 한 커밋에 섞지 않음 | §18 |
| 15 | **커밋 메시지**: `[Structural]`/`[Behavioral]` + conventional type, 테스트·린트 통과 시에만 커밋 | §19 |

---

## 0. 적용 범위 & 우선순위

- **MUST**: 이 템플릿으로 생성한 프로젝트는 반드시 따른다.
- **SHOULD**: 특별한 사유가 없으면 따른다. 벗어나면 §22 「프로젝트 고유 결정(예외)」에 사유를 남긴다.
- **MAY**: 프로젝트 성격에 따라 선택한다.
- 본 가이드와 프로젝트의 추가 문서(`docs/` 등)가 충돌하면 **본 가이드 우선**이다.
- 예외(프로젝트 고유 결정)는 **§22 한 곳에만** 기록한다. `AGENTS.md` 는 그 절을 링크만 한다.

---

## 1. 프로젝트 명명 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| **저장소/루트 폴더** | `PascalCase` 또는 `snake_case` 일관 유지(프로젝트 내 통일) | `MyProject`, `my_project` |
| **표시 이름** | 스캐폴드 입력값 그대로 — `app/main.py` 의 `PROJECT_NAME`, 템플릿 전역 `project_name` | `My Project` |
| **PostgreSQL DB명·쿠키 접두사** | `snake_case`, 프로젝트명 기반(스캐폴드가 변환) | `my_project`, `my_project_session` |
| **DB 테이블명** | `snake_case` **복수형**. 외부(ERP 등) 연동 테이블은 접미사로 출처 표기 | `users`, `notices`, `orders_erp` |
| **Python 모듈 파일** | `snake_case`, 모델은 **단수** | `order.py`, `order_service.py` |
| **Jinja 템플릿** | `<영역>/<화면>.html`, htmx 조각은 `partials/<이름>.html`, 레이아웃 조각은 `_` 접두사 | `admin/orders.html`, `partials/order_row.html`, `admin/_layout.html` |
| **블루프린트·엔드포인트** | 블루프린트 이름 = 모듈 이름, 뷰 함수는 동작을 드러내는 `snake_case` | `admin.edit_notice`, `public.notice_detail` |
| **환경변수** | `UPPER_SNAKE` | `DATABASE_URL`, `COOKIE_SECURE` |

---

## 2. 기술 스택 표준

- **언어/런타임**: Python 3.13+ (`X | None` 문법, `Mapped[]` 타입 힌트, PEP 695 제네릭) — 하한은 `scripts/versions.env`(`MIN_PYTHON`), 정확 핀은 루트 `.python-version`(pyenv)
- **웹 프레임워크**: Flask 3 + Jinja. Flask 가 하한으로만 요구하는 **Werkzeug·Jinja2·MarkupSafe·itsdangerous 도 `requirements.txt` 에 직접 `==` 고정**한다(재현성)
- **WSGI 서버(운영)**: `waitress`(Windows·Linux) 또는 `gunicorn`(Linux — `requirements.txt` 에 `sys_platform != "win32"` 마커). 개발은 `flask --app app.main run --debug`
- **CSRF**: Flask-WTF `CSRFProtect` 만 쓴다. 폼 검증은 WTForms 폼 클래스가 아니라 `schemas/` 의 pydantic 모델이다(검증 규칙을 한 벌로 유지 — §8)
- **ORM/마이그레이션**: SQLAlchemy 2.x (2.0 스타일 `Mapped`/`mapped_column`) + Alembic
- **DB 드라이버**: PostgreSQL(16+ 권장, CI 는 `postgres:16`) + `psycopg2-binary`
- **설정**: `pydantic-settings` (BaseSettings) / **검증**: Pydantic 2.x
- **인증**: DB 세션 불투명 토큰 + bcrypt(§9). `PyJWT` 는 인증에 쓰지 않지만 공통 `core/security.py` 가 import 하므로 남긴다
- **업로드·정화**: Pillow(이미지 검증·재인코딩), nh3(본문 HTML 허용 목록)
- **화면**: Jinja 템플릿 + **htmx 2**(`app/static/js/htmx.min.js` 벤더링, 버전은 `versions.env` 의 `HTMX_VERSION`) + `app/static/js/app.js`(확인 대화상자 하나)
- **스타일**: Tailwind CSS v4 **standalone CLI**(`scripts/tailwind.*` 가 `versions.env` 의 `TAILWIND_VERSION` 바이너리를 내려받아 SHA-256 을 확인한 뒤 빌드) — §15
- **테스트·린트**: `pytest` + Flask `test_client`, `ruff`
- **버전 고정**: `requirements.txt` 에 **`==` 정확한 버전 핀** (재현성 우선). 버전별 주의는 [`stack-versions` 스킬](.claude/skills/stack-versions/SKILL.md)

> 클라이언트 상태(모달 스택·드래그·실시간 동기화)가 화면의 핵심이면 htmx 로 흉내 내지 않는다. 형제 SPA 스타터(FastAPI + React)를 검토하고 결정을 §22 에 남긴다.

---

## 3. 저장소 구조(목표)

```
<ProjectName>/
├── app/                     # Flask 앱 — 웹 계층 + 공통 계층 (§4)
├── alembic/                 # 마이그레이션 (versions/0001~0004 포함)
├── alembic.ini
├── tests/
├── scripts/                 # bootstrap · tailwind (.sh / .ps1) · versions.env · tailwind-sha256sums.txt
├── uploads/                 # UPLOAD_DIR 기본값 — public/·private/, .gitignore 대상
├── .tools/                  # Tailwind CLI 바이너리(내려받기), .gitignore 대상
├── .github/                 # CI(workflows/ci.yml), PS 5.1 구문 검사, PR 템플릿
├── .claude/skills/          # 작업별 AI 스킬
├── docs/                    # 프로젝트 고유 문서 (PRD·유저 플로우·기획서·<연동>-가이드 등)
├── requirements.txt · pyproject.toml(ruff) · pytest.ini
├── .env.example             # 키 목록 — 복사한 .env 는 커밋하지 않는다
├── .python-version
├── AGENTS.md                # AI 에이전트 공통 지침 (CLAUDE.md 가 @import)
├── CLAUDE.md                # Claude Code 진입점
├── ARCHITECTURE.md          # 본 가이드 — 벗어난 결정/사유도 여기 기록
├── PLAN.md                  # TDD 작업 순서 (필수)
└── README.md
```

- 평면 구조다 — `backend/`·`frontend/` 분리가 없고 명령은 모두 프로젝트 루트에서 실행한다. 공통 `config.py` 의 `BACKEND_ROOT` 는 이 구조에서 프로젝트 루트를 가리킨다.
- 루트에 `PLAN.md`를 두고 **TDD 작업 순서**(실패 테스트 단위)를 관리한다.

---

## 4. 앱 구조(`app/`)

```
app/
├── __init__.py
├── main.py                 # create_app() — 설정 검사, Flask 설정(쿠키·업로드 상한·CSRF), 보안 헤더, 오류 처리, 블루프린트, 관리자 시드
├── config.py               # Settings(BaseSettings) + get_settings()                    ┐
├── cli.py                  # python -m app.cli create-admin / set-password              │
├── core/                   # security(now·비밀번호·세션 토큰) · storage · sanitize · logging │ 공통 계층
├── db/                     # base(Base) · engine(KST connect_args) · session(SessionLocal)  │ (형제 템플릿과
├── models/                 # app_meta · user · auth_session · notice · banner · <domain>  │  같은 파일)
├── schemas/                # pydantic 요청·응답·폼 검증                                    │
├── services/               # *_service.py 도메인 로직 + exceptions.ServiceError           ┘
├── dependencies.py         # get_db, current_user, login_required, admin_required, 인증 쿠키  ★단일 파일 (§6)
├── web/                    # 얇은 HTTP 계층 (Flask 전용)
│   ├── __init__.py         # register_blueprints — 블루프린트 등록 한 곳
│   ├── public.py           # /  /notices  /notices/<id>
│   ├── auth.py             # /login (GET·POST)  /logout (POST)
│   ├── admin/              # /admin/* — 블루프린트 before_request 로 전체 관리자 전용
│   │   ├── __init__.py     #   bp + 하위 모듈 import(라우트 등록)
│   │   ├── dashboard.py · users.py · notices.py · banners.py
│   ├── api.py              # /api/v1/health, /api/v1/health/db, /api/v1/notices/<id>/attachments/<aid>
│   ├── files.py            # /uploads/public/<key> 정적 서빙, 첨부 응답·업로드 읽기 공통
│   ├── errors.py           # ServiceError·StorageError·CSRF·HTTP 오류 → 응답 (STATUS_BY_CODE)
│   ├── htmx.py             # is_htmx, render_page_or_partial, htmx_redirect
│   ├── forms.py            # parse_form(pydantic), checkbox, optional_*
│   ├── pagination.py       # page_arg, page_links
│   └── security_headers.py # CSP·nosniff·HSTS·Cache-Control
├── templates/              # base.html · public/ · auth/ · admin/ · errors/ · partials/
└── static/                 # css/input.css(→ app.css 빌드) · js/htmx.min.js · js/app.js
```

### 계층 규칙 (MUST)
- **뷰(`app/web/`)는 얇게**: 요청 값 읽기 → `parse_form` 으로 스키마 검증 → 서비스 호출 → 템플릿 렌더링 또는 redirect. 비즈니스 로직 금지.
- **도메인 로직은 `services/`**: DB 트랜잭션, 규칙 검증, 외부 연동. ⛔ 서비스에서 Flask(`request`·`g`·`flash`)를 import 하지 않는다 — 공통 계층이 형제 템플릿과 같은 코드로 남아야 한다.
- **`schemas/`**: Pydantic 검증·직렬화 전용. ORM 모델과 분리.
- **의존성**: DB 세션·현재 사용자는 항상 `app/dependencies.py` 의 `get_db()`·`current_user()` 로 얻는다(§6).
- ⛔ 공통 계층(`config.py`·`cli.py`·`core/`·`db/`·`models/`·`schemas/`·`services/`·`alembic/`)에 Flask 의존 코드를 넣지 않는다.

### `main.py` 구성 (요약 — 전체는 `app/main.py`)
```python
import app.models  # noqa: F401  모델 메타데이터 등록

def create_app(*, session_factory=None) -> Flask:
    settings = get_settings()            # ⛔ 모듈 전역 settings 금지 — 생성 시점에 읽는다 (§5)
    configure_logging(settings.log_level)
    check_startup_settings(settings)     # 안전하지 않은 운영 설정이면 기동 거부 (§9, §21)
    storage.ensure_dirs()                # UPLOAD_DIR/public·private
    flask_app = Flask(__name__)
    flask_app.config.update(
        SECRET_KEY=settings.secret_key,                  # flash·CSRF 서명 쿠키 전용 — 인증은 DB 세션 (§9)
        SESSION_COOKIE_NAME="<snake>_flash", SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=settings.cookie_secure,
        MAX_CONTENT_LENGTH=..., MAX_FORM_MEMORY_SIZE=...,  # 요청 본문·폼 필드 상한 (§8)
        WTF_CSRF_TIME_LIMIT=None, WTF_CSRF_SSL_STRICT=settings.cookie_secure,
    )
    csrf.init_app(flask_app)                       # 전역 CSRF (§14)
    dependencies.init_app(flask_app, session_factory)
    register_security_headers(flask_app)           # §9
    register_error_handlers(flask_app)             # §8
    register_blueprints(flask_app)
    seed_default_admin(settings, session_factory)  # SEED_DEFAULT_ADMIN (§9)
    # ⛔ create_all 을 호출하지 않는다 — 스키마는 Alembic 으로만 만든다 (§11)
    return flask_app
```

- ⛔ 모듈 전역 `app = create_app()` 을 두지 않는다 — import 만으로 설정 검사·시드가 돈다. 실행은 `flask --app app.main run`(Flask 가 `create_app` 을 찾는다), `waitress-serve --call app.main:create_app`, `gunicorn "app.main:create_app()"`.

### 블루프린트 등록 (`app/web/__init__.py`)
```python
def register_blueprints(app: Flask) -> None:
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(files_bp)
    # 새 영역 블루프린트를 여기에 추가한다. 관리자 화면은 app/web/admin/__init__.py 의 import 목록에 모듈을 더한다.
```

---

## 5. 설정 (`config.py`)  — `get_settings()` + `@lru_cache`

공통 계층 파일이다(형제 템플릿과 같은 코드). 요약:

```python
BACKEND_ROOT = Path(__file__).resolve().parent.parent   # 평면 구조에서는 프로젝트 루트
ENV_FILE = BACKEND_ROOT / ".env"                         # 실행 디렉터리와 무관하게 항상 루트 .env

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"   # 그 밖의 값은 기동 거부
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str | None = None                      # 미설정이면 엔진 생성에서 fail-fast (§7)
    secret_key: str = DEFAULT_SECRET_KEY                 # 공개된 기본값 — 운영 기동 거부 (§9)
    refresh_token_expire_days: int = 14                  # 이 템플릿에서는 로그인 세션 수명 (§9)
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)
    login_max_failures: int = 5
    login_lockout_minutes: int = 15
    cookie_secure: bool = False
    tz: str = "Asia/Seoul"
    seed_default_admin: bool = False                     # ⛔ 비밀번호 기본값 없음
    default_admin_password: str | None = None
    upload_dir: Path = BACKEND_ROOT / "uploads"          # 상대 경로는 프로젝트 루트 기준
    public_files_base_url: str = ""
    max_image_upload_mb: int = 5
    max_attachment_upload_mb: int = 20
    # (FastAPI 형제 전용 필드 — 아래 참고)

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _apply_timezone(settings.tz)          # TZ 적용 (§10)
    return settings
```

규칙:
- **접근은 항상 `get_settings()` 함수로** (모듈 전역 `settings` 싱글톤 금지). → 테스트에서 `get_settings.cache_clear()`로 환경을 재설정할 수 있어야 한다.
- 공통 `Settings` 에는 형제 FastAPI 템플릿만 쓰는 필드(`access_token_expire_minutes`·`refresh_token_transport`·`cors_origins`·`frontend_url`·`backend_public_url`)도 있다. 이 템플릿은 읽지 않으며 `.env.example` 에도 두지 않는다 — 공통 파일을 고치지 않기 위해 그대로 둔다.
- 환경변수명이 필드명과 다르면 `Field(validation_alias=...)`로 명시한다.

### 설정 주입은 항상 루트 `.env` — OS 독립 (MUST)

> **개발 환경 설정은 OS에 관계없이 프로젝트 루트 `.env` 파일로 주입한다.** `.env.example` 을 복사해 만든다(스캐폴드가 무작위 비밀값을 넣어 만들어 준다).

- `pydantic-settings`가 `ENV_FILE`(절대 경로)을 읽으므로 어느 디렉터리에서 실행해도 같은 파일을 읽는다. 코드에 설정값 하드코딩 금지.
- **금지(MUST)**: 개발 중 OS별 셸 환경변수 설정에 의존하는 방식 — PowerShell `$env:VAR=...`, bash `export VAR=...`, `set VAR=...`, `launch.json`/IDE·OS 사용자 환경변수에 비밀값을 박아두는 것.
- **예외**: 컨테이너/CI/배포 런타임에서 **오케스트레이터가 주입하는 실제 환경변수는 허용**(같은 키를 `pydantic-settings` 가 같은 인터페이스로 읽는다). 로컬 개발은 `.env` 강제, 운영은 동일 키를 환경변수로 주입.
- 실제 `.env`는 **커밋 금지(`.gitignore`)**, `.env.example`에 **키만** 채워 커밋한다(§17).
- 줄바꿈/인코딩은 `UTF-8` 로 통일한다. 저장소에는 `.gitattributes`의 `* text=auto eol=lf`를 둔다.

---

## 6. 의존성 (`app/dependencies.py`)  ★단일 파일

Flask 에는 FastAPI 의 `Depends` 가 없으므로 같은 역할을 **요청 훅과 데코레이터**로 둔다.

```python
def init_app(app, session_factory):
    app.extensions["db_session_factory"] = session_factory
    app.before_request(_load_current_user)     # 쿠키 → 세션 행 → 사용자 (정적 파일·헬스 체크는 건너뛴다)
    app.teardown_appcontext(_close_db)         # 요청이 끝나면 세션을 닫는다
    app.context_processor(lambda: {"current_user": current_user()})

def get_db() -> Session:                       # 요청 단위 DB 세션 — 같은 요청 안에서는 같은 세션
    if "db" not in g:
        g.db = current_app.extensions["db_session_factory"]()
    return g.db

def current_user() -> User | None: ...         # 살아 있는 세션 + 활성 사용자일 때만

def login_required(view): ...                  # 비로그인 → /login?next=… (htmx 요청은 401 + HX-Redirect)
def admin_required(view): ...                  # 비로그인 → 로그인 화면, 로그인했지만 관리자가 아니면 403
def set_auth_cookie(response, token): ...      # 인증 쿠키 속성은 여기 한 곳 (§14)
def clear_auth_cookie(response): ...
```

- 위 코드는 요약이다. 공통 의존성(`get_db`, 현재 사용자, 권한 데코레이터, 인증 쿠키 이름·속성, 로그인 후 복귀 경로 검사 `safe_next_path`)은 **`app/dependencies.py` 한 곳**에 모은다.
- 관리자 블루프린트는 `before_request` 에 `admin_required` 를 걸어 `/admin/*` 전체를 막는다 — 뷰마다 데코레이터를 빠뜨려도 열리지 않는다.

---

## 7. DB · 세션 · 엔진

`app/db/engine.py` (엔진 팩토리 — SQLite 테스트/PostgreSQL 운영 동시 지원, 공통 계층):
```python
def postgres_connect_args() -> dict[str, str]:
    return {"options": "-c timezone=Asia/Seoul"}   # ★ KST

def create_engine_from_settings(settings: Settings) -> Engine:
    # DATABASE_URL 미설정 시 조용한 폴백 없이 fail-fast 한다 (alembic/env.py 와 동일 정책)
    url = settings.database_url
    if not url:
        raise RuntimeError(f"DATABASE_URL 이 설정되지 않았습니다 ({ENV_FILE} 확인).")
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    elif "postgresql" in url:
        kwargs["connect_args"] = postgres_connect_args()
    return create_engine(url, pool_pre_ping=True, **kwargs)
```

- `app/db/base.py`: `class Base(DeclarativeBase)`.
- `app/db/session.py`: 모듈 로드 시 엔진과 `SessionLocal`(세션 옵션 `SESSION_OPTIONS` — 테스트 픽스처도 같은 값을 쓴다)을 만든다. 요청 단위 세션은 `dependencies.get_db` 가 연다.
- **PostgreSQL 연결에는 반드시 `timezone=Asia/Seoul` connect_args를 적용한다.**
- WSGI 서버가 여러 스레드로 요청을 받으므로 세션은 요청마다 새로 열고 닫는다(`g` 에 보관, `teardown_appcontext` 에서 닫음). ⛔ 모듈 전역 세션을 공유하지 않는다.

---

## 8. 모델 · 스키마 · 서비스 규칙

### 모델 (`models/`) — SQLAlchemy 2.x `Mapped`
```python
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, server_default=func.now())
```
- 모든 모델은 `models/__init__.py`에서 import(re-export)하여 메타데이터에 등록한다.
- 생성 시각은 `default=now`(KST naive). 열거형은 `enum.StrEnum`을 상속(ruff UP042 — `str, enum.Enum` 다중 상속 금지).
- **기본값이 있는 NOT NULL 컬럼은 `default`(ORM)와 `server_default`(DB)를 함께 둔다** — ORM 을 거치지 않는 경로(psql 수동 INSERT, ETL, 데이터 이관)에서도 NOT NULL 위반이 나지 않게 한다. 불리언은 `server_default=true()`/`false()`, 숫자는 `"0"`, 시각은 `func.now()`(DB 세션 timezone 이 Asia/Seoul 이라 KST 다, §7). 기본값이 없는 필수 입력 컬럼(예: `title`)에는 두지 않는다.

### 스키마 (`schemas/`)
- 요청 본문과 응답을 **용도별 클래스로 나눈다**. 생성·전체 교체가 같은 본문이면 `XxxWrite` 하나로 둔다(예: `NoticeWrite`·`BannerWrite`).
- 제약은 `Field(ge=, gt=, max_length=)`, 복합 규칙은 `@field_validator`/`@model_validator`. 오류 메시지는 화면에 그대로 나가므로 **한국어**로 쓴다(`ValueError("…")`).
- **폼 검증도 이 스키마로 한다** — 뷰는 `app/web/forms.py` 의 `parse_form(Model, **values)` 로 `(데이터, {필드: 첫 오류})` 를 받고, 오류가 있으면 입력값과 함께 같은 템플릿을 **422** 로 다시 그린다. 체크박스·빈 문자열·`datetime-local` 값은 `checkbox`·`optional_text`·`optional_datetime` 으로 바꿔 넘긴다. pydantic 의 `"Value error, "` 접두어는 `parse_form` 이 뗀다.

### 서비스 (`services/`)
- 함수형 서비스(`def create_order(db, user, data)`)를 기본으로 한다.
- 실패는 `ServiceError(code, message)` **도메인 예외**로 던진다. 뷰에서 `try/except` 로 직접 HTTP 로 바꾸지 않는다 — 예외는 폼을 다시 그려야 하는 경우(예: 본문이 비어 있음 `empty_body`)와 로그인 화면(`invalid_credentials` 401·`too_many_attempts` 429)뿐이다.
- N+1 방지: 조회 시 `selectinload` 등 명시적 로딩 옵션.
- `ServiceError(code)`(와 저장소의 `StorageError`)는 `app/web/errors.py` 의 전역 핸들러가 `STATUS_BY_CODE` 표로 HTTP 상태를 정한다(`not_found` 404, `self_modification`·`last_admin`·`too_many_attachments` 409, `file_too_large` 413, 검증류 422, **표에 없으면 400**). 표는 형제 템플릿의 `app/api/errors.py` 와 같은 값이다. **새 코드를 만들면 `STATUS_BY_CODE` 에 등록한다** — 등록을 잊으면 조용히 400 이 된다.
- 오류 응답 형식은 요청에 따라 다르다: `/api/v1/*` 는 JSON `{"detail", "code"}`, htmx 요청은 `partials/alert.html` 을 `HX-Retarget: #alerts` 로, 그 밖은 `errors/error.html` 전체 페이지. 처리되지 않은 예외는 원인을 서버 로그에만 남기고 500 화면을 낸다.

### 기본 제공 테이블

| 테이블 | 리비전 | 용도 |
|--------|--------|------|
| `app_meta` | `0001_initial` | 연결 확인용 샘플(`/api/v1/health/db`) |
| `users` | `0002_users` | 자체 계정 — `username`(unique)·`hashed_password`(bcrypt)·`role`(`user`/`admin`)·`is_active` |
| `auth_sessions`, `login_throttles` | `0003_auth_sessions` | 로그인 세션(토큰 해시만 저장), 계정별 로그인 실패 카운터 (§9) |
| `notices` | `0004_notices_banners` | 공지 — `body_html`(저장 시 정화), `is_pinned`, `is_published`, `published_at`(처음 게시 때 1회), `view_count`, `author_id`(FK users, `SET NULL`) |
| `notice_attachments` | 〃 | 공지 첨부 — `notice_id`(FK, `CASCADE`), `storage_key`(private 키), `original_name`, `content_type`, `size_bytes`. 공지당 최대 10개 |
| `banners` | 〃 | 배너 — `image_key`(public/banners 키)·`image_width/height`(서버가 잰 값), `link_url`(http(s) 또는 `/` 내부 경로만), `alt_text`, `starts_at`/`ends_at`(노출 기간, NULL=무제한), `sort_order`, `is_active` |

컬럼의 SSOT 는 `app/models/`·`alembic/versions/` 다. 테이블은 형제 템플릿과 같으므로 두 템플릿이 같은 DB 를 읽을 수 있다(`auth_sessions` 의 회전 컬럼은 이 템플릿이 쓰지 않는다 — §9).

### 파일 업로드 · 저장소 · 본문 HTML 정화

**저장소(`core/storage.py`)** — 업로드 파일은 `UPLOAD_DIR`(기본 `uploads/`, 상대 경로는 프로젝트 루트 기준) 아래에 **서버가 만든 키**로만 저장한다. 사용자 파일명은 디스크 경로에 쓰지 않는다.

| 키 | 내용 | 노출 |
|----|------|------|
| `public/editor/YYYY/MM/DD/<uuid>.<ext>` | 공지 본문 이미지 | `/uploads/public/...` (`app/web/files.py`, `Cache-Control: public, max-age=31536000, immutable`) |
| `public/banners/YYYY/MM/DD/<uuid>.<ext>` | 배너 이미지 | 〃 |
| `private/attachments/YYYY/MM/DD/<uuid>.<ext>` | 공지 첨부(원본 파일명은 DB) | ⛔ 정적 서빙 금지 — 다운로드 경로로만 |

- **이미지**: 매직 바이트 + Pillow 로 실제 이미지인지 확인(PNG·JPEG·WebP·GIF 만) → EXIF 방향 반영 → 긴 변 `MAX_LONG_EDGE` 초과 시 축소 → **메타데이터 없이 재인코딩**(GIF 는 애니메이션 보존을 위해 그대로). 상한 `MAX_IMAGE_UPLOAD_MB`.
- **첨부**: 확장자 허용 목록, `Content-Type` 은 클라이언트 값이 아니라 확장자 표로 정한다. 상한 `MAX_ATTACHMENT_UPLOAD_MB`. 다운로드는 `Content-Disposition: attachment; filename="<ASCII 대체>"; filename*=UTF-8''<RFC 5987>` + `Cache-Control: private, no-store`(`app/web/files.py` 의 `attachment_response`).
- **경로 탈출 방지**: 키는 정규식에 맞아야 해석하고 해석된 경로가 `UPLOAD_DIR` 안인지 다시 확인한다. 공개 서빙 루트가 `UPLOAD_DIR/public` 이고 `send_from_directory` 가 루트 밖 경로를 거부하므로 `../` 로 private 에 닿지 않는다.
- **URL**: 공개 파일 URL = `PUBLIC_FILES_BASE_URL` + `/uploads/` + key. 같은 오리진에서 서빙하면 비워 둔다(루트 상대 경로). 첨부 `download_url` 도 같은 접두사를 쓰며 경로 `/api/v1/notices/<id>/attachments/<aid>` 는 공통 `notice_service.download_url` 과 같아야 한다.
- **요청 크기**: `MAX_CONTENT_LENGTH`(가장 큰 업로드 상한 + 여유)를 넘는 본문은 Werkzeug 가 413 으로 끊고, 파일별 상한은 `read_upload` 가 상한+1 바이트까지만 읽어 판정한다. 파일이 아닌 폼 필드는 `MAX_FORM_MEMORY_SIZE` 가 상한이다(공지 본문 상한을 받도록 Werkzeug 기본값보다 크게 둔다). 운영에서는 앞단 프록시에도 본문 상한을 둔다.
- **삭제**: 공지·첨부·배너 행을 지우면 커밋 후 파일도 지운다(배너 이미지는 다른 배너가 같은 키를 참조하지 않을 때만). 본문 이미지는 본문 HTML 이 참조하므로 자동으로 지우지 않는다 — 고아 파일 정리는 별도 배치 몫.

**본문 HTML 정화(`core/sanitize.py`, nh3)** — 공지 본문은 **서비스 계층이 저장 직전에** `sanitize_html` 을 거친다(관리자 입력도 믿지 않는다). 보기 화면은 저장된(정화된) HTML 만 `|safe` 로 넣는다.

- 허용 태그·속성·URL 스킴은 `core/sanitize.py` 의 표가 SSOT 다(`script`·`style`·`on*`·`style=` 속성·`javascript:` 는 제거, `iframe` 은 YouTube embed 만 — `sandbox` 강제). 정화 후 글자·`img`·`iframe` 이 없으면 빈 본문으로 422.
- 정화 결과의 `style` 제거와 `iframe` 호스트는 CSP(§9)와 한 쌍이다 — 허용 목록을 넓히면 CSP 와 `tests/test_sanitize.py` 를 같은 변경에서 고친다.
- 본문 편집은 HTML `textarea` 다. 본문 이미지는 `POST /admin/editor/images` 로 올리면 붙여 넣을 `<img>` 코드를 돌려준다(`partials/editor_image.html`). 리치 텍스트 편집기를 들이면 정화 허용 목록과 CSP 를 함께 검토한다.

### 화면 경로 요약

| 경로 | 접근 | 설명 |
|------|------|------|
| `GET /` · `GET /notices?page&q` · `GET /notices/<id>` | 공개 | 홈(활성 배너·최근 공지), 공지 목록(고정 먼저 → 게시일 최신순, 검색은 htmx 예제) · 상세(`view_count` +1, 초안은 404) |
| `GET·POST /login` · `POST /logout` | 공개 | 로그인(성공 시 `next` 또는 역할별 홈) · 로그아웃 (§14) |
| `GET /admin/` | admin | 대시보드 — 사용자·활성 세션·잠긴 계정·공지(게시/초안)·활성 배너 집계, DB 상태·Alembic 리비전 |
| `/admin/users` · `POST /admin/users/<id>` · `POST /admin/users/<id>/sessions/revoke` | 〃 | 역할·활성 변경(htmx 행 저장 예제), 자기 강등·비활성 금지, 마지막 활성 관리자 보호(409), 세션 모두 종료 |
| `/admin/sessions` · `POST /admin/sessions/<id>/revoke` · `POST /admin/login-throttles/<username>/clear` | 〃 | 살아 있는 세션 목록·강제 종료, 로그인 잠금 해제 |
| `/admin/notices`(목록·`new`·`<id>`·`<id>/delete`) · `/admin/notices/<id>/attachments`(추가·다운로드·삭제) · `POST /admin/editor/images` | 〃 | 공지 작성·수정·삭제, 첨부, 본문 이미지 |
| `/admin/banners`(목록·`new`·`<id>`·`<id>/delete`) · `POST /admin/banners/<id>/move` | 〃 | 배너 작성·수정(이미지 업로드)·삭제, 순서 이동(htmx 예제) |
| `GET /api/v1/health` · `GET /api/v1/health/db` · `GET /api/v1/notices/<id>/attachments/<aid>` | 공개 | 헬스 체크 JSON(DB 장애 시 503), 게시된 공지의 첨부 다운로드 |
| `GET /uploads/public/<key>` | 공개 | 공개 업로드 파일 |

---

## 9. 인증 (DB 세션 쿠키 · SSO)

- `core/security.py` 에 비밀번호 정책·해시, 세션 토큰 생성·해시, `now()` 를 둔다. 세션 도메인 로직은 `services/session_service.py`, 로그인·스로틀은 `services/user_service.py`, HTTP 변환은 `app/web/auth.py`·`app/dependencies.py` 가 담당한다(§4 계층 분리 그대로). 서비스는 형제 템플릿과 같은 코드다.

### 세션 모델 (자체 계정 — skeleton 구현)

- **로그인 하나 = `auth_sessions` 행 하나.** 토큰은 JWT 가 아니라 불투명(opaque) 토큰 `"<session_id>.<urlsafe 무작위>"` 다. DB 에는 **SHA-256 해시만** 저장한다 — DB 가 유출되어도 평문 토큰을 복원할 수 없고, 검증은 해시 재계산 + 상수시간 비교(`hmac.compare_digest`)다.
- **인증 쿠키**: 이름 `<snake>_session`, `Path=/`, `HttpOnly`, `SameSite=Lax`, `Secure=COOKIE_SECURE`, `Max-Age` = `REFRESH_TOKEN_EXPIRE_DAYS`(기본 14일). 세션의 절대 수명(`expires_at` = 로그인 시점 + 같은 일수)은 연장되지 않는다.
- **요청마다 확인**: `before_request` 훅이 쿠키 토큰으로 세션 행(존재·미폐기·미만료·해시 일치)과 사용자(활성)를 DB 에서 다시 읽는다 — 로그아웃·관리자 강제 종료·비활성화·강등이 **다음 요청부터 바로** 반영된다. 역할도 쿠키가 아니라 DB 에서 읽는다(강등 즉시 403).
- **회전 없음**: 형제 템플릿의 refresh 회전·재사용 감지는 짧은 access JWT 를 갱신하기 위한 장치다. 이 템플릿은 요청마다 DB 세션을 직접 확인하므로 토큰을 회전하지 않는다(`auth_sessions` 의 `prev_token_hash`·`rotated_at` 은 비어 있다).
- **Flask `session`**: 서명 쿠키 `<snake>_flash` 는 flash 메시지와 CSRF 토큰만 담는다. ⛔ 사용자 id·역할을 넣지 않는다 — 서명 쿠키는 서버에서 폐기할 수 없다.

### 로그인 · 로그아웃 (`app/web/auth.py`)

| 경로 | 요청 | 응답 |
|------|------|------|
| `GET /login?next=` | — | 로그인 화면. 이미 로그인했으면 `next` 또는 역할별 홈으로 redirect |
| `POST /login` | 폼 `username`, `password`, `next`, `csrf_token` | 성공: 세션 생성 → `session.clear()`(로그인 전 flash·CSRF 토큰 폐기) → 인증 쿠키 → redirect. 검증 오류 422, 자격증명 오류 401, 잠금 429 + `Retry-After` — 모두 로그인 화면을 다시 그린다 |
| `POST /logout` | 폼 `csrf_token` | 세션 폐기(토큰 해시 일치 시) + 쿠키 삭제 → 홈. ⛔ GET 으로는 로그아웃하지 않는다(링크·prefetch 로 끊기지 않게) |

- `next` 는 `safe_next_path` 로 같은 사이트의 `/` 경로만 받는다(`//`·스킴·제어 문자 거부 — 열린 리다이렉트 차단).

### 로그인 보호 (계정 존재 비노출 · 시도 제한)

- **실패 메시지 통일**: 로그인 실패는 원인(자격증명 불일치/비활성 계정)과 무관하게 같은 문구·같은 401 이다. 미존재 계정에도 **더미 bcrypt 해시로 1회 검증**해 응답 시간으로도 존재 여부가 드러나지 않게 한다.
- **로그인 스로틀**: 계정(username)별 DB 카운터(`login_throttles`). 연속 실패가 `LOGIN_MAX_FAILURES`(기본 5) 이상이면 `LOGIN_LOCKOUT_MINUTES`(기본 15분) 동안 **429** + `Retry-After`(남은 초, 올림·최소 1)다. **미존재 계정도 같은 429 를 받는다.** 성공 시 스로틀 행은 삭제된다. 카운트 증가는 SQL 식 하나로 처리해 동시 요청에서도 사라지지 않는다. 잠금 단위가 계정이므로 제3자가 특정 계정을 반복 잠글 수 있다 — 운영에서는 앞단 프록시(또는 WAF)에 IP 단위 요청 제한을 함께 둔다(§21).
- **감사 로그**: 보안 이벤트(로그인 성공/실패/잠금, 로그아웃, 관리자의 세션 폐기·잠금 해제·권한 변경, CLI 비밀번호 재설정)는 전용 로거 **`app.audit`** 로 남긴다. `app/core/logging.py` 가 `app` 로거에 표준 출력 핸들러를 붙이고 수준은 `LOG_LEVEL`(기본 `INFO`)이다.

### 비밀번호 정책

- **새로 저장하는 비밀번호**는 `core/security.py` 의 `validate_new_password()` 한 곳에서 검증한다 — 최소 `PASSWORD_MIN_LENGTH`(8자) + `len(password.encode("utf-8")) <= 72`(bcrypt 상한). 한글은 UTF-8 에서 글자당 3 bytes 이므로 문자 수 제한과 같지 않다. 조합 규칙은 두지 않는다(NIST SP 800-63B 방식).
- 위반하면 `ValueError` 다. 현재 새 비밀번호를 받는 경로는 서비스(`user_service.create_user()`)·CLI·기본 관리자 시드뿐이고 화면은 없다. 비밀번호 변경·회원가입 화면을 추가하면 **같은 규칙을 폼 스키마의 `@field_validator` 로도 걸어 422 로 다시 그린다** — `ValueError` 가 500 으로 새지 않게 한다.
- 하한(8자)은 로그인 검증에는 적용하지 않는다. 상한(72 bytes)은 로그인 폼 스키마(`LoginRequest`)에서도 422 로 거부하고, `hash_password()` 는 초과 시 `ValueError`, `verify_password()` 는 bcrypt 의 `ValueError` 를 `False` 로 바꿔 401 이 되게 한다(bcrypt 5 는 72 bytes 초과에 예외를 던진다).

### SECRET_KEY · 초기 관리자 · `APP_ENV`

- `APP_ENV` 는 `development`·`test`·`production` 만 허용한다 — 그 밖의 값은 설정 검증에서 기동을 거부한다.
- `SECRET_KEY` 는 Flask 서명 쿠키(flash·CSRF 토큰)의 키다. 공개된 기본값(`change-me-in-production-use-32-bytes`)이거나 32 bytes 미만이면 개발에서는 **경고**, `APP_ENV=production` 에서는 **기동 실패**다(`app/main.py` 의 `check_startup_settings`). 스캐폴드가 `.env` 에 무작위로 생성해 넣는다.
- `APP_ENV=production` 이면 `BCRYPT_ROUNDS` 12 미만, `COOKIE_SECURE=false`, `SEED_DEFAULT_ADMIN=true` 도 기동을 거부한다.
- **운영 관리자 계정**은 명령줄 도구로 만든다 — `python -m app.cli create-admin --username <이름>`, 비밀번호 재설정은 `python -m app.cli set-password --username <이름>`(해당 사용자의 세션 전체 폐기·잠금 해제). 비밀번호는 인자로 받지 않고 대화형 입력 또는 `--password-stdin` 으로만 받는다.
- 기본 관리자(`admin`)는 `SEED_DEFAULT_ADMIN=true` + `DEFAULT_ADMIN_PASSWORD` 로 기동 시 시드한다. **코드 기본값은 꺼짐**이고, 스캐폴드가 개발용 `.env` 에서만 켜고 무작위 비밀번호를 넣는다. 비밀번호가 비어 있으면 시드를 건너뛰고 에러 로그를 남긴다. ⛔ 비밀번호 기본값·하드코딩 기본 계정은 금지.

### SSO (도입 시 선택적 확장)

- **OIDC SSO**: 앱이 authorize→callback→userinfo 처리 후 같은 `auth_sessions` 세션과 인증 쿠키를 발급한다. IdP 의 ID 토큰 검증은 **PyJWT 의 `PyJWKClient`** 또는 **Authlib** 를 쓴다. 최초 로그인 시 서비스 함수로 사용자 upsert. 콜백 경로의 `state`·`nonce` 검증은 CSRF 보호와 별도로 반드시 한다.

### 응답 보안 헤더 · CSP · 캐시 (`app/web/security_headers.py`)

- 모든 응답에 `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Cross-Origin-Opener-Policy: same-origin` 을 붙인다.
- **CSP**: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; frame-src https://www.youtube-nocookie.com https://www.youtube.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`. 공지 본문의 외부 이미지 허용(`img-src https:`)과 YouTube embed(`frame-src`)는 정화 허용 목록(§8)과 한 쌍이다. 이 CSP 가 htmx 사용 방식(§13)을 제한한다.
- HSTS(`max-age=31536000`)는 `COOKIE_SECURE=true` 이거나 `APP_ENV=production` 일 때만 보낸다.
- HTML 응답은 `Cache-Control: private, no-store` 가 기본이다(로그인 상태에 따라 내용이 달라진다). `/admin*`·`/login`·`/logout` 은 항상 `private, no-store`. 공개 업로드 파일은 길게 캐시한다(§8).

---

## 10. 날짜·시간 (KST)  — MUST

- **기준**: 저장·비교·업무 일자는 **KST naive** 로 통일한다. 애플리케이션 안에 UTC↔KST 변환 레이어를 두지 않는다.
- **PostgreSQL**: 엔진 `connect_args`에 `options="-c timezone=Asia/Seoul"`.
- **앱 코드**: 현재 시각은 `app.core.security.now()` 로만 얻는다 — `datetime.now(KST).replace(tzinfo=None)`, `KST` 는 고정 오프셋 UTC+9(한국은 일광절약시간이 없다)라 OS 시각대·`TZ`·tzdata 와 무관하다. ⛔ naive `datetime.now()`·`date.today()`·`datetime.fromtimestamp(ts)`(시각대 인자 없이)·인자 없는 `astimezone()` 은 OS 시각대를 따르므로 쓰지 않는다.
- **로그**: `app/core/logging.py` 의 포매터가 로그 시각을 KST 로 찍는다(OS 시각대와 무관).
- **실행 환경 `TZ`**: Unix 에서는 `.env` 의 `TZ`(기본 `Asia/Seoul`)를 프로세스에 적용(`tzset()`)해 외부 라이브러리·하위 프로세스의 로컬 시각도 KST 로 맞춘다. Windows 는 C 런타임이 IANA 이름을 해석하지 못해 UTC 로 보므로 프로세스 환경에 넣지 않는다. **OS 시각대를 서울로 바꿀 필요는 없다** — 앱 시각·로그는 어느 OS 에서든 KST 다.
- **금지(신규 코드)**: `datetime.now(timezone.utc)` 같은 aware 시각을 저장·비교에 쓰는 것, DB 에 UTC 로 저장하는 것.
- **허용**: 외부 연동 값(UTC 를 주는 외부 API, OIDC `exp` 등)을 경계에서 KST naive 로 바꿔 받아들이거나, 사용자에게 다른 시각대로 **표시**하기 위해 `zoneinfo.ZoneInfo` 로 변환하는 것. 시각대가 붙은 입력은 경계에서 KST naive 로 바꾼다(예: `schemas/banner.py` 의 `astimezone(KST).replace(tzinfo=None)`).
- **화면**: 서버 값은 KST naive 다. 템플릿에서는 `strftime` 으로 그대로 표시하고, `<input type="datetime-local">` 값(`YYYY-MM-DDTHH:MM`)은 `forms.optional_datetime` 으로 KST naive 로 받는다.

---

## 11. 마이그레이션 (Alembic)  — MUST: DB는 항상 Alembic으로 관리

> **모든 DB 스키마는 예외 없이 Alembic 마이그레이션으로만 생성·변경한다.**
> 개발·스테이징·운영 어느 환경에서도 동일하다. 스키마의 단일 진실 공급원(SSOT)은 마이그레이션 히스토리다.

- `alembic/env.py`에서 `app.config.get_settings()`의 DB URL과 `Base.metadata`를 사용한다(URL 미설정 시 fail-fast).
- `import app.models`로 모든 모델을 로드한 뒤 `target_metadata = Base.metadata`. `compare_type=True`, PostgreSQL은 `NullPool`. offline/online 모두 지원.
- 초기 스키마(`0001`~`0004`, §8 기본 제공 테이블)는 이미 들어 있다. ⛔ `alembic init` 을 다시 하지 않는다.
- 명령은 프로젝트 루트에서 실행한다(`alembic.ini` 위치). 모델 변경 절차는 [`db-migration` 스킬](.claude/skills/db-migration/SKILL.md)을 따른다. 요약: `alembic revision --autogenerate` 로 초안 → 생성된 `versions/*.py` 직접 검토·수정 → `alembic upgrade head` → PostgreSQL 에서 `alembic check`.
- 모든 마이그레이션은 **`downgrade()`를 작성**하고, 가능하면 되돌릴 수 있게 한다. CI 가 `upgrade head` → `check` → `downgrade base` → `upgrade head` 왕복을 검사한다(§20).
- 마이그레이션 파일은 **반드시 커밋**한다. head 가 갈라지면 `alembic merge`로 정리.
- ⛔ `alembic.ini` 에는 ASCII 만 쓴다(Windows 로캘 인코딩으로 읽혀 한글 주석이 있으면 alembic 이 뜨지 않는다). `path_separator = os` 를 지우지 않는다.

### 금지 (MUST NOT)
- **런타임 `Base.metadata.create_all()`로 운영/개발 스키마를 만드는 행위** — 단, **테스트 임시 DB 에서만 예외 허용**(§12).
- `DATABASE_AUTO_DDL` 같은 **자동 DDL 플래그를 dev/prod에서 켜는 것**.
- DB 콘솔에서 직접 `ALTER TABLE` 등 **마이그레이션을 거치지 않은 수동 스키마 변경**.

---

## 12. 테스트 (pytest)

- `pytest.ini`: `pythonpath = .`, `testpaths = tests`. 실행은 `pytest -q`(CI 는 `-W error::DeprecationWarning` 을 붙인다).
- DB 는 테스트마다 **임시 SQLite 파일**(`tmp_path`)이고 `Base.metadata.create_all/drop_all` 한다. in-memory(StaticPool)는 연결 하나를 모든 세션이 공유해 트랜잭션 경계가 운영과 달라지므로 쓰지 않는다.
- 앱은 `create_app(session_factory=...)` 로 테스트 DB 에 붙인다. 요청은 운영과 같이 **요청마다 새 세션**을 열고 닫는다 — 테스트의 `db_session` 을 요청에 넘기면 커밋하지 않은 변경도 보여 `commit()` 누락을 잡지 못한다. 요청 뒤에는 `db_session` 캐시를 만료해 단언이 커밋된 값을 읽는다.
- bcrypt 비용은 `BCRYPT_ROUNDS=4` 로 낮춘다(운영 12).
- `conftest.py`는 앱 import 전에 테스트용 환경변수를 **대입**한다(`APP_ENV=test`, `SEED_DEFAULT_ADMIN=false`, `COOKIE_SECURE=false`, `BCRYPT_ROUNDS=4` 등) — 개발자의 `.env` 가 테스트 결과를 흔들지 않게 한다.
- **CSRF 는 테스트에서도 켜 둔다.** 폼 POST 는 `post_form(client, url, data, htmx=False)` 로 토큰을 실어 보낸다(`htmx=True` 면 `HX-Request` 헤더도 붙인다). 토큰 없는 POST 가 거부되는지도 테스트한다.
- `conftest.py`의 공통 픽스처:
  - `_clear_settings_cache` (autouse): `get_settings.cache_clear()`.
  - `upload_dir` (autouse): `UPLOAD_DIR` 을 테스트별 `tmp_path` 로 돌려 저장소에 파일을 남기지 않는다.
  - `db_session_factory` · `db_session`: 테스트 엔진에 바인딩된 세션 팩토리와 테스트별 세션.
  - `flask_app` · `client`: 테스트 DB 에 붙인 앱과 `test_client`.
  - `admin_user` · `normal_user`: 관리자·일반 사용자 행. `admin_client` · `user_client`: 그 계정으로 **실제 로그인**한 클라이언트.
- 테스트 배치: 공통 계층은 형제 템플릿과 같은 `test_cli.py`·`test_config.py`·`test_sanitize.py`·`test_storage.py`(+ `media_factory.py`)이고, Flask 계층은 `test_startup.py`(기동 설정 검사·시드·보안 헤더·HSTS), `test_web_auth.py`(로그인·로그아웃·잠금·CSRF·`next`·즉시 무효화), `test_passwords.py`(비밀번호 정책·bcrypt 72 bytes 경계·계정 존재 비노출 — 형제 템플릿의 같은 검증을 폼 POST 기준으로 옮긴 것), `test_web_public.py`, `test_web_admin.py` 다.
- 화면 테스트는 상태 코드와 `get_data(as_text=True)` 안의 핵심 문구로 확인한다. htmx 경로는 partial 만 왔는지(전체 레이아웃 없음), 오류면 `HX-Retarget: #alerts` 인지 확인한다. 브라우저 동작(htmx 교체·CSP 위반 없음)은 테스트로 잡히지 않으므로 개발 서버에서 확인한다.

```python
@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

---

## 13. 화면 구조 (Jinja · htmx)

> 형제 템플릿에서는 프론트엔드(React) 구조 절이다. 이 템플릿은 서버가 HTML 을 렌더링하므로 템플릿·htmx 규칙을 둔다. 작업 절차는 [`add-screen` 스킬](.claude/skills/add-screen/SKILL.md).

### 템플릿 배치

| 위치 | 용도 |
|---|---|
| `templates/base.html` | 공통 레이아웃 — `{% block title %}`·`{% block content %}`, 상단 내비(로그인 상태·관리자 메뉴·로그아웃 폼), `#alerts`(flash·오류 알림), `<body hx-headers>`(CSRF), `htmx-config` 메타 |
| `templates/admin/_layout.html` | 관리자 사이드 메뉴 — 관리자 화면은 이것을 extends 하고 `{% block admin %}` 을 채운다 |
| `templates/<영역>/<화면>.html` | 전체 페이지(`public/`·`auth/`·`admin/`·`errors/`) |
| `templates/partials/<이름>.html` | htmx 가 교체할 조각과 공용 조각(`alert`·`fields`·`pagination`). 전체 페이지는 같은 partial 을 `{% include %}` 한다 — 같은 마크업을 두 벌 두지 않는다 |

- 전역: `project_name`, `current_user`(비로그인이면 `None`), `csrf_field()`, `csrf_token()`. 폼 오류는 `partials/fields.html` 의 `field_error(errors, name)`, 폼 전체 오류는 `errors._form`.
- Jinja 자동 이스케이프를 끄지 않는다. `|safe` 는 서버가 정화한 공지 본문(§8)에만 쓴다.

### 요청·응답 흐름

- **조회**: GET → 전체 페이지. 목록 검색·페이지 이동은 같은 URL 의 GET 폼·링크다.
- **변경**: POST 폼(`{{ csrf_field() }}` 포함) → 성공하면 `flash(…, "success")` + redirect(PRG), 검증 실패면 입력값·오류와 함께 같은 템플릿을 **422** 로.
- ⛔ GET 으로 상태를 바꾸지 않는다(로그아웃 포함). ⛔ 상태를 바꾸는 JSON API 를 화면용으로 만들지 않는다 — 변경은 CSRF 로 보호된 폼 POST 로만 한다.

### htmx (선택적 보강)

- **htmx 없이 먼저 완성**한 뒤 같은 요소에 `hx-get`/`hx-post`·`hx-target`·`hx-swap`(필요하면 `hx-push-url`)을 덧붙인다. JS 가 꺼지거나 htmx 가 실패해도 일반 폼·링크로 동작해야 한다.
- 뷰는 `app/web/htmx.py` 헬퍼로만 분기한다. ⛔ 뷰에서 `HX-Request` 헤더를 직접 읽지 않는다.
  - `is_htmx()` — htmx 요청인가(히스토리 복원 요청 `HX-History-Restore-Request` 는 전체 페이지가 필요하므로 아니다).
  - `render_page_or_partial(page, partial, status, **context)` — 같은 context 로 htmx 면 partial, 아니면 전체 페이지. `Vary: HX-Request` 를 붙여 캐시가 섞이지 않게 한다.
  - `htmx_redirect(url)` — htmx 요청에 전체 페이지 이동을 지시한다(204 + `HX-Redirect`). 302 는 partial 자리에 끼워지므로 쓰지 않는다.
- **오류**: `ServiceError`·CSRF·HTTP 오류는 htmx 요청이면 `app/web/errors.py` 가 alert partial 을 `HX-Retarget: #alerts` 로 돌려준다. 폼 검증 오류를 그 자리에 다시 그리려면 partial 을 422 로 렌더링한다.
- **설정**(`base.html` 의 `<meta name="htmx-config">`): `allowEval:false`(CSP — `hx-on`·`hx-vars`·`js:` 접두사 불가), `includeIndicatorStyles:false`(인라인 스타일 금지 — indicator 스타일은 `input.css` 의 `.htmx-request`), `historyCacheSize:0`(로그인 상태가 담긴 화면을 브라우저 저장소에 남기지 않는다), `responseHandling` 으로 4xx·5xx 도 swap(오류 알림 표시).
- **CSRF**: `<body hx-headers='{"X-CSRFToken": "…"}'>` 가 모든 htmx 요청에 토큰을 싣는다. 폼 안의 `csrf_field()` 도 그대로 둔다(htmx 없이 제출될 때 필요).
- **인증 만료**: 로그인이 필요한 경로에 htmx 요청이 오면 401 + `HX-Redirect` 로 로그인 화면 전체로 이동한다(§14).
- **예제**(skeleton): 공지 검색(`public/notices.html` + `partials/notice_list.html` — 입력 지연 300ms, URL 갱신), 사용자 행 저장(`partials/admin_user_row.html`), 배너 순서 이동(`partials/admin_banner_rows.html`).
- ⛔ htmx 로 클라이언트 상태(모달 스택·드래그·실시간 동기화)를 흉내 내지 않는다(§2).

### 스크립트

- 스크립트는 `app/static/js/` 의 파일만 쓰고 `base.html` 에서 `defer` 로 불러온다. 현재 `htmx.min.js`(벤더링)와 `app.js`(`data-confirm="<문구>"` 폼의 제출 전 확인) 뿐이다.
- ⛔ 인라인 `<script>`·`on*=` 속성·`javascript:` URL·외부 CDN 스크립트(CSP §9). 외부 라이브러리가 필요하면 벤더링하고 버전·무결성을 `scripts/versions.env` 에 기록한다([`stack-versions` 스킬](.claude/skills/stack-versions/SKILL.md)).
- 되돌릴 수 없는 폼(삭제·강제 종료·비활성화)에는 `data-confirm` 을 붙인다.

---

## 14. 화면 인증 흐름 (쿠키 · CSRF · 권한)

> 형제 템플릿에서는 SPA 의 토큰 흐름 절이다. 이 템플릿은 브라우저가 쿠키만 들고 다니며 JS 는 인증에 관여하지 않는다.

```
브라우저 ──GET /admin/notices──▶ before_request: 쿠키 → auth_sessions(해시·만료·폐기) → users(활성·역할)
          ◀─ 비로그인: 302 /login?next=/admin/notices   (htmx 요청: 401 + HX-Redirect)
          ◀─ 일반 사용자: 403 화면
브라우저 ──POST /login (username, password, next, csrf_token)──▶ user_service.authenticate
          ◀─ 302 next + Set-Cookie <snake>_session=<sid>.<secret>; HttpOnly; SameSite=Lax; Path=/
브라우저 ──POST /logout (csrf_token)──▶ 세션 폐기 ◀─ 302 / + 쿠키 삭제
```

- **권한 경계는 서버**다. 템플릿이 메뉴를 숨기는 것(`current_user.role`)은 화면 노출용이고, 실제 차단은 `login_required`·`admin_required`·관리자 블루프린트의 `before_request` 다.
- **CSRF**: `CSRFProtect` 가 모든 POST 를 검사한다(폼 필드 `csrf_token` 또는 헤더 `X-CSRFToken`). 토큰은 Flask 서명 쿠키(`<snake>_flash`)에 묶이고 시간 만료가 없다(`WTF_CSRF_TIME_LIMIT=None` — 긴 글 작성 중 저장 실패 방지). 로그인 성공 시 `session.clear()` 로 새 토큰을 받는다. HTTPS 에서는 `WTF_CSRF_SSL_STRICT` 로 `Referer` 가 같은 호스트여야 한다. 실패는 400 + 안내 문구(htmx 면 `#alerts`).
- `SameSite=Lax` 쿠키는 교차 사이트 POST 에 실리지 않는다 — CSRF 토큰과 함께 이중 방어다. ⛔ 인증 쿠키를 `SameSite=None` 으로 바꾸지 않는다.
- **배포**: 앱·정적 파일·업로드를 **같은 오리진**에서 서빙한다(리버스 프록시가 전부 Flask 로 넘기거나 `/static`·`/uploads/public` 만 프록시가 직접 서빙). HTTPS 종단 뒤에 두고 `COOKIE_SECURE=true`. 프록시 뒤라면 `Host`·`X-Forwarded-Proto` 가 올바르게 전달되는지 확인한다(CSRF `Referer` 검사·redirect URL 이 이것에 의존한다).

---

## 15. 스타일 — Tailwind CSS v4 (standalone CLI)

- **CSS-first**: `app/static/css/input.css` 에 `@import "tailwindcss"`, 클래스 탐색 위치 `@source "../../templates"`·`@source "../js"`, 색 토큰 `@theme`(`surface`·`panel`·`ink`·`muted`·`line`·`accent`·`danger`, 다크 모드는 `prefers-color-scheme`). 별도 `tailwind.config.js` 를 두지 않는다.
- 공용 컴포넌트 클래스(`input`·`btn`·`btn-primary`·`badge`·`table`·`rich-text` 등)는 `input.css` 의 `@layer components` 에 둔다.
- **빌드**: `scripts/tailwind.ps1`(Windows) · `./scripts/tailwind.sh`(macOS/Linux) — `.tools/` 에 `TAILWIND_VERSION` 바이너리가 없을 때만 내려받고 **`scripts/tailwind-sha256sums.txt` 와 SHA-256 이 다르면 쓰지 않고 중단**한다. 개발 중에는 `-Watch` / `--watch`. ⛔ Node·npm 으로 빌드하지 않는다.
- 출력 `app/static/css/app.css` 는 빌드 결과라 커밋하지 않는다(`.gitignore`). 배포 산출물을 만들 때 다시 빌드한다.
- ⛔ 클래스 이름을 문자열 조합(`"text-" ~ color`)으로 만들지 않는다 — 빌드가 찾지 못한다. 조건부 클래스는 완성된 이름 전체를 쓴다.
- ⛔ `style="…"` 속성·`<style>` 블록(CSP §9).
- 한글 UI 기본 폰트는 시스템 폰트 스택을 쓴다. 웹 폰트를 들이면 파일을 `app/static/` 에 두고(CSP `font-src` 미지정 → `default-src 'self'`) 라이선스를 확인한다.

---

## 16. 네이밍 컨벤션 (요약)

| 대상 | 규칙 |
|------|------|
| Python 파일/함수/변수 | `snake_case` |
| Python 클래스 / Enum | `PascalCase` (Enum 멤버는 `UPPER_CASE`) |
| DB 테이블 | `snake_case` 복수형 |
| 서비스 파일 | `<domain>_service.py` |
| 뷰 모듈 | `app/web/<영역>.py` 또는 `app/web/admin/<domain>.py`, 블루프린트 이름 = 모듈 이름 |
| 템플릿 | `<영역>/<화면>.html`, `partials/<이름>.html`, 레이아웃 조각 `_<이름>.html` |
| URL | 화면은 리소스 복수형(`/admin/notices`, `/admin/notices/<id>`), 변경 동작은 POST 하위 경로(`/<id>/delete`, `/<id>/move`), JSON 은 `/api/v1/<resource>` |
| CSS 클래스 | Tailwind 유틸리티 + `input.css` 의 공용 컴포넌트 이름 |

---

## 17. 환경변수 표준

> 모든 설정은 **프로젝트 루트 `.env` 파일로 OS 독립적으로 주입**한다(강제 규칙은 §5 참조). 셸 환경변수에 의존하지 않는다. 키 목록의 원본은 `.env.example` 이고, 스캐폴드가 만드는 `.env` 의 키 집합은 이것과 같다.

| 키 | 용도 |
|----|------|
| `DATABASE_URL` | PostgreSQL 연결 — 단일 지원(개별 `DB_*` 키 미지원), 미설정 시 기동에서 fail-fast |
| `APP_ENV` | `development`·`test`·`production` 만 허용(그 밖은 기동 거부). `production` 이면 안전하지 않은 설정(기본·32 bytes 미만 `SECRET_KEY`, 관리자 시드, `COOKIE_SECURE=false`, `BCRYPT_ROUNDS` 12 미만)으로 기동을 거부한다 |
| `LOG_LEVEL` | `app.*` 로거 수준(감사 로그 `app.audit` 포함, 기본 `INFO`) |
| `SECRET_KEY` | Flask 서명 쿠키(flash·CSRF 토큰) 키 — 스캐폴드가 무작위 생성 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 로그인 세션 수명(일, 기본 14) — `auth_sessions` 만료와 인증 쿠키 `Max-Age`. 키 이름은 공통 설정을 따른다(§9) |
| `LOGIN_MAX_FAILURES`, `LOGIN_LOCKOUT_MINUTES` | 로그인 시도 제한 — 계정별 연속 실패 임계치(기본 5)와 잠금 시간(분, 기본 15) (§9) |
| `BCRYPT_ROUNDS` | bcrypt 비용(기본 12, 운영 하한 12) — 테스트만 낮춘다(`.env.example` 에는 주석으로만 있다) |
| `COOKIE_SECURE` | 인증·flash 쿠키의 `Secure` 속성과 HSTS·CSRF 엄격 검사. 로컬 `false`, 운영(HTTPS) `true` 필수(아니면 기동 거부) |
| `UPLOAD_DIR` | 업로드 저장 위치(기본 `uploads`, 상대 경로는 프로젝트 루트 기준). `public/` 만 `/uploads/public` 으로 서빙 (§8) |
| `PUBLIC_FILES_BASE_URL` | 공개 파일·첨부 다운로드 URL 접두사. 같은 오리진이면 비운다 |
| `MAX_IMAGE_UPLOAD_MB`, `MAX_ATTACHMENT_UPLOAD_MB` | 업로드 크기 상한(MB, 기본 5 / 20) — 초과 시 413. 요청 본문 상한(`MAX_CONTENT_LENGTH`)도 이 값에서 정해진다 |
| `TZ` | Unix 프로세스 시각대(기본 `Asia/Seoul`, 외부 라이브러리용). 앱 시각(`now()`)·로그는 이 값·OS 와 무관하게 KST 다. Windows 에서는 프로세스에 적용하지 않는다 (§10) |
| `SEED_DEFAULT_ADMIN`, `DEFAULT_ADMIN_PASSWORD` | 기동 시 기본 관리자(admin) 시드 여부·초기 비밀번호. **코드 기본값은 꺼짐** — 스캐폴드가 개발용 `.env` 에서만 무작위 비밀번호로 켠다(§9, §21) |
| `OAUTH_*` | SSO 도입 시 추가(authorize/token/userinfo URL, client id/secret, redirect uri) |

- 공통 설정의 FastAPI 전용 키(`ACCESS_TOKEN_EXPIRE_MINUTES`·`REFRESH_TOKEN_TRANSPORT`·`CORS_ORIGINS`·`FRONTEND_URL`·`BACKEND_PUBLIC_URL`)는 이 템플릿이 읽지 않으므로 `.env` 에 두지 않는다(§5).
- 키를 추가·삭제하면 `.env.example` 을 같은 변경에서 고친다. 실제 `.env` 는 커밋 금지.

---

## 18. 개발 원칙 (TDD · Tidy First)

- **TDD 사이클**: Red → Green → Refactor. `PLAN.md` 순서대로 **한 번에 실패하는 테스트 하나**. 결함도 화면·서비스 레벨 실패 테스트부터 작성한다.
- **최소 구현**으로 Green을 만들고, **Refactor는 Green 상태에서만**.
- **Tidy First**: **구조 변경(Structural)과 동작 변경(Behavioral)을 분리**한다. 한 커밋에 섞지 않는다.
- **중복 제거**를 철저히, 함수는 작게. 같은 마크업은 partial 로 한 벌만 둔다(§13).
- **서비스 레이어**: 뷰는 얇게, 도메인 로직은 `services/`.
- **의존성**: DB 세션·현재 사용자는 `app/dependencies.py` 에서 얻는다(§6).

---

## 19. 커밋 규칙

- **형식**: `[Category] <type>: <요약>` — Category 는 `[Structural]`(구조 변경, 동작 불변) 또는 `[Behavioral]`(기능·버그·로직 변경), type 은 `feat` `fix` `refactor` `docs` `style` `test` `chore`.
- 한 커밋에는 Structural·Behavioral 중 **하나만** 담는다(§18 Tidy First).
- 모든 테스트 통과 + 린트 경고 0일 때만 커밋한다.
- 요약 작성법·예시는 [`pr-workflow` 스킬](.claude/skills/pr-workflow/SKILL.md)에 있다.

---

## 20. 변경 반영 (GitHub)

원칙:
- 커밋·push 전에 로컬에서 `ruff check`·`pytest` 를 통과시킨다. 템플릿·CSS·htmx 를 바꿨으면 CSS 를 빌드하고 브라우저에서 화면과 콘솔(CSP 위반 없음)을 확인한다. 실패했거나 확인하지 않은 변경은 push 하지 않는다.
- CI(`.github/workflows/ci.yml`)는 push·PR 마다 Ubuntu·Windows 테스트, CSS 빌드(SHA-256 검증 포함), PostgreSQL 마이그레이션 왕복, PowerShell 5.1 구문 검사, `pip-audit`(경고성)를 돈다. CI 가 실패하면 되돌리거나 바로 고치는 커밋을 올린다.
- AI 에이전트는 **사용자가 요청할 때만** 커밋·push 한다.

기본 흐름(단독 개발은 `main` 직접 커밋, 브랜치·PR 은 선택), push 전 검증 명령, 브랜치·PR 을 쓰는 기준, 협업자가 생겼을 때의 전환은 **[`pr-workflow` 스킬](.claude/skills/pr-workflow/SKILL.md) 한 곳**에 둔다. PR 본문 양식은 `.github/pull_request_template.md` 다.

---

## 21. 생성 직후 확인과 배포 전 체크리스트

저장소 구조, 앱 골격, Alembic 초기 마이그레이션(`0001`~`0004`), 인증 흐름, 화면, 테스트, CI 는 **스캐폴드가 이미 만들어 두었다.** ⛔ `alembic init`·골격 재생성을 하지 않는다. 아래 첫 목록은 할 일이 아니라 **동작 확인**이다.

### 생성 직후 확인

- [ ] `AGENTS.md` 「프로젝트 개요」의 `<…>` 자리표시를 채운다 — 비어 있으면 첫 작업 전에 사용자에게 묻는다
- [ ] CSS 를 빌드하고(`scripts/tailwind.*`) 개발 서버가 뜬다(`flask --app app.main run --debug`) — `GET /api/v1/health` 200, `GET /api/v1/health/db` 가 `{"db": "ok", …}` 를 돌려준다(DB 에 접근할 수 없으면 503)
- [ ] 기본 관리자(`admin`, 비밀번호는 `.env` 의 `DEFAULT_ADMIN_PASSWORD`)로 로그인되고 관리자 대시보드에 「DB 정상」과 리비전이 보인다
- [ ] 브라우저 개발자 도구 콘솔에 CSP 위반이 없다(공지 검색·사용자 행 저장·배너 순서 이동)
- [ ] 로컬 검증이 통과한다 — `ruff check .`·`pytest -q` ([`pr-workflow` 스킬](.claude/skills/pr-workflow/SKILL.md))
- [ ] 첫 push 후 CI 가 통과한다
- [ ] 첫 기능을 `PLAN.md` 에 적고 실패 테스트 하나부터 시작한다 (§18)

### 배포 전 체크리스트 (스타터 기본값 제거 — MUST)

skeleton 은 개발 편의를 위해 기본 관리자 계정(`admin`)을 자동 시드한다(비밀번호는 스캐폴드가 무작위로 생성해 `.env` 의 `DEFAULT_ADMIN_PASSWORD` 에 넣는다). **운영 배포 전 반드시 제거·변경한다.**

- [ ] `SECRET_KEY` 를 무작위 값으로 교체 — 기본값이면 개발에서는 경고, `APP_ENV=production` 에서는 **기동 실패**다
- [ ] `APP_ENV=production` 설정 — 기본·짧은 `SECRET_KEY`, 관리자 시드, `COOKIE_SECURE=false`, 낮은 `BCRYPT_ROUNDS` 중 하나라도 남아 있으면 기동이 실패한다 (§9, §17)
- [ ] 기본 관리자 시드 정리 — 운영 `.env` 에서 `SEED_DEFAULT_ADMIN=false`. 운영 관리자는 `python -m app.cli create-admin --username <이름>` 으로 만들고, 개발 중 쓴 계정 비밀번호는 `python -m app.cli set-password` 로 바꾼다 (§9)
- [ ] 개발 서버(`flask run`) 대신 WSGI 서버로 띄운다 — `waitress-serve --call app.main:create_app` 또는 `gunicorn "app.main:create_app()"` (§4)
- [ ] HTTPS 종단 뒤에 배치하고 `COOKIE_SECURE=true` — 인증 쿠키가 평문 HTTP 로 나가지 않게 한다. 프록시가 `Host`·`X-Forwarded-Proto` 를 전달하는지 확인한다 (§9, §14)
- [ ] 앞단 프록시(또는 WAF)에 로그인 경로의 IP 단위 요청 제한과 업로드 본문 상한을 둔다 — 앱의 로그인 잠금은 계정 단위다 (§8, §9)
- [ ] CSS 를 빌드한 `app.css` 를 배포 산출물에 포함한다 (§15)
- [ ] 로그 수집 대상에 `app.audit` 를 포함한다 (`LOG_LEVEL=INFO` 이상, §9)
- [ ] 운영 DB 의 KST 확인 — 연결 시각대(`SHOW timezone` = `Asia/Seoul`)와 DB 기본값(`func.now()`)이 KST 인지 본다. 앱 시각·로그는 OS 시각대와 무관하게 KST 이므로 서버 OS 시각대는 바꾸지 않아도 된다 (§7, §10)
- [ ] 운영 DB 에 `alembic upgrade head` 를 적용하는 시점과 롤백 계획을 정한다 (§11)
- [ ] `UPLOAD_DIR` 을 영속 저장소에 둔다 (§8)

---

## 22. 프로젝트 고유 결정(예외)

> 이 가이드에서 벗어난 결정은 **여기 한 곳에만** 기록한다(`AGENTS.md` 는 이 절을 링크한다). 사용자와 합의한 뒤 적고, ⛔ 표시 MUST 는 예외로 만들 수 없다.

| 날짜 | 벗어난 규칙(§) | 사유 | 재검토 조건 |
|---|---|---|---|
| — | 없음 | — | — |
