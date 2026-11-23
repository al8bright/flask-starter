// 선택된 이미지/영상 위 오버레이 — 형제 템플릿 components/editor/MediaOverlay.tsx 와 대응한다.
// - 편집 영역 래퍼(position:relative) 안에 absolute 로 놓고, getBoundingClientRect 차이로 배치한다.
//   스크롤·리사이즈·이미지 로드·크기 변화(ResizeObserver) 때 다시 잰다.
// - 모서리 핸들 4개: 드래그 중에는 el.style.width(CSSOM)로 미리보기만 하고 pointerup 에 한 번 커밋(onResize).
//   커밋은 편집기가 selectNode + insertHTML 로 처리한다(undo 스택에 남도록).
// - 미니 도구 모음: 이미지(크기 프리셋·폭 입력·대체 텍스트·다시 자르기·교체·삭제) / 영상(크기 프리셋·폭 입력·링크 바꾸기·삭제).
import { h, placeBox, uid } from "./dom.js";
import { icon } from "./icons.js";
import {
  IMAGE_MIN_WIDTH,
  IMAGE_WIDTH_PRESETS,
  sizeForWidth,
  VIDEO_MAX_WIDTH,
  VIDEO_MIN_WIDTH,
  VIDEO_SIZE_PRESETS,
  videoSizeForWidth,
} from "./image-transform.js";

const CORNERS = ["nw", "ne", "sw", "se"];
const CORNER_POS = {
  nw: "left-0 top-0 cursor-nwse-resize",
  ne: "left-full top-0 cursor-nesw-resize",
  sw: "left-0 top-full cursor-nesw-resize",
  se: "left-full top-full cursor-nwse-resize",
};
const BUTTON =
  "inline-flex min-h-11 min-w-11 items-center justify-center gap-1 rounded-md px-2 text-sm font-medium text-ink hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40 aria-pressed:bg-accent aria-pressed:text-white";
// 미니 도구 모음 예상 폭 — 오른쪽 여유가 없으면 왼쪽으로 당긴다.
const TOOLBAR_WIDTH = 360;

/**
 * 오버레이를 만든다. 반환: {destroy()}.
 * opts: {kind: "image"|"video", target, container, natural: Size, currentWidth, canRecrop,
 *        onResize(width), onDelete(), onAltText(), onRecrop(), onReplace(), onChangeLink()}
 */
export function createMediaOverlay(opts) {
  const { kind, target, container, natural, currentWidth, canRecrop } = opts;
  let box = null;
  let preview = null;
  let drag = null;

  const sizeFor = (width) => (kind === "image" ? sizeForWidth(natural, width) : videoSizeForWidth(width));
  // 미리보기 대상 — 영상은 래퍼가 아니라 iframe 크기를 바꾼다.
  const previewEl = () => (kind === "video" ? (target.querySelector("iframe") ?? target) : target);

  // ---------- 선택 테두리 + 모서리 핸들 ----------
  const sizeBadge = h("span", { class: "absolute bottom-2 right-2 rounded bg-black/70 px-2 py-0.5 text-xs text-white", hidden: true });
  const handles = CORNERS.map((corner) =>
    h("span", {
      "aria-hidden": "true",
      "data-corner": corner,
      class: `pointer-events-auto absolute h-7 w-7 -translate-x-1/2 -translate-y-1/2 touch-none after:absolute after:inset-2 after:rounded-sm after:border-2 after:border-accent after:bg-white ${CORNER_POS[corner]}`,
    }),
  );
  const frame = h("div", { class: "pointer-events-none absolute z-10 outline-2 outline-accent", hidden: true }, [...handles, sizeBadge]);

  for (const handle of handles) {
    const corner = handle.dataset.corner;
    handle.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      drag = { corner, startX: e.clientX, startWidth: previewEl().getBoundingClientRect().width || currentWidth, pointerId: e.pointerId };
      handle.setPointerCapture?.(e.pointerId);
    });
    handle.addEventListener("pointermove", (e) => {
      if (!drag || drag.pointerId !== e.pointerId) return;
      const dx = e.clientX - drag.startX;
      const grow = drag.corner === "nw" || drag.corner === "sw" ? -dx : dx;
      preview = sizeFor(drag.startWidth + grow);
      placeBox(previewEl(), { width: preview.width, height: preview.height });
      render();
    });
    const end = (e) => {
      if (!drag || drag.pointerId !== e.pointerId) return;
      drag = null;
      handle.releasePointerCapture?.(e.pointerId);
      const el = previewEl();
      placeBox(el, { width: null, height: null });
      if (!el.getAttribute("style")) el.removeAttribute("style");
      const size = preview;
      preview = null;
      render();
      if (size && size.width !== currentWidth) opts.onResize(size.width);
    };
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
  }

  // ---------- 미니 도구 모음 ----------
  const presets =
    kind === "image"
      ? [
          { label: "소", width: IMAGE_WIDTH_PRESETS[0] },
          { label: "중", width: IMAGE_WIDTH_PRESETS[1] },
          { label: "대", width: IMAGE_WIDTH_PRESETS[2] },
          { label: "원본", width: natural.width },
        ]
      : [...VIDEO_SIZE_PRESETS.map(([w, hh]) => ({ label: `${w}×${hh}`, width: w })), { label: "전체 폭", width: VIDEO_MAX_WIDTH }];
  const minWidth = kind === "image" ? Math.min(IMAGE_MIN_WIDTH, natural.width) : VIDEO_MIN_WIDTH;
  const maxWidth = kind === "image" ? natural.width : VIDEO_MAX_WIDTH;
  const widthId = uid("media-width");

  const widthInput = h("input", {
    id: widthId,
    type: "number",
    inputmode: "numeric",
    min: minWidth,
    max: maxWidth,
    class: "min-h-11 w-20 rounded-md border border-line bg-surface px-2 text-sm text-ink outline-none focus:border-accent",
  });
  widthInput.value = String(currentWidth);
  const commitDraft = () => {
    const n = Number.parseInt(widthInput.value, 10);
    if (!Number.isFinite(n)) {
      widthInput.value = String(currentWidth);
      return;
    }
    const size = sizeFor(n);
    widthInput.value = String(size.width);
    if (size.width !== currentWidth) opts.onResize(size.width);
  };
  widthInput.addEventListener("blur", commitDraft);
  widthInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitDraft();
    }
  });

  const toolButton = (label, iconName, onClick, extra = {}) =>
    h("button", { type: "button", class: BUTTON, "aria-label": label, title: extra.title ?? label, disabled: extra.disabled, onclick: onClick }, [icon(iconName)]);

  const actions =
    kind === "image"
      ? [
          toolButton("대체 텍스트", "alt", () => opts.onAltText()),
          toolButton("다시 자르기", "crop", () => opts.onRecrop(), {
            disabled: !canRecrop,
            title: canRecrop ? "다시 자르기" : "GIF 는 자를 수 없습니다",
          }),
          toolButton("이미지 교체", "replace", () => opts.onReplace()),
        ]
      : [toolButton("링크 바꾸기", "link", () => opts.onChangeLink())];
  const deleteButton = h(
    "button",
    {
      type: "button",
      class: `${BUTTON} text-danger`,
      "aria-label": kind === "image" ? "이미지 삭제" : "영상 삭제",
      title: "삭제",
      onclick: () => opts.onDelete(),
    },
    [icon("trash")],
  );

  const toolbar = h(
    "div",
    {
      role: "toolbar",
      "aria-label": kind === "image" ? "이미지 도구" : "영상 도구",
      class: "absolute z-20 flex max-w-full flex-wrap items-center gap-0.5 rounded-lg border border-line bg-panel p-1 shadow-lg",
      hidden: true,
    },
    [
      h(
        "div",
        { role: "group", "aria-label": "크기", class: "flex flex-wrap gap-0.5" },
        presets.map((p) =>
          h("button", {
            type: "button",
            class: BUTTON,
            "aria-pressed": String(currentWidth === p.width),
            disabled: kind === "image" && p.width > natural.width,
            title: `폭 ${p.width}px`,
            text: p.label,
            onclick: () => opts.onResize(p.width),
          }),
        ),
      ),
      h("label", { for: widthId, class: "ml-1 text-xs text-muted", text: "폭(px)" }),
      widthInput,
      h("span", { class: "mx-1 h-6 w-px bg-line", "aria-hidden": "true" }),
      ...actions,
      deleteButton,
    ],
  );
  // 버튼 클릭이 편집 영역 선택을 바꾸지 않도록 (입력칸은 포커스가 필요하다).
  toolbar.addEventListener("mousedown", (e) => {
    if (!(e.target instanceof HTMLInputElement)) e.preventDefault();
  });

  // ---------- 배치 ----------
  function render() {
    if (!box) return;
    frame.hidden = false;
    toolbar.hidden = false;
    placeBox(frame, {
      left: box.left,
      top: box.top,
      width: preview?.width ?? box.width,
      height: preview?.height ?? box.height,
    });
    sizeBadge.hidden = !preview;
    if (preview) sizeBadge.textContent = `${preview.width} × ${preview.height}`;
    const above = box.top > 64;
    toolbar.classList.toggle("-translate-y-full", above);
    placeBox(toolbar, {
      left: Math.max(0, Math.min(box.left, box.containerWidth - TOOLBAR_WIDTH)),
      top: above ? box.top - 8 : box.top + box.height + 8,
    });
  }

  let frameId = 0;
  const measure = () => {
    cancelAnimationFrame(frameId);
    frameId = requestAnimationFrame(() => {
      const t = target.getBoundingClientRect();
      const c = container.getBoundingClientRect();
      box = { containerWidth: c.width, left: t.left - c.left, top: t.top - c.top, width: t.width, height: t.height };
      render();
    });
  };
  const ro = typeof ResizeObserver === "function" ? new ResizeObserver(measure) : null;
  ro?.observe(target);
  ro?.observe(container);
  window.addEventListener("resize", measure);
  window.addEventListener("scroll", measure, true);
  target.addEventListener("load", measure);
  container.append(frame, toolbar);
  measure();

  return {
    destroy() {
      cancelAnimationFrame(frameId);
      ro?.disconnect();
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      target.removeEventListener("load", measure);
      frame.remove();
      toolbar.remove();
    },
  };
}
