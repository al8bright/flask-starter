// 모달 대화상자 — 형제 템플릿 components/ui/Dialog.tsx·components/editor/TextPromptDialog.tsx 와 대응한다.
//
// - role="dialog" + aria-modal, 포커스 가둠(Tab 순환), Esc 로 닫기, 닫히면 열기 전 포커스로 돌아간다.
// - <body> 에 붙인다: 편집기가 <form> 안에 있어도 중첩 form·제출이 생기지 않도록 대화상자는 <form> 을 쓰지 않고
//   Enter 를 직접 처리한다. 대화상자 안 keydown 은 여기서 전파를 끊는다.
import { h, uid } from "./dom.js";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export const BUTTON =
  "inline-flex min-h-11 items-center justify-center gap-1 rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-surface disabled:opacity-50";
export const BUTTON_PRIMARY =
  "inline-flex min-h-11 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50";

/**
 * 대화상자를 연다. content(Node 배열)를 제목 아래에 넣는다.
 * 반환: {panel, close()} — close 는 onClose 를 부르지 않고 닫기만 한다(호출 측이 결과를 이미 처리한 경우).
 */
export function openDialog({ title, content, onClose, wide = false }) {
  const previous = document.activeElement;
  const titleId = uid("dialog-title");
  const panel = h(
    "div",
    {
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": titleId,
      tabindex: "-1",
      class: `max-h-full w-full overflow-auto rounded-lg border border-line bg-panel p-5 text-ink shadow-xl outline-none ${
        wide ? "max-w-3xl" : "max-w-md"
      }`,
    },
    [h("h2", { id: titleId, class: "text-lg font-semibold", text: title }), ...content],
  );
  const backdrop = h("div", { class: "fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" }, [panel]);

  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    backdrop.remove();
    if (previous instanceof HTMLElement && previous.isConnected) previous.focus({ preventScroll: true });
  };
  const dismiss = () => {
    close();
    onClose?.();
  };

  backdrop.addEventListener("mousedown", (e) => {
    if (e.target === backdrop) dismiss();
  });
  panel.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Escape") {
      e.preventDefault();
      dismiss();
      return;
    }
    if (e.key !== "Tab") return;
    const items = Array.from(panel.querySelectorAll(FOCUSABLE));
    if (!items.length) {
      e.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  document.body.appendChild(backdrop);
  const autofocus = panel.querySelector("[data-autofocus]") ?? panel.querySelector(FOCUSABLE);
  (autofocus ?? panel).focus();
  return { panel, close, dismiss };
}

/**
 * 한 줄 입력 대화상자 — 링크 걸기·유튜브 링크·대체 텍스트에 쓴다.
 * validate 가 문구를 돌려주면 닫지 않고 오류를 보여 준다. 확인하면 onSubmit(value) 후 닫는다.
 */
export function promptDialog({
  title,
  label,
  initialValue = "",
  placeholder,
  hint,
  submitLabel = "적용",
  inputType = "text",
  validate,
  onSubmit,
  onClose,
}) {
  const inputId = uid("prompt-input");
  const hintId = uid("prompt-hint");
  const errorId = uid("prompt-error");
  const input = h("input", {
    id: inputId,
    type: inputType,
    "data-autofocus": true,
    placeholder,
    "aria-describedby": hint ? hintId : null,
    class: "input mt-1 min-h-11",
  });
  input.value = initialValue;
  const error = h("p", { id: errorId, role: "alert", class: "mt-2 rounded-md bg-danger/10 px-3 py-2 text-sm text-danger", hidden: true });

  let dialog;
  const submit = () => {
    const problem = validate?.(input.value) ?? null;
    if (problem) {
      error.textContent = problem;
      error.hidden = false;
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", [hint ? hintId : "", errorId].filter(Boolean).join(" "));
      return;
    }
    dialog.close();
    onSubmit(input.value);
  };
  input.addEventListener("input", () => {
    error.hidden = true;
    input.removeAttribute("aria-invalid");
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.isComposing) {
      e.preventDefault();
      submit();
    }
  });

  dialog = openDialog({
    title,
    onClose,
    content: [
      h("label", { for: inputId, class: "mt-4 block text-sm font-medium", text: label }),
      input,
      hint ? h("p", { id: hintId, class: "mt-1 text-xs text-muted", text: hint }) : null,
      error,
      h("div", { class: "mt-5 flex justify-end gap-2" }, [
        h("button", { type: "button", class: BUTTON, text: "취소", onclick: () => dialog.dismiss() }),
        h("button", { type: "button", class: BUTTON_PRIMARY, text: submitLabel, onclick: submit }),
      ]),
    ].filter(Boolean),
  });
  return dialog;
}
