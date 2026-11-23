# flask-starter — Claude Code 지침 (템플릿 저장소용)

@AGENTS.md

> 공통 규칙의 원본은 위에서 import 한 [`AGENTS.md`](AGENTS.md)다(Codex·Cursor 등 다른 에이전트와 공용).
> 규칙을 바꿀 때는 `AGENTS.md` 를 고치고, 이 파일에는 **Claude Code 전용 내용만** 둔다.

## Claude Code 전용

- **답변은 세션 첫 응답부터 항상 한국어로 한다.** 요약·표·질문(선택지 포함)도 한국어로 쓴다.
- `skeleton/` 아래 파일을 읽으면 `skeleton/CLAUDE.md`(생성 프로젝트용)와 그것이 import 하는 `skeleton/AGENTS.md` 가 함께 로드된다.
  그 안의 코드 규칙은 `skeleton/` 수정에 적용하되, 저장소 운영(검증·커밋·push·문서 위치)은 루트 `AGENTS.md` 「지침 적용 범위」를 따른다.
- `skeleton/.claude/skills/` 의 스킬도 `skeleton/` 작업 중 로드된다. 그 안의 `__PROJECT_NAME__` 은 치환 전 토큰이며, 커밋 절차 등은 생성 프로젝트 기준이다.
  버전 작업 전에는 `skeleton/.claude/skills/stack-versions/SKILL.md` 를 직접 읽는다.
- 라이브러리 API·릴리스 변경은 Context7 MCP(연결된 경우)를 웹 검색보다 먼저 쓴다. 릴리스 노트 원문은 `gh api repos/<소유자>/<저장소>/releases` 로 확인한다.
- 임시 스캐폴드·venv·로그 등 검증 산출물은 세션 스크래치 폴더에 만든다(⛔ 저장소 안).
- 한국어 문서(`docs/`·CHANGELOG·README)는 `korean-report-style` 스킬이 있으면 그 규약과 검사기로 확인한다.
- 공통 계층 원본(`../fastapi-react-pg-starter`)은 읽기만 한다. 그쪽을 고쳐야 하면 사용자에게 보고하고, 고칠 때는 그 저장소의 `git status` 를 먼저 확인한다 — 다른 세션의 미커밋 작업이 있을 수 있다.
