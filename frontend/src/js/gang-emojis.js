/** Pack de emojis exclusivo THE GANG. */

export const GANG_EMOJIS = [
  { id: "tg", emoji: "👑", label: "THE GANG" },
  { id: "booyah", emoji: "🏆", label: "Booyah" },
  { id: "headshot", emoji: "🎯", label: "Headshot" },
  { id: "clutch", emoji: "🔥", label: "Clutch" },
  { id: "igl", emoji: "🧠", label: "IGL" },
  { id: "rush", emoji: "⚡", label: "Rush" },
  { id: "revive", emoji: "💉", label: "Revive" },
  { id: "drop", emoji: "🪂", label: "Drop" },
  { id: "loot", emoji: "🎒", label: "Loot" },
  { id: "gg", emoji: "🤝", label: "GG" },
  { id: "tilted", emoji: "😤", label: "Tilt" },
  { id: "mvp", emoji: "⭐", label: "MVP" },
];

export const QUICK_REACTS = [
  ...GANG_EMOJIS.slice(0, 6).map((e) => e.emoji),
  "😂",
  "❤️",
];

export function gangEmojiPickerHtml(attrs = "") {
  return `
    <div class="gang-emoji-pack" ${attrs}>
      <div class="gang-emoji-title">Pack THE GANG</div>
      <div class="gang-emoji-grid">
        ${GANG_EMOJIS.map(
          (e) =>
            `<button type="button" class="gang-emoji-btn" data-gang-emoji="${e.emoji}" title="${e.label}">
              <span>${e.emoji}</span><small>${e.label}</small>
            </button>`
        ).join("")}
      </div>
    </div>
  `;
}
