/** Modal para criar grupo (servidor). */

import { api } from "./api.js";
import { openModal } from "./modal.js";
import { toast } from "./ui.js";

export function openCreateGroupModal({ onCreated }) {
  openModal({
    title: "Criar grupo",
    subtitle: "Cada grupo tem canais, call e cargos — igual um servidor do Discord.",
    bodyHtml: `
      <form id="create-group-form" class="create-group-form">
        <div class="group-preview">
          <div class="group-preview-icon">TG</div>
          <div>
            <strong id="preview-name">novo-grupo</strong>
            <span id="preview-desc">Já nasce com #geral e uma sala de voz</span>
          </div>
        </div>

        <label>Nome do grupo
          <input name="name" maxlength="40" placeholder="ex: tropa, scrims" required autocomplete="off" />
        </label>

        <label>Descrição <span class="optional">(opcional)</span>
          <textarea name="description" rows="3" maxlength="255" placeholder="Para que serve este grupo?"></textarea>
        </label>

        <div class="privacy-cards">
          <label class="privacy-card">
            <input type="radio" name="is_private" value="false" checked />
            <div>
              <strong>🌐 Aberto ao time</strong>
              <span>Todos os membros do THE GANG entram automaticamente.</span>
            </div>
          </label>
          <label class="privacy-card">
            <input type="radio" name="is_private" value="true" />
            <div>
              <strong>🔒 Privado</strong>
              <span>Só você entra. Ideal para staff.</span>
            </div>
          </label>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" data-cancel>Cancelar</button>
          <button type="submit" class="btn btn-primary">Criar grupo</button>
        </div>
      </form>
    `,
    onMount(card, close) {
      const form = card.querySelector("#create-group-form");
      const nameInput = form.querySelector('[name="name"]');
      const descInput = form.querySelector('[name="description"]');
      const previewName = card.querySelector("#preview-name");
      const previewDesc = card.querySelector("#preview-desc");

      const syncPreview = () => {
        previewName.textContent = slugify(nameInput.value) || "novo-grupo";
        previewDesc.textContent = descInput.value.trim() || "Já nasce com #geral e uma sala de voz";
      };
      nameInput.addEventListener("input", syncPreview);
      descInput.addEventListener("input", syncPreview);
      form.querySelector("[data-cancel]").addEventListener("click", close);
      nameInput.focus();

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
          const group = await api("/api/groups", {
            method: "POST",
            body: {
              name: String(data.get("name") || "").trim(),
              description: String(data.get("description") || "").trim(),
              is_private: data.get("is_private") === "true",
            },
          });
          toast(`Grupo ${group.name} criado.`);
          close();
          onCreated?.(group);
        } catch (error) {
          toast(error.message, true);
          submit.disabled = false;
        }
      });
    },
  });
}

function slugify(value) {
  return value.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^\w\-]+/gu, "").slice(0, 40);
}
