# jQuery 4.1.0 도입 검토

- **일자**: 2026-11-23
- **결정**: 유지 — jQuery 를 도입하지 않고 바닐라 JS(브라우저 표준 DOM API)와 htmx 로 둔다. jQuery 등 DOM 유틸리티 라이브러리 금지를 `skeleton/ARCHITECTURE.md` ★MUST #1·§13 「스크립트」와 `skeleton/AGENTS.md` 에 명시하였다
- **대상**: `skeleton/app/static/js/`(화면 스크립트), 도입이 검토 중인 공지 본문 편집기([위지웍 편집기 검토](2026-11-23-wysiwyg-editor.md))
- **반영 커밋**: 이 기록과 같은 커밋(기준 문서 갱신)
- **관련 기준**: `skeleton/ARCHITECTURE.md` ★MUST #1(Node 빌드·SPA·Alpine.js 금지), §9(CSP), §13(htmx·스크립트), `stack-versions` 스킬 §5-2(벤더링 무결성)

## 배경

공지 본문 편집기를 직접 만들 경우 화면 JS 가 처음으로 수백 줄 규모가 된다. 그 전에 DOM 조작 계층으로 jQuery 4.1.0 을 둘지, 표준 DOM API 만 쓸지 정한다.

현재 화면 JS 는 벤더링한 `htmx.min.js` 와 `app.js`(확인 대화상자, 749 bytes) 뿐이다. ★MUST #1 은 Alpine.js 를 금지하지만 jQuery 에 대한 규정은 없다.

## jQuery 4.1.0 현황

| 항목 | 내용 | 출처·상태 |
|---|---|---|
| 배포 | 2026-11-17(npm `latest`). 배포 24시간 규칙 충족 | npm registry 실측 |
| 지원 정책 | 4.x 가 현행 계열이다. 같은 날 배포된 3.8.0 을 끝으로 3.x 는 중대한 보안·버그 수정만 받는다 | jQuery 공식 블로그(2026-11-17) |
| 4.1.0 변경 | 선택자 식별자 정규식 ReDoS 수정, 내부 `getElementsBy*` → `querySelectorAll` 전환, `jqXHR.responseURL` 추가, form-associated custom element 직렬화 | GitHub 릴리스 노트 |
| 4.0.0 주요 변경 | ESM 배포(`dist-module/`), TrustedHTML 기본 지원, `dataType` 없는 Ajax 응답의 스크립트 자동 실행 중단 | GitHub 릴리스 노트 |
| 크기 | `jquery.min.js` 78,965 bytes(gzip 27,491) · slim 56,030 bytes(gzip 19,387). 참고로 `htmx.min.js` 는 52,182 bytes(gzip 16,838) | 실측(gzip -9) |
| 라이선스 | MIT | npm 메타데이터 |

## CSP 호환성

`dist/jquery.js`(4.1.0) 소스를 검사하였다(실측, 정적 분석 — 브라우저 미검증).

- **불러오기 시점**: 지원 여부 검사가 `el.style.cssText` 대입(CSSOM)만 쓴다. CSSOM 조작은 `style-src` 검사 대상이 아니므로 현재 CSP 에서 로드할 수 있다.
- **함정 1**: `.html()`·`.append()` 등으로 `<script>` 가 든 HTML 을 넣으면 jQuery 가 그 스크립트를 인라인 `<script>` 로 다시 만들어 실행한다(`DOMEval`). `script-src 'self'` 에서 차단되어 콘솔에 위반이 남는다. `$.getScript` 와 `<script src>` 삽입 경로(`_evalUrl` → `DOMEval`)도 같다.
- **함정 2**: `.html("<p style=…>")` 처럼 `style=` 이 든 문자열은 `innerHTML` 로 해석되어 차단된다. 바닐라 `innerHTML` 과 같은 제약이며 jQuery 가 완화하지 않는다.

정리하면 jQuery 는 현재 CSP 아래에서 쓸 수 있지만, 문자열 HTML 조립 위주의 jQuery 관용구가 CSP 위반으로 이어지기 쉽다.

## 비교

| 기준 | jQuery 4.1.0 | 바닐라 JS |
|---|---|---|
| DOM 선택·이벤트 위임·class 조작 | `$()`·`.on(이벤트, 선택자)`·`.toggleClass` | `querySelector`·`closest`·`addEventListener`·`classList` — 대상 브라우저 전부 표준 지원 |
| 서버 요청 | `$.ajax`(CSRF 헤더는 `$.ajaxSetup`) | 화면 갱신은 htmx 가 맡는다. 편집기 이미지 업로드 같은 단건은 `fetch` + `FormData` + `X-CSRFToken` 헤더로 충분하다 |
| 편집기 핵심(contentEditable·Selection·Range·`execCommand`·붙여넣기·한글 조합 이벤트) | **해당 API 없음** — 결국 표준 API 를 직접 호출한다 | 형제 템플릿 편집기가 이미 이 방식이다. 순수 로직은 타입 표기만 지우고 옮길 수 있다 |
| htmx 교체 후 재바인딩 | 직접 바인딩한 핸들러는 교체된 요소에서 사라진다 — 위임 또는 `htmx.onLoad` 필요 | 같다(위임으로 해결). 차이 없음 |
| 페이지 비용 | 모든 화면 +27 KB(gzip). 편집기 화면에만 싣는다면 그 화면만 | 0 |
| 운영 비용 | `versions.env` 기록, SHA-256 확인, `check_projects.py` 버전 검사 추가, `stack-versions` 스킬·템플릿 CI 갱신, 4.x 보안 릴리스 추적 | 없음 |
| 형제 템플릿과의 대응 | 형제(React 등)는 jQuery 를 쓰지 않는다 — 이식 코드가 두 관용구로 갈라진다 | 형제 편집기 코드와 함수 단위로 대응한다 |
| 플러그인 생태계 | jQuery UI·날짜 선택기 등 기존 플러그인을 쓸 수 있다 | 필요한 위젯은 직접 만들거나 표준 요소(`<dialog>`·`<input type="date">`)를 쓴다 |

## 판정

바닐라 JS 를 권장한다.

1. jQuery 의 주된 이점(브라우저 차이 흡수, 간결한 DOM·Ajax 호출)은 표준 API 와 htmx 가 이미 채운다.
2. 도입 동기인 편집기의 핵심 기능에는 jQuery API 가 없다. jQuery 를 넣어도 난이도가 낮아지지 않고, 형제 편집기 코드와의 대응만 약해진다.
3. 모든 화면에 27 KB(gzip)와 벤더링 관리 절차가 추가되는 데 비해 얻는 기능이 적다.
4. 문자열 HTML 조립 관용구가 CSP 위반(인라인 스크립트·`style=`)을 유발하기 쉽다.

jQuery 가 유리한 경우는 **jQuery 플러그인을 그대로 들여야 할 때**다. 그 경우에도 해당 화면에만 싣고, 플러그인의 CSP 호환(인라인 `style=` 주입 여부)을 먼저 확인한다.

## 반영 사항

- `skeleton/ARCHITECTURE.md` ★MUST #1 금지 목록과 §13 「스크립트」, `skeleton/AGENTS.md` 「스택 고정」에 jQuery 등 DOM 유틸리티 라이브러리 금지를 추가하였다. 플러그인이 꼭 필요해지면 이 문서의 재검토 조건에 따라 새 검토 기록을 남긴다.
- 편집기 이식 시 공통 헬퍼(CSRF 헤더를 붙이는 `fetch` 래퍼, 이벤트 위임)는 `app/static/js/` 의 작은 모듈 하나로 둔다.

## 미확인 항목

- jQuery 4.1.0 을 실제 화면에 올렸을 때의 CSP 콘솔 위반 여부 — 브라우저 미검증(정적 분석만 수행).
- `dist-module/jquery.module.min.js` 를 `<script type="module">` 로 불러오는 방식의 동작 — 미검증.

## 재검토 조건

- 들여야 할 jQuery 플러그인이 생기는 경우.
- 편집기를 외부 라이브러리로 전환하는데 그 라이브러리가 jQuery 를 요구하는 경우.
