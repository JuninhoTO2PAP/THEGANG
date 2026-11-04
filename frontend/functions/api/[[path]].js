/** Proxy /api/* → backend (WebSocket + HTTP). */

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

const FALLBACK_API_ORIGIN = "https://the-gang-api.onrender.com";

function backendOrigin(env) {
  const origin = (env.API_ORIGIN || FALLBACK_API_ORIGIN || "").replace(/\/$/, "");
  if (!origin) {
    throw new Error("API_ORIGIN não configurada no Pages.");
  }
  return origin;
}

export async function onRequest(context) {
  const { request, env } = context;
  let origin;
  try {
    origin = backendOrigin(env);
  } catch (error) {
    return new Response(
      JSON.stringify({
        detail:
          "API offline: configure API_ORIGIN no Cloudflare Pages (ex: https://api-gang.httpslaudo.com.br).",
      }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }

  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);

  // WebSocket: NÃO remova Upgrade/Connection — senão a presença nunca sobe.
  if ((request.headers.get("Upgrade") || "").toLowerCase() === "websocket") {
    const wsHeaders = new Headers(request.headers);
    wsHeaders.set("Host", target.host);
    try {
      return await fetch(target.toString(), {
        headers: wsHeaders,
      });
    } catch (error) {
      return new Response(`Falha no WebSocket: ${error.message || error}`, {
        status: 502,
      });
    }
  }

  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  }
  headers.set("Host", target.host);

  const init = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }

  try {
    return await fetch(target.toString(), init);
  } catch (error) {
    return new Response(
      JSON.stringify({ detail: `Falha ao falar com a API: ${error.message || error}` }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}
