/** Configurações: conta, perfil, notificações, privacidade, voz, atalhos, convites. */

import { api, apiUpload, getAccessToken, mediaUrl, saveSession } from "./api.js";
import { getNotifyPrefs, setNotifyPrefs } from "./notify-prefs.js";
import { setupPush } from "./push.js";
import {
  getPrivacyPrefs,
  getShortcutPrefs,
  getVoicePrefs,
  setPrivacyPrefs,
  setShortcutPrefs,
  setVoicePrefs,
} from "./prefs.js";
import {
  ACCENTS,
  BANNER_THEMES,
  FF_REGIONS,
  FF_ROLES,
  applyAccent,
  applyTheme,
  ffRoleLabel,
  formatDay,
  formatTime,
  getAccent,
  getTheme,
  initials,
  toast,
} from "./ui.js";

const MENU = [
  { id: "conta", label: "Minha conta", icon: "👤" },
  { id: "perfil", label: "Perfil", icon: "🪪" },
  { id: "aparencia", label: "Aparência", icon: "🎨" },
  { id: "notificacoes", label: "Notificações", icon: "🔔" },
  { id: "privacidade", label: "Privacidade", icon: "🔒" },
  { id: "voz", label: "Voz e vídeo", icon: "🎙️" },
  { id: "atalhos", label: "Atalhos", icon: "⌨️" },
  { id: "convites", label: "Convites", icon: "🔗", adminOnly: true },
  { id: "admin", label: "Administrador", icon: "♛", adminOnly: true },
];

export function renderSettings(
  container,
  user,
  { initialTab = "conta", onUserUpdated, onClose, onLogout } = {}
) {
  let tab = initialTab;
  let current = user;

  container.innerHTML = `
    <div class="settings-layout">
      <aside class="settings-side">
        <div class="settings-side-head">
          <h2>Configurações</h2>
          <button type="button" class="icon-btn" id="settings-close" title="Voltar">✕</button>
        </div>
        <nav class="settings-nav" id="settings-nav"></nav>
        <button type="button" class="settings-logout" id="settings-logout">Sair da conta</button>
      </aside>
      <section class="settings-main">
        <div class="settings-card" id="settings-body"></div>
      </section>
    </div>
  `;

  container.querySelector("#settings-close")?.addEventListener("click", () => onClose?.());
  container.querySelector("#settings-logout")?.addEventListener("click", () => onLogout?.());

  const nav = container.querySelector("#settings-nav");
  const body = container.querySelector("#settings-body");
  const items = MENU.filter((item) => !item.adminOnly || current.is_admin);

  function paintNav() {
    nav.innerHTML = items
      .map(
        (item) => `
          <button type="button" data-tab="${item.id}" class="${item.id === tab ? "active" : ""}">
            <span>${item.icon}</span><span>${item.label}</span>
          </button>
        `
      )
      .join("");
  }

  async function paintBody() {
    if (tab === "conta") {
      body.innerHTML = accountHtml(current);
      bindAccount();
      return;
    }
    if (tab === "perfil") {
      paintProfile();
      return;
    }
    if (tab === "notificacoes") {
      paintNotifications();
      return;
    }
    if (tab === "privacidade") {
      paintPrivacy();
      return;
    }
    if (tab === "voz") {
      paintVoice();
      return;
    }
    if (tab === "atalhos") {
      paintShortcuts();
      return;
    }
    if (tab === "aparencia") {
      body.innerHTML = `
        <h2>Aparência</h2>
        <p class="section-lead">Deixe o THE GANG com a sua cara.</p>
        ${themeBlock()}
        ${accentBlock()}
      `;
      bindTheme();
      bindAccent();
      return;
    }
    if (tab === "convites") {
      await paintInvites(body);
      return;
    }
    if (tab === "admin") {
      await paintAdmin(body);
    }
  }

  function avatarMarkup(user, sizeClass = "lg") {
    const url = mediaUrl(user.avatar_url);
    const inner = url
      ? `<img src="${escapeAttr(url)}" alt="" class="avatar-img" />`
      : initials(user.nickname);
    return `<div class="avatar ${sizeClass}">${inner}<span class="dot"></span></div>`;
  }

  function paintProfile() {
    const theme = current.banner_theme || "gold";
    body.innerHTML = `
      <h2>Perfil</h2>
      <p class="section-lead">Carta Free Fire + identidade no THE GANG.</p>

      <div class="profile-edit-card">
        <div class="profile-banner banner-theme-${escapeAttr(theme)}"></div>
        <div class="profile-edit-body">
          <div class="avatar-edit-wrap">
            ${avatarMarkup(current, "xl")}
            <button type="button" class="avatar-change-btn" id="pick-avatar">Trocar foto</button>
            <input type="file" id="avatar-file" accept="image/jpeg,image/png,image/webp" hidden />
          </div>
          <div class="profile-edit-meta">
            <strong id="live-nickname">${escapeHtml(current.nickname)}</strong>
            <span id="live-username">@${escapeHtml(current.username)}</span>
            ${current.is_admin ? `<span class="badge ok">Admin</span>` : ""}
            ${current.ff_role ? `<span class="badge">${escapeHtml(FF_ROLES.find((r) => r.id === current.ff_role)?.label || current.ff_role)}</span>` : ""}
          </div>
        </div>
      </div>

      <form id="profile-form" class="profile-form">
        <div class="identity-grid">
          <label class="identity-field">
            <span class="identity-label">Nome de exibição</span>
            <input name="nickname" maxlength="32" minlength="2" value="${escapeAttr(current.nickname)}" required />
            <span class="field-help">Aparece no chat e nos grupos.</span>
          </label>
          <label class="identity-field">
            <span class="identity-label">@usuário</span>
            <div class="at-input">
              <span>@</span>
              <input name="username" maxlength="32" minlength="3" value="${escapeAttr(current.username)}" required />
            </div>
            <span class="field-help">Único no time. Letras, números e _.</span>
          </label>
        </div>

        <h3 class="profile-section-title">Carta Free Fire</h3>
        <div class="identity-grid">
          <label class="identity-field">
            <span class="identity-label">ID Free Fire</span>
            <input name="ff_id" maxlength="32" value="${escapeAttr(current.ff_id || "")}" placeholder="ex: 123456789" />
          </label>
          <label class="identity-field">
            <span class="identity-label">Nick in-game</span>
            <input name="ff_nick" maxlength="32" value="${escapeAttr(current.ff_nick || "")}" placeholder="Nick do Free Fire" />
          </label>
          <label class="identity-field">
            <span class="identity-label">Função</span>
            <select name="ff_role">
              <option value="">Sem função</option>
              ${FF_ROLES.map(
                (r) =>
                  `<option value="${r.id}" ${current.ff_role === r.id ? "selected" : ""}>${r.label}</option>`
              ).join("")}
            </select>
          </label>
          <label class="identity-field">
            <span class="identity-label">Região</span>
            <select name="ff_region">
              <option value="">Sem região</option>
              ${FF_REGIONS.map(
                (r) =>
                  `<option value="${r.id}" ${current.ff_region === r.id ? "selected" : ""}>${r.label}</option>`
              ).join("")}
            </select>
          </label>
        </div>

        <h3 class="profile-section-title">Banner pessoal</h3>
        <div class="banner-theme-picker" id="banner-theme-picker">
          ${BANNER_THEMES.map(
            (t) => `
            <label class="banner-theme-option">
              <input type="radio" name="banner_theme" value="${t.id}" ${theme === t.id ? "checked" : ""} />
              <span class="banner-swatch banner-theme-${t.id}"></span>
              <span>${t.label}</span>
            </label>`
          ).join("")}
        </div>

        <div class="modal-actions" style="justify-content:flex-start;margin-top:8px">
          <button class="btn btn-primary" type="submit">Salvar alterações</button>
          <button class="btn btn-secondary" type="button" id="remove-avatar" ${current.avatar_url ? "" : "hidden"}>
            Remover foto
          </button>
        </div>
      </form>
    `;

    const form = body.querySelector("#profile-form");
    const nickInput = form.querySelector('[name="nickname"]');
    const userInput = form.querySelector('[name="username"]');
    const fileInput = body.querySelector("#avatar-file");

    nickInput.addEventListener("input", () => {
      body.querySelector("#live-nickname").textContent = nickInput.value.trim() || current.nickname;
    });
    userInput.addEventListener("input", () => {
      const value = userInput.value.replace(/^@/, "").trim().toLowerCase() || current.username;
      body.querySelector("#live-username").textContent = `@${value}`;
    });

    body.querySelector("#pick-avatar").addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files?.[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        toast("A foto deve ter no máximo 5MB.", true);
        fileInput.value = "";
        return;
      }
      const data = new FormData();
      data.append("file", file);
      try {
        const updated = await apiUpload("/api/uploads/avatar", data);
        current = updated;
        persistUser(updated);
        onUserUpdated?.(updated);
        toast("Foto atualizada.");
        paintBody();
      } catch (error) {
        toast(error.message, true);
      } finally {
        fileInput.value = "";
      }
    });

    body.querySelector("#remove-avatar")?.addEventListener("click", async () => {
      try {
        current = await clearAvatar();
        persistUser(current);
        onUserUpdated?.(current);
        toast("Foto removida.");
        paintBody();
      } catch (error) {
        toast(error.message, true);
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(form);
      try {
        const updated = await api("/api/users/me", {
          method: "PATCH",
          body: {
            nickname: String(data.get("nickname") || "").trim(),
            username: String(data.get("username") || "").trim(),
            ff_id: String(data.get("ff_id") || "").trim() || null,
            ff_nick: String(data.get("ff_nick") || "").trim() || null,
            ff_role: String(data.get("ff_role") || "").trim() || null,
            ff_region: String(data.get("ff_region") || "").trim() || null,
            banner_theme: String(data.get("banner_theme") || "gold"),
          },
        });
        current = updated;
        persistUser(updated);
        onUserUpdated?.(updated);
        toast("Perfil atualizado.");
        paintBody();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  async function clearAvatar() {
    return api("/api/users/me/avatar", { method: "DELETE" });
  }

  function paintNotifications() {
    const prefs = getNotifyPrefs();
    body.innerHTML = `
      <h2>Notificações</h2>
      <p class="section-lead">Escolha o que o THE GANG pode te avisando.</p>
      <div class="toggle-list">
        ${toggleRow("desktop", "Notificações no desktop", "Aviso com o app em segundo plano.", prefs.desktop)}
        ${toggleRow("sound", "Som de mensagem", "Som curto ao receber mensagem.", prefs.sound)}
        ${toggleRow("mentions_only", "Só menções", "Avisa só quando alguém te marcar.", prefs.mentions_only)}
        ${toggleRow("mute_dms", "Silenciar DMs", "Não avisa conversas privadas.", prefs.mute_dms)}
        ${toggleRow("show_previews", "Prévia da mensagem", "Mostra um pedaço do texto no aviso.", prefs.show_previews)}
      </div>
      <div class="notify-note">
        <strong>Dica</strong>
        <p>Aceite a permissão do navegador para as notificações de desktop.</p>
        <button type="button" class="btn btn-secondary" id="ask-permission">Pedir permissão do navegador</button>
      </div>
    `;
    bindToggles(body, setNotifyPrefs);
    body.querySelector("#ask-permission")?.addEventListener("click", async () => {
      if (!("Notification" in window)) {
        toast("Este navegador não suporta notificações.", true);
        return;
      }
      const result = await Notification.requestPermission();
      if (result === "granted") {
        setNotifyPrefs({ desktop: true });
        toast("Permissão concedida.");
        paintBody();
      } else {
        toast("Permissão negada ou ignorada.", true);
      }
    });
  }

  function paintPrivacy() {
    const prefs = getPrivacyPrefs();
    body.innerHTML = `
      <h2>Privacidade</h2>
      <p class="section-lead">Controle o que os outros membros veem sobre você.</p>
      <div class="toggle-list">
        ${toggleRow("show_online", "Mostrar status online", "Os outros veem quando você está conectado.", prefs.show_online)}
        ${toggleRow("allow_dms", "Permitir mensagens diretas", "Membros do time podem te mandar DM.", prefs.allow_dms)}
        ${toggleRow("show_activity", "Mostrar atividade", "Exibe se você está em um canal de voz (quando existir).", prefs.show_activity)}
        ${toggleRow("read_receipts", "Confirmação de leitura", "Mostra quando você leu as mensagens.", prefs.read_receipts)}
      </div>
      <div class="settings-panel-note">
        <strong>Em breve</strong>
        <p>Bloqueio de membros e histórico de logins entram nas próximas fases.</p>
      </div>
    `;
    bindToggles(body, setPrivacyPrefs);
  }

  async function paintVoice() {
    const prefs = getVoicePrefs();
    body.innerHTML = `
      <h2>Voz e vídeo</h2>
      <p class="section-lead">Escolha dispositivos e qualidade. A call real (LiveKit) entra na Fase 3.</p>

      <div class="device-panel">
        <div class="device-panel-head">
          <strong>Saída de som</strong>
          <kbd>CTRL V</kbd>
        </div>
        <div class="device-section">
          <div class="device-label">Dispositivo de saída</div>
          <div class="device-list" id="output-devices"><p class="soon">Carregando dispositivos…</p></div>
        </div>
        <div class="device-section">
          <div class="device-label">Som espacial</div>
          <div class="device-list" id="spatial-options"></div>
        </div>
        <button type="button" class="device-more" id="ask-media">Mais configurações / liberar microfone</button>
      </div>

      <div class="device-panel" style="margin-top:14px">
        <div class="device-panel-head"><strong>Entrada (microfone)</strong></div>
        <div class="device-list" id="input-devices"><p class="soon">Peça permissão para listar o microfone.</p></div>
      </div>

      <div class="slider-list" style="margin-top:14px">
        ${sliderRow("input_volume", "Volume do microfone", prefs.input_volume)}
        ${sliderRow("output_volume", "Volume dos outros", prefs.output_volume)}
      </div>

      <div class="toggle-list" style="margin-top:14px">
        ${toggleRow("noise_suppression", "Supressão de ruído", "Corta barulho de fundo no microfone.", prefs.noise_suppression)}
        ${toggleRow("echo_cancellation", "Cancelamento de eco", "Evita ouvir sua própria voz.", prefs.echo_cancellation)}
        ${toggleRow("auto_gain", "Controle automático de ganho", "Equaliza o volume da sua voz.", prefs.auto_gain)}
        ${toggleRow("camera_mirrored", "Espelhar câmera", "Mostra sua imagem espelhada na prévia.", prefs.camera_mirrored)}
      </div>
    `;

    bindToggles(body, setVoicePrefs);
    body.querySelectorAll("[data-slider]").forEach((input) => {
      const label = body.querySelector(`[data-slider-value="${input.dataset.slider}"]`);
      input.addEventListener("input", () => {
        label.textContent = `${input.value}%`;
        setVoicePrefs({ [input.dataset.slider]: Number(input.value) });
      });
    });

    const spatial = [
      { id: "off", label: "Desativado" },
      { id: "sonic", label: "Windows Sonic for Headphones" },
      { id: "dts", label: "Fone de Ouvido DTS:X" },
    ];
    const spatialEl = body.querySelector("#spatial-options");
    const currentSpatial = prefs.spatial || "off";
    spatialEl.innerHTML = spatial
      .map(
        (item) => `
          <button type="button" class="device-option ${item.id === currentSpatial ? "active" : ""}" data-spatial="${item.id}">
            <span class="device-indicator"></span>
            <span>${item.label}</span>
          </button>
        `
      )
      .join("");
    spatialEl.querySelectorAll("[data-spatial]").forEach((button) => {
      button.addEventListener("click", () => {
        setVoicePrefs({ spatial: button.dataset.spatial });
        paintBody();
        toast("Som espacial atualizado.");
      });
    });

    body.querySelector("#ask-media")?.addEventListener("click", async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
        toast("Permissão concedida.");
        await fillDevices();
      } catch {
        toast("Não foi possível acessar o microfone.", true);
      }
    });

    await fillDevices();

    async function fillDevices() {
      if (!navigator.mediaDevices?.enumerateDevices) {
        body.querySelector("#output-devices").innerHTML =
          `<p class="soon">Seu navegador não lista dispositivos de áudio.</p>`;
        return;
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const outputs = devices.filter((d) => d.kind === "audiooutput");
      const inputs = devices.filter((d) => d.kind === "audioinput");
      const selectedOut = prefs.output_device_id || outputs[0]?.deviceId || "";
      const selectedIn = prefs.input_device_id || inputs[0]?.deviceId || "";

      body.querySelector("#output-devices").innerHTML = outputs.length
        ? outputs
            .map(
              (device) => `
                <button type="button" class="device-option ${device.deviceId === selectedOut ? "active" : ""}" data-output="${escapeAttr(device.deviceId)}">
                  <span class="device-indicator"></span>
                  <span>🔊 ${escapeHtml(device.label || "Alto-falante")}</span>
                </button>
              `
            )
            .join("")
        : `<p class="soon">Nenhuma saída listada. Clique em liberar microfone/áudio acima.</p>`;

      body.querySelector("#input-devices").innerHTML = inputs.length
        ? inputs
            .map(
              (device) => `
                <button type="button" class="device-option ${device.deviceId === selectedIn ? "active" : ""}" data-input="${escapeAttr(device.deviceId)}">
                  <span class="device-indicator"></span>
                  <span>🎙️ ${escapeHtml(device.label || "Microfone")}</span>
                </button>
              `
            )
            .join("")
        : `<p class="soon">Nenhum microfone listado ainda.</p>`;

      body.querySelectorAll("[data-output]").forEach((button) => {
        button.addEventListener("click", () => {
          setVoicePrefs({ output_device_id: button.dataset.output });
          paintBody();
          toast("Saída de som escolhida.");
        });
      });
      body.querySelectorAll("[data-input]").forEach((button) => {
        button.addEventListener("click", () => {
          setVoicePrefs({ input_device_id: button.dataset.input });
          paintBody();
          toast("Microfone escolhido.");
        });
      });
    }
  }

  function paintShortcuts() {
    const prefs = getShortcutPrefs();
    body.innerHTML = `
      <h2>Atalhos</h2>
      <p class="section-lead">Teclas rápidas do app. Você pode ligar ou desligar o Enter para enviar.</p>

      <div class="toggle-list">
        ${toggleRow("send_on_enter", "Enter envia mensagem", "Shift+Enter continua quebrando linha.", prefs.send_on_enter)}
      </div>

      <div class="shortcut-table">
        ${shortcutRow("Pesquisar", prefs.search)}
        ${shortcutRow("Abrir configurações", prefs.toggle_settings)}
        ${shortcutRow("Mutar microfone", prefs.mute_mic)}
        ${shortcutRow("Mutar som", prefs.mute_sound)}
      </div>
      <p class="hint-inline">Os atalhos de voz passam a valer quando as chamadas forem ativadas.</p>
    `;
    bindToggles(body, (partial) => {
      // send_on_enter is boolean; shortcut strings stay as defaults for now
      if ("send_on_enter" in partial) setShortcutPrefs(partial);
    });
  }

  function bindAccount() {
    body.querySelector("#edit-profile")?.addEventListener("click", () => {
      tab = "perfil";
      paintNav();
      paintBody();
    });
    body.querySelector("#go-invites")?.addEventListener("click", () => {
      tab = "convites";
      paintNav();
      paintBody();
    });
    body.querySelectorAll("[data-presence]").forEach((btn) => {
      btn.addEventListener("click", () => {
        body.querySelectorAll("[data-presence]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });
    body.querySelector("#save-status")?.addEventListener("click", async () => {
      const presence =
        body.querySelector("[data-presence].active")?.dataset.presence || "online";
      const status_text = body.querySelector("#status-text")?.value || "";
      try {
        const updated = await api("/api/users/me/status", {
          method: "PATCH",
          body: { presence, status_text },
        });
        current = updated;
        persistUser(updated);
        onUserUpdated?.(updated);
        toast("Status atualizado.");
      } catch (error) {
        toast(error.message, true);
      }
    });
    body.querySelector("#enable-push")?.addEventListener("click", async () => {
      try {
        await setupPush();
        toast("Notificações ativadas (se o navegador permitir).");
      } catch (error) {
        toast(error.message || "Falha ao ativar push.", true);
      }
    });
    const pwdForm = body.querySelector("#password-form");
    body.querySelector("#change-password")?.addEventListener("click", () => {
      if (pwdForm) pwdForm.hidden = !pwdForm.hidden;
    });
    pwdForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(event.target);
      try {
        await api("/api/users/me/password", {
          method: "POST",
          body: {
            current_password: String(data.get("current_password") || ""),
            new_password: String(data.get("new_password") || ""),
          },
        });
        event.target.reset();
        pwdForm.hidden = true;
        toast("Senha alterada.");
      } catch (error) {
        toast(error.message, true);
      }
    });
    bindTheme();
    bindAccent();
    body.querySelectorAll("[data-quick]").forEach((button) => {
      button.addEventListener("click", () => {
        tab = button.dataset.quick;
        paintNav();
        paintBody();
      });
    });
  }

  function bindTheme() {
    body.querySelectorAll("[data-theme-set]").forEach((button) => {
      button.addEventListener("click", () => {
        applyTheme(button.dataset.themeSet);
        paintBody();
        toast("Tema atualizado.");
      });
    });
  }

  function bindAccent() {
    body.querySelectorAll("[data-accent]").forEach((button) => {
      button.addEventListener("click", async () => {
        const accent = button.dataset.accent;
        applyAccent(accent);
        paintBody();
        try {
          const updated = await api("/api/users/me/accent", {
            method: "PATCH",
            body: { accent },
          });
          current = updated;
          persistUser(updated);
          onUserUpdated?.(updated);
        } catch (error) {
          toast(error.message || "Cor salva neste aparelho.", true);
        }
      });
    });
  }

  nav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tab]");
    if (!button) return;
    tab = button.dataset.tab;
    paintNav();
    paintBody();
  });

  paintNav();
  paintBody();
}

function bindToggles(root, setter) {
  root.querySelectorAll("[data-pref]").forEach((input) => {
    input.addEventListener("change", () => {
      setter({ [input.dataset.pref]: input.checked });
      toast("Preferência salva.");
    });
  });
}

function persistUser(user) {
  const access = getAccessToken();
  const refresh = localStorage.getItem("tg_refresh");
  if (access && refresh) {
    saveSession({ user, tokens: { access_token: access, refresh_token: refresh } });
  }
}

function toggleRow(id, title, help, checked) {
  return `
    <label class="toggle-row">
      <div>
        <strong>${title}</strong>
        <span>${help}</span>
      </div>
      <input type="checkbox" data-pref="${id}" ${checked ? "checked" : ""} />
    </label>
  `;
}

function sliderRow(id, title, value) {
  return `
    <label class="slider-row">
      <div class="slider-head">
        <strong>${title}</strong>
        <span data-slider-value="${id}">${value}%</span>
      </div>
      <input type="range" min="0" max="100" value="${value}" data-slider="${id}" />
    </label>
  `;
}

function shortcutRow(label, keys) {
  return `
    <div class="shortcut-row">
      <span>${label}</span>
      <kbd>${escapeHtml(keys)}</kbd>
    </div>
  `;
}

function accountHtml(user) {
  const created = formatDay(user.created_at);
  const url = mediaUrl(user.avatar_url);
  const avatar = url
    ? `<img src="${escapeAttr(url)}" alt="" class="avatar-img" />`
    : initials(user.nickname);
  return `
    <div class="profile-hero">
      <div class="avatar lg">${avatar}<span class="dot"></span></div>
      <div>
        <h3>${escapeHtml(user.nickname)} ${user.is_admin ? "👑" : ""}</h3>
        <div class="handle">@${escapeHtml(user.username)}</div>
      </div>
    </div>

    <div class="field-card">
      <div>
        <div class="label">E-mail</div>
        <div>${escapeHtml(user.email)}</div>
      </div>
      <span>✉️</span>
    </div>
    <div class="field-card">
      <div>
        <div class="label">Conta criada em</div>
        <div>${created}</div>
      </div>
      <span>📅</span>
    </div>

    <div class="status-picker">
      <h4>Status</h4>
      <div class="status-options" id="status-options">
        <button type="button" data-presence="online" class="${(user.presence || "online") === "online" ? "active" : ""}">🟢 Online</button>
        <button type="button" data-presence="away" class="${user.presence === "away" ? "active" : ""}">🟡 Ausente</button>
        <button type="button" data-presence="dnd" class="${user.presence === "dnd" ? "active" : ""}">🔴 Não perturbe</button>
        <button type="button" data-presence="invisible" class="${user.presence === "invisible" ? "active" : ""}">⚫ Invisível</button>
      </div>
      <label>Texto do status
        <input id="status-text" maxlength="120" placeholder="ex: Em ranked / Em call" value="${escapeAttr(user.status_text || "")}" />
      </label>
      <button class="btn btn-secondary" type="button" id="save-status">Salvar status</button>
    </div>

    <div class="actions-col">
      <button class="btn btn-primary" type="button" id="edit-profile">Editar perfil</button>
      <button class="btn btn-secondary" type="button" id="change-password">🔒 Alterar senha ▸</button>
      <button class="btn btn-secondary" type="button" id="enable-push">🔔 Ativar notificações push</button>
    </div>
    <form id="password-form" class="stack password-form" hidden>
      <label>Senha atual
        <input type="password" name="current_password" required autocomplete="current-password" />
      </label>
      <label>Nova senha
        <input type="password" name="new_password" required minlength="8" autocomplete="new-password" />
      </label>
      <button class="btn btn-primary" type="submit">Salvar nova senha</button>
    </form>

    ${themeBlock()}
    ${accentBlock()}

    <div class="quick-list">
      <button type="button" data-quick="notificacoes"><span>🔔 Notificações</span><span>›</span></button>
      <button type="button" data-quick="voz"><span>🎧 Dispositivos de voz</span><span>›</span></button>
      <button type="button" data-quick="privacidade"><span>🛡️ Privacidade</span><span>›</span></button>
      ${
        user.is_admin
          ? `<button type="button" id="go-invites"><span>🔗 Convites</span><span>›</span></button>`
          : ""
      }
    </div>
  `;
}

function themeBlock() {
  const theme = getTheme();
  return `
    <div class="theme-row">
      <h4>Tema</h4>
      <div class="segment">
        <button type="button" data-theme-set="dark" class="${theme === "dark" ? "active" : ""}">Escuro</button>
        <button type="button" data-theme-set="light" class="${theme === "light" ? "active" : ""}">Claro</button>
      </div>
    </div>
  `;
}

function accentBlock() {
  const current = getAccent();
  return `
    <div class="accent-row">
      <h4>Cor de destaque</h4>
      <div class="swatches">
        ${ACCENTS.map(
          (item) => `
            <button type="button" class="swatch ${item.id === current ? "active" : ""}"
              data-accent="${item.id}" style="background:${item.value}" title="${item.id}">${
                item.id === current ? "✓" : ""
              }</button>
          `
        ).join("")}
      </div>
    </div>
  `;
}

async function paintInvites(body) {
  body.innerHTML = `
    <h2>Convites</h2>
    <p class="section-lead">Gere um código e envie para a pessoa. Cada convite vale uma vez e já define o time (A ou B).</p>
    <div class="invite-block">
      <form id="invite-form" class="stack" style="margin-bottom:12px">
        <label>Time
          <select name="team">
            <option value="a" selected>THE GANG A</option>
            <option value="b">THE GANG B</option>
          </select>
        </label>
        <label>Validade
          <select name="expires_in_days">
            <option value="1">1 dia</option>
            <option value="3">3 dias</option>
            <option value="7" selected>7 dias</option>
            <option value="30">30 dias</option>
            <option value="0">Nunca expira</option>
          </select>
        </label>
        <button class="btn btn-primary" type="submit">Gerar convite</button>
      </form>
      <div id="invite-list"><p class="soon">Carregando…</p></div>
    </div>
  `;

  const list = body.querySelector("#invite-list");
  const form = body.querySelector("#invite-form");

  async function load() {
    try {
      const invites = await api("/api/auth/invites");
      if (!invites.length) {
        list.innerHTML = `<p class="soon">Nenhum convite ainda.</p>`;
        return;
      }
      list.innerHTML = invites
        .map((invite) => {
          const used = Boolean(invite.used_by);
          return `
            <div class="invite-row">
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <code>${invite.code}</code>
                <span class="badge ${used ? "used" : "ok"}">${used ? "Usado" : "Disponível"}</span>
                <button type="button" class="btn btn-ghost" data-copy="${invite.code}">Copiar</button>
                <button type="button" class="btn btn-ghost danger-text" data-delete="${invite.id}">Excluir</button>
              </div>
              <div class="soon">Time ${String(invite.team || "a").toUpperCase()} · ${invite.expires_at ? `Expira: ${formatDay(invite.expires_at)}` : "nunca expira"}</div>
            </div>
          `;
        })
        .join("");
      list.querySelectorAll("[data-copy]").forEach((button) => {
        button.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(button.dataset.copy);
            toast("Convite copiado.");
          } catch {
            toast("Não deu para copiar.", true);
          }
        });
      });
      list.querySelectorAll("[data-delete]").forEach((button) => {
        button.addEventListener("click", async () => {
          const row = button.closest(".invite-row");
          const code = row?.querySelector("code")?.textContent || "este convite";
          if (!window.confirm(`Excluir o convite ${code}?`)) return;
          try {
            await api(`/api/auth/invites/${button.dataset.delete}`, { method: "DELETE" });
            toast("Convite excluído.");
            await load();
          } catch (error) {
            toast(error.message, true);
          }
        });
      });
    } catch (error) {
      list.innerHTML = `<p class="soon">${escapeHtml(error.message)}</p>`;
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const days = Number(data.get("expires_in_days"));
    const team = String(data.get("team") || "a");
    try {
      const invite = await api("/api/auth/invites", {
        method: "POST",
        body: {
          expires_in_days: Number.isFinite(days) ? days : 7,
          team: team === "b" ? "b" : "a",
        },
      });
      toast(`Convite: ${invite.code}`);
      await load();
    } catch (error) {
      toast(error.message, true);
    }
  });

  await load();
}

async function paintAdmin(body) {
  body.innerHTML = `
    <h2>Administrador</h2>
    <p class="section-lead">Só você entra aqui. Dá para ver quem está no app, o login de cada conta e os dados da carta.</p>
    <p class="hint">A senha não fica visível. Se alguém perder a senha, defina uma nova aqui e passe para a pessoa. O login é o usuário ou o e-mail.</p>
    <div id="admin-list"><p class="soon">Carregando…</p></div>
  `;
  const list = body.querySelector("#admin-list");
  try {
    const members = await api("/api/admin/members");
    if (!members.length) {
      list.innerHTML = `<p class="soon">Nenhuma conta ainda.</p>`;
      return;
    }
    const online = members.filter((member) => member.is_online).length;
    list.innerHTML = `
      <p class="admin-count">${online} online · ${members.length} contas</p>
      <div class="admin-list">
        ${members.map((member) => adminCard(member)).join("")}
      </div>
    `;
    list.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(button.dataset.copy);
          toast("Copiado.");
        } catch {
          toast(button.dataset.copy);
        }
      });
    });
    list.querySelectorAll("form.admin-reset").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const password = String(new FormData(form).get("new_password") || "");
        const name = form.dataset.name || "essa pessoa";
        if (!window.confirm(`Definir uma nova senha para ${name}? A senha antiga deixa de funcionar.`)) {
          return;
        }
        try {
          await api(`/api/admin/members/${form.dataset.user}/password`, {
            method: "POST",
            body: { new_password: password },
          });
          form.reset();
          toast(`Senha de ${name} atualizada. Passe a nova senha para a pessoa.`);
        } catch (error) {
          toast(error.message, true);
        }
      });
    });
    list.querySelectorAll("[data-delete-user]").forEach((button) => {
      button.addEventListener("click", async () => {
        const name = button.dataset.name || "essa pessoa";
        if (!window.confirm(`Excluir a conta de ${name}? Essa pessoa deixa de entrar no THE GANG.`)) {
          return;
        }
        try {
          await api(`/api/admin/members/${button.dataset.deleteUser}`, { method: "DELETE" });
          toast(`Conta de ${name} excluída.`);
          await paintAdmin(body);
        } catch (error) {
          toast(error.message, true);
        }
      });
    });
  } catch (error) {
    list.innerHTML = `<p class="soon">${escapeHtml(error.message)}</p>`;
  }
}

function adminCard(member) {
  const role = member.ff_role ? ffRoleLabel(member.ff_role) : "Sem função";
  const seen = member.last_seen
    ? `${formatDay(member.last_seen)} · ${formatTime(member.last_seen)}`
    : "—";
  return `
    <article class="admin-card ${member.is_online ? "is-online" : ""}">
      <header>
        <strong>${escapeHtml(member.nickname)}</strong>
        <span class="badge ${member.is_online ? "ok" : ""}">${member.is_online ? "Online" : "Offline"}</span>
        ${member.is_admin ? `<span class="badge ok">Admin</span>` : ""}
      </header>
      <dl>
        <div><dt>Login</dt><dd><code>${escapeHtml(member.username)}</code><button type="button" class="btn btn-ghost" data-copy="${escapeAttr(member.username)}">Copiar</button></dd></div>
        <div><dt>E-mail</dt><dd><code>${escapeHtml(member.email)}</code><button type="button" class="btn btn-ghost" data-copy="${escapeAttr(member.email)}">Copiar</button></dd></div>
        <div><dt>ID da conta</dt><dd>${member.id}</dd></div>
        <div><dt>Função</dt><dd>${escapeHtml(role)}</dd></div>
        <div><dt>ID Free Fire</dt><dd>${escapeHtml(member.ff_id || "—")}</dd></div>
        <div><dt>Nick FF</dt><dd>${escapeHtml(member.ff_nick || "—")}</dd></div>
        <div><dt>Região</dt><dd>${escapeHtml(member.ff_region || "—")}</dd></div>
        <div><dt>Time</dt><dd>${escapeHtml(member.team || "—")}</dd></div>
        <div><dt>Convite</dt><dd>${
          member.invite_code
            ? `<code>${escapeHtml(member.invite_code)}</code><button type="button" class="btn btn-ghost" data-copy="${escapeAttr(member.invite_code)}">Copiar</button>`
            : "—"
        }</dd></div>
        <div><dt>Visto por último</dt><dd>${escapeHtml(seen)}</dd></div>
        <div><dt>Conta criada</dt><dd>${escapeHtml(formatDay(member.created_at))}</dd></div>
      </dl>
      <form class="admin-reset" data-user="${member.id}" data-name="${escapeAttr(member.nickname)}">
        <label>Nova senha, se ${escapeHtml(member.nickname)} perdeu a antiga
          <input type="text" name="new_password" minlength="8" maxlength="128" required placeholder="Letras e números, mínimo 8" autocomplete="off" />
        </label>
        <button class="btn btn-secondary" type="submit">Definir senha</button>
      </form>
      ${
        member.is_admin
          ? ""
          : `<button type="button" class="btn btn-ghost danger-text" data-delete-user="${member.id}" data-name="${escapeAttr(member.nickname)}">Excluir conta</button>`
      }
    </article>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}
