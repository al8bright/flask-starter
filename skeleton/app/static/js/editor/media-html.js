// 미디어 마크업 템플릿·직렬화 — 형제 템플릿 lib/editor/mediaHtml.ts 와 대응한다. 저장 마크업은 이 파일 한 곳에서만 만든다.
//
// ⚠️ 마크업을 바꾸면 서버 app/core/sanitize.py 허용 목록·tests/test_editor.py 출력 계약을 같은 변경에서 고친다.
import { escapeAttr, parseFragment } from "./rich-text.js";
import { VIDEO_DEFAULT_WIDTH, videoSizeForWidth } from "./image-transform.js";

const YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{11}$/;
const YOUTUBE_HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
]);

const positiveInt = (v) => (typeof v === "number" && Number.isFinite(v) && v >= 1 ? Math.round(v) : null);

/** `<img src alt width height>` — 속성값은 모두 이스케이프한다. style 은 쓰지 않는다. */
export function imageHtml({ src, alt = "", width, height }) {
  const w = positiveInt(width);
  const h = positiveInt(height);
  let html = `<img src="${escapeAttr(src)}" alt="${escapeAttr(alt)}"`;
  if (w) html += ` width="${w}"`;
  if (h) html += ` height="${h}"`;
  return `${html}>`;
}

/** 유튜브 임베드 주소 — 쿼리 문자열을 붙이지 않는다(서버 정화기가 쿼리 있는 iframe 을 통째로 지운다). */
export function youtubeEmbedSrc(id) {
  if (!YOUTUBE_ID_RE.test(id)) throw new Error(`유효하지 않은 유튜브 ID: ${id}`);
  return `https://www.youtube-nocookie.com/embed/${id}`;
}

/**
 * 유튜브 임베드 저장 마크업. 폭은 [200,1280] 으로 맞추고 높이는 16:9.
 * editing=true 면 편집 중에만 쓰는 contenteditable="false" 를 래퍼에 붙인다(직렬화 때 제거).
 */
export function youtubeEmbedHtml(id, width = VIDEO_DEFAULT_WIDTH, editing = false) {
  const size = videoSizeForWidth(width);
  const ce = editing ? ' contenteditable="false"' : "";
  return (
    `<div class="video" data-youtube-video${ce}>` +
    `<iframe src="${youtubeEmbedSrc(id)}" width="${size.width}" height="${size.height}" title="YouTube 영상" allowfullscreen></iframe>` +
    `</div>`
  );
}

/**
 * 유튜브 링크에서 영상 ID(11자)를 뽑는다. 지원: `watch?v=`, `youtu.be/`, `shorts/`, `embed/`, `live/`.
 * 스킴이 없으면 https 로 간주한다. 그 외(다른 호스트·잘못된 ID)는 null.
 */
export function extractYoutubeId(input) {
  const value = input.trim();
  if (!value) return null;
  let url;
  try {
    url = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(value) ? value : `https://${value}`);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  const host = url.hostname.toLowerCase();
  const segments = url.pathname.split("/").filter(Boolean);
  let id = null;
  if (host === "youtu.be") {
    id = segments[0] ?? null;
  } else if (YOUTUBE_HOSTS.has(host)) {
    if (segments[0] === "watch") id = url.searchParams.get("v");
    else if (["shorts", "embed", "live", "v"].includes(segments[0] ?? "")) id = segments[1] ?? null;
  }
  return id && YOUTUBE_ID_RE.test(id) ? id : null;
}

/** iframe src 에서 유튜브 ID 를 다시 읽는다(링크 바꾸기·크기 조절 때 마크업 재생성용). */
export function youtubeIdFromEmbedSrc(src) {
  const m = /^https:\/\/www\.youtube(?:-nocookie)?\.com\/embed\/([A-Za-z0-9_-]{11})$/.exec(src ?? "");
  return m ? m[1] : null;
}

// 편집 중에만 붙는 속성 — 저장 HTML 에 남기지 않는다(브라우저 편집 명령이 만든 style 도 지운다).
const EDITOR_ONLY_ATTRS = ["contenteditable", "data-selected", "data-uploading", "draggable", "style"];
// execCommand 가 만드는 비표준 태그를 저장 표준 태그로 바꾼다(정화기는 둘 다 허용하지만 저장 형식을 하나로).
const CANONICAL_TAGS = { b: "strong", i: "em", strike: "s" };

/**
 * 편집 영역 innerHTML → 저장 HTML. 정화(sanitize)는 하지 않는다 — 서버 몫.
 * - 업로드 중 자리표시(`[data-uploading]`)는 통째로 제거한다(blob: 주소가 저장되지 않도록).
 *   그래서 업로드가 끝나기 전에 저장하면 그 이미지가 빠진다 — editor.js 가 업로드 중 제출을 막는다.
 * - contenteditable·data-selected·data-uploading·draggable·style 속성을 지운다.
 * - b·i·strike → strong·em·s, 속성 없는 span·font 는 껍데기를 벗긴다.
 * - 빈 문단만 남으면 빈 문자열을 돌려준다.
 */
export function serializeEditorHtml(html) {
  const template = parseFragment(html);
  const root = template.content;
  root.querySelectorAll("[data-uploading]").forEach((el) => el.remove());
  for (const el of Array.from(root.querySelectorAll("*"))) {
    for (const attr of EDITOR_ONLY_ATTRS) el.removeAttribute(attr);
  }
  // 깊은 요소부터 처리해야 바꾼 요소의 자식 참조가 끊기지 않는다.
  for (const el of Array.from(root.querySelectorAll("b, i, strike, span, font")).reverse()) {
    const tag = el.tagName.toLowerCase();
    const canonical = CANONICAL_TAGS[tag];
    if (canonical) {
      const next = document.createElement(canonical);
      for (const attr of Array.from(el.attributes)) next.setAttribute(attr.name, attr.value);
      while (el.firstChild) next.appendChild(el.firstChild);
      el.replaceWith(next);
    } else if (el.attributes.length === 0 || tag === "font") {
      el.replaceWith(...Array.from(el.childNodes));
    }
  }
  root.normalize();
  const out = template.innerHTML.trim();
  return /^(?:<p>(?:<br>)?<\/p>|<br>|\s)*$/.test(out) ? "" : out;
}
