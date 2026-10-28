/** Proxy /uploads/* → backend (avatars e anexos). */

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "cf-connecting-ip",
  "cf-ipcountry",
  "cf-ray",
  "cf-visitor",
  "x-forwarded-proto",
  "x-real-ip",
]);

const FALLBACK_API_ORIGIN = "https://cad-remaining-councils-notebooks.trycloudflare.com";

export async function onRequest(context) {
  const { request, env } = context;
  const origin = (env.API_ORIGIN || FALLBACK_API_ORIGIN || "").replace(/\/$/, "");
  if (!origin) {
    return new Response("API_ORIGIN não configurada", { status: 503 });
  }

  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);
  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  }
  headers.set("Host", target.host);

  return fetch(target.toString(), {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    redirect: "manual",
    duplex: "half",
  });
}
