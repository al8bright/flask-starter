# Changelog

스캐폴드 템플릿 `flask-starter` 의 변경 이력.
형식은 [Keep a Changelog](https://keepachangelog.com/)를 느슨히 따른다.

오래된 항목은 `docs/archive/changelog/` 에 연도별로 보관한다(규칙은 `AGENTS.md` 「문서 갱신」).

---

## 2026-11-23 — 문서·스캐폴드 정합 점검

템플릿 문서·스킬·스캐폴드 스크립트를 코드와 대조해 어긋난 서술과 두 스크립트 판의 차이를 바로잡았다.

### Fixed (수정)

- `.sh` 세 파일(`scaffold.sh`·`bootstrap.sh`·`tailwind.sh`)을 실행 권한(100755)으로 기록하였다. 그동안 macOS/Linux 생성물에서 안내대로 `./scripts/tailwind.sh` 를 실행하면 권한 오류가 났다. 템플릿 CI 에 실행 권한 검사를 추가하고, 생성물 CSS 빌드를 `./scripts/tailwind.sh` 로 직접 실행한다.
- `-SkipInstall`/`--skip-install`: 「실행 방법」 앞에 생략한 설치 단계(venv·pip·alembic·CSS)를 안내한다. 생략한 단계는 미완료(종료 코드 2)로 세지 않는다는 규칙은 그대로다.
- `scaffold.sh`: DB 포트가 숫자가 아니면 거부한다(인자는 종료 코드 1, 대화형 입력은 기존 값 유지 — `scaffold.ps1` 과 같다). Git Bash 의 psql 탐색 경로를 `scaffold.ps1` 과 같은 세 곳으로 넓히고, `Program Files (x86)` 의 `86` 을 메이저 버전으로 읽던 문제를 고쳤다.
- `tailwind.ps1`: 경로를 `-LiteralPath` 로 다루고 내려받기는 시스템 임시 폴더에서 한다 — 프로젝트 경로에 `[ ]` 가 있으면 실패하였다.
- 생성 프로젝트 `pytest.ini` 에 `filterwarnings = error::DeprecationWarning` 을 두어 로컬 `pytest -q` 가 CI 와 같은 기준으로 실패한다.

### Changed (변경)

- 두 스캐폴드의 사용자 문구를 맞추었다: bootstrap 실행 사유(하한 미달 / pyenv 핀 미설치), bootstrap 실패 문구 두 갈래, psql 발견 표식, 수동 DB 안내(접속 후 실행할 `CREATE DATABASE "<이름>"`·시각대 SQL — 셸마다 다른 인용 규칙을 피한다).
- `bootstrap.*` 에 `-SkipNextSteps`/`--skip-next-steps` 를 추가하였다. 스캐폴드가 부를 때는 스캐폴드가 곧바로 수행할 설치 안내를 출력하지 않는다. 머리 주석을 실제 정책(하한 이상이면 재사용)으로 고쳤다.
- 도움말: `scaffold.sh --help` 에 옵션 목록, `scaffold.ps1` 에 `.PARAMETER` 를 추가하였다.
- 문서: `skeleton/ARCHITECTURE.md`(Accept JSON 응답 갈래, 편집기 이미지 업로드 세 갈래, 테스트 배치, 디자인 서술, CSP 확인 목록 등), 생성 프로젝트 README·PLAN·스킬, 루트 README·AGENTS·TODO·`docs/README.md` 를 코드와 맞추었다.
- 공개 저장소에 남아 있던 비공개 형제 저장소의 이름·커밋 해시를 문서에서 지웠다.
- 이 파일이 200줄을 넘어 오래된 항목을 [`docs/archive/changelog/CHANGELOG-2026.md`](docs/archive/changelog/CHANGELOG-2026.md) 로 옮겼다(옮긴 항목은 상대 링크 경로만 고쳤다).

### 검증

- `scaffold.ps1`(PowerShell 5.1)·`scaffold.sh`(Git Bash)로 `-SkipDb -SkipInstall` 생성 → 두 결과물이 비밀값을 빼고 같음, 잔여 토큰 없음. 두 판 모두 [설치] 안내 출력.
- 접속 불가 포트·이름 `My-App` 으로 실행 → 두 판이 같은 수동 DB 안내를 내고 종료 코드 2. `scaffold.sh --db-port abc` 는 종료 코드 1.
- `scaffold.ps1` 설치 포함 생성 → Python 3.13.14 venv, `pip check`·`ruff check` 통과, `pytest -q` 189건 통과(`pytest.ini` 경고 기준 포함), Tailwind 빌드 성공.
- 모든 `.ps1` PowerShell 5.1 구문 검사, 모든 `.sh` `bash -n` 통과.
- 미검증: 실행 권한 수정의 POSIX 실제 동작(push 후 CI `scaffold-posix` 로 확인), ShellCheck(로컬 미설치 — CI 게이트).

## 2026-11-23 — 기본 화면 디자인 개편

생성 프로젝트의 기본 화면을 사무 문서에서 착안한 디자인으로 바꾸었다. 화면 동작·경로·폼 필드는 바꾸지 않았다.

### Changed (변경)

- 디자인 토큰(`input.css` `@theme`): 종이·먹·쪽빛(`accent`)·인주(`danger`) 색과 관리자 레일 색(`rail`·`rail-ink`·`rail-active`), 시스템 한글 글꼴 스택을 정하였다. 웹 글꼴은 내려받지 않는다.
- 공용 클래스: 표식 `badge`(게시·사용)·`seal`(고정·잠김)·`draft`(초안·중지), `panel`·`page-head`·`table-wrap`·`form-grid`·`link`·`link-danger`·`hint` 를 추가하였다.
- 공개 화면: 상단 쪽빛 띠와 바닥글, 게시판형 공지 목록(번호·제목·작성일·조회, 좁은 화면은 두 줄), 문서형 공지 상세, 로그인 패널.
- 관리자 화면: `base.html` 에 `{% block shell %}` 을 두고 관리자 골격을 왼쪽 메뉴 레일로 분리하였다. 대시보드는 집계 칸과 시스템 상태 면, 공지 작성은 본문과 게시 설정·첨부의 두 단, 배너 입력은 서식 표로 바꾸었다.
- `#alerts` 영역을 `partials/alerts_region.html` 로 분리하였다(골격마다 한 번).
- 편집기: 저장 버튼을 `form.elements` 로 찾는다(폼 밖 `form` 속성 버튼 포함).
- `skeleton/ARCHITECTURE.md` §13·§15, `add-screen` 스킬을 갱신하였다.

### 검증

- 생성물 `pytest`(189건) 통과. Docker(PostgreSQL 16 + waitress)에서 화면 12종과 좁은 화면(390px) 3종, 밝은·어두운 모드 스크린샷을 확인하였다. CSP 위반 0건. 편집기 브라우저 시나리오 27개 재통과.
- 미검증: Firefox·Safari, 실제 모바일 기기, 스크린 리더.

## 2026-11-23 — 공지 본문 위지웍 편집기 이식

형제 템플릿의 자체 편집기(contentEditable, 라이브러리 없음)를 빌드 없는 바닐라 JS ES 모듈로 옮겼다. 저장 마크업은 형제와 같고 서버 정화(nh3, 공통 계층)는 바꾸지 않았다.

### Added (추가)

- `skeleton/app/static/js/editor/`: 도구 모음(문단·제목·굵게·기울임·밑줄·취소선·형광펜·서식 지우기·정렬·목록·인용·구분선·링크), 붙여넣기 정리, 이미지 업로드(자르기·회전 대화상자, 모서리 핸들 크기 조절, 크기 프리셋, 대체 텍스트, 다시 자르기·바꾸기, 끌어 놓기·붙여넣기 업로드), YouTube 삽입. 업로드 중에는 저장 버튼을 비활성화한다. 한글 조합 중(`isComposing`)에는 단축키를 처리하지 않는다.
- `skeleton/app/web/accept.py`: `wants_json` — `Accept` 가 JSON 을 HTML 보다 선호하는지 판정한다.
- `skeleton/tests/test_editor.py`: JSON 업로드·오류·비로그인 401·CSRF 헤더, 편집기 마운트, CSP `blob:`, 편집기 출력의 정화 후 보존, 모듈 import 경로, 금지 코드(`eval`·`style=`·`cssText` 등) 검사.

### Changed (변경)

- `POST /admin/editor/images`: JSON 요청이면 201 `{key, url, width, height}` 를, 오류는 `{detail, code}` 를, 비로그인은 401 JSON 을 돌려준다. 브라우저 폼 요청은 이전과 같다.
- CSP `img-src` 에 `blob:` 을 추가하였다(업로드 중 미리보기).
- `base.html`: `<meta name="csrf-token">` 과 `{% block scripts %}` 를 추가하였다. `notice_form.html` 은 JS 가 없으면 기존 textarea·이미지 코드 받기로 동작한다.
- `skeleton/ARCHITECTURE.md` §2·§4·§8·§9·§13, `skeleton/README.md`, `add-screen` 스킬: 편집기 구조·JSON 업로드 예외·CSSOM 사용·파싱 전 인라인 속성 제거를 반영하였다.

### 검증

- 생성물(Python 3.13.12): `pip check`·`ruff check`·`pytest -q -W error::DeprecationWarning`(189건) 통과, 잔여 토큰 없음, Tailwind 빌드 통과.
- 설치된 Chrome headless(Playwright) + PostgreSQL 16 + waitress 로 편집 시나리오 27개 통과, CSP 위반 0건·콘솔 오류 0건. 이 과정에서 크기 조절 후 오버레이가 사라지는 결함과 붙여넣기 HTML 파싱 시 CSP 위반 보고를 발견하여 고쳤다.
- 미검증: 실제 한글 IME 입력, Firefox·Safari, macOS/Linux, 터치 기기 조작.
