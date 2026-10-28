/** Modal para criar canal de texto ou voz (sem prompt). */

import { api } from "./api.js";
import { openModal } from "./modal.js";
import { toast } from "./ui.js";

export function openCreateChannelModal(group, channelType, { onCreated } = {}) {
  const isVoice = channelType === "voice";
  openModal({
    title: isVoice ? "Nova sala de voz" : "Novo canal de texto",
    subtitle: `Em ${group.name}`,
    bodyHtml: `
      <form id="create-channel-form" class="stack">
        <label>
          Nome
          <input name="name" placeholder="${isVoice ? "ex: call-ranked" : "ex: geral"}" required maxlength="40" autocomplete="off" />
        </label>
        <label>
          Descrição <span class="muted">(opcional)</span>
          <input name="description" maxlength="255" placeholder="Para que serve este canal" />
        </label>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" data-cancel>Cancelar</button>
          <button type="submit" class="btn btn-primary">${isVoice ? "Criar call" : "Criar canal"}</button>
        </div>
      </form>
    `,
    onMount(card, close) {
      card.querySelector("[data-cancel]")?.addEventListener("click", close);
      const input = card.querySelector('input[name="name"]');
      input?.focus();
      card.querySelector("#create-channel-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData(event.target);
        const name = String(data.get("name") || "").trim();
        if (!name) return;
        try {
          const channel = await api(`/api/groups/${group.id}/channels`, {
            method: "POST",
            body: {
              name,
              description: String(data.get("description") || ""),
              channel_type: channelType,
            },
          });
          toast(`${isVoice ? "Call" : "Canal"} #${channel.name} criado.`);
          close();
          onCreated?.(channel);
        } catch (error) {
          toast(error.message, true);
        }
      });
    },
  });
}
