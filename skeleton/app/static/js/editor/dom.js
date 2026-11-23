// 편집기 화면 조립 도우미 — innerHTML 없이 요소를 만든다.
// ⛔ style 속성을 쓰지 않는다(CSP style-src 'self'). 위치·크기는 el.style.<속성>(CSSOM)으로만 바꾼다.

/**
 * 요소 생성. props: class·text·dataset·on<이벤트>(함수)·그 밖의 속성(true 면 빈 값, false·null 이면 생략).
 * children 은 Node·문자열(텍스트 노드)·그 배열이다.
 */
export function h(tag, props = {}, children = []) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value);
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : String(child));
  }
  return el;
}

let idSeq = 0;
/** 문서 안에서 겹치지 않는 id. */
export function uid(prefix) {
  idSeq += 1;
  return `${prefix}-${idSeq}`;
}

/** 위치·크기(px)를 CSSOM 으로 지정한다. 값이 null 이면 그 속성을 지운다. */
export function placeBox(el, box) {
  for (const key of ["left", "top", "width", "height"]) {
    if (!(key in box)) continue;
    const value = box[key];
    if (value === null || value === undefined) el.style.removeProperty(key);
    else el.style.setProperty(key, `${value}px`);
  }
}
