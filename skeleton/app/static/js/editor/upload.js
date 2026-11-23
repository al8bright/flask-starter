// 편집기 이미지 업로드 — 형제 템플릿 lib/editor/upload.ts 와 대응한다(axios 대신 fetch).
//
// 서버: POST <data-upload-url> (app/web/admin/notices.py upload_editor_image)
// - Accept: application/json 으로 부르면 201 {key, url, width, height}, 실패는 {detail, code} JSON 이다.
// - CSRF 토큰은 <meta name="csrf-token"> 값을 X-CSRFToken 헤더로 보낸다(Flask-WTF 가 헤더도 검사한다).
// 업로드 함수는 reject 하지 않고 실패를 {error: 문구} 로 돌려준다.

const GENERIC_ERROR = "이미지를 올리지 못했습니다. 잠시 후 다시 시도해 주세요.";

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ?? "";
}

/** 업로드 오류 → 사용자 문구. 상태 코드로 구분한다(모든 실패를 한 문구로 뭉개지 않는다). */
export function uploadErrorMessage(status, detail, maxMb) {
  switch (status) {
    case 413:
      return `이미지는 ${maxMb}MB 이하만 올릴 수 있습니다.`;
    case 401:
      return "로그인이 만료되었습니다. 다시 로그인한 뒤 올려 주세요.";
    case 403:
      return "이미지를 올릴 권한이 없습니다.";
    case 400:
    case 422:
      // 서버 문구(StorageError·CSRF 등)는 사용자용 한국어다.
      return typeof detail === "string" && detail ? detail : "이미지를 처리할 수 없습니다. 다른 파일로 다시 시도해 주세요.";
    default:
      return GENERIC_ERROR;
  }
}

/** multipart `file` 필드로 올린다. 성공 {url, width, height} / 실패 {error}. */
export async function uploadEditorImage(endpoint, blob, filename, maxMb) {
  const form = new FormData();
  form.append("file", blob, filename);
  let res;
  try {
    // Content-Type 은 지정하지 않는다 — 브라우저가 FormData 를 보고 boundary 를 포함해 채운다.
    res = await fetch(endpoint, {
      method: "POST",
      body: form,
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() },
    });
  } catch {
    return { error: "네트워크 오류로 이미지를 올리지 못했습니다. 연결을 확인해 주세요." };
  }
  let data = null;
  if ((res.headers.get("Content-Type") ?? "").includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }
  if (res.ok && data && typeof data.url === "string") {
    return { url: data.url, width: Number(data.width), height: Number(data.height) };
  }
  return { error: uploadErrorMessage(res.status, data?.detail, maxMb) };
}
