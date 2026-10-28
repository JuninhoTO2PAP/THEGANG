/** Cliente WebSocket do THE GANG. */

import { getAccessToken } from "./api.js";

let socket = null;
let listeners = new Set();
let reconnectTimer = null;
let intentionalClose = false;

export function onWs(handler) {
  listeners.add(handler);
  return () => listeners.delete(handler);
}

function emit(event) {
  for (const handler of listeners) {
    try {
      handler(event);
    } catch {
      /* ignore */
    }
  }
}

export function wsSend(payload) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

export function connectWs() {
  intentionalClose = false;
  const token = getAccessToken();
  if (!token) return;

  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/api/ws/?token=${encodeURIComponent(token)}`;
  socket = new WebSocket(url);

  socket.addEventListener("open", () => emit({ type: "_open" }));
  socket.addEventListener("message", (ev) => {
    try {
      emit(JSON.parse(ev.data));
    } catch {
      /* ignore */
    }
  });
  socket.addEventListener("close", () => {
    emit({ type: "_close" });
    if (!intentionalClose) {
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connectWs, 2000);
    }
  });
  socket.addEventListener("error", () => {
    socket?.close();
  });
}

export function disconnectWs() {
  intentionalClose = true;
  clearTimeout(reconnectTimer);
  socket?.close();
  socket = null;
}

export function subscribeChannel(channelId) {
  wsSend({ type: "subscribe_channel", channel_id: channelId });
}

export function subscribeDm(dmId) {
  wsSend({ type: "subscribe_dm", dm_id: dmId });
}

export function sendTyping({ channelId = null, dmId = null, peerIds = [] } = {}) {
  wsSend({
    type: "typing",
    channel_id: channelId,
    dm_id: dmId,
    peer_ids: peerIds,
  });
}
