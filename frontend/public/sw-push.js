/* global self */
self.addEventListener("push", (event) => {
  let payload = { title: "THE GANG", body: "Nova notificação", data: {} };
  try {
    if (event.data) payload = { ...payload, ...event.data.json() };
  } catch {
    /* ignore */
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "THE GANG", {
      body: payload.body || "",
      icon: "/icons/icon.svg",
      badge: "/icons/icon.svg",
      data: payload.data || {},
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  let url = "/";
  if (data.type === "dm" && data.dm_id) url = "/";
  event.waitUntil(self.clients.openWindow(url));
});
