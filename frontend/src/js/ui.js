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
  { id: "coach", label: "COACH" },
  { id: "r1", label: "R1" },
  { id: "r2", label: "R2" },
  { id: "r3", label: "R3" },
  { id: "sup", label: "SUP" },
];

const LEGACY_FF_ROLES = {
  cpt: "COACH",
  igl: "COACH",
  suporte: "SUP",
  support: "SUP",
  entry: "Entry",
  sniper: "Sniper",
  flex: "Flex",
};

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

function paintAccent(hex) {
  const root = document.documentElement;
  const n = Number.parseInt(String(hex).slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  root.style.setProperty("--accent", hex);
  root.style.setProperty("--accent-2", hex);
  root.style.setProperty("--accent-soft", `rgba(${r}, ${g}, ${b}, 0.16)`);
}

export function applyAccent(id) {
  const found = ACCENTS.find((item) => item.id === id) || ACCENTS[0];
  paintAccent(found.value);
  localStorage.setItem(ACCENT_KEY, found.id);
}

export function getAccent() {
  return localStorage.getItem(ACCENT_KEY) || "gold";
}

export function ffRoleLabel(id) {
  return FF_ROLES.find((r) => r.id === id)?.label || LEGACY_FF_ROLES[id] || id || "—";
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
