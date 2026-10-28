/** Toast, tema e cor de destaque. */

const THEME_KEY = "tg_theme";
const ACCENT_KEY = "tg_accent";

export const ACCENTS = [
  { id: "gold", value: "#f0b232" },
  { id: "orange", value: "#e67e22" },
  { id: "ember", value: "#f26522" },
  { id: "blue", value: "#5865f2" },
  { id: "purple", value: "#7c3aed" },
  { id: "pink", value: "#e879f9" },
  { id: "red", value: "#f23f43" },
  { id: "green", value: "#23a559" },
  { id: "cyan", value: "#22d3ee" },
];

export const FF_ROLES = [
  { id: "igl", label: "IGL" },
  { id: "entry", label: "Entry" },
  { id: "support", label: "Support" },
  { id: "sniper", label: "Sniper" },
  { id: "flex", label: "Flex" },
  { id: "coach", label: "Coach" },
];

export const FF_REGIONS = [
  { id: "BR", label: "Brasil" },
  { id: "LATAM", label: "LATAM" },
  { id: "NA", label: "América do Norte" },
  { id: "EU", label: "Europa" },
  { id: "ASIA", label: "Ásia" },
  { id: "OTHER", label: "Outra" },
];

export const BANNER_THEMES = [
  { id: "gold", label: "Ouro THE GANG" },
  { id: "ember", label: "Brasa" },
  { id: "navy", label: "Noite" },
  { id: "violet", label: "Violeta" },
  { id: "forest", label: "Floresta" },
  { id: "crimson", label: "Carmesim" },
];

export function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.hidden = false;
  el.textContent = message;
  el.classList.toggle("error", isError);
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    el.hidden = true;
  }, 3200);
}

export function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem(THEME_KEY, next);
}

export function getTheme() {
  return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
}

export function applyAccent(id) {
  const found = ACCENTS.find((item) => item.id === id) || ACCENTS[0];
  document.documentElement.style.setProperty("--accent", found.value);
  localStorage.setItem(ACCENT_KEY, found.id);
}

export function getAccent() {
  return localStorage.getItem(ACCENT_KEY) || "gold";
}

export function ffRoleLabel(id) {
  return FF_ROLES.find((r) => r.id === id)?.label || id || "—";
}

export function initTheme() {
  applyTheme(getTheme());
  applyAccent(getAccent());
}

export function formatDay(iso) {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function initials(name) {
  return (name || "?").slice(0, 1).toUpperCase();
}
