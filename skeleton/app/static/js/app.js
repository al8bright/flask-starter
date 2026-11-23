// 화면 공통 스크립트 — 최소한만 둔다 (ARCHITECTURE.md §13).
// ⛔ 클라이언트 상태 관리·화면 조립을 여기에 키우지 않는다. 필요해지면 SPA 스타터를 검토한다.

// data-confirm="메시지" 가 붙은 폼은 제출 전에 확인을 받는다 (삭제·폐기 같은 되돌릴 수 없는 작업).
// htmx 폼도 submit 이벤트를 먼저 거치므로 같은 확인이 적용된다.
document.addEventListener(
  "submit",
  (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const message = form.dataset.confirm;
    if (message && !window.confirm(message)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  },
  true,
);
