---
name: add-domain
description: __PROJECT_NAME__ 에 새 도메인/리소스(예: orders, events)를 추가할 때 사용. 실패 테스트부터 시작해 모델 → 마이그레이션 → 스키마 → 서비스 → 얇은 뷰·템플릿의 계층별 작성 위치를 ARCHITECTURE.md §4·§8 에 맞춰 TDD 로 안내한다.
---

# 도메인 추가

새 도메인 `<domain>`(테이블은 `snake_case` **복수형**)을 추가할 때 아래 순서를 따른다.
상세 근거: `ARCHITECTURE.md` §4(구조)·§8(모델/스키마/서비스). DB 변경은 [db-migration], 화면 작성은 [add-screen] 스킬 참조.

## TDD 우선
먼저 `PLAN.md` 에 작업 순서를 적고, **실패하는 화면(뷰) 레벨 테스트 하나**부터 작성한다(Red → Green → Refactor).
구조 변경(파일 이동/생성)과 동작 변경(로직)을 한 커밋에 섞지 않는다.

## 계층별 작성 위치 (계층 분리 MUST)

> 아래 번호는 계층의 의존 방향이지 작성 순서가 아니다. 작성은 TDD 다 — 6번 형식의 실패 테스트를 먼저 쓰고, 그 테스트를 통과시키는 데 필요한 계층만 1번부터 채운다.

1. **모델** `app/models/<domain>.py` — SQLAlchemy 2.x `Mapped`/`mapped_column`
   ```python
   from datetime import datetime

   from sqlalchemy import DateTime, String, func
   from sqlalchemy.orm import Mapped, mapped_column

   from app.core.security import now      # KST naive
   from app.db.base import Base


   class Order(Base):
       __tablename__ = "orders"           # snake_case 복수형
       id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
       status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
       created_at: Mapped[datetime] = mapped_column(DateTime, default=now, server_default=func.now())
       updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, server_default=func.now())
   ```
   - `app/models/__init__.py` 에서 **반드시 re-export**(메타데이터/Alembic 등록).
   - **기본값이 있는 NOT NULL 컬럼은 `default`(ORM)와 `server_default`(DB)를 함께 둔다** — ORM 을 거치지 않는 INSERT 에서도 NOT NULL 위반이 나지 않게 한다. 불리언은 `server_default=true()`/`false()`, 숫자는 `"0"`, 시각은 `func.now()`. 기준 예시는 `models/user.py`·`models/notice.py`(§8).
   - 시각 컬럼은 `default=now`(KST naive). 현재 시각은 `app.core.security.now()` 로만 얻는다 — ⛔ naive `datetime.now()`·`date.today()` 는 OS 시각대를 따른다. ⛔ aware 시각(`datetime.now(timezone.utc)` 등)을 저장하거나 naive 값과 비교하지 않는다(§10).

2. **마이그레이션** — 모델을 추가/변경했으면 Alembic 으로만 반영한다. → [db-migration] 스킬.
   ⛔ 런타임 `create_all`·수동 `ALTER` 금지(§11).

3. **스키마** `app/schemas/<domain>.py` — Pydantic 2.x
   - 생성·전체 수정이 같은 입력이면 `XxxWrite` 하나(예: `NoticeWrite`), 화면용 조회 결과는 `XxxListItem`/`XxxDetail` 로 둔다(§8).
   - 제약은 `Field(ge=, max_length=)`, 복합 규칙은 `@field_validator`·`@model_validator`. 오류 메시지는 화면에 그대로 나가므로 **한국어 문장**으로 쓴다(`ValueError("제목을 입력하세요.")`).
   - 새 비밀번호를 받는 스키마는 `core/security` 의 `validate_new_password()`(최소 8자 + UTF-8 72 bytes 상한)를 `@field_validator` 에서 호출한다. 한글은 UTF-8 에서 글자당 3 bytes 다(§9).

4. **서비스** `app/services/<domain>_service.py` — 함수형
   - `def create_order(db, *, actor_id, data): ...` 형태. 트랜잭션·규칙 검증·외부 연동을 여기서 처리한다. ⛔ Flask(`request`·`g`·`flash`)를 import 하지 않는다 — 서비스는 프레임워크와 무관해야 한다.
   - 실패는 `ServiceError(code, message)`(`app/services/exceptions.py`)로 던진다.
   - **새 오류 코드를 만들면 `app/web/errors.py` 의 `STATUS_BY_CODE` 에 상태를 등록한다** — 표에 없는 코드는 400 이 된다. 이미 있는 코드(`not_found` 404 등)로 표현되면 그것을 쓴다.
   - 조회는 N+1 을 막기 위해 `selectinload` 등으로 명시적으로 로딩한다.

5. **뷰** `app/web/<영역>.py` 또는 `app/web/admin/<domain>.py` — **얇게**
   - HTTP 입출력·폼 해석·템플릿 선택만 한다. ⛔ 비즈니스 로직을 두지 않는다.
   - 폼 값은 `app/web/forms.py` 의 `parse_form(XxxWrite, **values)` 로 검증한다 — `(모델, {필드: 메시지})` 를 돌려준다. 오류가 있으면 같은 폼을 **422** 로 다시 그린다. 체크박스는 `checkbox()`, 빈 문자열 → `None` 은 `optional_text()`·`optional_datetime()`.
   - DB 세션은 `get_db()`, 현재 사용자는 `current_user()`(`app/dependencies.py`). 로그인 필요 화면은 `@login_required` 를 붙인다. 관리자 화면은 `app/web/admin/` 에 두면 블루프린트 `before_request` 가 모두 막는다.
   - `ServiceError` 는 잡지 않고 올려 보낸다 — `app/web/errors.py` 가 상태 코드와 응답 형식(JSON·htmx alert·오류 페이지)을 정한다. **폼을 오류 메시지와 함께 다시 그려야 할 때만** 특정 코드를 잡아 422 로 렌더링한다(예: `admin/notices.py` 의 `empty_body`).
   - 성공한 POST 는 `flash()` + `redirect()`(PRG). htmx 요청이면 partial 을 돌려준다([add-screen]).
   - 새 모듈은 등록한다 — 공개·인증 영역은 `app/web/__init__.py` 의 `register_blueprints`, 관리자 영역은 `app/web/admin/__init__.py` 의 import 줄.
   - 화면용 JSON API 는 만들지 않는다 — 화면 데이터는 템플릿으로 내려 보낸다. 스크립트(fetch)가 꼭 JSON 을 받아야 하면 같은 폼 POST 경로에서 `app/web/accept.py` 의 `wants_json()` 으로 응답 형식을 고른다(§13, 예: `admin/notices.py` 의 편집기 이미지 업로드). `/api/v1` 에는 헬스 체크·첨부 다운로드만 있다 — 새 경로를 두려면 `ARCHITECTURE.md` §22 에 기록한다.

6. **테스트** `tests/test_<domain>.py` — pytest + Flask `test_client` + 임시 SQLite
   - `conftest.py` 픽스처를 쓴다: `client`·`db_session`(기본), `admin_client`·`user_client`(관리자·일반 사용자로 로그인한 클라이언트), `admin_user`·`normal_user`(사용자 행), `upload_dir`(자동 — 임시 업로드 폴더).
   - POST 는 `tests.conftest.post_form(client, url, data, htmx=False)` 로 보낸다 — CSRF 토큰을 실어 준다. 토큰 없이 보내면 400 이어야 한다.
   - 검증 항목: 상태 코드(302·422·404 등), `Location` 헤더, 화면 문구, DB 상태. htmx 경로는 `htmx=True` 로 partial 본문과 `HX-Retarget` 등 헤더를 확인한다.
   - 서비스 규칙은 서비스 함수를 직접 부르는 단위 테스트로도 고정한다.

## 마무리
- 모든 테스트 통과 + `ruff check .` 경고 0 일 때만 커밋. 커밋 흐름은 [pr-workflow] 스킬 참조.
