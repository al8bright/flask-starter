// 편집기 도구 모음 — 형제 템플릿 components/editor/EditorToolbar.tsx 와 대응한다.
// role="toolbar" + 화살표 키 이동(roving tabindex), 토글은 aria-pressed.
// 버튼은 mousedown 기본 동작을 막아 편집 영역의 선택·포커스를 유지한다.
import { h } from "./dom.js";
import { icon } from "./icons.js";

// pressed: 토글 버튼의 활성 판정(ActiveState → boolean). 없으면 일반 버튼(aria-pressed 미표시).
const GROUPS = [
  [
    { command: "undo", label: "실행 취소 (Ctrl+Z)", icon: "undo" },
    { command: "redo", label: "다시 실행 (Ctrl+Shift+Z)", icon: "redo" },
  ],
  [
    { command: "p", label: "본문", icon: "paragraph", pressed: (s) => s.block === "p" },
    { command: "h2", label: "제목 2", icon: "h2", pressed: (s) => s.block === "h2" },
    { command: "h3", label: "제목 3", icon: "h3", pressed: (s) => s.block === "h3" },
  ],
  [
    { command: "bold", label: "굵게 (Ctrl+B)", icon: "bold", pressed: (s) => s.bold },
    { command: "italic", label: "기울임 (Ctrl+I)", icon: "italic", pressed: (s) => s.italic },
    { command: "underline", label: "밑줄 (Ctrl+U)", icon: "underline", pressed: (s) => s.underline },
    { command: "strike", label: "취소선", icon: "strike", pressed: (s) => s.strike },
    { command: "mark", label: "형광펜", icon: "highlight", pressed: (s) => s.mark },
    { command: "clear", label: "서식 지우기", icon: "clear" },
  ],
  [
    { command: "align-left", label: "왼쪽 정렬", icon: "alignLeft", pressed: (s) => s.align === "left" },
    { command: "align-center", label: "가운데 정렬", icon: "alignCenter", pressed: (s) => s.align === "center" },
    { command: "align-right", label: "오른쪽 정렬", icon: "alignRight", pressed: (s) => s.align === "right" },
  ],
  [
    { command: "ul", label: "글머리 목록", icon: "ul", pressed: (s) => s.ul },
    { command: "ol", label: "번호 목록", icon: "ol", pressed: (s) => s.ol },
    { command: "blockquote", label: "인용", icon: "quote", pressed: (s) => s.block === "blockquote" },
    { command: "hr", label: "구분선", icon: "hr" },
  ],
  [
    { command: "link", label: "링크 걸기", icon: "link", pressed: (s) => s.link },
    { command: "unlink", label: "링크 풀기", icon: "unlink" },
    { command: "image", label: "이미지", icon: "image" },
    { command: "video", label: "영상", icon: "video" },
  ],
];

const BUTTON =
  "inline-flex h-11 w-11 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-accent aria-pressed:bg-accent aria-pressed:text-white";

/** 도구 모음을 만든다. 반환: {el, update(activeState)}. */
export function createToolbar({ controlsId, onCommand }) {
  const buttons = [];
  let focusIndex = 0;

  const groups = GROUPS.map((group, gi) => {
    const children = [];
    if (gi > 0) {
      children.push(h("span", { role: "separator", "aria-orientation": "vertical", class: "mx-1 h-6 w-px bg-line" }));
    }
    for (const item of group) {
      const index = buttons.length;
      const button = h(
        "button",
        {
          type: "button",
          "data-index": index,
          tabindex: index === 0 ? "0" : "-1",
          "aria-label": item.label,
          title: item.label,
          "aria-pressed": item.pressed ? "false" : null,
          class: BUTTON,
          onmousedown: (e) => e.preventDefault(),
          onfocus: () => setFocus(index, false),
          onclick: () => onCommand(item.command),
        },
        [icon(item.icon)],
      );
      buttons.push({ button, item });
      children.push(button);
    }
    return h("div", { class: "flex items-center gap-0.5" }, children);
  });

  const el = h(
    "div",
    {
      role: "toolbar",
      "aria-label": "서식 도구",
      "aria-controls": controlsId,
      class: "flex flex-wrap items-center gap-0.5 border-b border-line bg-panel p-1",
    },
    groups,
  );

  function setFocus(index, move) {
    focusIndex = index;
    buttons.forEach(({ button }, i) => button.setAttribute("tabindex", i === index ? "0" : "-1"));
    if (move) buttons[index].button.focus();
  }

  el.addEventListener("keydown", (e) => {
    const n = buttons.length;
    let next = null;
    if (e.key === "ArrowRight") next = (focusIndex + 1) % n;
    else if (e.key === "ArrowLeft") next = (focusIndex - 1 + n) % n;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = n - 1;
    if (next === null) return;
    e.preventDefault();
    setFocus(next, true);
  });

  /** 활성 상태를 버튼의 aria-pressed 에 반영한다. */
  function update(active) {
    for (const { button, item } of buttons) {
      if (item.pressed) button.setAttribute("aria-pressed", String(Boolean(item.pressed(active))));
    }
  }

  return { el, update };
}
