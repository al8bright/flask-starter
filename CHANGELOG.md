# Changelog

스캐폴드 템플릿 `flask-starter` 의 변경 이력.
형식은 [Keep a Changelog](https://keepachangelog.com/)를 느슨히 따른다.

오래된 항목은 `docs/archive/changelog/` 에 연도별로 보관한다(규칙은 `AGENTS.md` 「문서 갱신」).

---

## 2026-11-23 — 운영 배포 보강과 생성 기준 기록

골격에 빠져 있던 운영 설정·배포 예시·기본 파일을 보강하였다.

### Added (추가)

- **리버스 프록시 신뢰 `TRUSTED_PROXY_HOPS`**(`app/web/proxy.py`, 기본 0): 값만큼 `X-Forwarded-For`·`Proto`·`Host` 를 믿는다(werkzeug `ProxyFix`). HTTPS 를 끝내는 프록시 뒤에서는 앱이 요청을 HTTP 로 보아 Flask-WTF 의 HTTPS `Referer` 검사(`request.is_secure` 일 때만 동작)가 적용되지 않으므로, 프록시 뒤 운영은 1 로 둔다. `COOKIE_SECURE=true` 인데 0 이면 기동 시 경고하고, 범위(0~3)를 벗어나면 기동을 거부한다. 공통 `config.py` 는 형제 템플릿과 같은 파일이라 고치지 않고 웹 계층 전용 설정으로 두었다(ARCHITECTURE §5). `.env.example`·두 스캐폴드의 `.env` 생성 블록에 키를 추가하였다.
- **운영 배포 예시 `skeleton/deploy/`**: systemd 서비스(gunicorn), nginx 사이트(`/login` IP 단위 요청 제한·본문 상한·전달 헤더), 갱신 배포 스크립트 `deploy.sh`(pull → pip → CSS → alembic → 재기동 → 상태 확인, 실패 시 중단), 최초 설치 절차(앱 전용 DB 계정·운영 `.env` 값). 값은 일반 예시이며, 공개 저장소에 실제 운영 값을 두지 않도록 안내한다. 토큰 치환 대상 확장자에 `.sh`·`.conf`·`.service` 를 더하였다.
- **생성 기준 기록 `.flask-starter`**: 두 스캐폴드가 생성 프로젝트 루트에 템플릿 커밋(`commit=<해시>`, 미커밋 변경이 있으면 `-dirty`, git 이 없으면 `unknown`)을 남긴다. 이후 템플릿 수정을 옮길 때 이 커밋 이후의 CHANGELOG 항목과 비교한다(생성 프로젝트 README 「템플릿 수정 반영」). HTTP 로 서빙되는 위치가 아니다.
- 기본 아이콘 `static/img/favicon.svg`·`favicon.ico`(자리표시 그림)와 `/favicon.ico` 경로 — 브라우저가 매 화면 요청해 404 가 로그에 쌓이던 문제를 없앴다.
- `/robots.txt`(모두 허용)와 로그인·관리자·API 응답의 `X-Robots-Tag: noindex`. 색인 제외 경로를 `robots.txt` 에 나열하지 않는다 — 누구나 읽는 파일이라 관리자 경로 목록이 공격 단서가 된다.
- `base.html` 에 `{% block head %}`(화면별 `meta description` 등)와 `{% block main %}`(전체 폭 띠가 필요한 화면이 `<main>` 을 통째로 대체한다)을 두었다.

### Changed (변경)

- CSP 위반 코드 정적 점검을 편집기 폴더에서 `app/static/js/` 아래 모든 스크립트로 넓혔다(`tests/test_static_js.py`, 벤더링한 htmx 제외). 새 스크립트도 테스트를 따로 만들지 않고 검사된다.
- `skeleton/ARCHITECTURE.md`: §3·§4 구조, §5 웹 계층 전용 설정, §8 외부 HTTP 호출 지침(서버 호출·짧은 타임아웃·캐시·실패 시 직전 값·재시도 간격·테스트에서 네트워크 차단), §9 `X-Robots-Tag`, §12 테스트 배치, §13 블록·아이콘·검색엔진, §14 프록시 신뢰, §17 키 표, §21 체크리스트. 생성 프로젝트 README·AGENTS·PLAN·`add-screen`·`stack-versions` 스킬, 루트 README·AGENTS(ShellCheck 대상에 `deploy.sh`)를 맞추었다. 템플릿 CI 의 ShellCheck 대상에 `skeleton/deploy/deploy.sh` 를 추가하였다.

### 검증

- 실패 테스트를 먼저 쓰지 않고 구현과 함께 추가하였다(Red 단계 미확인). 추가 테스트: 프록시 신뢰 0·1 의 scheme·host·IP, 잘못된 값 기동 거부, `COOKIE_SECURE=true` + 0 경고, `/favicon.ico`·아이콘 링크, `robots.txt` 에 비공개 경로 없음, `X-Robots-Tag` 대상·비대상, 모든 스크립트 CSP 점검.
- `scaffold.ps1`(PowerShell 5.1)·`scaffold.sh`(Git Bash)로 이름 `My App`, `-SkipDb -SkipInstall` 생성 → 두 결과물이 `.env` 를 빼고 같음(`.flask-starter` 포함), 잔여 토큰 없음, `.env` 키 집합 = `.env.example`, `deploy/` 파일의 토큰이 `my_app`·`My App` 으로 치환됨.
- 생성물(Python 3.13.14 venv): `pip check`·`ruff check` 통과, `pytest -q` 214건 통과. 공통 계층 동일(`tools/check_common_layer.py`). 모든 `.ps1` PowerShell 5.1 구문 검사, 모든 `.sh` `bash -n`·ShellCheck(`-S warning`) 통과.
- **미검증**: `deploy/` 예시를 실제 Linux 서버에서 실행(`nginx -t`·systemd 기동·`deploy.sh`), 브라우저에서 아이콘 표시, POSIX 에서 `deploy.sh` 실행 권한과 `.flask-starter` 생성(push 후 CI `scaffold-posix`).

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
