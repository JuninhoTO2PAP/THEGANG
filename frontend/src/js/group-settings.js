/** Configurações do grupo — painel grande estilo Discord. */

import { api, mediaUrl } from "./api.js";
import { closeModal } from "./modal.js";
import { PERM_OPTIONS, Perm, can } from "./perms.js";
import { initials, toast } from "./ui.js";

const TABS = [
  { id: "overview", label: "Visão geral", icon: "🏠" },
  { id: "cargos", label: "Cargos", icon: "🎭" },
  { id: "membros", label: "Membros", icon: "👥" },
  { id: "canais", label: "Canais", icon: "#" },
  { id: "convites", label: "Convites", icon: "🔗" },
];

const COLOR_PRESETS = [
  "#5865f2",
  "#57f287",
  "#fee75c",
  "#eb459e",
  "#ed4245",
  "#f26522",
  "#3ba55d",
  "#1abc9c",
  "#3498db",
  "#9b59b6",
  "#e91e63",
  "#95a5a6",
];

export function openGroupSettings(group, { onChanged, onDeleted }) {
  closeModal();
  document.getElementById("tg-gs")?.remove();

  let tab = "overview";
  let roles = [];
  let members = [];
  let channels = [];
  let selectedRoleId = null;
  let current = { ...group };

  const overlay = document.createElement("div");
  overlay.id = "tg-gs";
  overlay.className = "gs-overlay";
  overlay.innerHTML = `
    <div class="gs-shell" role="dialog" aria-modal="true" aria-label="Configurações do grupo">
      <aside class="gs-nav">
        <div class="gs-nav-brand">
          <div class="gs-nav-icon">${escapeHtml(current.name.slice(0, 2).toUpperCase())}</div>
          <div>
            <strong>${escapeHtml(current.name)}</strong>
            <span>Configurações</span>
          </div>
        </div>
        <nav class="gs-nav-list" id="gs-nav"></nav>
        <button type="button" class="gs-esc" id="gs-close-side">Esc · Fechar</button>
      </aside>
      <section class="gs-main">
        <header class="gs-main-head">
          <div>
            <h2 id="gs-title">Visão geral</h2>
            <p id="gs-sub">Nome, descrição e resumo do grupo.</p>
          </div>
          <button type="button" class="gs-x" id="gs-close" aria-label="Fechar">×</button>
        </header>
        <div class="gs-content" id="gs-body"><p class="gs-loading">Carregando…</p></div>
      </section>
    </div>
  `;
  document.body.appendChild(overlay);

  const nav = overlay.querySelector("#gs-nav");
  const body = overlay.querySelector("#gs-body");
  const titleEl = overlay.querySelector("#gs-title");
  const subEl = overlay.querySelector("#gs-sub");

  function close() {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  }

  function onKey(event) {
    if (event.key === "Escape") close();
  }

  overlay.querySelector("#gs-close").addEventListener("click", close);
  overlay.querySelector("#gs-close-side").addEventListener("click", close);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) close();
  });
  document.addEventListener("keydown", onKey);

  function paintNav() {
    nav.innerHTML = TABS.map(
      (item) => `
        <button type="button" data-tab="${item.id}" class="${item.id === tab ? "active" : ""}">
          <span class="gs-nav-ico">${item.icon}</span>
          <span>${item.label}</span>
        </button>`
    ).join("");
  }

  const SUBS = {
    overview: "Nome, descrição e resumo do grupo.",
    cargos: "Crie cargos, defina cor e permissões granulares.",
    membros: "Veja quem está no grupo e atribua cargos.",
    canais: "Canais de texto e salas de voz.",
    convites: "Links para entrar neste grupo.",
  };

  function setTab(next) {
    tab = next;
    titleEl.textContent = TABS.find((t) => t.id === tab)?.label || "";
    subEl.textContent = SUBS[tab] || "";
    paintNav();
    paint();
  }

  async function load() {
    try {
      [roles, members, channels] = await Promise.all([
        api(`/api/groups/${current.id}/roles`),
        api(`/api/groups/${current.id}/members`),
        api(`/api/groups/${current.id}/channels`),
      ]);
      if (selectedRoleId && !roles.some((r) => r.id === selectedRoleId)) {
        selectedRoleId = null;
      }
      paint();
    } catch (error) {
      body.innerHTML = `<p class="gs-empty">${escapeHtml(error.message)}</p>`;
    }
  }

  function paint() {
    if (tab === "overview") paintOverview();
    else if (tab === "cargos") paintRoles();
    else if (tab === "membros") paintMembers();
    else if (tab === "canais") paintChannels();
    else paintInvites();
  }

  function paintOverview() {
    const manage = can(current.my_permissions, Perm.MANAGE_GROUP);
    const isDefault = current.name === "the-gang";
    const texts = channels.filter((c) => c.channel_type === "text").length;
    const voices = channels.filter((c) => c.channel_type === "voice").length;
    body.innerHTML = `
      <div class="gs-stats">
        <div class="gs-stat"><strong>${members.length}</strong><span>Membros</span></div>
        <div class="gs-stat"><strong>${texts}</strong><span>Canais de texto</span></div>
        <div class="gs-stat"><strong>${voices}</strong><span>Canais de voz</span></div>
        <div class="gs-stat"><strong>${roles.length}</strong><span>Cargos</span></div>
      </div>
      <form id="overview-form" class="gs-form ${manage ? "" : "is-locked"}">
        <label>Nome do grupo
          <input name="name" value="${escapeAttr(current.name)}" maxlength="40" ${manage ? "" : "disabled"} required />
        </label>
        <label>Descrição
          <textarea name="description" rows="3" maxlength="255" placeholder="Sobre o time, regras, avisos…" ${manage ? "" : "disabled"}>${escapeHtml(current.description || "")}</textarea>
        </label>
        ${
          manage
            ? `<div class="gs-form-actions">
                <button class="btn btn-primary" type="submit">Salvar alterações</button>
              </div>`
            : `<p class="gs-hint">Só quem gerencia o grupo pode editar estes campos.</p>`
        }
      </form>
      ${
        manage
          ? `<div class="gs-danger-zone">
              <div>
                <strong>Zona de perigo</strong>
                <p>${
                  isDefault
                    ? "O grupo padrão THE GANG não pode ser apagado."
                    : "Apagar o grupo remove canais, mensagens, cargos e convites. Não dá para desfazer."
                }</p>
              </div>
              <button type="button" class="btn-danger-ghost" id="gs-delete-group" ${isDefault ? "disabled" : ""}>
                Excluir grupo
              </button>
            </div>`
          : ""
      }
    `;
    body.querySelector("#overview-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(event.target);
      try {
        const updated = await api(`/api/groups/${current.id}`, {
          method: "PATCH",
          body: {
            name: String(data.get("name") || "").trim(),
            description: String(data.get("description") || "").trim(),
          },
        });
        current = { ...current, ...updated };
        overlay.querySelector(".gs-nav-brand strong").textContent = current.name;
        overlay.querySelector(".gs-nav-icon").textContent = current.name.slice(0, 2).toUpperCase();
        toast("Grupo atualizado.");
        onChanged?.();
      } catch (error) {
        toast(error.message, true);
      }
    });

    body.querySelector("#gs-delete-group")?.addEventListener("click", async () => {
      if (isDefault) return;
      const ok = window.confirm(
        `Excluir o grupo "${current.name}"?\n\nCanais, mensagens e cargos serão apagados para sempre.`
      );
      if (!ok) return;
      const again = window.prompt(`Digite o nome do grupo para confirmar:\n${current.name}`);
      if (again !== current.name) {
        toast("Nome não confere. Grupo não foi apagado.", true);
        return;
      }
      const btn = body.querySelector("#gs-delete-group");
      if (btn) btn.disabled = true;
      try {
        await api(`/api/groups/${current.id}`, { method: "DELETE" });
        toast("Grupo excluído.");
        close();
        onDeleted?.(current);
      } catch (error) {
        toast(error.message, true);
        if (btn) btn.disabled = false;
      }
    });
  }

  function permBitsFromForm(form) {
    let bits = 0;
    form.querySelectorAll("[data-perm]:checked").forEach((input) => {
      bits |= Number(input.dataset.perm);
    });
    return bits;
  }

  function permTogglesHtml(selected = MEMBER_DEFAULT, { disabled = false } = {}) {
    return `
      <div class="gs-perm-grid">
        ${PERM_OPTIONS.map(
          (opt) => `
          <label class="gs-perm ${opt.flag === Perm.ADMINISTRATOR ? "danger" : ""}">
            <div>
              <strong>${escapeHtml(opt.label)}</strong>
              <span>${escapeHtml(opt.help)}</span>
            </div>
            <input type="checkbox" data-perm="${opt.flag}" ${selected & opt.flag ? "checked" : ""} ${disabled ? "disabled" : ""} />
          </label>`
        ).join("")}
      </div>`;
  }

  const MEMBER_DEFAULT =
    Perm.VIEW_CHANNELS | Perm.SEND_MESSAGES | Perm.CONNECT_VOICE;

  function colorPickerHtml(selected = "#5865f2") {
    return `
      <div class="gs-colors">
        ${COLOR_PRESETS.map(
          (c) => `
          <button type="button" class="gs-swatch ${c === selected ? "active" : ""}" data-color="${c}" style="background:${c}" title="${c}"></button>`
        ).join("")}
        <label class="gs-swatch custom" title="Cor custom">
          <input type="color" name="color" value="${escapeAttr(selected)}" />
        </label>
      </div>`;
  }

  function paintRoles() {
    const manage = can(current.my_permissions, Perm.MANAGE_ROLES);
    const selected = roles.find((r) => r.id === selectedRoleId) || null;

    body.innerHTML = `
      <div class="gs-split">
        <div class="gs-split-side">
          <div class="gs-section-label">Cargos do grupo</div>
          <div class="gs-role-list">
            ${roles
              .map(
                (role) => `
              <button type="button" class="gs-role-item ${selectedRoleId === role.id ? "active" : ""}" data-pick-role="${role.id}">
                <span class="role-dot" style="background:${escapeAttr(role.color)}"></span>
                <div>
                  <strong>${escapeHtml(role.name)}</strong>
                  <span>${role.is_default ? "Padrão" : role.permissions & Perm.ADMINISTRATOR ? "Administrador" : `${countPerms(role.permissions)} perms`}</span>
                </div>
              </button>`
              )
              .join("")}
          </div>
          ${
            manage
              ? `<button type="button" class="btn btn-secondary gs-new-role" id="new-role-btn">+ Novo cargo</button>`
              : ""
          }
        </div>
        <div class="gs-split-main" id="role-editor">
          ${
            selected
              ? roleEditorHtml(selected, manage)
              : `<div class="gs-empty-panel">
                  <h3>Selecione um cargo</h3>
                  <p>Escolha à esquerda para ver permissões${manage ? ", ou crie um novo." : "."}</p>
                </div>`
          }
        </div>
      </div>
    `;

    body.querySelectorAll("[data-pick-role]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedRoleId = Number(btn.dataset.pickRole);
        paintRoles();
      });
    });

    body.querySelector("#new-role-btn")?.addEventListener("click", () => {
      selectedRoleId = null;
      body.querySelector("#role-editor").innerHTML = roleCreateHtml();
      bindRoleCreate();
      bindColorPicker(body.querySelector("#role-editor"));
    });

    if (selected) {
      bindRoleEditor(selected, manage);
      bindColorPicker(body.querySelector("#role-editor"));
    }
  }

  function countPerms(bits) {
    return PERM_OPTIONS.filter((o) => bits & o.flag && o.flag !== Perm.ADMINISTRATOR).length;
  }

  function roleCreateHtml() {
    return `
      <form id="role-create" class="gs-form">
        <div class="gs-section-label">Criar cargo</div>
        <label>Nome
          <input name="name" placeholder="ex: Mod, Coach, Capitao" required maxlength="40" />
        </label>
        <div class="gs-field">
          <span class="gs-label">Cor de exibição</span>
          ${colorPickerHtml()}
        </div>
        <div class="gs-field">
          <span class="gs-label">Permissões</span>
          ${permTogglesHtml(MEMBER_DEFAULT)}
        </div>
        <div class="gs-form-actions">
          <button type="button" class="btn btn-ghost" id="cancel-create">Cancelar</button>
          <button class="btn btn-primary" type="submit">Criar cargo</button>
        </div>
      </form>`;
  }

  function roleEditorHtml(role, manage) {
    const renameLocked = role.is_default || !manage;
    const editLocked = !manage;
    return `
      <form id="role-edit" class="gs-form" data-role-id="${role.id}">
        <div class="gs-role-head">
          <span class="role-dot lg" style="background:${escapeAttr(role.color)}"></span>
          <div>
            <h3>${escapeHtml(role.name)}</h3>
            <p>${role.is_default ? "Base de todos os membros — ajuste o que o time pode fazer." : "Edite nome, cor e poderes."}</p>
          </div>
        </div>
        <label>Nome
          <input name="name" value="${escapeAttr(role.name)}" maxlength="40" ${renameLocked ? "disabled" : ""} required />
        </label>
        <div class="gs-field">
          <span class="gs-label">Cor</span>
          ${colorPickerHtml(role.color)}
        </div>
        <div class="gs-field">
          <span class="gs-label">Permissões</span>
          ${permTogglesHtml(role.permissions, { disabled: editLocked })}
        </div>
        ${
          manage && !role.is_default
            ? `<div class="gs-form-actions between">
                <button type="button" class="btn btn-danger-ghost" data-del-role="${role.id}">Apagar cargo</button>
                <button class="btn btn-primary" type="submit">Salvar cargo</button>
              </div>`
            : manage
              ? `<div class="gs-form-actions"><button class="btn btn-primary" type="submit">Salvar permissões</button></div>`
              : `<p class="gs-hint">Sem permissão para editar cargos.</p>`
        }
      </form>`;
  }

  function bindColorPicker(root) {
    const input = root.querySelector('input[name="color"]');
    root.querySelectorAll("[data-color]").forEach((btn) => {
      btn.addEventListener("click", () => {
        root.querySelectorAll(".gs-swatch").forEach((s) => s.classList.remove("active"));
        btn.classList.add("active");
        if (input) input.value = btn.dataset.color;
      });
    });
    input?.addEventListener("input", () => {
      root.querySelectorAll(".gs-swatch[data-color]").forEach((s) => s.classList.remove("active"));
    });
  }

  function bindRoleCreate() {
    body.querySelector("#cancel-create")?.addEventListener("click", () => paintRoles());
    body.querySelector("#role-create")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.target;
      const data = new FormData(form);
      const permissions = permBitsFromForm(form);
      const isAdmin = Boolean(permissions & Perm.ADMINISTRATOR);
      try {
        const created = await api(`/api/groups/${current.id}/roles`, {
          method: "POST",
          body: {
            name: String(data.get("name") || "").trim(),
            color: String(data.get("color") || "#5865f2"),
            is_admin: isAdmin,
            permissions: isAdmin ? 0 : permissions,
          },
        });
        toast("Cargo criado.");
        selectedRoleId = created.id;
        await load();
        onChanged?.();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  function bindRoleEditor(role, manage) {
    body.querySelector("#role-edit")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!manage) return;
      const form = event.target;
      const data = new FormData(form);
      const permissions = permBitsFromForm(form);
      const isAdmin = Boolean(permissions & Perm.ADMINISTRATOR);
      const payload = {
        color: String(data.get("color") || role.color),
        is_admin: isAdmin,
        permissions: isAdmin ? Perm.ADMINISTRATOR : permissions,
      };
      if (!role.is_default) {
        payload.name = String(data.get("name") || "").trim();
      }
      try {
        await api(`/api/groups/${current.id}/roles/${role.id}`, {
          method: "PATCH",
          body: payload,
        });
        toast("Cargo salvo.");
        await load();
        onChanged?.();
      } catch (error) {
        toast(error.message, true);
      }
    });

    body.querySelector("[data-del-role]")?.addEventListener("click", async (event) => {
      if (!window.confirm("Apagar este cargo? Membros perdem essa atribuição.")) return;
      try {
        await api(`/api/groups/${current.id}/roles/${event.currentTarget.dataset.delRole}`, {
          method: "DELETE",
        });
        toast("Cargo removido.");
        selectedRoleId = null;
        await load();
        onChanged?.();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  function paintMembers() {
    const manage = can(current.my_permissions, Perm.MANAGE_ROLES);
    const assignable = roles.filter((role) => !role.is_default);
    body.innerHTML = `
      <div class="gs-toolbar">
        <input type="search" id="member-filter" placeholder="Filtrar por nome ou @" />
        <span class="gs-count">${members.length} membros</span>
      </div>
      <div class="gs-member-list" id="member-list">
        ${members.map((m) => memberCard(m, assignable, manage)).join("") || `<p class="gs-empty">Nenhum membro.</p>`}
      </div>
    `;

    body.querySelector("#member-filter")?.addEventListener("input", (event) => {
      const q = event.target.value.trim().toLowerCase();
      body.querySelectorAll(".gs-member-card").forEach((card) => {
        const hay = card.dataset.search || "";
        card.hidden = Boolean(q) && !hay.includes(q);
      });
    });

    body.querySelectorAll("[data-save-roles]").forEach((button) => {
      button.addEventListener("click", async () => {
        const userId = Number(button.dataset.saveRoles);
        const roleIds = [
          ...body.querySelectorAll(`input[data-user="${userId}"]:checked`),
        ].map((input) => Number(input.dataset.role));
        try {
          await api(`/api/groups/${current.id}/members/${userId}/roles`, {
            method: "PUT",
            body: { role_ids: roleIds },
          });
          toast("Cargos atualizados.");
          await load();
          onChanged?.();
        } catch (error) {
          toast(error.message, true);
        }
      });
    });
  }

  function memberCard(member, assignable, manage) {
    const url = mediaUrl(member.avatar_url);
    const avatar = url
      ? `<img src="${escapeAttr(url)}" class="avatar-img" alt="" />`
      : initials(member.nickname);
    const online = member.is_online ? "online" : "offline";
    const selects = assignable
      .map(
        (role) => `
        <label class="chip-check">
          <input type="checkbox" data-user="${member.id}" data-role="${role.id}"
            ${member.role_ids.includes(role.id) ? "checked" : ""}
            ${manage ? "" : "disabled"} />
          <span style="color:${escapeAttr(role.color)}">${escapeHtml(role.name)}</span>
        </label>`
      )
      .join("");
    return `
      <article class="gs-member-card" data-search="${escapeAttr(`${member.nickname} ${member.username}`.toLowerCase())}">
        <div class="gs-member-top">
          <div class="avatar">${avatar}<span class="dot ${member.is_online ? "" : "off"}"></span></div>
          <div>
            <strong>${escapeHtml(member.nickname)}</strong>
            <span>@${escapeHtml(member.username)} · ${online}</span>
          </div>
          ${
            manage
              ? `<button type="button" class="btn btn-secondary" data-save-roles="${member.id}">Salvar</button>`
              : ""
          }
        </div>
        <div class="role-checks">${selects || `<span class="gs-hint">Só @everyone</span>`}</div>
      </article>`;
  }

  function paintChannels() {
    const manage = can(current.my_permissions, Perm.MANAGE_CHANNELS);
    const texts = channels.filter((c) => c.channel_type === "text");
    const voices = channels.filter((c) => c.channel_type === "voice");
    body.innerHTML = `
      <div class="gs-two-col">
        <div>
          <div class="gs-section-label">Canais de texto · ${texts.length}</div>
          <div class="gs-channel-list">
            ${
              texts
                .map(
                  (ch) => `
                <div class="gs-channel-row">
                  <span class="hash">#</span>
                  <div>
                    <strong>${escapeHtml(ch.name)}</strong>
                    <span>${escapeHtml(ch.description || "Sem descrição")}</span>
                  </div>
                </div>`
                )
                .join("") || `<p class="gs-empty">Nenhum canal de texto.</p>`
            }
          </div>
          <div class="gs-section-label" style="margin-top:18px">Canais de voz · ${voices.length}</div>
          <div class="gs-channel-list">
            ${
              voices
                .map(
                  (ch) => `
                <div class="gs-channel-row">
                  <span>🔊</span>
                  <div>
                    <strong>${escapeHtml(ch.name)}</strong>
                    <span>${escapeHtml(ch.description || "Sala de call")}</span>
                  </div>
                </div>`
                )
                .join("") || `<p class="gs-empty">Nenhuma sala de voz.</p>`
            }
          </div>
        </div>
        <div>
          ${
            manage
              ? `<form id="channel-form" class="gs-form cardish">
                  <div class="gs-section-label">Criar canal</div>
                  <label>Nome
                    <input name="name" placeholder="ex: avisos, ranked" required maxlength="40" />
                  </label>
                  <label>Descrição
                    <input name="description" placeholder="Opcional" maxlength="255" />
                  </label>
                  <label>Tipo
                    <select name="channel_type">
                      <option value="text"># Texto</option>
                      <option value="voice">🔊 Voz</option>
                    </select>
                  </label>
                  <button class="btn btn-primary" type="submit">Criar canal</button>
                </form>`
              : `<p class="gs-hint">Peça a um Admin para criar canais.</p>`
          }
        </div>
      </div>
    `;

    body.querySelector("#channel-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(event.target);
      try {
        await api(`/api/groups/${current.id}/channels`, {
          method: "POST",
          body: {
            name: String(data.get("name") || "").trim(),
            description: String(data.get("description") || "").trim(),
            channel_type: String(data.get("channel_type") || "text"),
          },
        });
        toast("Canal criado.");
        await load();
        onChanged?.();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  async function paintInvites() {
    const manage = can(current.my_permissions, Perm.MANAGE_GROUP);
    if (!manage) {
      body.innerHTML = `<p class="gs-empty">Só quem gerencia o grupo pode criar links de convite.</p>`;
      return;
    }
    body.innerHTML = `<p class="gs-loading">Carregando convites…</p>`;
    let invites = [];
    try {
      invites = await api(`/api/groups/${current.id}/invites`);
    } catch (error) {
      body.innerHTML = `<p class="gs-empty">${escapeHtml(error.message)}</p>`;
      return;
    }

    body.innerHTML = `
      <div class="gs-two-col">
        <form id="invite-form" class="gs-form cardish">
          <div class="gs-section-label">Novo link</div>
          <label>Validade
            <select name="expires_in_days">
              <option value="1">1 dia</option>
              <option value="3">3 dias</option>
              <option value="7" selected>7 dias</option>
              <option value="30">30 dias</option>
              <option value="0">Nunca expira</option>
            </select>
          </label>
          <label>Máximo de usos
            <input name="max_uses" type="number" min="1" max="1000" placeholder="Ilimitado" />
          </label>
          <button class="btn btn-primary" type="submit">Gerar convite</button>
        </form>
        <div class="gs-invite-list">
          ${
            invites
              .map((inv) => {
                const link = `${location.origin}${inv.link_path || `/join/${inv.code}`}`;
                const uses =
                  inv.max_uses != null ? `${inv.uses}/${inv.max_uses} usos` : `${inv.uses} usos`;
                const exp = inv.expires_at
                  ? `expira ${new Date(inv.expires_at).toLocaleDateString("pt-BR")}`
                  : "nunca expira";
                return `
                  <div class="gs-invite-card">
                    <div>
                      <strong>${escapeHtml(inv.code)}</strong>
                      <span>${uses} · ${exp}</span>
                      <code>${escapeHtml(link)}</code>
                    </div>
                    <button type="button" class="btn btn-secondary" data-copy="${escapeAttr(link)}">Copiar</button>
                  </div>`;
              })
              .join("") || `<p class="gs-empty">Nenhum convite ainda. Gere o primeiro à esquerda.</p>`
          }
        </div>
      </div>
    `;

    body.querySelector("#invite-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(event.target);
      const maxRaw = String(data.get("max_uses") || "").trim();
      const days = Number(data.get("expires_in_days"));
      try {
        await api(`/api/groups/${current.id}/invites`, {
          method: "POST",
          body: {
            expires_in_days: Number.isFinite(days) ? days : 7,
            max_uses: maxRaw ? Number(maxRaw) : null,
          },
        });
        toast("Convite criado.");
        paintInvites();
      } catch (error) {
        toast(error.message, true);
      }
    });

    body.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.copy);
          toast("Link copiado.");
        } catch {
          toast(btn.dataset.copy);
        }
      });
    });
  }

  nav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tab]");
    if (!button) return;
    setTab(button.dataset.tab);
  });

  paintNav();
  requestAnimationFrame(() => overlay.classList.add("open"));
  load();
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
