# __PROJECT_NAME__ 에이전트 지침 (AGENTS.md)

> 이 파일은 `flask-starter` 로 생성된 프로젝트의 저장소 로컬 지침이다.
> 전체 아키텍처 기준(SSOT)은 `ARCHITECTURE.md` 이며, 작업에 필요한 절만 읽는다.
> 작업 순서는 `PLAN.md`, PRD·유저 플로우 등 프로젝트 문서는 `docs/` 에 둔다.
> 이 파일은 모든 AI 코딩 에이전트의 공통 지침이다. Claude Code 는 `CLAUDE.md` 가 이 파일을 import 해 읽는다.
> 실행 환경에 전역 지침이 있으면 함께 적용하되, 이 저장소의 규칙은 이 파일과 저장소 안의 문서만으로 이해하고 실행할 수 있어야 한다.

## 프로젝트 개요 (작성)

> 아래 `<…>` 자리표시가 그대로 남아 있으면 첫 작업을 시작하기 전에 사용자에게 물어 채운다.

- **목적**: <한 줄 설명>
- **인증**: <자체 계정 DB 세션 — 기본 | SSO — 도입 시 확장 | 다른 인증 방식>
- **주요 도메인**: <예: 주문/계약, 이벤트/설문 등>

## 반드시 지킨다 (시작 전 확인 — 상세는 ARCHITECTURE.md ★MUST 요약)

- **스택 고정**: Flask 3 + Jinja 서버 렌더링 + SQLAlchemy 2 + Alembic / **PostgreSQL**. 화면 보강은 htmx(선택), 스타일은 Tailwind CSS v4 standalone CLI 다. ⛔ Node·npm 빌드 단계, SPA 프레임워크, Alpine.js, jQuery 등 DOM 유틸리티 라이브러리를 들이지 않는다(DOM 조작은 브라우저 표준 API 로 한다). 정확한 버전은 `scripts/versions.env`·`requirements.txt` 와 `stack-versions` 스킬을 확인한다.
- **DB는 항상 Alembic으로만 관리**: 런타임 `create_all`, 자동 DDL, 수동 `ALTER` 는 금지한다. 테스트의 임시 SQLite DB 만 예외다.
- **환경 파일**: 프로젝트 루트의 `.env` 하나를 쓴다. `.env.example` 을 복사하고 실제 `.env` 는 커밋하지 않는다. 셸 환경변수(`$env:`·`export`)에 기대는 설정을 만들지 않는다.
- **시각은 KST 단일 기준(OS 무관)**: 현재 시각은 `app.core.security.now()`(고정 오프셋 UTC+9 로 계산한 KST naive)로만 얻는다. ⛔ naive `datetime.now()`·`date.today()`·인자 없는 `astimezone()` 처럼 OS 시각대를 따르는 호출을 쓰지 않는다. PostgreSQL `timezone=Asia/Seoul` 정책을 유지한다. OS 시각대를 서울로 바꿀 필요는 없다(Unix 는 `.env` 의 `TZ` 를 외부 라이브러리용으로 적용하고, Windows 는 적용하지 않는다).
- **설정·의존성**: 설정은 `get_settings()`(`@lru_cache`), 요청별 DB 세션·현재 사용자·권한 데코레이터·인증 쿠키는 `app/dependencies.py` 한 파일에 둔다.
- **계층 분리**: 뷰(`app/web/`)는 HTTP 입출력·폼 해석·템플릿 선택만 한다. 도메인 로직은 `services/`, 검증은 `schemas/`(pydantic)에 둔다. 도메인 오류는 `ServiceError` 로 던지고 상태 코드는 `app/web/errors.py` 의 `STATUS_BY_CODE` 에서 정한다.
- **공통 계층은 형제 템플릿과 같다**: `app/config.py`·`app/cli.py`·`app/core/`·`app/db/`·`app/models/`·`app/schemas/`·`app/services/`·`alembic/` 은 FastAPI 형제 템플릿과 파일 단위로 같은 코드에서 시작하였다. 프레임워크(Flask) 의존 코드를 이쪽에 넣지 않는다.
- **인증**: 로그인마다 `auth_sessions` 행 하나를 만들고 불투명 토큰을 httpOnly·SameSite=Lax 쿠키로 보낸다. 요청마다 DB 에서 세션을 확인한다. ⛔ JWT·Flask-Login·Flask 기본 `session` 으로 인증 상태를 들고 다니지 않는다(Flask `session` 은 flash 메시지와 CSRF 토큰 전용). 흐름은 `ARCHITECTURE.md` §9.
- **CSRF**: 상태를 바꾸는 요청은 모두 POST 이고 Flask-WTF `CSRFProtect` 가 전역으로 검사한다. 폼에는 `{{ csrf_field() }}` 를 넣고, htmx 요청은 `<body>` 의 `hx-headers` 가 `X-CSRFToken` 을 보낸다. ⛔ 뷰에 `csrf.exempt` 를 붙이지 않는다.
- **htmx 는 선택적 보강**: 모든 화면은 htmx 없이 일반 폼·링크로 동작해야 한다. `HX-Request` 분기는 `app/web/htmx.py` 의 헬퍼로만 한다.
- **CSP**: `script-src 'self'`·`style-src 'self'` 다. ⛔ 인라인 `<script>`·`style=` 속성·`on*=` 이벤트 속성·외부 CDN 스크립트를 쓰지 않는다. 스크립트는 `app/static/js/`, 스타일은 Tailwind 클래스로 쓴다.

## 작업 방식

- 대화와 문서는 한국어를 기본으로 하고, 명령 예시는 현재 OS 에 맞게 작성한다(Windows 는 PowerShell).
- 새 작업은 `PLAN.md` 에 기록하고 실패하는 테스트 하나부터 시작한다(Red → Green → Refactor).
- 테스트가 통과하는 상태에서만 리팩터링한다.
- Structural 변경과 Behavioral 변경을 한 커밋이나 PR 에 섞지 않는다. 커밋 제목에는 `[Structural]` 또는 `[Behavioral]` 접두사를 붙이고 변경 의도를 간결하게 적는다.
- **커밋·push 는 사용자가 요청할 때만 한다.** 요청이 없으면 변경을 작업 트리에 두고 검증 결과와 함께 보고한다. 커밋 전 검증 명령과 흐름은 `pr-workflow` 스킬을 따른다.
- 실행하지 못한 검증은 통과한 것처럼 쓰지 않고, 무엇을 왜 못 했는지 밝힌다.
- 전역 지침과 충돌하거나 프로젝트 고유 예외가 필요하면 임의로 우회하지 말고 사용자에게 확인한 뒤 아래 「프로젝트 고유 결정」의 위치에 근거와 함께 기록한다.

## 작업별 스킬 (필요할 때 로드)

스킬 원문은 `.claude/skills/<이름>/SKILL.md` 에 있다. Claude Code 는 자동으로 로드하고, 다른 에이전트는 해당 작업 전에 파일을 직접 읽는다.

- **add-domain**: 도메인 추가(모델 → 마이그레이션 → 스키마 → 서비스 → 뷰·템플릿 → 테스트, §4·§8)
- **db-migration**: DB 스키마 변경 시 Alembic 워크플로와 금지사항(§11)
- **add-screen**: 화면 추가(Jinja 템플릿·htmx partial·Tailwind·CSRF·CSP, §13·§15)
- **pr-workflow**: 커밋·push 흐름, push 전 검증 명령, 브랜치·PR 기준(`[Structural]`/`[Behavioral]`)
- **stack-versions**: 고정 방식, 버전별 주의사항과 업그레이드 검증 절차

각 절차의 근거와 상세 규칙은 `ARCHITECTURE.md` 의 해당 절을 확인한다. `.claude/skills/` 는 저장소에 포함된 선택적 작업 가이드이며 개인 홈 디렉터리의 설정을 전제하지 않는다.

## 프로젝트 고유 결정

기본 아키텍처에서 벗어난 결정은 `ARCHITECTURE.md` §22 「프로젝트 고유 결정(예외)」 **한 곳에만** 기록한다. 이 파일에는 내용을 옮겨 적지 않는다.
