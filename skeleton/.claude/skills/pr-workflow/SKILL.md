---
name: pr-workflow
description: __PROJECT_NAME__ 에서 변경을 커밋·push 할 때 사용. 단독 개발 기본 흐름(main 직접 커밋), push 전 로컬 검증 명령, 커밋 메시지 형식([Structural]/[Behavioral]), Structural·Behavioral 분리, 브랜치·PR 을 쓰는 기준과 협업 전환을 안내한다. 커밋 절차의 원본은 이 스킬이다(ARCHITECTURE.md §19·§20 은 원칙만 둔다).
---

# 커밋 · push (브랜치·PR 은 선택)

> 이 스킬이 커밋·push 절차의 원본이다. `ARCHITECTURE.md` §19·§20 에는 원칙만 있고, 이 프로젝트의 고유 결정이 있으면 §22 가 우선한다.
> 단독 개발의 기본 흐름은 **`main` 에서 작업 → 로컬 검증 → 커밋 → push** 다. 협업자가 생기면 맨 아래 「협업자가 생기면」으로 전환한다.

## 에이전트 규칙
- AI 코딩 에이전트는 **사용자가 요청할 때만** 커밋·push 한다. 요청이 없으면 변경을 작업 트리에 둔 채 검증 결과와 함께 보고한다.
- 검증을 실행하지 못했으면 통과한 것처럼 쓰지 않고, 무엇을 왜 못 했는지 보고한다.

## push 전 로컬 검증

단독 흐름에는 PR 리뷰 단계가 없으므로 **검증을 건너뛰면 깨진 코드가 곧바로 `main` 에 남는다.**

```bash
# macOS / Linux — 프로젝트 루트에서. 하나라도 실패하면 && 가 거기서 멈춘다
./.venv/bin/python -m pip check && ./.venv/bin/python -m ruff check . && ./.venv/bin/python -m pytest -q
```

```powershell
# Windows (PowerShell) — 프로젝트 루트에서. ';' 는 실패해도 다음 명령을 실행하므로 종료 코드를 확인해 멈춘다
.\.venv\Scripts\python -m pip check;  if ($LASTEXITCODE) { throw "pip check 실패" }
.\.venv\Scripts\python -m ruff check .; if ($LASTEXITCODE) { throw "ruff 실패" }
.\.venv\Scripts\python -m pytest -q;    if ($LASTEXITCODE) { throw "pytest 실패" }
```

- CI 와 같은 검사다 — `pytest.ini` 의 `filterwarnings` 가 `DeprecationWarning` 을 실패로 바꾸므로 `pytest -q` 가 CI 의 `-W error::DeprecationWarning` 과 같은 기준이다.
- 실패했거나 확인하지 않았으면 **push 하지 않는다.**
- 템플릿·CSS 를 바꿨으면 `scripts/tailwind.*` 로 빌드해 브라우저에서 화면을 확인한다. 개발자 도구 콘솔에 CSP 위반이 없어야 한다.
- 문서만 고쳤으면 생략 가능하다.
- DB 스키마를 바꿨으면 PostgreSQL 에서 `alembic upgrade head` → `alembic check` 도 확인한다([db-migration]).
- `.ps1` 을 고쳤으면 `powershell -NoProfile -ExecutionPolicy Bypass -File .\.github\scripts\check-ps1-syntax.ps1` 로 Windows PowerShell 5.1 파싱을 확인한다.

## push 후 CI
- `main` push 와 `main` 대상 PR 마다 `.github/workflows/ci.yml` 이 Ubuntu·Windows 테스트, CSS 빌드, PostgreSQL 마이그레이션 왕복, PowerShell 5.1 구문 검사, `pip-audit`(경고성)를 돌린다. 잡 목록은 `README.md` 「CI」.
- CI 는 사후 안전망이다. 로컬 검증을 CI 로 대신하지 않는다. CI 가 실패하면 되돌리거나 즉시 고친다.

## 커밋 메시지 (§19)
- **형식**: `[Category] <type>: <요약(한글, 50자 이내, 현재형)>`
- **Category**: `[Structural]`(구조 변경, 로직 불변) / `[Behavioral]`(기능·버그·로직 변경)
- **type**: `feat` `fix` `refactor` `docs` `style` `test` `chore`
- 예: `[Behavioral] feat: 주문 생성 화면을 추가한다`, `[Structural] refactor: 폼 헬퍼를 forms.py 로 옮긴다`
- **Tidy First**: 구조 변경과 동작 변경을 **한 커밋에 섞지 않는다.** 브랜치가 없어도 이 분리는 유지한다.
- **작게 유지**: 한 커밋은 한 가지 목적. 나중에 되돌릴 수 있는 크기로.

## 기본 흐름 (단독 개발)
```bash
git pull --ff-only
# ... 작업 → 위 로컬 검증 통과 ...
git add <파일>
git commit -m "[Behavioral] feat: 주문 생성 화면을 추가한다"
git push
```

## 브랜치·PR 을 쓰는 경우 (선택)

아래에 해당할 때만. 그 외에는 `main` 직접 커밋으로 충분하다.
- 되돌리기 어렵거나 광범위한 변경 — 마이그레이션이 얽힌 리팩터링, 의존성 대량 상향
- 여러 커밋에 걸쳐 진행 중이라 중간 상태를 `main` 에 두고 싶지 않을 때
- 리뷰를 받고 싶을 때

- 브랜치 명명(kebab-case): `feat/<요약>`, `fix/<요약>`, `refactor/<요약>`, `docs/<요약>`
- PR 제목은 커밋과 동일 형식. **하나의 PR 도 Structural·Behavioral 중 하나만** 담는다.
- 머지 전 **본인 diff 셀프 리뷰**, 머지 후 브랜치 삭제.

```bash
git switch -c feat/order-create
# ... 작업 + 검증 + 커밋 ...
git push -u origin feat/order-create
gh pr create --fill --base main
gh pr checks --watch                     # CI 결과를 기다린다
# 셀프 리뷰와 CI 통과를 확인한 뒤에만 머지한다 — AI 에이전트는 사용자가 요청할 때만 머지한다
gh pr merge --squash --delete-branch
```

- `gh` 가 없으면: `brew install gh`(macOS) 또는 `winget install GitHub.cli`(Windows) 후 `gh auth login`.
- 원격(remote)이 아직 없으면 먼저 연결한다(`git remote add origin <url>`).

## 협업자가 생기면
`main` 브랜치 보호를 켜고 **PR 흐름을 기본으로 되돌린다.** 위 `main` 직접 커밋 흐름은 단독 개발을 전제로 한다. 전환했으면 `ARCHITECTURE.md` §22 에 기록한다.
