/** Modal genérico do THE GANG. */

export function openModal({ title, subtitle = "", bodyHtml, onMount }) {
  closeModal();

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "tg-modal";
  overlay.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true" aria-label="${escapeAttr(title)}">
      <header class="modal-head">
        <div>
          <h2>${escapeHtml(title)}</h2>
          ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}
        </div>
        <button type="button" class="modal-close" aria-label="Fechar">×</button>
      </header>
      <div class="modal-body">${bodyHtml}</div>
    </div>
  `;

  document.body.appendChild(overlay);

  const close = () => closeModal();
  overlay.querySelector(".modal-close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) close();
  });
  document.addEventListener("keydown", onEscape);

  function onEscape(event) {
    if (event.key === "Escape") close();
  }

  overlay._onEscape = onEscape;

  if (onMount) onMount(overlay.querySelector(".modal-card"), close);
  requestAnimationFrame(() => overlay.classList.add("open"));
  return overlay;
}

export function closeModal() {
  const existing = document.getElementById("tg-modal");
  if (!existing) return;
  if (existing._onEscape) {
    document.removeEventListener("keydown", existing._onEscape);
  }
  existing.remove();
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
