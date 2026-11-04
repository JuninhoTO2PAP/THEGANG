/** Layout Discord: grupos → canais/DM + WS ao vivo. */

import { api, apiUpload, mediaUrl } from "./api.js";
import { openCreateChannelModal } from "./create-channel.js";
import { openCreateGroupModal } from "./create-group.js";
import { openGroupSettings } from "./group-settings.js";
import { Perm, can } from "./perms.js";
import { gangEmojiPickerHtml, QUICK_REACTS } from "./gang-emojis.js";
import { playMention } from "./sounds.js";
import { formatDay, formatTime, ffRoleLabel, initials, toast } from "./ui.js";
import { leaveVoiceCall, startVoiceCall } from "./voice-call.js";
import {
  connectWs,
  onWs,
  sendTyping,
  subscribeChannel,
  subscribeDm,
} from "./ws.js";

const QUICK_EMOJIS = QUICK_REACTS;

export function renderChat(container, user, { onOpenSettings, onLogout }) {
  let groups = [];
  let members = [];
  let dms = [];
  let activeGroup = null;
  let channels = [];
  let activeChannel = null;
  let activeDm = null;
  let mode = "home"; // home | channel | dm
  let messages = [];
  let pinned = [];
  let replyTo = null;
  let typingUsers = new Map();
  let typingTimer = null;
  let offlineIds = new Set();
  let pendingJoin = sessionStorage.getItem("tg_join_code");

  container.innerHTML = `
    <div class="chat-layout" id="chat-layout">
      <aside class="server-rail" aria-label="Grupos">
        <button class="server-pill home" title="Início / DMs" type="button" id="home-pill">TG</button>
        <div class="rail-sep"></div>
        <div id="group-rail"></div>
        <div class="rail-sep"></div>
        ${
          user.is_admin
            ? `<button class="server-pill add" type="button" id="create-group-rail" title="Criar grupo">+</button>`
            : ""
        }
      </aside>

      <aside class="channels-panel">
        <div class="guild-header">
          <span id="group-title">Mensagens diretas</span>
          <button type="button" class="icon-btn" id="group-settings-btn" title="Configurações do grupo" hidden>⚙</button>
        </div>
        <div class="channel-scroll" id="channel-scroll"></div>
        <div class="user-bar">
          ${avatarHtml(user)}
          <div class="user-meta">
            <strong>${escapeHtml(user.nickname)}</strong>
            <span>@${escapeHtml(user.username)}</span>
          </div>
          <button class="icon-btn" type="button" id="open-settings" title="Configurações">⚙</button>
          <button class="icon-btn" type="button" id="logout-btn" title="Sair">⏻</button>
        </div>
      </aside>

      <section class="chat-panel">
        <div class="gang-watermark" aria-hidden="true">THE GANG</div>
        <header class="chat-header" id="chat-header">
          <span>Mensagens diretas</span>
          <div class="header-actions">
            <button type="button" class="icon-btn" id="search-btn" title="Buscar" hidden>⌕</button>
          </div>
        </header>
        <div class="pins-bar" id="pins-bar" hidden></div>
        <div class="messages" id="messages"></div>
        <div class="typing-line" id="typing-line" hidden></div>
        <div class="reply-bar" id="reply-bar" hidden></div>
        <form class="composer" id="composer" hidden>
          <input type="file" id="attach-input" accept="image/jpeg,image/png,image/webp" hidden />
          <div class="composer-emoji-pop" id="composer-emoji-pop" hidden>
            ${gangEmojiPickerHtml()}
          </div>
          <div class="composer-box">
            <button class="plus" type="button" id="attach-btn" title="Enviar imagem">+</button>
            <button class="plus" type="button" id="emoji-btn" title="Emojis THE GANG">☺</button>
            <input name="content" id="composer-input" placeholder="Digite uma mensagem..." autocomplete="off" />
            <button class="send-btn" type="submit" title="Enviar">➤</button>
          </div>
        </form>
      </section>

      <aside class="members-panel" id="members-panel" hidden>
        <div class="members-head">Membros</div>
        <div class="members-scroll" id="members-scroll"></div>
      </aside>
    </div>
  `;

  const rail = container.querySelector("#group-rail");
  const scroll = container.querySelector("#channel-scroll");
  const titleEl = container.querySelector("#group-title");
  const settingsBtn = container.querySelector("#group-settings-btn");
  const headerEl = container.querySelector("#chat-header");
  const messagesEl = container.querySelector("#messages");
  const composer = container.querySelector("#composer");
  const composerInput = container.querySelector("#composer-input");
  const typingLine = container.querySelector("#typing-line");
  const layoutEl = container.querySelector("#chat-layout");
  const membersPanel = container.querySelector("#members-panel");
  const membersScroll = container.querySelector("#members-scroll");
  const searchBtn = container.querySelector("#search-btn");
  const attachInput = container.querySelector("#attach-input");
  const pinsBar = container.querySelector("#pins-bar");
  const replyBar = container.querySelector("#reply-bar");

  function setMembersVisible(visible) {
    membersPanel.hidden = !visible;
    layoutEl.classList.toggle("with-members", visible);
  }

  function setReply(message) {
    replyTo = message;
    if (!message) {
      replyBar.hidden = true;
      replyBar.innerHTML = "";
      return;
    }
    replyBar.hidden = false;
    replyBar.innerHTML = `
      <div class="reply-bar-inner">
        <div>
          <strong>Respondendo a ${escapeHtml(message.sender?.nickname || "?")}</strong>
          <span>${escapeHtml((message.content || "").slice(0, 80))}</span>
        </div>
        <button type="button" class="icon-btn" id="cancel-reply" title="Cancelar">✕</button>
      </div>`;
    replyBar.querySelector("#cancel-reply")?.addEventListener("click", () => setReply(null));
    composerInput.focus();
  }

  container.querySelector("#open-settings").addEventListener("click", onOpenSettings);
  container.querySelector("#logout-btn")?.addEventListener("click", () => onLogout?.());
  container.querySelector("#create-group-rail")?.addEventListener("click", () => {
    if (!user.is_admin) return;
    openCreateGroupModal({ onCreated: () => loadGroups(true) });
  });
  container.querySelector("#home-pill").addEventListener("click", () => {
    activeGroup = null;
    activeChannel = null;
    activeDm = null;
    mode = "home";
    paintRail();
    showHome();
  });
  settingsBtn.addEventListener("click", () => {
    if (!activeGroup) return;
    openGroupSettings(activeGroup, {
      onChanged: async () => {
        await openGroup(activeGroup.id);
      },
      onDeleted: async () => {
        activeGroup = null;
        activeChannel = null;
        await loadGroups();
      },
    });
  });
  searchBtn.addEventListener("click", openSearch);
  container.querySelector("#attach-btn").addEventListener("click", () => attachInput.click());
  attachInput.addEventListener("change", onAttach);
  const emojiPop = container.querySelector("#composer-emoji-pop");
  container.querySelector("#emoji-btn")?.addEventListener("click", () => {
    emojiPop.hidden = !emojiPop.hidden;
  });
  emojiPop?.querySelectorAll("[data-gang-emoji]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const emoji = btn.dataset.gangEmoji;
      const start = composerInput.selectionStart ?? composerInput.value.length;
      const end = composerInput.selectionEnd ?? start;
      const value = composerInput.value;
      composerInput.value = `${value.slice(0, start)}${emoji}${value.slice(end)}`;
      composerInput.focus();
      const caret = start + emoji.length;
      composerInput.setSelectionRange(caret, caret);
      emojiPop.hidden = true;
    });
  });

  const offWs = onWs(handleWsEvent);
  connectWs();

  function paintRail() {
    rail.innerHTML = groups
      .map((group) => {
        const label = group.name.slice(0, 2).toUpperCase();
        const active = activeGroup?.id === group.id ? "active" : "";
        return `<button class="server-pill ${active}" type="button" data-group="${group.id}" title="${escapeAttr(group.name)}">${escapeHtml(label)}</button>`;
      })
      .join("");
  }

  function paintChannels() {
    if (!activeGroup) return;
    const texts = channels.filter((c) => c.channel_type === "text");
    const voices = channels.filter((c) => c.channel_type === "voice");
    const canManage = can(activeGroup.my_permissions, Perm.MANAGE_CHANNELS);

    scroll.innerHTML = `
      <div class="cat-row">
        <div class="cat">Canais de texto</div>
        ${canManage ? `<button type="button" class="icon-btn" id="add-text" title="Novo canal">+</button>` : ""}
      </div>
      <div id="text-channels">
        ${
          texts
            .map(
              (ch) => `
              <button type="button" class="channel-item ${activeChannel?.id === ch.id && mode === "channel" ? "active" : ""}" data-channel="${ch.id}">
                <span class="hash">#</span><span>${escapeHtml(ch.name)}</span>
              </button>`
            )
            .join("") ||
          `<p class="hint" style="padding:6px 10px;text-transform:none;font-weight:400">Nenhum canal de texto.</p>`
        }
      </div>
      <div class="cat-row">
        <div class="cat">Canais de voz</div>
        ${canManage ? `<button type="button" class="icon-btn" id="add-voice" title="Nova call">+</button>` : ""}
      </div>
      <div id="voice-channels">
        ${
          voices
            .map(
              (ch) => `
              <button type="button" class="channel-item voice ${activeChannel?.id === ch.id && mode === "channel" ? "active" : ""}" data-channel="${ch.id}">
                <span>🔊</span><span>${escapeHtml(ch.name)}</span>
              </button>`
            )
            .join("") ||
          `<p class="hint" style="padding:6px 10px;text-transform:none;font-weight:400">Nenhuma sala de voz.</p>`
        }
      </div>
    `;

    scroll.querySelector("#add-text")?.addEventListener("click", () => {
      openCreateChannelModal(activeGroup, "text", {
        onCreated: (ch) => openGroup(activeGroup.id, ch.id),
      });
    });
    scroll.querySelector("#add-voice")?.addEventListener("click", () => {
      openCreateChannelModal(activeGroup, "voice", {
        onCreated: (ch) => openGroup(activeGroup.id, ch.id),
      });
    });
    scroll.querySelectorAll("[data-channel]").forEach((button) => {
      button.addEventListener("click", () => openChannel(Number(button.dataset.channel)));
    });
  }

  function paintMembers() {
    if (!activeGroup || mode === "dm" || mode === "home") {
      setMembersVisible(false);
      return;
    }
    setMembersVisible(true);
    const online = members.filter((m) => m.is_online && !offlineIds.has(m.id));
    const offline = members.filter((m) => !m.is_online || offlineIds.has(m.id));
    const section = (title, list) => `
      <div class="members-cat">${title} — ${list.length}</div>
      ${list
        .map((m) => {
          const presence = m.presence || (m.is_online ? "online" : "offline");
          const status = m.status_text ? ` · ${escapeHtml(m.status_text)}` : "";
          return `
        <button type="button" class="member-row" data-dm-user="${m.id}" title="Abrir DM">
          ${avatarHtml(m, m.is_online && !offlineIds.has(m.id), presence)}
          <div>
            <strong>${escapeHtml(m.nickname)}</strong>
            <span>@${escapeHtml(m.username)}${status}</span>
          </div>
        </button>`;
        })
        .join("")}
    `;
    membersScroll.innerHTML = `
      ${section("Online", online)}
      ${section("Offline", offline)}
    `;
    membersScroll.querySelectorAll("[data-dm-user]").forEach((btn) => {
      btn.addEventListener("click", () => openDmWith(Number(btn.dataset.dmUser)));
    });
  }

  function paintDmList() {
    titleEl.textContent = "Mensagens diretas";
    settingsBtn.hidden = true;
    setMembersVisible(false);
    scroll.innerHTML = `
      <div class="cat">Conversas</div>
      ${
        dms
          .map(
            (dm) => `
          <button type="button" class="channel-item dm-item ${activeDm?.id === dm.id ? "active" : ""}" data-dm="${dm.id}">
            ${avatarHtml(dm.other, dm.other.is_online)}
            <span class="dm-name">${escapeHtml(dm.other.nickname)}</span>
          </button>`
          )
          .join("") ||
        `<p class="side-empty">Nenhuma DM ainda. Abra um grupo e clique num membro.</p>`
      }
      <div class="cat">Convite de grupo</div>
      <form id="join-form" class="join-card">
        <input name="code" placeholder="GRP-XXXXXXXX" maxlength="64" autocomplete="off" />
        <button class="btn btn-primary" type="submit">Entrar</button>
      </form>
    `;
    scroll.querySelectorAll("[data-dm]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const dm = dms.find((d) => d.id === Number(btn.dataset.dm));
        if (dm) openDm(dm);
      });
    });
    scroll.querySelector("#join-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const code = String(new FormData(event.target).get("code") || "").trim();
      if (!code) return;
      await joinByCode(code);
    });
  }

  async function showHome() {
    mode = "home";
    activeChannel = null;
    activeDm = null;
    activeGroup = null;
    paintRail();
    composer.hidden = true;
    searchBtn.hidden = true;
    typingLine.hidden = true;
    setMembersVisible(false);
    await loadDms();
    paintDmList();
    headerEl.innerHTML = `<span class="header-title">Home · THE GANG</span>`;
    messagesEl.innerHTML = `<div class="home-loading">Carregando a Home…</div>`;
    try {
      const [home, stats] = await Promise.all([
        api("/api/home"),
        api("/api/events/stats").catch(() => null),
      ]);
      paintHome(home, stats);
    } catch (error) {
      messagesEl.innerHTML = `<p class="gs-empty">${escapeHtml(error.message)}</p>`;
    }
  }

  function paintHome(home, stats = null) {
    const eventWhen = home.next_event_at
      ? `${formatDay(home.next_event_at)} · ${formatTime(home.next_event_at)}`
      : "Horário a confirmar";
    const online = home.online || [];
    const s = stats || {};
    messagesEl.innerHTML = `
      <div class="gang-home">
        <section class="gang-banner">
          <div class="gang-banner-glow" aria-hidden="true"></div>
          <div class="gang-logo-anim" aria-hidden="true">
            <span class="gang-logo-ring"></span>
            <span class="gang-logo-core">TG</span>
          </div>
          <div class="gang-banner-copy">
            <p class="gang-kicker">HOME</p>
            <h2>${escapeHtml(home.banner_title || "THE GANG")}</h2>
            <p>${escapeHtml(home.banner_subtitle || "Tropa Free Fire")}</p>
          </div>
          ${
            user.is_admin
              ? `<button type="button" class="btn btn-secondary gang-banner-edit" id="home-edit">Editar Home</button>`
              : ""
          }
        </section>

        <section class="gang-stats-strip">
          <div><strong>${s.wins ?? 0}</strong><span>Vitórias</span></div>
          <div><strong>${s.booyah_total ?? 0}</strong><span>Booyah</span></div>
          <div><strong>${s.kills_total ?? 0}</strong><span>Kills</span></div>
          <div><strong>${s.points_total ?? 0}</strong><span>Pontos</span></div>
          <div><strong>${s.events_total ?? 0}</strong><span>Eventos</span></div>
        </section>

        <div class="gang-emoji-home">
          ${gangEmojiPickerHtml()}
        </div>

        <div class="gang-home-grid">
          <section class="gang-card gang-note">
            <h3>Recado do admin</h3>
            <p>${escapeHtml(home.admin_note || "Sem recado por enquanto.")}</p>
          </section>

          <section class="gang-card gang-event">
            <h3>Próximo scrim / ranked</h3>
            <strong>${escapeHtml(home.next_event_title || "Nenhum evento marcado")}</strong>
            <span>${escapeHtml(home.next_event_title ? eventWhen : "Peça ao admin para marcar.")}</span>
          </section>

          <section class="gang-card gang-online">
            <h3>Quem tá online — ${online.length}</h3>
            <div class="gang-online-list">
              ${
                online
                  .map(
                    (m) => `
                  <button type="button" class="gang-online-row" data-dm-user="${m.id}">
                    ${avatarHtml(m, true, m.presence)}
                    <div>
                      <strong>${escapeHtml(m.nickname)}${m.is_admin ? " ♛" : ""}</strong>
                      <span>${
                        m.ff_role
                          ? escapeHtml(ffRoleLabel(m.ff_role))
                          : `@${escapeHtml(m.username)}`
                      }${m.status_text ? ` · ${escapeHtml(m.status_text)}` : ""}</span>
                    </div>
                  </button>`
                  )
                  .join("") || `<p class="hint">Ninguém online agora.</p>`
              }
            </div>
          </section>

          <section class="gang-card gang-profile-card banner-theme-${escapeAttr(user.banner_theme || "gold")}">
            <h3>Seu perfil FF</h3>
            <strong>${escapeHtml(user.ff_nick || user.nickname)}</strong>
            <span>${
              user.ff_id ? `ID ${escapeHtml(user.ff_id)}` : "ID Free Fire não preenchido"
            }</span>
            <span>${
              user.ff_role ? escapeHtml(ffRoleLabel(user.ff_role)) : "Função não definida"
            }${user.ff_region ? ` · ${escapeHtml(user.ff_region)}` : ""}</span>
            <button type="button" class="btn btn-secondary" id="home-open-profile">Completar perfil</button>
          </section>
        </div>

        ${
          user.is_admin
            ? `<div class="welcome-actions home-admin-actions">
                <button type="button" class="btn btn-primary" id="welcome-create">Criar grupo</button>
              </div>`
            : ""
        }

        <form id="home-edit-form" class="gang-home-edit" hidden>
          <h3>Editar Home THE GANG</h3>
          <label>Título do banner
            <input name="banner_title" maxlength="80" value="${escapeAttr(home.banner_title || "")}" required />
          </label>
          <label>Subtítulo
            <input name="banner_subtitle" maxlength="160" value="${escapeAttr(home.banner_subtitle || "")}" />
          </label>
          <label>Recado do admin
            <textarea name="admin_note" rows="3" maxlength="2000">${escapeHtml(home.admin_note || "")}</textarea>
          </label>
          <label>Próximo evento
            <input name="next_event_title" maxlength="120" value="${escapeAttr(home.next_event_title || "")}" placeholder="ex: Ranked / Scrim vs X" />
          </label>
          <label>Data e hora
            <input name="next_event_at" type="datetime-local" value="${escapeAttr(toLocalInput(home.next_event_at))}" />
          </label>
          <div class="modal-actions" style="justify-content:flex-start">
            <button class="btn btn-primary" type="submit">Salvar Home</button>
            <button class="btn btn-secondary" type="button" id="home-edit-cancel">Cancelar</button>
          </div>
        </form>
      </div>
    `;

    messagesEl.querySelector("#welcome-create")?.addEventListener("click", () => {
      openCreateGroupModal({ onCreated: () => loadGroups(true) });
    });
    messagesEl.querySelector("#home-open-profile")?.addEventListener("click", () => {
      onOpenSettings?.("perfil");
    });
    messagesEl.querySelectorAll("[data-dm-user]").forEach((btn) => {
      btn.addEventListener("click", () => openDmWith(Number(btn.dataset.dmUser)));
    });

    const editForm = messagesEl.querySelector("#home-edit-form");
    messagesEl.querySelector("#home-edit")?.addEventListener("click", () => {
      editForm.hidden = false;
      editForm.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    messagesEl.querySelector("#home-edit-cancel")?.addEventListener("click", () => {
      editForm.hidden = true;
    });
    editForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(editForm);
      const local = String(data.get("next_event_at") || "").trim();
      try {
        const updated = await api("/api/home", {
          method: "PATCH",
          body: {
            banner_title: String(data.get("banner_title") || "").trim(),
            banner_subtitle: String(data.get("banner_subtitle") || "").trim(),
            admin_note: String(data.get("admin_note") || "").trim(),
            next_event_title: String(data.get("next_event_title") || "").trim() || null,
            next_event_at: local ? new Date(local).toISOString() : null,
          },
        });
        toast("Home atualizada.");
        const stats = await api("/api/events/stats").catch(() => null);
        paintHome(updated, stats);
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  function toLocalInput(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  async function openGroup(groupId, preferChannelId = null) {
    activeGroup = groups.find((g) => g.id === groupId) || null;
    activeDm = null;
    if (!activeGroup) return;
    paintRail();
    titleEl.textContent = activeGroup.name;
    settingsBtn.hidden = false;
    try {
      [channels, members] = await Promise.all([
        api(`/api/groups/${groupId}/channels`),
        api(`/api/groups/${groupId}/members`),
      ]);
      paintChannels();
      paintMembers();
      const prefer =
        channels.find((c) => c.id === preferChannelId) ||
        channels.find((c) => c.channel_type === "text") ||
        channels[0];
      if (prefer) await openChannel(prefer.id);
      else {
        activeChannel = null;
        mode = "channel";
        composer.hidden = true;
        messagesEl.innerHTML = `<p class="hint" style="padding:16px">Grupo sem canais ainda.</p>`;
      }
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function openChannel(channelId) {
    activeChannel = channels.find((c) => c.id === channelId) || null;
    activeDm = null;
    mode = "channel";
    if (!activeChannel || !activeGroup) return;
    paintChannels();
    paintMembers();
    typingUsers.clear();
    updateTyping();

    setReply(null);
    pinsBar.hidden = true;
    if (activeChannel.channel_type === "voice") {
      composer.hidden = true;
      searchBtn.hidden = true;
      subscribeChannel(channelId);
      headerEl.innerHTML = `<span>🔊</span><span>${escapeHtml(activeChannel.name)}</span>`;
      const canJoin = can(activeGroup.my_permissions, Perm.CONNECT_VOICE);
      messagesEl.innerHTML = `
        <div class="welcome">
          <div class="welcome-badge">🎙️</div>
          <h2>${escapeHtml(activeChannel.name)}</h2>
          <p>Call ao vivo + eventos Diário / Intensivo / Campeonato.</p>
          <div class="welcome-actions">
            <button type="button" class="btn btn-primary" id="join-call" ${canJoin ? "" : "disabled"}>
              ${canJoin ? "Entrar na call" : "Sem permissão de voz"}
            </button>
          </div>
        </div>
      `;
      messagesEl.querySelector("#join-call")?.addEventListener("click", async () => {
        await startVoiceCall(activeChannel, messagesEl, {
          user,
          group: activeGroup,
        });
      });
      return;
    }

    composer.hidden = !can(activeGroup.my_permissions, Perm.SEND_MESSAGES);
    searchBtn.hidden = false;
    headerEl.innerHTML = `
      <span class="hash">#</span>
      <span class="header-title">${escapeHtml(activeChannel.name)}</span>
      <div class="header-actions">
        <button type="button" class="icon-btn" id="pins-btn" title="Fixadas">📌</button>
        <button type="button" class="icon-btn" id="search-btn-inner" title="Buscar">⌕</button>
      </div>
    `;
    headerEl.querySelector("#search-btn-inner")?.addEventListener("click", openSearch);
    headerEl.querySelector("#pins-btn")?.addEventListener("click", togglePins);
    messagesEl.innerHTML = `<p class="hint" style="padding:12px;text-transform:none">Carregando…</p>`;
    try {
      [messages, pinned] = await Promise.all([
        api(`/api/channels/${channelId}/messages?limit=50`),
        api(`/api/channels/${channelId}/pins`).catch(() => []),
      ]);
      paintPins();
      renderMessages();
      subscribeChannel(channelId);
      markRead(messages);
    } catch (error) {
      messagesEl.innerHTML = `<p class="hint" style="padding:12px">${escapeHtml(error.message)}</p>`;
    }
  }

  function paintPins() {
    if (!pinned.length || mode !== "channel") {
      pinsBar.hidden = true;
      return;
    }
    pinsBar.hidden = false;
    pinsBar.innerHTML = pinned
      .slice(0, 3)
      .map(
        (m) => `
      <button type="button" class="pin-chip" data-jump="${m.id}">
        📌 <strong>${escapeHtml(m.sender?.nickname || "")}</strong>
        <span>${escapeHtml((m.content || "").slice(0, 48))}</span>
      </button>`
      )
      .join("");
    pinsBar.querySelectorAll("[data-jump]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const el = messagesEl.querySelector(`[data-msg="${btn.dataset.jump}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
        el?.classList.add("flash");
        setTimeout(() => el?.classList.remove("flash"), 1200);
      });
    });
  }

  async function togglePins() {
    if (!activeChannel) return;
    try {
      pinned = await api(`/api/channels/${activeChannel.id}/pins`);
      paintPins();
      pinsBar.hidden = !pinned.length ? true : !pinsBar.hidden;
      if (!pinned.length) toast("Nenhuma mensagem fixada.");
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function openDmWith(userId) {
    if (userId === user.id) return;
    try {
      const conv = await api("/api/dm", { method: "POST", body: { user_id: userId } });
      await loadDms();
      openDm(conv);
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function openDm(conv) {
    activeDm = conv;
    activeGroup = null;
    activeChannel = null;
    mode = "dm";
    paintRail();
    paintDmList();
    setMembersVisible(false);
    composer.hidden = false;
    searchBtn.hidden = true;
    headerEl.innerHTML = `
      ${avatarHtml(conv.other, conv.other.is_online)}
      <span>${escapeHtml(conv.other.nickname)}</span>
      <span class="sub">@${escapeHtml(conv.other.username)}</span>
    `;
    messagesEl.innerHTML = `<p class="hint" style="padding:12px;text-transform:none">Carregando…</p>`;
    try {
      messages = await api(`/api/dm/${conv.id}/messages?limit=50`);
      renderMessages();
      subscribeDm(conv.id);
      markRead(messages);
    } catch (error) {
      messagesEl.innerHTML = `<p class="hint" style="padding:12px">${escapeHtml(error.message)}</p>`;
    }
  }

  function renderMessages() {
    if (!messages.length) {
      const title =
        mode === "dm"
          ? `@${activeDm?.other?.username || ""}`
          : `#${activeChannel?.name || ""}`;
      messagesEl.innerHTML = `
        <div class="welcome">
          <h2>${escapeHtml(title)}</h2>
          <p>Mande a primeira mensagem.</p>
        </div>
      `;
      return;
    }
    let html = "";
    let lastDay = "";
    let lastSender = null;
    let lastTs = 0;
    for (const message of messages) {
      const day = formatDay(message.created_at);
      if (day !== lastDay) {
        html += `<div class="day-sep"><span>${day}</span></div>`;
        lastDay = day;
        lastSender = null;
      }
      const ts = new Date(message.created_at).getTime();
      const compact =
        lastSender === message.sender.id &&
        !message.reply_to_id &&
        ts - lastTs < 7 * 60 * 1000;
      html += messageHtml(message, user, { compact });
      lastSender = message.sender.id;
      lastTs = ts;
    }
    messagesEl.innerHTML = html;
    messagesEl.scrollTop = messagesEl.scrollHeight;
    bindMessageActions();
  }

  function bindMessageActions() {
    messagesEl.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => editMessage(Number(btn.dataset.edit)));
    });
    messagesEl.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", () => deleteMessage(Number(btn.dataset.del)));
    });
    messagesEl.querySelectorAll("[data-reply]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = messages.find((m) => m.id === Number(btn.dataset.reply));
        if (msg) setReply(msg);
      });
    });
    messagesEl.querySelectorAll("[data-pin]").forEach((btn) => {
      btn.addEventListener("click", () => togglePin(Number(btn.dataset.pin), true));
    });
    messagesEl.querySelectorAll("[data-unpin]").forEach((btn) => {
      btn.addEventListener("click", () => togglePin(Number(btn.dataset.unpin), false));
    });
    messagesEl.querySelectorAll("[data-react]").forEach((btn) => {
      btn.addEventListener("click", () => react(Number(btn.dataset.react), btn.dataset.emoji));
    });
    messagesEl.querySelectorAll("[data-add-react]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.stopPropagation();
        const msgId = Number(btn.dataset.addReact);
        document.querySelectorAll(".react-pack-pop").forEach((el) => el.remove());
        const pop = document.createElement("div");
        pop.className = "react-pack-pop";
        pop.innerHTML = gangEmojiPickerHtml();
        btn.closest(".msg-toolbar")?.appendChild(pop);
        pop.querySelectorAll("[data-gang-emoji]").forEach((emojiBtn) => {
          emojiBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            await react(msgId, emojiBtn.dataset.gangEmoji);
            pop.remove();
          });
        });
        const close = (ev) => {
          if (!pop.contains(ev.target) && ev.target !== btn) {
            pop.remove();
            document.removeEventListener("click", close);
          }
        };
        setTimeout(() => document.addEventListener("click", close), 0);
      });
    });
  }

  async function react(messageId, emoji) {
    try {
      const updated = await api(`/api/messages/${messageId}/reactions`, {
        method: "POST",
        body: { emoji },
      });
      upsertMessage(updated);
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function togglePin(messageId, pinnedFlag) {
    try {
      const updated = await api(`/api/messages/${messageId}/pin`, {
        method: pinnedFlag ? "POST" : "DELETE",
      });
      upsertMessage(updated);
      if (activeChannel) {
        pinned = await api(`/api/channels/${activeChannel.id}/pins`).catch(() => []);
        paintPins();
      }
      toast(pinnedFlag ? "Mensagem fixada." : "Pin removido.");
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function editMessage(id) {
    const msg = messages.find((m) => m.id === id);
    if (!msg) return;
    const next = window.prompt("Editar mensagem:", msg.content);
    if (next == null || !next.trim()) return;
    try {
      const updated = await api(`/api/messages/${id}`, {
        method: "PATCH",
        body: { content: next.trim() },
      });
      upsertMessage(updated);
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function deleteMessage(id) {
    if (!window.confirm("Apagar esta mensagem?")) return;
    try {
      await api(`/api/messages/${id}`, { method: "DELETE" });
      messages = messages.filter((m) => m.id !== id);
      renderMessages();
    } catch (error) {
      toast(error.message, true);
    }
  }

  function upsertMessage(message) {
    const idx = messages.findIndex((m) => m.id === message.id);
    if (idx >= 0) messages[idx] = message;
    else messages.push(message);
    messages.sort((a, b) => a.id - b.id);
    renderMessages();
  }

  function messageBelongsHere(message, event = {}) {
    if (mode === "channel" && activeChannel) {
      return message.channel_id === activeChannel.id || event.channel_id === activeChannel.id;
    }
    if (mode === "dm" && activeDm) {
      return event.dm_id === activeDm.id || (!message.channel_id && event.dm_id);
    }
    return false;
  }

  function handleWsEvent(event) {
    if (event.type === "hello") {
      const onlineSet = new Set(event.online_user_ids || []);
      if (event.user_id) onlineSet.add(event.user_id);
      offlineIds = new Set();
      members = members.map((m) => ({
        ...m,
        is_online: onlineSet.has(m.id),
      }));
      paintMembers();
      return;
    }
    if (event.type === "presence" || event.type === "status") {
      if (event.is_online) offlineIds.delete(event.user_id);
      else offlineIds.add(event.user_id);
      members = members.map((m) =>
        m.id === event.user_id
          ? {
              ...m,
              is_online: !!event.is_online,
              presence: event.presence || m.presence,
              status_text: event.status_text !== undefined ? event.status_text : m.status_text,
            }
          : m
      );
      paintMembers();
      return;
    }
    if (event.type === "message") {
      const msg = event.message;
      if (!msg) return;
      if (msg.sender?.id !== user.id) {
        const mention = new RegExp(`@${user.username}\\b`, "i");
        if (mention.test(msg.content || "")) playMention();
      }
      if (mode === "channel" && msg.channel_id === activeChannel?.id) {
        upsertMessage(msg);
        markRead([msg]);
      } else if (mode === "dm" && event.dm_id === activeDm?.id) {
        upsertMessage(msg);
        markRead([msg]);
      }
      return;
    }
    if (event.type === "message_update") {
      const msg = event.message;
      if (msg && messages.some((m) => m.id === msg.id)) upsertMessage(msg);
      return;
    }
    if (event.type === "message_delete") {
      if (
        (mode === "channel" && event.channel_id === activeChannel?.id) ||
        (mode === "dm" && event.dm_id === activeDm?.id)
      ) {
        messages = messages.filter((m) => m.id !== event.id);
        renderMessages();
      }
      return;
    }
    if (event.type === "typing") {
      if (event.user_id === user.id) return;
      const ok =
        (mode === "channel" && event.channel_id === activeChannel?.id) ||
        (mode === "dm" && event.dm_id === activeDm?.id);
      if (!ok) return;
      const member =
        members.find((m) => m.id === event.user_id) ||
        (activeDm?.other?.id === event.user_id ? activeDm.other : null);
      typingUsers.set(event.user_id, {
        name: member?.nickname || "Alguém",
        until: Date.now() + 3000,
      });
      updateTyping();
    }
  }

  function updateTyping() {
    const now = Date.now();
    for (const [id, info] of [...typingUsers.entries()]) {
      if (info.until < now) typingUsers.delete(id);
    }
    const names = [...typingUsers.values()].map((t) => t.name);
    if (!names.length) {
      typingLine.hidden = true;
      typingLine.textContent = "";
      return;
    }
    typingLine.hidden = false;
    typingLine.textContent =
      names.length === 1
        ? `${names[0]} está digitando…`
        : `${names.slice(0, 2).join(", ")} estão digitando…`;
    setTimeout(updateTyping, 1000);
  }

  async function markRead(list) {
    const ids = list.filter((m) => m.sender?.id !== user.id).map((m) => m.id);
    if (!ids.length) return;
    try {
      await api("/api/messages/read", { method: "POST", body: { message_ids: ids } });
    } catch {
      /* ignore */
    }
  }

  async function onAttach() {
    const file = attachInput.files?.[0];
    attachInput.value = "";
    if (!file) return;
    if (mode !== "channel" && mode !== "dm") return;
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await apiUpload("/api/uploads/chat-image", form);
      const content = String(composerInput.value || "").trim();
      await sendMessage(content, uploaded.url, uploaded.mime);
      composerInput.value = "";
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function sendMessage(content, attachmentUrl = null, attachmentType = null) {
    if (!content && !attachmentUrl) return;
    const payload = {
      content: content || "",
      attachment_url: attachmentUrl,
      attachment_type: attachmentType,
      reply_to_id: replyTo?.id || null,
    };
    if (mode === "channel" && activeChannel) {
      const message = await api(`/api/channels/${activeChannel.id}/messages`, {
        method: "POST",
        body: payload,
      });
      upsertMessage(message);
      setReply(null);
      return;
    }
    if (mode === "dm" && activeDm) {
      const message = await api(`/api/dm/${activeDm.id}/messages`, {
        method: "POST",
        body: payload,
      });
      upsertMessage(message);
      setReply(null);
    }
  }

  composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = String(composerInput.value || "").trim();
    if (!content) return;
    try {
      await sendMessage(content);
      composer.reset();
    } catch (error) {
      toast(error.message, true);
    }
  });

  composerInput.addEventListener("input", () => {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      if (mode === "channel" && activeChannel) {
        sendTyping({ channelId: activeChannel.id });
      } else if (mode === "dm" && activeDm) {
        sendTyping({
          dmId: activeDm.id,
          peerIds: [user.id, activeDm.other.id],
        });
      }
    }, 200);
  });

  async function openSearch() {
    if (!activeGroup || !activeChannel) return;
    const q = window.prompt("Buscar mensagens (ou @usuario):");
    if (!q || q.trim().length < 2) return;
    try {
      const results = await api(
        `/api/messages/search?group_id=${activeGroup.id}&q=${encodeURIComponent(q.trim())}`
      );
      if (!results.length) {
        toast("Nada encontrado.");
        return;
      }
      messagesEl.innerHTML = `
        <div class="search-results">
          <h3>Resultados (${results.length})</h3>
          ${results.map((m) => messageHtml(m, user)).join("")}
          <button type="button" class="btn btn-ghost" id="back-channel">Voltar ao canal</button>
        </div>
      `;
      messagesEl.querySelector("#back-channel")?.addEventListener("click", () =>
        openChannel(activeChannel.id)
      );
      bindMessageActions();
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function joinByCode(code) {
    try {
      const group = await api("/api/groups/join", { method: "POST", body: { code } });
      sessionStorage.removeItem("tg_join_code");
      toast(`Entrou em ${group.name}.`);
      await loadGroups();
      await openGroup(group.id);
    } catch (error) {
      toast(error.message, true);
    }
  }

  rail.addEventListener("click", (event) => {
    const button = event.target.closest("[data-group]");
    if (!button) return;
    openGroup(Number(button.dataset.group));
  });

  async function loadDms() {
    try {
      dms = await api("/api/dm");
    } catch {
      dms = [];
    }
  }

  async function loadGroups(selectNewest = false) {
    groups = await api("/api/groups");
    paintRail();
    if (pendingJoin) {
      const code = pendingJoin;
      pendingJoin = null;
      await joinByCode(code);
      return;
    }
    if (!groups.length) {
      await showHome();
      return;
    }
    if (selectNewest) {
      await openGroup(groups[groups.length - 1].id);
      return;
    }
    if (activeGroup && groups.some((g) => g.id === activeGroup.id)) {
      await openGroup(activeGroup.id, activeChannel?.id);
      return;
    }
    const defaultGroup =
      groups.find((g) => g.name === "the-gang") || groups[0];
    if (defaultGroup) {
      await openGroup(defaultGroup.id);
      return;
    }
    await showHome();
  }

  (async () => {
    try {
      await loadGroups();
    } catch (error) {
      toast(error.message, true);
      await showHome();
    }
  })();

  container._cleanup = () => {
    offWs();
    leaveVoiceCall();
  };
}

function messageHtml(message, me, { compact = false } = {}) {
  const crown = message.sender.is_admin ? `<span class="crown" title="Admin">♛</span>` : "";
  const edited = message.edited_at ? `<span class="edited">(editada)</span>` : "";
  const pinned = message.pinned_at ? `<span class="pin-tag" title="Fixada">📌</span>` : "";
  const mine = message.sender.id === me.id;
  const attach = message.attachment_url
    ? `<a class="msg-image" href="${escapeAttr(mediaUrl(message.attachment_url))}" target="_blank" rel="noopener"><img src="${escapeAttr(mediaUrl(message.attachment_url))}" alt="" /></a>`
    : "";
  const reply = message.reply_to
    ? `<button type="button" class="reply-preview" data-jump-reply="${message.reply_to.id}">
        <strong>${escapeHtml(message.reply_to.sender_nickname)}</strong>
        <span>${escapeHtml(message.reply_to.content)}</span>
      </button>`
    : "";
  const reactionList = message.reactions || [];
  const reactions = reactionList.length
    ? `<div class="react-row">${reactionList
        .map(
          (r) => `
        <button type="button" class="react-chip ${r.me ? "mine" : ""}" data-react="${message.id}" data-emoji="${escapeAttr(r.emoji)}">
          <span class="react-emoji">${escapeHtml(r.emoji)}</span><span class="react-count">${r.count}</span>
        </button>`
        )
        .join("")}</div>`
    : "";
  const quick = QUICK_EMOJIS.map(
    (e) =>
      `<button type="button" class="react-quick" data-react="${message.id}" data-emoji="${e}" title="${e}">${e}</button>`
  ).join("");
  const actions = `
    <div class="msg-toolbar" role="toolbar">
      <div class="msg-reacts">${quick}</div>
      <button type="button" data-add-react="${message.id}" title="Reagir">😀</button>
      <button type="button" data-reply="${message.id}" title="Responder">↩</button>
      ${
        message.pinned_at
          ? `<button type="button" data-unpin="${message.id}" title="Desafixar">📌</button>`
          : `<button type="button" data-pin="${message.id}" title="Fixar">📌</button>`
      }
      ${mine ? `<button type="button" data-edit="${message.id}" title="Editar">✎</button>` : ""}
      <button type="button" data-del="${message.id}" title="Apagar">🗑</button>
    </div>`;
  if (compact) {
    return `
      <article class="message compact ${message.pinned_at ? "is-pinned" : ""}" data-msg="${message.id}">
        <time class="msg-time-gutter" title="${escapeAttr(formatTime(message.created_at))}">${formatTime(message.created_at)}</time>
        <div class="msg-main">
          ${actions}
          ${reply}
          <div class="body">${formatContent(message.content)}</div>
          ${attach}
          ${reactions}
        </div>
      </article>`;
  }
  return `
    <article class="message ${message.pinned_at ? "is-pinned" : ""}" data-msg="${message.id}">
      ${avatarHtml(message.sender, true, message.sender.presence)}
      <div class="msg-main">
        ${actions}
        <div class="head">
          <strong>${escapeHtml(message.sender.nickname)}</strong>
          ${crown}${pinned}
          <time>${formatTime(message.created_at)}</time>
          ${edited}
        </div>
        ${reply}
        <div class="body">${formatContent(message.content)}</div>
        ${attach}
        ${reactions}
      </div>
    </article>
  `;
}

function formatContent(content) {
  const escaped = escapeHtml(content);
  return escaped.replace(/@([a-z0-9_]{3,32})/gi, '<span class="mention">@$1</span>');
}

function avatarHtml(person, online = true, presence = "online") {
  const url = mediaUrl(person.avatar_url);
  const inner = url
    ? `<img src="${escapeAttr(url)}" alt="" class="avatar-img" />`
    : initials(person.nickname);
  let dotClass = "dot off";
  if (online && presence !== "invisible") {
    if (presence === "dnd") dotClass = "dot dnd";
    else if (presence === "away") dotClass = "dot away";
    else dotClass = "dot";
  }
  return `<div class="avatar">${inner}<span class="${dotClass}"></span></div>`;
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
