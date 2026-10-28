/** Chamadas HTTP com JWT e renovação automática do access token. */

const ACCESS_KEY = "tg_access";
const REFRESH_KEY = "tg_refresh";
const USER_KEY = "tg_user";

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function saveSession(payload) {
  localStorage.setItem(ACCESS_KEY, payload.tokens.access_token);
  localStorage.setItem(REFRESH_KEY, payload.tokens.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

async function parseError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg || JSON.stringify(item)).join(" ");
    }
  } catch {
    /* ignore */
  }
  return `Erro ${response.status}`;
}

let refreshPromise = null;

async function refreshTokens() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) throw new Error("Sessão expirada.");
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        clearSession();
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      saveSession(data);
      return data;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function api(path, { method = "GET", body, auth = true, retry = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && auth && retry) {
    await refreshTokens();
    return api(path, { method, body, auth, retry: false });
  }

  if (response.status === 204) return null;
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

/** Upload multipart (avatar etc.). Não define Content-Type — o browser coloca o boundary. */
export async function apiUpload(path, formData, { retry = true } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(path, { method: "POST", headers, body: formData });

  if (response.status === 401 && retry) {
    await refreshTokens();
    return apiUpload(path, formData, { retry: false });
  }
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path;
}
