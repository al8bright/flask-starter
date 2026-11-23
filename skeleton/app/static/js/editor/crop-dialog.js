// 자르기·회전 대화상자 — 형제 템플릿 components/editor/ImageCropDialog.tsx 와 대응한다.
// - 미리보기 위에서 드래그로 선택 영역을 만들고, 모서리·변 핸들로 크기를, 내부 드래그로 위치를 바꾼다.
// - 회전은 자르기보다 먼저 적용된다(선택 영역은 회전한 이미지 좌표계). 회전하면 선택을 초기화한다.
// - 표시 좌표 → 원본 좌표로 환산한 뒤 clampCrop 으로 정수·경계를 맞춰 onApply({crop, rotate}) 에 넘긴다.
import { BUTTON, BUTTON_PRIMARY, openDialog } from "./dialog.js";
import { h, placeBox } from "./dom.js";
import { icon } from "./icons.js";
import { decodeImage, drawPreview, releaseImage, sizeOf } from "./image-canvas.js";
import {
  centeredCrop,
  clampCrop,
  CROP_RATIOS,
  displayToSource,
  dragCrop,
  normalizeRotation,
  previewScale,
  rotatedSize,
} from "./image-transform.js";

const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
const HANDLE_POS = {
  nw: "left-0 top-0 cursor-nwse-resize",
  n: "left-1/2 top-0 cursor-ns-resize",
  ne: "left-full top-0 cursor-nesw-resize",
  e: "left-full top-1/2 cursor-ew-resize",
  se: "left-full top-full cursor-nwse-resize",
  s: "left-1/2 top-full cursor-ns-resize",
  sw: "left-0 top-full cursor-nesw-resize",
  w: "left-0 top-1/2 cursor-ew-resize",
};
const RATIO_ACTIVE = ["border-accent", "bg-accent", "text-white", "hover:bg-accent"];

/**
 * 자르기 대화상자를 연다.
 * mode: "insert"(새 이미지 — "그대로 넣기" 제공) | "recrop"(이미 넣은 이미지 다시 자르기)
 * onApply({crop: Rect|null, rotate}) · onSkip() · onCancel()
 */
export function openCropDialog({ file, mode, onApply, onSkip, onCancel }) {
  let image = null;
  let rotate = 0;
  let ratio = null;
  let selection = null;
  let geometry = null;
  let drag = null;
  let disposed = false;
  // 미리보기 상자 — 대화상자를 여는 시점의 화면 크기 기준.
  const frameBox = {
    width: Math.max(200, Math.min(720, window.innerWidth - 80)),
    height: Math.max(160, Math.min(440, window.innerHeight - 300)),
  };

  // ---------- 요소 ----------
  const ratioButtons = CROP_RATIOS.map((r) =>
    h("button", { type: "button", class: BUTTON, "aria-pressed": "false", text: r.label, onclick: () => chooseRatio(r.value) }),
  );
  const rotateLeft = h("button", { type: "button", class: BUTTON, "aria-label": "왼쪽으로 90° 회전", disabled: true, onclick: () => rotateBy(-90) }, [
    icon("rotateLeft"),
  ]);
  const rotateRight = h("button", { type: "button", class: BUTTON, "aria-label": "오른쪽으로 90° 회전", disabled: true, onclick: () => rotateBy(90) }, [
    icon("rotateRight"),
  ]);
  const status = h("p", { role: "status", class: "text-sm text-muted", text: "이미지를 불러오는 중…" });
  const canvas = h("canvas", { class: "block h-full w-full", "aria-label": "자르기 미리보기", role: "img" });
  const cropBox = h(
    "div",
    {
      "data-crop-box": "",
      tabindex: "0",
      role: "group",
      class: "absolute cursor-move border-2 border-white shadow-[0_0_0_9999px_rgb(0_0_0/0.5)] outline-none focus-visible:border-accent",
      hidden: true,
    },
    HANDLES.map((handle) =>
      h("span", {
        "data-handle": handle,
        "aria-hidden": "true",
        class: `absolute h-6 w-6 -translate-x-1/2 -translate-y-1/2 after:absolute after:inset-[7px] after:rounded-sm after:border after:border-accent after:bg-white ${HANDLE_POS[handle]}`,
      }),
    ),
  );
  const stage = h("div", { class: "relative touch-none select-none overflow-hidden", hidden: true }, [canvas, cropBox]);
  const applyButton = h("button", { type: "button", class: BUTTON_PRIMARY, text: "적용", disabled: true, onclick: apply });

  const dialog = openDialog({
    title: mode === "insert" ? "이미지 자르기" : "이미지 다시 자르기",
    wide: true,
    onClose: () => {
      dispose();
      onCancel();
    },
    content: [
      h("p", { class: "mt-1 text-sm text-muted", text: "드래그해서 남길 영역을 고르세요. 고르지 않으면 이미지 전체를 씁니다." }),
      h("div", { class: "mt-3 flex flex-wrap items-center gap-2" }, [
        h("div", { role: "group", "aria-label": "자르기 비율", class: "flex flex-wrap gap-1" }, ratioButtons),
        h("div", { class: "ml-auto flex gap-1" }, [rotateLeft, rotateRight]),
      ]),
      h("div", { class: "mt-3 flex min-h-40 items-center justify-center rounded-md bg-surface p-2" }, [status, stage]),
      h("div", { class: "mt-5 flex flex-wrap justify-end gap-2" }, [
        h("button", { type: "button", class: BUTTON, text: "취소", onclick: () => dialog.dismiss() }),
        mode === "insert" && onSkip
          ? h("button", {
              type: "button",
              class: BUTTON,
              text: "그대로 넣기",
              onclick: () => {
                finish();
                onSkip();
              },
            })
          : null,
        applyButton,
      ]),
    ],
  });

  function dispose() {
    disposed = true;
    releaseImage(image);
    image = null;
  }
  function finish() {
    dialog.close();
    dispose();
  }

  // ---------- 상태 반영 ----------
  function computeGeometry() {
    if (!image) return null;
    const natural = rotatedSize(sizeOf(image), rotate);
    const scale = previewScale(natural, frameBox.width, frameBox.height);
    return { natural, scale, display: { width: Math.round(natural.width * scale), height: Math.round(natural.height * scale) } };
  }

  function renderRatio() {
    CROP_RATIOS.forEach((r, i) => {
      const active = ratio === r.value;
      ratioButtons[i].setAttribute("aria-pressed", String(active));
      ratioButtons[i].classList.toggle(RATIO_ACTIVE[0], active);
      for (const cls of RATIO_ACTIVE.slice(1)) ratioButtons[i].classList.toggle(cls, active);
    });
  }

  function renderSelection() {
    if (!selection || !geometry) {
      cropBox.hidden = true;
      return;
    }
    cropBox.hidden = false;
    placeBox(cropBox, { left: selection.x, top: selection.y, width: selection.width, height: selection.height });
    cropBox.setAttribute(
      "aria-label",
      `자르기 영역 ${Math.round(selection.width / geometry.scale)}×${Math.round(selection.height / geometry.scale)}px — 화살표로 이동, Shift+화살표로 크기 조절`,
    );
  }

  function renderStage() {
    geometry = computeGeometry();
    if (!geometry || !image) return;
    status.hidden = true;
    stage.hidden = false;
    placeBox(stage, { width: geometry.display.width, height: geometry.display.height });
    drawPreview(canvas, image, rotate, geometry.display);
    renderSelection();
  }

  // ---------- 동작 ----------
  function chooseRatio(value) {
    ratio = value;
    if (value && geometry) selection = centeredCrop(geometry.display, value);
    renderRatio();
    renderSelection();
  }

  function rotateBy(deg) {
    rotate = normalizeRotation(rotate + deg);
    // 회전하면 좌표계가 바뀐다 — 선택을 지운다(비율이 있으면 적용 시 가운데 영역을 쓴다).
    selection = null;
    renderStage();
  }

  function apply() {
    const g = geometry;
    finish();
    if (!g) {
      onApply({ crop: null, rotate });
      return;
    }
    const sel = selection ?? (ratio ? centeredCrop(g.display, ratio) : null);
    const crop = sel ? clampCrop(displayToSource(sel, g.scale), g.natural, ratio) : null;
    const isFull = crop && crop.x === 0 && crop.y === 0 && crop.width === g.natural.width && crop.height === g.natural.height;
    onApply({ crop: isFull ? null : crop, rotate });
  }

  const pointFrom = (e) => {
    const rect = stage.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  stage.addEventListener("pointerdown", (e) => {
    if (!geometry || e.button !== 0) return;
    const t = e.target;
    const handle = t instanceof HTMLElement ? t.dataset.handle : undefined;
    const base = { originX: e.clientX, originY: e.clientY, pointerId: e.pointerId };
    if (handle && selection) {
      drag = { mode: handle, start: selection, ...base };
    } else if (t === cropBox && selection) {
      drag = { mode: "move", start: selection, ...base };
    } else {
      // 빈 곳에서 새로 그린다 — 0 크기 사각형의 se 핸들을 끄는 것과 같다.
      const p = pointFrom(e);
      const start = { x: p.x, y: p.y, width: 0, height: 0 };
      drag = { mode: "se", start, ...base };
      selection = dragCrop(start, "se", 0, 0, geometry.display, ratio, 0);
      renderSelection();
    }
    e.preventDefault();
    stage.setPointerCapture?.(e.pointerId);
  });
  stage.addEventListener("pointermove", (e) => {
    if (!drag || drag.pointerId !== e.pointerId || !geometry) return;
    selection = dragCrop(
      drag.start,
      drag.mode,
      e.clientX - drag.originX,
      e.clientY - drag.originY,
      geometry.display,
      ratio,
      drag.start.width === 0 ? 0 : 8,
    );
    renderSelection();
  });
  const endDrag = (e) => {
    if (!drag || drag.pointerId !== e.pointerId) return;
    drag = null;
    stage.releasePointerCapture?.(e.pointerId);
    // 클릭만 한 경우(아주 작은 영역)는 선택 해제 = 전체.
    if (selection && (selection.width < 4 || selection.height < 4)) selection = null;
    renderSelection();
  };
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);

  // 키보드: 화살표 이동, Shift+화살표 크기 조절.
  cropBox.addEventListener("keydown", (e) => {
    if (!selection || !geometry) return;
    const step = 10;
    const deltas = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const d = deltas[e.key];
    if (!d) return;
    e.preventDefault();
    selection = dragCrop(selection, e.shiftKey ? "se" : "move", d[0], d[1], geometry.display, ratio);
    renderSelection();
  });

  renderRatio();
  decodeImage(file).then(
    (img) => {
      if (disposed) {
        releaseImage(img);
        return;
      }
      image = img;
      rotateLeft.disabled = false;
      rotateRight.disabled = false;
      applyButton.disabled = false;
      renderStage();
    },
    () => {
      if (disposed) return;
      status.setAttribute("role", "alert");
      status.className = "text-sm text-danger";
      status.textContent = `이미지를 읽을 수 없습니다.${mode === "insert" ? " 그대로 넣기를 눌러 원본을 올릴 수 있습니다." : ""}`;
    },
  );
  return dialog;
}
