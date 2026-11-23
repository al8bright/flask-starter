// 공지 본문 위지웍 편집기 (ARCHITECTURE.md §13) — 형제 템플릿 components/editor/RichTextEditor.tsx 를 옮긴 것이다.
// contentEditable + execCommand, 라이브러리 없음. 진입점: <textarea data-rich-editor data-upload-url data-max-image-mb>.
//
// - 점진적 향상: JS 가 없으면 textarea 에 HTML 을 직접 쓴다. 편집기가 붙으면 textarea 와 [data-editor-fallback] 을 숨기고,
//   변경마다 직렬화한 HTML 을 textarea 에 넣는다 — 폼 제출은 그대로 textarea 값을 보낸다.
// - 입력 중에는 innerHTML 을 다시 쓰지 않는다(캐럿·undo 스택 보존).
// - 저장 전 정화는 서버 서비스 계층의 sanitize_html 몫이다 — 편집기는 정화하지 않는다.
// - 이미지 업로드 중에는 폼 제출을 막는다(자리표시는 직렬화에서 빠지므로 이미지가 빠진 본문이 저장된다).
import { openCropDialog } from "./crop-dialog.js";
import { promptDialog } from "./dialog.js";
import { h, uid } from "./dom.js";
import {
  applyLink,
  caretAfter,
  clearFormatting,
  closestLink,
  decorateEditable,
  deleteNode,
  exec,
  insertHtmlAt,
  isAtDocumentEnd,
  rangeAtEnd,
  rangeFromPoint,
  readActiveState,
  removeLink,
  replaceNode,
  selectionRangeIn,
  selectRange,
  setBlock,
  toggleAlign,
  toggleMark,
} from "./editor-dom.js";
import { transformImage } from "./image-canvas.js";
import { sizeForWidth, videoSizeForWidth } from "./image-transform.js";
import { createMediaOverlay } from "./media-overlay.js";
import { extractYoutubeId, imageHtml, serializeEditorHtml, youtubeEmbedHtml, youtubeIdFromEmbedSrc } from "./media-html.js";
import {
  cleanPastedHtml,
  EDITOR_IMAGE_TYPES,
  editorImageProblem,
  escapeHtml,
  isRichTextEmpty,
  normalizeLinkUrl,
  plainTextToHtml,
} from "./rich-text.js";
import { createToolbar } from "./toolbar.js";
import { uploadEditorImage } from "./upload.js";

const ACCEPT = EDITOR_IMAGE_TYPES.join(",");
const BLANK_GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
const RECROP_ERROR = "이 이미지는 다시 자를 수 없습니다. 새로 올려 주세요.";
const BUSY_SUBMIT_ERROR = "이미지를 올리는 중입니다. 끝난 뒤 저장하세요.";

let uploadSeq = 0;

/** 커밋 마크업에 선택 표식을 붙여, 치환 뒤 새 노드를 다시 찾는다(직렬화 때 제거됨). */
const withSelectedMarker = (html) => html.replace(/^<(\w+)/, '<$1 data-selected="true"');

function imageNatural(img) {
  const attrW = Number.parseInt(img.getAttribute("width") ?? "", 10);
  const attrH = Number.parseInt(img.getAttribute("height") ?? "", 10);
  const width = img.naturalWidth || attrW || 0;
  const height = img.naturalHeight || attrH || 0;
  return width > 0 && height > 0 ? { width, height } : { width: 1600, height: 900 };
}

function currentWidthOf(sel) {
  const el = sel.kind === "image" ? sel.el : sel.el.querySelector("iframe");
  const attr = Number.parseInt(el?.getAttribute("width") ?? "", 10);
  if (Number.isFinite(attr) && attr > 0) return attr;
  return sel.kind === "image" ? imageNatural(sel.el).width : 640;
}

function imageFilesFrom(data) {
  if (!data) return [];
  const files = Array.from(data.files ?? []).filter((f) => f.type.startsWith("image/"));
  if (files.length) return files;
  return Array.from(data.items ?? [])
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter((f) => f !== null);
}

function filenameFromUrl(src) {
  try {
    return decodeURIComponent(new URL(src, window.location.href).pathname.split("/").pop() || "image");
  } catch {
    return "image";
  }
}

class RichTextEditor {
  constructor(textarea) {
    this.textarea = textarea;
    this.form = textarea.form;
    this.uploadUrl = textarea.dataset.uploadUrl;
    this.maxImageMb = Number.parseInt(textarea.dataset.maxImageMb ?? "5", 10) || 5;
    this.selected = null; // {el, kind: "image"|"video"}
    this.overlay = null;
    this.savedRange = null;
    this.pendingRange = null;
    this.replaceTarget = null;
    this.uploading = 0;
    this.lastHtml = null;
    // 이 세션에서 올린 이미지의 원본 — 다시 자르기에 쓴다(서버 재인코딩본 대신 원본 화질).
    this.originals = new Map();
    this.build();
    this.bind();
  }

  // ---------- 화면 ----------

  build() {
    const ta = this.textarea;
    const editorId = uid("rich-editor");
    this.errorId = uid("rich-editor-error");
    const label = ta.id ? document.querySelector(`label[for="${CSS.escape(ta.id)}"]`) : null;
    if (label && !label.id) label.id = uid("rich-editor-label");

    this.toolbar = createToolbar({ controlsId: editorId, onCommand: (c) => this.runCommand(c) });
    this.area = h("div", {
      id: editorId,
      class: "editor rich-text min-h-60 px-4 py-3 text-ink outline-none",
      contenteditable: "true",
      role: "textbox",
      "aria-multiline": "true",
      "aria-labelledby": label?.id ?? null,
      "aria-label": label ? null : "본문",
      "data-placeholder": ta.getAttribute("placeholder") || "내용을 입력하세요",
      spellcheck: "true",
    });
    this.wrapper = h("div", { class: "relative" }, [this.area]);
    this.statusText = h("p", { role: "status", class: "text-sm text-muted", hidden: true });
    this.errorText = h("span");
    this.errorBox = h(
      "div",
      { id: this.errorId, role: "alert", class: "flex items-center justify-between gap-2 rounded-md bg-danger/10 px-3 py-2 text-sm text-danger", hidden: true },
      [
        this.errorText,
        h("button", { type: "button", class: "min-h-11 min-w-11 rounded-md font-medium hover:underline", "aria-label": "오류 닫기", text: "닫기", onclick: () => this.setError(null) }),
      ],
    );
    this.footer = h("div", { class: "space-y-1 border-t border-line px-3 py-2", hidden: true }, [this.statusText, this.errorBox]);
    this.fileInput = h("input", { type: "file", accept: ACCEPT, multiple: true, hidden: true, "aria-label": "이미지 파일 선택" });
    this.replaceInput = h("input", { type: "file", accept: ACCEPT, hidden: true, "aria-label": "교체할 이미지 파일 선택" });
    this.root = h("div", { class: "mt-1 rounded-md border border-line bg-panel focus-within:border-accent", "data-rich-editor-root": "" }, [
      this.toolbar.el,
      this.wrapper,
      this.footer,
      this.fileInput,
      this.replaceInput,
    ]);

    const initial = ta.value;
    this.area.innerHTML = initial && initial.trim() ? initial : "<p><br></p>";
    decorateEditable(this.area);
    this.lastHtml = serializeEditorHtml(this.area.innerHTML);
    this.updateEmpty();

    ta.hidden = true;
    ta.after(this.root);
    // JS 가 있을 때는 필요 없는 안내(HTML 직접 입력·이미지 코드 붙여 넣기)를 숨긴다.
    this.form?.parentElement?.querySelectorAll("[data-editor-fallback]").forEach((el) => {
      el.hidden = true;
    });
    // 라벨을 누르면 숨긴 textarea 대신 편집 영역으로 간다.
    label?.addEventListener("click", (e) => {
      e.preventDefault();
      this.focusEditor();
    });
  }

  bind() {
    const area = this.area;
    area.addEventListener("input", () => {
      decorateEditable(area);
      this.emitChange();
    });
    area.addEventListener("paste", (e) => this.onPaste(e));
    area.addEventListener("dragover", (e) => {
      if (Array.from(e.dataTransfer?.types ?? []).includes("Files")) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }
    });
    area.addEventListener("drop", (e) => this.onDrop(e));
    area.addEventListener("click", (e) => this.onClick(e));
    area.addEventListener("keydown", (e) => this.onKeyDown(e));
    area.addEventListener("focus", () => {
      // 편집 명령 기본값: 문단 구분자 <p>, 서식은 태그로(style 금지).
      exec("defaultParagraphSeparator", "p");
      exec("styleWithCSS", "false");
    });

    // 선택 변화 — 도구 모음 활성 상태, 마지막 선택 위치 저장, 미디어 선택 해제.
    document.addEventListener("selectionchange", () => {
      const range = selectionRangeIn(area);
      if (!range) return;
      this.savedRange = range;
      this.toolbar.update(readActiveState(area));
      if (this.selected) {
        const el = this.selected.el;
        if (!(range.intersectsNode(el) || el.contains(range.startContainer))) this.setSelected(null);
      }
    });
    // 미디어 선택 중 편집기 바깥을 누르면 해제(오버레이·대화상자 안은 제외).
    document.addEventListener("mousedown", (e) => {
      if (!this.selected) return;
      const t = e.target;
      if (this.wrapper.contains(t)) return;
      if (t instanceof Element && t.closest("[role=dialog]")) return;
      this.setSelected(null);
    });

    this.fileInput.addEventListener("change", () => {
      const files = Array.from(this.fileInput.files ?? []);
      this.fileInput.value = "";
      this.handleFiles(files, this.pendingRange);
    });
    this.replaceInput.addEventListener("change", () => {
      const file = this.replaceInput.files?.[0];
      this.replaceInput.value = "";
      const target = this.replaceTarget;
      this.replaceTarget = null;
      if (file && target) void this.finishReplace(target, file);
    });

    // 업로드 중 저장 방지 + 제출 직전 동기화.
    this.form?.addEventListener(
      "submit",
      (e) => {
        if (this.uploading > 0) {
          e.preventDefault();
          e.stopImmediatePropagation();
          this.setError(BUSY_SUBMIT_ERROR);
          return;
        }
        this.textarea.value = serializeEditorHtml(this.area.innerHTML);
      },
      true,
    );
  }

  // ---------- 상태 ----------

  updateEmpty() {
    const empty = isRichTextEmpty(this.area.innerHTML) && !this.area.querySelector("hr, table");
    if (empty) this.area.dataset.empty = "true";
    else delete this.area.dataset.empty;
  }

  /** 직렬화해 textarea 에 넣는다 — 이전 값과 같으면 건너뛴다. 모든 변경 경로가 이 함수로 모인다. */
  emitChange() {
    const html = serializeEditorHtml(this.area.innerHTML);
    this.updateEmpty();
    // 선택했던 노드가 문서에서 빠졌으면 선택만 비운다. 표식(data-selected)은 건드리지 않는다 —
    // insertHTML 은 input 이벤트를 동기로 내므로, 치환 직후 여기서 표식을 지우면 reselectMarked 가 새 노드를 못 찾는다.
    if (this.selected && !this.selected.el.isConnected) {
      this.selected = null;
      this.renderOverlay();
    }
    if (html !== this.lastHtml) {
      this.lastHtml = html;
      this.textarea.value = html;
      this.textarea.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  setError(message) {
    this.errorText.textContent = message ?? "";
    this.errorBox.hidden = !message;
    if (message) this.area.setAttribute("aria-describedby", this.errorId);
    else this.area.removeAttribute("aria-describedby");
    this.renderFooter();
  }

  setUploading(delta) {
    this.uploading += delta;
    this.statusText.hidden = this.uploading <= 0;
    this.statusText.textContent = this.uploading > 0 ? `이미지 올리는 중… (${this.uploading})` : "";
    // 업로드가 끝나기 전에는 저장 버튼을 막는다(제출 이벤트에서도 한 번 더 막는다).
    this.form?.querySelectorAll('button:not([type]), button[type="submit"]').forEach((b) => {
      b.disabled = this.uploading > 0;
    });
    this.renderFooter();
  }

  renderFooter() {
    this.footer.hidden = this.statusText.hidden && this.errorBox.hidden;
  }

  /** 미디어 선택 상태와 오버레이를 갱신한다. sel: {el, kind} 또는 null. */
  setSelected(sel) {
    this.selected = sel;
    this.area.querySelectorAll("[data-selected]").forEach((n) => {
      if (n !== sel?.el) n.removeAttribute("data-selected");
    });
    sel?.el.setAttribute("data-selected", "true");
    this.renderOverlay();
  }

  renderOverlay() {
    this.overlay?.destroy();
    this.overlay = null;
    const sel = this.selected;
    if (!sel) return;
    const isImage = sel.kind === "image";
    const src = isImage ? (sel.el.getAttribute("src") ?? "") : "";
    this.overlay = createMediaOverlay({
      kind: sel.kind,
      target: sel.el,
      container: this.wrapper,
      natural: isImage ? imageNatural(sel.el) : { width: 1280, height: 720 },
      currentWidth: currentWidthOf(sel),
      canRecrop: isImage && !/\.gif(?:$|\?)/i.test(src),
      onResize: (w) => this.resizeSelected(w),
      onDelete: () => this.deleteSelected(),
      onAltText: () => this.openAltDialog(sel.el),
      onRecrop: () => void this.startRecrop(sel.el),
      onReplace: () => {
        this.replaceTarget = sel.el;
        this.replaceInput.click();
      },
      onChangeLink: () => {
        const id = youtubeIdFromEmbedSrc(sel.el.querySelector("iframe")?.getAttribute("src"));
        this.openYoutubeDialog(null, sel.el, id ? `https://www.youtube.com/watch?v=${id}` : "");
      },
    });
  }

  editorHasFocus() {
    return Boolean(document.activeElement && this.area.contains(document.activeElement));
  }

  /** 포커스를 편집 영역으로 되돌리고 마지막 선택을 복원한다(도구 모음·대화상자에서 돌아올 때). */
  focusEditor(range = this.savedRange) {
    if (!this.editorHasFocus()) this.area.focus({ preventScroll: true });
    if (range && this.area.contains(range.commonAncestorContainer)) selectRange(range);
  }

  /**
   * 사용자의 현재 선택을 보존하며 노드를 치환/삭제한다(업로드 완료 등 비동기 커밋).
   * 편집 영역에 포커스가 없으면 execCommand 가 포커스를 빼앗지 않도록 DOM 직접 치환으로 처리한다.
   */
  commitAsync(fn) {
    const keep = this.editorHasFocus() ? selectionRangeIn(this.area) : null;
    const focused = document.activeElement;
    fn();
    if (keep && this.area.contains(keep.startContainer)) selectRange(keep);
    else if (!keep && focused instanceof HTMLElement && focused !== document.body && !this.area.contains(focused)) {
      focused.focus({ preventScroll: true });
    }
    decorateEditable(this.area);
    this.emitChange();
  }

  // 포커스 여부에 따라 exec(undo 가능) 또는 직접 치환.
  replaceNodeCommitted(node, html) {
    replaceNode(node, html, !this.editorHasFocus());
  }

  removeNodeCommitted(node) {
    deleteNode(node, !this.editorHasFocus());
  }

  selectMedia(node) {
    if (!node) {
      this.setSelected(null);
      return;
    }
    const range = document.createRange();
    range.selectNode(node);
    selectRange(range);
    this.setSelected({ el: node, kind: node.matches("img") ? "image" : "video" });
  }

  /** 치환 커밋 후 표식으로 새 노드를 찾아 다시 선택한다. */
  reselectMarked() {
    const next = this.area.querySelector("[data-selected]");
    if (next) this.selectMedia(next);
    else this.setSelected(null);
  }

  // ---------- 이미지 업로드 ----------

  async safeUpload(blob, filename) {
    try {
      return await uploadEditorImage(this.uploadUrl, blob, filename, this.maxImageMb);
    } catch {
      return { error: "이미지를 올리지 못했습니다. 잠시 후 다시 시도해 주세요." };
    }
  }

  async prepare(file, edit) {
    try {
      return await transformImage(file, { crop: edit?.crop ?? null, rotate: edit?.rotate ?? 0 });
    } catch {
      return { blob: file, filename: file.name || "image" };
    }
  }

  /** 자리표시를 넣고 각 파일을 변환·업로드한 뒤 결과로 치환(실패 시 제거 + 오류). items: [{file, edit}] */
  insertUploads(items, range) {
    const el = this.area;
    if (!items.length) return;
    const entries = items.map((item) => {
      uploadSeq += 1;
      const id = `u${Date.now().toString(36)}${uploadSeq}`;
      const preview = typeof URL.createObjectURL === "function" ? URL.createObjectURL(item.file) : BLANK_GIF;
      return { ...item, id, preview };
    });
    const placeholders = entries.map((e) => `<img data-uploading="${e.id}" src="${escapeHtml(e.preview)}" alt="업로드 중">`).join("");
    const target = range && el.contains(range.commonAncestorContainer) ? range : rangeAtEnd(el);
    // 편집 영역 바로 아래(문단 밖)에 들어가면 문단으로 감싼다.
    const html = target.startContainer === el ? `<p>${placeholders}</p>` : placeholders;
    this.focusEditor(target);
    insertHtmlAt(el, target, html);
    decorateEditable(el);
    this.emitChange();
    this.setError(null);

    for (const entry of entries) {
      this.setUploading(1);
      void (async () => {
        const prepared = await this.prepare(entry.file, entry.edit);
        const result = await this.safeUpload(prepared.blob, prepared.filename);
        if (entry.preview.startsWith("blob:")) URL.revokeObjectURL(entry.preview);
        this.setUploading(-1);
        const placeholder = el.querySelector(`img[data-uploading="${entry.id}"]`);
        if ("error" in result) {
          this.setError(result.error);
          if (placeholder) this.commitAsync(() => this.removeNodeCommitted(placeholder));
          return;
        }
        this.originals.set(result.url, entry.file);
        // 사용자가 업로드 중 자리표시를 지웠으면 넣지 않는다.
        if (!placeholder) return;
        const markup = imageHtml({ src: result.url, alt: "", width: result.width, height: result.height });
        this.commitAsync(() => this.replaceNodeCommitted(placeholder, markup));
      })();
    }
  }

  /** 버튼·붙여넣기·드롭으로 들어온 파일 처리 — 사전 검사 후 1장(GIF 제외)이면 자르기 대화상자. */
  handleFiles(files, range) {
    const valid = [];
    let problem = null;
    for (const file of files) {
      const p = editorImageProblem(file, this.maxImageMb * 1024 * 1024);
      if (p) problem ??= p;
      else valid.push(file);
    }
    this.setError(problem);
    if (!valid.length) return;
    if (valid.length === 1 && valid[0].type !== "image/gif") {
      const file = valid[0];
      openCropDialog({
        file,
        mode: "insert",
        onApply: (edit) => this.insertUploads([{ file, edit }], range),
        onSkip: () => this.insertUploads([{ file, edit: null }], range),
        onCancel: () => {},
      });
      return;
    }
    // 여러 장은 대화상자 없이 전부 "그대로 넣기".
    this.insertUploads(
      valid.map((file) => ({ file, edit: null })),
      range,
    );
  }

  /** 다시 자르기 — 세션 원본 또는 fetch(src). 결과는 새 파일로 업로드 후 src 교체. */
  async startRecrop(img) {
    const src = img.getAttribute("src") ?? "";
    let file = this.originals.get(src) ?? null;
    if (!file) {
      try {
        const res = await fetch(src, { credentials: "same-origin" });
        if (!res.ok) throw new Error(String(res.status));
        const blob = await res.blob();
        if (!blob.type.startsWith("image/")) throw new Error(blob.type);
        file = new File([blob], filenameFromUrl(src), { type: blob.type });
      } catch {
        // 외부 이미지는 CSP(connect-src 'self')로 가져올 수 없다 — 새로 올리도록 안내한다.
        this.setError(RECROP_ERROR);
        return;
      }
    }
    if (file.type === "image/gif") {
      this.setError("GIF 이미지는 자를 수 없습니다.");
      return;
    }
    const source = file;
    openCropDialog({
      file: source,
      mode: "recrop",
      onApply: (edit) => void this.finishRecrop(img, source, edit),
      onCancel: () => {},
    });
  }

  async finishRecrop(target, file, edit) {
    this.setUploading(1);
    const prepared = await this.prepare(file, edit);
    const result = await this.safeUpload(prepared.blob, prepared.filename);
    this.setUploading(-1);
    if ("error" in result) {
      this.setError(result.error);
      return;
    }
    this.originals.set(result.url, file);
    if (!target.isConnected) return;
    const keepWidth = Number.parseInt(target.getAttribute("width") ?? "", 10);
    const size = sizeForWidth(result, Number.isFinite(keepWidth) ? keepWidth : result.width);
    const markup = imageHtml({ src: result.url, alt: target.getAttribute("alt") ?? "", ...size });
    this.commitAsync(() => this.replaceNodeCommitted(target, markup));
    this.setSelected(null);
  }

  async finishReplace(target, file) {
    const problem = editorImageProblem(file, this.maxImageMb * 1024 * 1024);
    if (problem) {
      this.setError(problem);
      return;
    }
    this.setError(null);
    this.setUploading(1);
    const prepared = await this.prepare(file, null);
    const result = await this.safeUpload(prepared.blob, prepared.filename);
    this.setUploading(-1);
    if ("error" in result) {
      this.setError(result.error);
      return;
    }
    this.originals.set(result.url, file);
    if (!target.isConnected) return;
    const markup = imageHtml({ src: result.url, alt: target.getAttribute("alt") ?? "", width: result.width, height: result.height });
    this.commitAsync(() => this.replaceNodeCommitted(target, markup));
    this.setSelected(null);
  }

  // ---------- 미디어 커밋 (selectNode → insertHTML) ----------

  resizeSelected(width) {
    if (!this.selected) return;
    const { el, kind } = this.selected;
    let html = null;
    if (kind === "image") {
      const size = sizeForWidth(imageNatural(el), width);
      html = imageHtml({ src: el.getAttribute("src") ?? "", alt: el.getAttribute("alt") ?? "", ...size });
    } else {
      const id = youtubeIdFromEmbedSrc(el.querySelector("iframe")?.getAttribute("src"));
      if (id) html = youtubeEmbedHtml(id, videoSizeForWidth(width).width, true);
    }
    if (!html) return;
    this.focusEditor(null);
    replaceNode(el, withSelectedMarker(html));
    decorateEditable(this.area);
    this.reselectMarked();
    this.emitChange();
  }

  deleteSelected() {
    if (!this.selected) return;
    const el = this.selected.el;
    this.focusEditor(null);
    deleteNode(el);
    this.setSelected(null);
    this.emitChange();
  }

  // ---------- 도구 모음 ----------

  runCommand(command) {
    const el = this.area;
    const range = selectionRangeIn(el) ?? this.savedRange;
    if (command === "image") {
      this.pendingRange = range;
      this.fileInput.click();
      return;
    }
    if (command === "video") {
      this.openYoutubeDialog(range, null, "");
      return;
    }
    if (command === "link") {
      this.openLinkDialog(range);
      return;
    }
    this.focusEditor(range);
    exec("defaultParagraphSeparator", "p");
    exec("styleWithCSS", "false");
    switch (command) {
      case "undo":
      case "redo":
      case "bold":
      case "italic":
      case "underline":
        exec(command);
        break;
      case "p":
      case "h2":
      case "h3":
      case "blockquote":
        setBlock(el, command);
        break;
      case "strike":
        exec("strikeThrough");
        break;
      case "mark":
        this.setError(toggleMark(el));
        break;
      case "clear":
        clearFormatting(el);
        break;
      case "align-left":
      case "align-center":
      case "align-right":
        toggleAlign(el, command.replace("align-", ""));
        break;
      case "ul":
        exec("insertUnorderedList");
        break;
      case "ol":
        exec("insertOrderedList");
        break;
      case "hr":
        if (!exec("insertHorizontalRule")) insertHtmlAt(el, selectionRangeIn(el), "<hr>");
        break;
      case "unlink":
        removeLink(el);
        break;
      default:
        break;
    }
    decorateEditable(el);
    this.emitChange();
    this.toolbar.update(readActiveState(el));
  }

  // ---------- 편집 영역 이벤트 ----------

  onPaste(e) {
    const el = this.area;
    const data = e.clipboardData;
    if (!data) return;
    const html = data.getData("text/html");
    const text = data.getData("text/plain");
    const files = imageFilesFrom(data);
    const range = selectionRangeIn(el);
    // 워드·엑셀은 서식 HTML 과 함께 "그림" 표현을 같이 싣는다 — 글자가 있는 HTML 이면 HTML 을 우선한다.
    const htmlHasText = html ? !isRichTextEmpty(html.replace(/<img[^>]*>/gi, "")) : false;
    e.preventDefault();
    if (files.length && !htmlHasText) {
      this.handleFiles(files, range);
      return;
    }
    this.setSelected(null);
    if (html) {
      const cleaned = cleanPastedHtml(html);
      if (cleaned) insertHtmlAt(el, range, cleaned);
    } else if (text) {
      if (!/[\r\n]/.test(text)) {
        if (range) selectRange(range);
        if (!exec("insertText", text)) insertHtmlAt(el, range, escapeHtml(text));
      } else {
        insertHtmlAt(el, range, plainTextToHtml(text));
      }
    }
    decorateEditable(el);
    this.emitChange();
  }

  onDrop(e) {
    const el = this.area;
    const files = imageFilesFrom(e.dataTransfer);
    if (!files.length) {
      // 파일이 아니면(글자 끌어 옮기기 등) 브라우저 기본 동작 — 직렬화가 style 등을 지운다.
      if (Array.from(e.dataTransfer?.types ?? []).includes("Files")) e.preventDefault();
      return;
    }
    e.preventDefault();
    const point = rangeFromPoint(e.clientX, e.clientY);
    this.handleFiles(files, point && el.contains(point.startContainer) ? point : selectionRangeIn(el));
  }

  onClick(e) {
    const el = this.area;
    const target = e.target;
    if (!(target instanceof Element)) return;
    const img = target.closest("img");
    if (img && el.contains(img) && !img.hasAttribute("data-uploading")) {
      this.selectMedia(img);
      return;
    }
    const video = target.closest("[data-youtube-video]");
    if (video && el.contains(video)) {
      this.selectMedia(video);
      return;
    }
    if (this.selected) this.setSelected(null);
  }

  onKeyDown(e) {
    // 한글 등 IME 조합 중에는 미디어 단축키를 처리하지 않는다(조합 확정 Enter 등).
    if (e.isComposing || !this.selected) return;
    const node = this.selected.el;
    const el = this.area;
    if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      this.deleteSelected();
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      caretAfter(node);
      this.setSelected(null);
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (this.selected.kind === "video") {
        const next = node.nextElementSibling;
        if (!(next && next.matches("p") && isRichTextEmpty(next.innerHTML))) {
          caretAfter(node);
          insertHtmlAt(el, selectionRangeIn(el), "<p><br></p>");
        }
        const p = node.nextElementSibling;
        if (p) {
          const r = document.createRange();
          r.setStart(p, 0);
          r.collapse(true);
          selectRange(r);
        }
      } else {
        caretAfter(node);
        if (!exec("insertParagraph")) insertHtmlAt(el, selectionRangeIn(el), "<p><br></p>");
      }
      this.setSelected(null);
      this.emitChange();
      return;
    }
    // 그 밖의 키: 선택을 풀고 캐럿을 미디어 뒤로 — 글자 입력이 미디어를 덮어쓰지 않게 한다.
    if (e.key.length === 1 || e.key.startsWith("Arrow")) {
      if (!e.key.startsWith("Arrow")) caretAfter(node);
      this.setSelected(null);
    }
  }

  // ---------- 대화상자 ----------

  openLinkDialog(range) {
    const initial = closestLink(range?.startContainer ?? null, this.area)?.getAttribute("href") ?? "";
    promptDialog({
      title: "링크 걸기",
      label: "링크 주소",
      inputType: "url",
      initialValue: initial,
      placeholder: "https://example.com",
      hint: "http·https·mailto·tel 링크를 넣을 수 있습니다.",
      validate: (v) => (normalizeLinkUrl(v) ? null : "http·https·mailto·tel 링크만 넣을 수 있습니다."),
      onSubmit: (v) => {
        const url = normalizeLinkUrl(v);
        if (!url) return;
        this.focusEditor(range);
        applyLink(this.area, range, url);
        this.emitChange();
      },
    });
  }

  openYoutubeDialog(range, target, initial) {
    promptDialog({
      title: target ? "영상 링크 바꾸기" : "유튜브 영상 넣기",
      label: "유튜브 링크",
      inputType: "url",
      initialValue: initial,
      placeholder: "https://www.youtube.com/watch?v=…",
      hint: "watch·youtu.be·shorts·embed 링크를 넣을 수 있습니다.",
      submitLabel: target ? "바꾸기" : "넣기",
      validate: (v) => (extractYoutubeId(v) ? null : "유튜브 링크만 넣을 수 있습니다."),
      onSubmit: (v) => this.submitYoutube(v, range, target),
    });
  }

  submitYoutube(value, range, target) {
    const el = this.area;
    const id = extractYoutubeId(value);
    if (!id) return;
    if (target && target.isConnected) {
      const width = Number.parseInt(target.querySelector("iframe")?.getAttribute("width") ?? "", 10);
      this.focusEditor(null);
      replaceNode(target, withSelectedMarker(youtubeEmbedHtml(id, Number.isFinite(width) ? width : undefined, true)));
      decorateEditable(el);
      this.reselectMarked();
      this.emitChange();
      return;
    }
    const at = range && el.contains(range.commonAncestorContainer) ? range : rangeAtEnd(el);
    const atEnd = isAtDocumentEnd(el, at);
    this.focusEditor(at);
    insertHtmlAt(el, at, youtubeEmbedHtml(id, undefined, true) + (atEnd ? "<p><br></p>" : ""));
    decorateEditable(el);
    this.emitChange();
  }

  openAltDialog(target) {
    promptDialog({
      title: "대체 텍스트",
      label: "이미지 설명",
      initialValue: target.getAttribute("alt") ?? "",
      hint: "화면 낭독기 사용자에게 읽어 줄 설명입니다. 장식용 이미지면 비워 두세요.",
      onSubmit: (v) => {
        if (!target.isConnected) return;
        const width = Number.parseInt(target.getAttribute("width") ?? "", 10);
        const height = Number.parseInt(target.getAttribute("height") ?? "", 10);
        this.focusEditor(null);
        replaceNode(target, withSelectedMarker(imageHtml({ src: target.getAttribute("src") ?? "", alt: v.trim(), width, height })));
        decorateEditable(this.area);
        this.reselectMarked();
        this.emitChange();
      },
    });
  }
}

/** textarea[data-rich-editor] 마다 편집기를 붙인다(한 번만). */
export function mountEditors(root = document) {
  root.querySelectorAll("textarea[data-rich-editor]").forEach((textarea) => {
    if (textarea.dataset.richEditorMounted) return;
    textarea.dataset.richEditorMounted = "true";
    textarea.richEditor = new RichTextEditor(textarea);
  });
}

// 모듈 스크립트는 문서 파싱 뒤에 실행된다(defer 와 같다).
mountEditors();
