# 공지 본문 위지웍 편집기 검토

- **일자**: 2026-11-23
- **결정**: 보류 — 구현 방식은 「형제 템플릿 자체 편집기의 바닐라 JS 이식 + nh3 서버 정화 유지」를 권장안으로 정하였다. 착수 여부와 범위(1단계만·2단계까지)는 사용자 결정으로 남긴다
- **대상**: `skeleton/app/templates/admin/notice_form.html`(본문 입력), `POST /admin/editor/images`(본문 이미지 업로드), 공통 계층 `app/core/sanitize.py`(nh3 정화)
- **반영 커밋**: 없음
- **관련 기준**: `skeleton/ARCHITECTURE.md` §2(Node 빌드 금지), §8(본문 HTML 정화), §9(CSP), §13(스크립트)

## 배경

공지 본문은 HTML `textarea` 에 직접 입력한다. 이미지는 따로 올린 뒤 돌려받은 `<img>` 코드를 붙여 넣는다. HTML 을 모르는 관리자가 쓰기 어렵다.

검토 질문은 「nh3 로 자체 위지웍을 만들 수 있는가」였다. 역할을 나누면 다음과 같다.

| 구성 요소 | 역할 | 위치 |
|---|---|---|
| 위지웍 편집기 | 브라우저에서 서식을 입히고 HTML 을 만든다 | 클라이언트 JS(`contenteditable`) |
| nh3 | 저장 직전에 허용 목록 밖의 태그·속성·URL 을 제거한다 | 서버 `app/core/sanitize.py`(이미 적용) |

nh3 는 편집 기능을 제공하지 않는다. 위지웍은 클라이언트 JS 로 만들고, nh3 는 지금처럼 최종 방어선으로 둔다. 편집기가 만드는 HTML 이 정화 허용 목록 안에 들어가야 서식이 보존된다.

## 제약 조건

1. **Node 빌드 금지**(§2) — TypeScript·번들러를 쓸 수 없다. 브라우저가 바로 읽는 JS(`<script type="module" src>` 포함)만 쓴다.
2. **CSP `script-src 'self'`·`style-src 'self'`**(§9) — 인라인 스크립트·`on*=` 속성·`<style>`·HTML 의 `style=` 속성을 쓸 수 없다. CSSOM 으로 값을 넣는 `el.style.width = …` 는 CSP 대상이 아니다(브라우저 미검증).
3. **정화 허용 목록은 공통 계층**(§8) — `sanitize.py` 를 바꾸면 형제 템플릿 다섯 곳이 함께 바뀐다. 편집기는 현재 허용 목록(태그 41종, class 는 `align-left`·`align-center`·`align-right`·`video` 만, `style` 속성 불허, iframe 은 YouTube embed 만) 안에서 출력해야 한다.
4. **htmx 는 선택적 보강**(§13) — JS 가 꺼지면 지금의 `textarea` 로 동작해야 한다.

## 선택지

| 선택지 | 내용 | 판정 |
|---|---|---|
| A. 현행 유지 | HTML `textarea` + 이미지 코드 붙여 넣기 | 비용 없음. 관리자 사용성 문제가 남는다 |
| B. 외부 편집기 벤더링 | 빌드 없이 쓸 수 있는 배포 파일을 `app/static/` 에 둔다 | 비권장. ProseMirror 계열(TipTap·Lexical 등)은 번들러 사용이 전제다. Quill 은 정렬을 `ql-*` class 로 표현하는데 정화기가 이를 버린다(`sanitize.py` 주석). 다른 라이브러리의 CSP 호환(`<style>` 주입 여부)은 미확인이다 |
| C. 형제 자체 편집기 이식 | `fastapi-react-pg-starter` 의 `components/editor/`·`lib/editor/` 를 바닐라 JS 로 옮긴다 | **권장**. 출력 형식이 이미 정화 허용 목록에 맞춰져 있고, 외부 의존성이 없다 |

## 형제 자체 편집기 분석

형제 템플릿은 라이브러리 없이 `contentEditable` + `document.execCommand` 로 편집기를 만들었다. `execCommand` 는 표준에서 폐기 예정(deprecated)이지만 주요 브라우저가 지원한다. 형제 코드는 호출을 `editorDom.ts` 의 `exec()` 한 곳에 모으고 실패 시 DOM 직접 수정 폴백을 둔다.

**기능**: 실행 취소·다시 실행, 본문·제목 2·제목 3, 굵게·기울임·밑줄·취소선·형광펜, 서식 지우기, 정렬 3종, 글머리·번호 목록, 인용, 구분선, 링크 넣기·빼기, 이미지(업로드·끌어 놓기·크기 조절·자르기), YouTube 영상, 붙여넣기 정리.

**규모**(실측, 테스트 제외 줄 수):

| 구분 | 파일 | 줄 수 | 이식 방식 |
|---|---|---|---|
| 순수 로직 | `editorDom.ts`·`richText.ts`·`mediaHtml.ts`·`imageTransform.ts`·`imageCanvas.ts`·`upload.ts` | 1,199 | 타입 표기만 지우면 거의 그대로 쓸 수 있다 |
| React 화면 | `RichTextEditor.tsx`·`MediaOverlay.tsx`·`ImageCropDialog.tsx`·`EditorToolbar.tsx`·`TextPromptDialog.tsx`·`EditorIcon.tsx` | 1,809 | 상태·이벤트 처리를 DOM API 로 다시 작성해야 한다 |
| 테스트 | Vitest 5개 파일 | 985 | 그대로 옮길 수 없다(Node 금지) |

## 권장안 — 단계별 이식

**1단계(최소 기능)**
- `app/static/js/editor/` 에 ES 모듈로 둔다. `notice_form.html` 의 `textarea` 를 그대로 두고, JS 가 있으면 숨긴 뒤 편집 영역과 도구 모음을 붙인다. 제출 직전에 직렬화한 HTML 을 `textarea` 에 넣는다.
- 기능: 도구 모음 서식 전체, 링크, 붙여넣기 정리, 이미지 업로드 후 삽입(크기 조절·자르기 제외), YouTube 삽입.
- 서버 변경: `POST /admin/editor/images` 가 `Accept: application/json` 이면 `{url, width, height}` 를 돌려준다(CSRF 는 `X-CSRFToken` 헤더). 정화 허용 목록은 바꾸지 않는다.
- 예상 규모: JS 900~1,200줄(미측정 — 형제 코드 기준 추정).

**2단계(형제와 같은 기능)**
- 이미지 크기 조절 핸들, 자르기 대화상자(canvas), 끌어 놓기 업로드. 예상 JS 700~900줄 추가(미측정).

**유지 원칙**
- 출력 계약(태그·class·영상 래퍼 `<div class="video" data-youtube-video>`)은 형제 편집기와 같게 둔다. 서식을 추가하면 형제와 함께 정화 허용 목록·`test_sanitize.py` 를 고친다(공통 계층).
- 편집 전용 속성(`contenteditable`·`draggable`·`data-selected`)과 `style` 은 직렬화 때 지운다(형제 `serializeEditorHtml` 과 같다).

## 위험과 대응

| 위험 | 대응 |
|---|---|
| JS 로직을 자동 테스트할 수 없다(Node 금지) | 서버 쪽에서 편집기 출력 예시가 정화 후 그대로 남는지 pytest 로 고정한다. 브라우저 동작은 체크리스트로 확인하고, 확인하지 못하면 미검증으로 남긴다 |
| 한글 IME 조합 중 단축키·도구 모음 동작이 조합을 깨뜨릴 수 있다 | `compositionstart`·`compositionend`·`isComposing` 중에는 키 처리를 건너뛴다. 형제 편집기는 대화상자에서만 `isComposing` 을 검사하므로 본문 영역도 브라우저에서 확인한다 |
| 붙여넣은 HTML 의 `style=` 속성이 편집 영역에 들어가면 CSP 위반이 콘솔에 남는다 | 붙여넣기를 가로채 정리(형제 `cleanPastedHtml`)한 뒤 넣는다 |
| 형제 편집기와 두 벌을 유지해야 한다 | 순수 로직 파일은 형제 파일과 함수 단위로 대응시키고, 형제 변경 시 함께 옮긴다. 공통 계층처럼 동일성 검사를 할 수는 없다(언어가 다르다) |
| `execCommand` 폐기 | 호출을 한 함수에 모아 대체 시 그곳만 바꾼다(형제와 같은 구조) |

## 미확인 항목

- CSSOM 으로 넣은 크기(`el.style.width`)가 `style-src 'self'` 아래에서 콘솔 위반 없이 동작하는지(2단계 크기 조절이 의존한다) — 브라우저 미검증.
- 벤더링 후보 라이브러리별 CSP 호환과 출력 형식 — 선택지 B 를 다시 검토할 때 확인한다.

## 재검토 조건

- 착수가 결정되면 1단계 범위로 `TODO.md` 에 작업을 만들고, 완료 시 이 문서 머리에 반영 커밋을 부기한다.
- 형제 편집기가 라이브러리 기반으로 바뀌거나 정화 허용 목록이 바뀌면 이 검토를 다시 한다.
