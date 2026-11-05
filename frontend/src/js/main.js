/** Shell: Chat (Discord) e Configurações. */

import { api, getStoredUser, saveSession, getAccessToken } from "./api.js";
import { logout, renderAuth } from "./auth.js";
import { renderChat } from "./chat.js";
import { renderSettings } from "./settings.js";
import { applyAccent, getAccent, initTheme, toast } from "./ui.js";
import { setupPush } from "./push.js";
import { disconnectWs } from "./ws.js";

const root = document.getElementById("app");
let currentUser = getStoredUser();
let view = "chat";
let settingsTab = "conta";

// Convite de grupo: /join/GRP-XXXX
const joinMatch = location.pathname.match(/^\/join\/([A-Za-z0-9\-]+)/);
if (joinMatch) {
  sessionStorage.setItem("tg_join_code", joinMatch[1]);
  history.replaceState({}, "", "/");
}

function renderShell() {
  root.innerHTML = `<div class="app-root" id="workspace"></div>`;
  const workspace = root.querySelector("#workspace");

  if (view === "settings") {
    renderSettings(workspace, currentUser, {
      initialTab: settingsTab,
      onClose() {
        view = "chat";
        renderShell();
      },
      onUserUpdated(user) {
        currentUser = user;
      },
      onLogout: async () => {
        disconnectWs();
        await logout();
        currentUser = null;
        toast("Você saiu.");
        boot();
      },
    });
    return;
  }

  renderChat(workspace, currentUser, {
    onOpenSettings(tab = "conta") {
      view = "settings";
      settingsTab = tab || "conta";
      renderShell();
    },
    onLogout: async () => {
      disconnectWs();
      await logout();
      currentUser = null;
      toast("Você saiu.");
      boot();
    },
  });
}

function syncAccent(user) {
  if (!user?.accent) return user;
  const local = getAccent();
  if (user.accent === "gold" && local !== "gold") {
    applyAccent(local);
    api("/api/users/me/accent", { method: "PATCH", body: { accent: local } }).catch(() => {});
    return { ...user, accent: local };
  }
  applyAccent(user.accent);
  return user;
}

async function boot() {
  initTheme();
  currentUser = getStoredUser();
  if (!currentUser || !getAccessToken()) {
    renderAuth(root, {
      onSuccess(user) {
        currentUser = syncAccent(user);
        view = "chat";
        renderShell();
      },
    });
    return;
  }
  try {
    const me = syncAccent(await api("/api/auth/me"));
    currentUser = me;
    const refresh = localStorage.getItem("tg_refresh");
    const access = getAccessToken();
    if (refresh && access) {
      saveSession({ user: me, tokens: { access_token: access, refresh_token: refresh } });
    }
  } catch {
    await logout();
    currentUser = null;
    boot();
    return;
  }
  renderShell();
  setupPush().catch(() => {});
}

boot();
