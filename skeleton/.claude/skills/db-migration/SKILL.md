---
name: db-migration
description: __PROJECT_NAME__ 의 DB 스키마를 바꿀 때(SQLAlchemy 모델 생성/변경, 테이블 추가/수정) 사용. Alembic revision/upgrade 워크플로와 금지사항(런타임 create_all·수동 ALTER 금지)을 ARCHITECTURE.md §11 기준으로 안내한다.
---

# DB 마이그레이션 (Alembic)

> **모든 DB 스키마는 예외 없이 Alembic 마이그레이션으로만 생성·변경한다.** (ARCHITECTURE.md §11)
> 스키마의 단일 진실 공급원(SSOT)은 마이그레이션 히스토리다. dev/스테이징/운영 동일.
> 초기 스키마(`alembic/versions/0001`~`0004`)는 이미 있다. ⛔ `alembic init` 을 다시 실행하지 않는다.

## 워크플로 (프로젝트 루트에서)

```bash
# macOS / Linux
./.venv/bin/python -m alembic revision --autogenerate -m "<변경 요약>"   # 초안 생성
# → alembic/versions/*.py 를 반드시 검토·수정 (autogenerate 는 초안일 뿐!)
./.venv/bin/python -m alembic upgrade head                               # 적용
./.venv/bin/python -m alembic check                                      # 모델과 DB 차이가 없는지 확인
```

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python -m alembic revision --autogenerate -m "<변경 요약>"
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m alembic check
```

- 대상 DB 는 `.env` 의 `DATABASE_URL` 이다. 검증은 SQLite 가 아니라 **실제 PostgreSQL** 에서 한다 — `alembic check` 가 "No new upgrade operations detected" 를 출력해야 한다.
- 검증용 PostgreSQL 이 없으면 Docker 로 임시 컨테이너를 띄운다: `docker run --rm -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:16` 후 `.env` 의 `DATABASE_URL` 을 `postgresql+psycopg2://postgres:postgres@localhost:55432/postgres` 로 바꿔 실행한다(끝나면 되돌린다).

## 체크리스트
- 모델을 추가했으면 `app/models/__init__.py` 에서 **re-export 되었는지 먼저 확인**(안 그러면 autogenerate 가 못 잡음).
- 생성된 `versions/*.py` 의 `upgrade()`/`downgrade()` 를 **직접 읽고 검토**한다. 타입 변경·인덱스·`server_default` 누락을 확인한다(기본값이 있는 NOT NULL 컬럼 규칙은 §8).
- 기존 행이 있는 테이블에 NOT NULL 컬럼을 추가할 때는 `server_default` 를 주거나, nullable 로 추가 → 데이터 채움 → NOT NULL 전환의 단계로 나눈다.
- 모든 마이그레이션은 **`downgrade()` 를 작성**하고 가능하면 되돌릴 수 있게 한다. `alembic downgrade -1` → `alembic upgrade head` 왕복으로 확인한다.
- 마이그레이션 파일은 **반드시 커밋**한다(모델 변경과 같은 커밋).
- 머지 시 head 가 갈라지면 `alembic merge` 로 정리한다.
- `alembic/env.py` 는 `get_settings()` 의 DB URL + `Base.metadata`(`import app.models` 후)를 쓰고, `compare_type=True`·`compare_server_default=True` 로 타입·서버 기본값 변경도 감지한다.
- ⛔ `alembic.ini` 는 ASCII 로 유지하고 `path_separator = os` 를 지우지 않는다([stack-versions] §3).

## ⛔ 금지 (MUST NOT)
- 런타임 `Base.metadata.create_all()` 로 dev/운영 스키마 생성 — **테스트(임시 SQLite)에서만 예외**(§12). `app/main.py` 의 `create_app()` 에서도 호출하지 않는다.
- 자동 DDL 플래그를 dev/prod 에서 켜기.
- DB 콘솔에서 마이그레이션을 거치지 않은 수동 `ALTER TABLE`.

## 시각(KST) 주의
- PostgreSQL 연결은 `connect_args` 에 `options="-c timezone=Asia/Seoul"` (엔진 팩토리에 이미 적용, §7·§10). 그래서 `server_default=func.now()` 도 KST 다.
- 시각 컬럼은 `DateTime`(timezone 없음) + `default=now`(naive KST). ⛔ `DateTime(timezone=True)` 나 UTC 저장을 새로 들이지 않는다(§10).

## 커밋
- DB 변경 커밋에는 마이그레이션 파일을 함께 담는다. 커밋 흐름은 [pr-workflow] 스킬 참조.
