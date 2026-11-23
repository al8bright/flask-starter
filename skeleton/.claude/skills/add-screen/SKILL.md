---
name: add-screen
description: __PROJECT_NAME__ 에 화면(페이지·폼·목록)을 추가하거나 htmx 로 일부만 바꾸는 상호작용을 붙일 때 사용. Jinja 템플릿 배치, 폼 POST → redirect, CSRF, htmx partial 응답, 오류 표시(#alerts), CSP 제약, Tailwind 클래스 빌드를 ARCHITECTURE.md §13·§15 기준으로 안내한다.
---

# 화면 추가 (Jinja · htmx · Tailwind)

> 기본은 **서버가 전체 페이지를 렌더링**하는 것이다. htmx 는 선택적 보강이며, 모든 화면은 htmx 없이 일반 링크·폼으로 동작해야 한다(§13).
> 데이터·규칙이 필요한 화면이면 먼저 [add-domain] 으로 서비스까지 만든다.

## 1. 템플릿 배치

| 위치 | 용도 |
|---|---|
| `app/templates/base.html` | 공통 레이아웃 — `{% block title %}`·`{% block content %}`, 상단 내비, `#alerts`(flash·오류 알림) |
| `app/templates/admin/_layout.html` | 관리자 사이드 메뉴 — 관리자 화면은 이것을 extends 하고 `{% block admin %}` 을 채운다. 메뉴 항목은 이 파일의 목록에 추가한다 |
| `app/templates/<영역>/<화면>.html` | 전체 페이지 |
| `app/templates/partials/<이름>.html` | htmx 가 교체할 조각. 전체 페이지는 같은 partial 을 `{% include %}` 한다 — 같은 마크업을 두 번 쓰지 않는다 |

- 전역으로 쓸 수 있는 값: `project_name`, `current_user`(비로그인이면 `None`), `csrf_field()`, `csrf_token()`.
- 폼 오류는 `{% from "partials/fields.html" import field_error %}` 후 `{{ field_error(errors, "title") }}`. 폼 전체 오류는 `errors._form` 이다.
- 목록 페이지 이동은 `partials/pagination.html`(뷰에서 `page_links(result, "<endpoint>", **params)` 로 만든 링크).

## 2. 폼과 CSRF

- 상태를 바꾸는 요청은 모두 `method="post"` 다. 폼 안에 반드시 `{{ csrf_field() }}` 를 넣는다 — 없으면 400 이다. ⛔ `csrf.exempt` 로 우회하지 않는다.
- 성공하면 `flash(메시지, "success")` + `redirect()`(PRG), 검증 실패면 같은 템플릿을 입력값·오류와 함께 **422** 로 렌더링한다.
- 삭제·폐기처럼 되돌릴 수 없는 폼에는 `data-confirm="<확인 문구>"` 를 붙인다(`app/static/js/app.js` 가 확인을 받는다). ⛔ `onclick="return confirm(...)"` 은 CSP 에 막힌다.
- 링크로 상태를 바꾸지 않는다(GET 은 조회 전용). 로그아웃도 POST 폼이다.

## 3. htmx 로 일부만 바꾸기

1. 일반 폼·링크를 먼저 완성한다(htmx 없이 동작 확인).
2. 같은 요소에 `hx-get`/`hx-post`·`hx-target`·`hx-swap` 을 덧붙인다. 목록 검색처럼 주소가 바뀌어야 하면 `hx-push-url="true"`.
3. 뷰는 `app/web/htmx.py` 헬퍼로 응답을 고른다. ⛔ 뷰에서 `request.headers["HX-Request"]` 를 직접 읽지 않는다.
   - 조회: `render_page_or_partial("<page>.html", "partials/<partial>.html", **context)` — 같은 context 로 htmx 면 partial, 아니면 전체 페이지(`Vary: HX-Request` 포함).
   - POST: `if is_htmx(): return render_template("partials/...")` 로 교체할 조각을, 아니면 `flash` + `redirect`.
   - htmx 요청에 전체 페이지 이동이 필요하면 `htmx_redirect(url)`(302 는 partial 자리에 끼워진다).
4. 오류는 신경 쓰지 않아도 된다 — `ServiceError`·CSRF·HTTP 오류가 htmx 요청이면 `app/web/errors.py` 가 alert partial 을 `HX-Retarget: #alerts` 로 돌려준다. 폼 검증 오류(422)를 그 자리에 다시 그리려면 partial 을 422 로 렌더링한다.
5. CSRF 토큰은 `<body hx-headers>` 가 모든 htmx 요청에 `X-CSRFToken` 으로 싣는다. 폼 안의 `csrf_field()` 도 그대로 둔다(htmx 없이 제출될 때 필요).

기존 예제: 공지 검색(`public/notices.html` + `partials/notice_list.html`), 사용자 행 저장(`partials/admin_user_row.html`), 배너 순서 변경(`partials/admin_banner_rows.html`).

⛔ htmx 로 클라이언트 상태(모달 스택·드래그·실시간 동기화)를 흉내 내지 않는다. 그런 화면이 핵심이면 SPA 스타터(형제 FastAPI 템플릿)를 검토하고 `ARCHITECTURE.md` §22 에 결정을 남긴다.

## 4. CSP 제약 (§9·§13 — 보안 헤더 `app/web/security_headers.py`)

- `script-src 'self'`: ⛔ 인라인 `<script>`, `on*=` 속성, `javascript:` URL, 외부 CDN 스크립트. 스크립트가 필요하면 `app/static/js/` 에 파일로 두고 `base.html` 에서 `defer` 로 불러온다. 외부 라이브러리는 벤더링하고 버전을 `scripts/versions.env` 에 기록한다([stack-versions]).
- `style-src 'self'`: ⛔ `style="..."` 속성·`<style>` 블록. Tailwind 클래스를 쓴다.
- htmx 설정(`base.html` 의 `htmx-config` 메타)은 `allowEval:false`·`includeIndicatorStyles:false` 다 — `hx-on`·`hx-vars`·`js:` 접두사는 동작하지 않는다.
- `img-src 'self' data: https:`, `frame-src` 는 YouTube 만 허용한다. 다른 출처가 필요하면 헤더를 고치고 이유를 §22 에 남긴다.

## 5. 스타일 (Tailwind CSS v4, §15)

- 입력은 `app/static/css/input.css`(`@theme` 색 토큰 `surface`·`panel`·`ink`·`muted`·`line`·`accent`·`danger`, 공용 컴포넌트 `input`·`btn`·`btn-primary`·`badge`·`table`). 출력 `app/static/css/app.css` 는 빌드 결과라 커밋하지 않는다.
- Tailwind 는 `app/templates/`·`app/static/js/` 를 훑어 쓰인 클래스만 생성한다. ⛔ 클래스 이름을 문자열 조합(`"text-" ~ color`)으로 만들지 않는다 — 빌드가 찾지 못한다. 조건부 클래스는 완성된 이름 전체를 쓴다.
- 템플릿을 고치는 동안 `scripts/tailwind.ps1 -Watch`(Windows) 또는 `./scripts/tailwind.sh --watch` 를 띄워 둔다.

## 6. 테스트

- 화면 테스트는 `client.get(...)` 의 상태 코드와 `res.get_data(as_text=True)` 안의 핵심 문구로 확인한다. POST 는 `tests.conftest.post_form(..., htmx=True|False)`.
- htmx 경로는 partial 만 왔는지(전체 레이아웃이 없는지), 오류면 `HX-Retarget` 이 `#alerts` 인지 확인한다.
- 브라우저 동작(htmx 교체·CSP 위반 없음)은 테스트로 잡히지 않는다 — 개발 서버를 띄워 직접 확인하고, 못 했으면 보고에 **미검증**으로 남긴다.
