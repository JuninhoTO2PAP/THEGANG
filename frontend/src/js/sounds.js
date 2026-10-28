/** Sons curtos THE GANG (Web Audio — sem arquivos). */

import { getNotifyPrefs } from "./notify-prefs.js";

let ctx = null;

function audio() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
  }
  if (ctx.state === "suspended") ctx.resume().catch(() => {});
  return ctx;
}

function tone(freq, start, dur, type = "sine", gain = 0.08) {
  const ac = audio();
  if (!ac) return;
  const osc = ac.createOscillator();
  const g = ac.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  g.gain.setValueAtTime(0.0001, ac.currentTime + start);
  g.gain.exponentialRampToValueAtTime(gain, ac.currentTime + start + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + start + dur);
  osc.connect(g);
  g.connect(ac.destination);
  osc.start(ac.currentTime + start);
  osc.stop(ac.currentTime + start + dur + 0.02);
}

/** Entrada na call — acorde dourado curto. */
export function playCallJoin() {
  if (!getNotifyPrefs().sound) return;
  tone(392, 0, 0.12, "triangle", 0.07);
  tone(523.25, 0.08, 0.16, "triangle", 0.08);
  tone(659.25, 0.16, 0.22, "sine", 0.06);
}

/** Menção @você — bip metálico. */
export function playMention() {
  if (!getNotifyPrefs().sound) return;
  tone(880, 0, 0.07, "square", 0.045);
  tone(1174.66, 0.08, 0.12, "square", 0.05);
}

/** Splash / login — marca sonora curta. */
export function playBrandChime() {
  tone(349.23, 0, 0.1, "triangle", 0.05);
  tone(440, 0.1, 0.12, "triangle", 0.06);
  tone(523.25, 0.22, 0.18, "sine", 0.05);
}
