/** Web Push — inscrição + SW. */

import { api, getAccessToken } from "./api.js";
import { getNotifyPrefs } from "./notify-prefs.js";
import { toast } from "./ui.js";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function setupPush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
  if (!getNotifyPrefs().desktop) return;
  if (!getAccessToken()) return;

  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;

    const { public_key: publicKey } = await api("/api/push/vapid-public-key");
    if (!publicKey) return;

    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }
    const json = sub.toJSON();
    await api("/api/push/subscribe", {
      method: "POST",
      body: {
        endpoint: json.endpoint,
        keys: json.keys,
      },
    });
  } catch (error) {
    console.warn("push setup", error);
  }
}

export async function disablePush() {
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (!sub) return;
    await api("/api/push/subscribe", {
      method: "DELETE",
      body: { endpoint: sub.endpoint },
    });
    await sub.unsubscribe();
    toast("Notificações desativadas.");
  } catch (error) {
    toast(error.message, true);
  }
}
