/** Preferências de notificação (locais até a Fase 2 / Web Push). */

const KEY = "tg_notify_prefs";

const DEFAULTS = {
  desktop: true,
  sound: true,
  mentions_only: false,
  mute_dms: false,
  show_previews: true,
};

export function getNotifyPrefs() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

export function setNotifyPrefs(partial) {
  const next = { ...getNotifyPrefs(), ...partial };
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
