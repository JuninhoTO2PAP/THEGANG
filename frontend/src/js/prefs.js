/** Preferências locais (privacidade, voz, atalhos). */

function load(key, defaults) {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(key) || "{}") };
  } catch {
    return { ...defaults };
  }
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
  return value;
}

const PRIVACY_KEY = "tg_privacy_prefs";
const PRIVACY_DEFAULTS = {
  show_online: true,
  allow_dms: true,
  show_activity: true,
  read_receipts: true,
};

const VOICE_KEY = "tg_voice_prefs";
const VOICE_DEFAULTS = {
  input_volume: 80,
  output_volume: 80,
  noise_suppression: true,
  echo_cancellation: true,
  auto_gain: true,
  camera_mirrored: true,
  spatial: "off",
  output_device_id: "",
  input_device_id: "",
};

const SHORTCUTS_KEY = "tg_shortcut_prefs";
const SHORTCUTS_DEFAULTS = {
  send_on_enter: true,
  mute_mic: "Ctrl+Shift+M",
  mute_sound: "Ctrl+Shift+D",
  toggle_settings: "Ctrl+,",
  search: "Ctrl+K",
};

export function getPrivacyPrefs() {
  return load(PRIVACY_KEY, PRIVACY_DEFAULTS);
}

export function setPrivacyPrefs(partial) {
  return save(PRIVACY_KEY, { ...getPrivacyPrefs(), ...partial });
}

export function getVoicePrefs() {
  return load(VOICE_KEY, VOICE_DEFAULTS);
}

export function setVoicePrefs(partial) {
  return save(VOICE_KEY, { ...getVoicePrefs(), ...partial });
}

export function getShortcutPrefs() {
  return load(SHORTCUTS_KEY, SHORTCUTS_DEFAULTS);
}

export function setShortcutPrefs(partial) {
  return save(SHORTCUTS_KEY, { ...getShortcutPrefs(), ...partial });
}
