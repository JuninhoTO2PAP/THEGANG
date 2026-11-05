/** Call LiveKit + eventos Diário / Intensivo / Campeonato. */

import { api } from "./api.js";
import { Perm, can } from "./perms.js";
import { playCallJoin } from "./sounds.js";
import { toast } from "./ui.js";
import { onWs } from "./ws.js";

let activeRoom = null;
let eventTimer = null;
let offEventWs = null;
let stageRoot = null;
let joinedChannelId = null;
let dockNode = null;
let rosterWatch = null;

export function onCallRoster(fn) {
  rosterWatch = fn;
}

function publishRoster(payload) {
  rosterWatch?.(payload);
}

export function setCallDock(el) {
  dockNode = el;
}

export function joinedCallId() {
  return joinedChannelId;
}

export function focusCall(mountEl) {
  if (!stageRoot || !mountEl) return false;
  stageRoot.classList.remove("compact");
  mountEl.replaceChildren(stageRoot);
  if (dockNode) dockNode.hidden = true;
  return true;
}

export function parkCall() {
  if (!stageRoot || !dockNode) return;
  if (stageRoot.parentElement === dockNode && stageRoot.classList.contains("compact")) return;
  stageRoot.classList.add("compact");
  dockNode.hidden = false;
  dockNode.replaceChildren(stageRoot);
}

const TYPE_LABEL = {
  diario: "Diário",
  intensivo: "Intensivo",
  campeonato: "Campeonato",
};

function formatTimer(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}

function clearEventTimer() {
  if (eventTimer) {
    clearInterval(eventTimer);
    eventTimer = null;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export async function startVoiceCall(channel, mountEl, { user, group } = {}) {
  await leaveVoiceCall();

  const canStartEvent =
    !!user &&
    (user.is_admin ||
      group?.created_by === user.id ||
      can(group?.my_permissions || 0, Perm.ADMINISTRATOR) ||
      can(group?.my_permissions || 0, Perm.START_EVENTS));

  mountEl.innerHTML = `
    <div class="call-stage">
      <div class="call-videos" id="call-videos"></div>
      <div class="event-panel" id="event-panel"></div>
      <div class="call-status" id="call-status">Conectando…</div>
      <div class="call-controls">
        <button type="button" class="call-btn" id="call-mute" title="Mute">🎤</button>
        <button type="button" class="call-btn" id="call-deafen" title="Deafen">🎧</button>
        <button type="button" class="call-btn" id="call-cam" title="Câmera">📷</button>
        <button type="button" class="call-btn" id="call-screen" title="Compartilhar tela">🖥️</button>
        <button type="button" class="call-btn danger" id="call-leave" title="Sair">✕</button>
      </div>
    </div>
  `;

  const statusEl = mountEl.querySelector("#call-status");
  const videosEl = mountEl.querySelector("#call-videos");
  const panelEl = mountEl.querySelector("#event-panel");
  stageRoot = mountEl.querySelector(".call-stage");
  joinedChannelId = channel.id;
  let muted = false;
  let deafened = false;
  let camOn = false;
  let screenOn = false;
  let currentEvent = null;
  let startedAtMs = null;

  function isOwner(ev) {
    return ev && user && ev.owner_id === user.id;
  }

  function startLocalTimer(ev) {
    clearEventTimer();
    startedAtMs = Date.now() - (ev.elapsed_seconds || 0) * 1000;
    const tick = () => {
      const el = panelEl.querySelector("#event-timer");
      if (!el || !startedAtMs) return;
      el.textContent = formatTimer((Date.now() - startedAtMs) / 1000);
    };
    tick();
    eventTimer = setInterval(tick, 1000);
  }

  async function startEvent(eventType) {
    try {
      currentEvent = await api("/api/events/start", {
        method: "POST",
        body: { channel_id: channel.id, event_type: eventType },
      });
      toast(`${TYPE_LABEL[eventType]} iniciado!`);
      paintEvent();
    } catch (error) {
      toast(error.message, true);
    }
  }

  function showFinishForm() {
    clearEventTimer();
    panelEl.innerHTML = `
      <div class="event-card finish">
        <div class="event-card-head">
          <strong>Resultado do evento</strong>
          <span>Colocação, Booyah, kills e pontos</span>
        </div>
        <form id="event-finish-form" class="event-finish-form">
          <label>Colocação
            <input name="placement" type="number" min="1" max="50" value="1" required />
          </label>
          <label>Booyah
            <input name="booyah_count" type="number" min="0" max="50" value="0" required />
          </label>
          <label>Kills no total
            <input name="kills" type="number" min="0" max="9999" value="0" required />
          </label>
          <label>Pontos
            <input name="points" type="number" min="0" max="999999" value="0" required />
          </label>
          <div class="modal-actions" style="justify-content:flex-start;margin-top:4px">
            <button class="btn btn-primary" type="submit">Salvar e abrir MVP</button>
            <button class="btn btn-secondary" type="button" id="finish-cancel">Voltar</button>
          </div>
        </form>
      </div>
    `;
    panelEl.querySelector("#finish-cancel")?.addEventListener("click", paintEvent);
    panelEl.querySelector("#event-finish-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!currentEvent) return;
      const data = new FormData(event.target);
      try {
        currentEvent = await api(`/api/events/${currentEvent.id}/finish`, {
          method: "POST",
          body: {
            placement: Number(data.get("placement")),
            booyah_count: Number(data.get("booyah_count")),
            kills: Number(data.get("kills")),
            points: Number(data.get("points")),
          },
        });
        toast(currentEvent.is_win ? "Vitória registrada! Vote no MVP." : "Resultado salvo. Vote no MVP.");
        paintEvent();
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  async function voteMvp(candidateId) {
    if (!currentEvent) return;
    try {
      currentEvent = await api(`/api/events/${currentEvent.id}/mvp-vote`, {
        method: "POST",
        body: { candidate_id: candidateId },
      });
      toast("Voto de MVP registrado.");
      paintEvent();
    } catch (error) {
      toast(error.message, true);
    }
  }

  async function closeMvp() {
    if (!currentEvent) return;
    try {
      currentEvent = await api(`/api/events/${currentEvent.id}/close-mvp`, { method: "POST" });
      toast(currentEvent.mvp_nickname ? `MVP: ${currentEvent.mvp_nickname}` : "Votação encerrada.");
      paintEvent();
    } catch (error) {
      toast(error.message, true);
    }
  }

  function paintEvent() {
    const ev = currentEvent;
    if (!ev) {
      clearEventTimer();
      panelEl.innerHTML = canStartEvent
        ? `
        <div class="event-card idle">
          <div class="event-card-head">
            <strong>Evento da call</strong>
            <span>CPT ou dono inicia</span>
          </div>
          <p class="hint">Escolha o tipo e comece o timer da call.</p>
          <div class="event-type-row">
            <button type="button" class="event-type-btn" data-start="diario">Diário</button>
            <button type="button" class="event-type-btn intensivo" data-start="intensivo">Intensivo</button>
            <button type="button" class="event-type-btn campeonato" data-start="campeonato">Campeonato</button>
          </div>
        </div>`
        : `
        <div class="event-card idle">
          <div class="event-card-head">
            <strong>Evento da call</strong>
            <span>Aguardando CPT</span>
          </div>
          <p class="hint">Só quem tem cargo CPT (ou o dono do app) inicia Diário, Intensivo ou Campeonato.</p>
        </div>`;
      panelEl.querySelectorAll("[data-start]").forEach((btn) => {
        btn.addEventListener("click", () => startEvent(btn.dataset.start));
      });
      return;
    }

    if (ev.status === "live") {
      panelEl.innerHTML = `
        <div class="event-card live">
          <div class="event-card-head">
            <strong>${TYPE_LABEL[ev.event_type] || ev.event_type}</strong>
            <span>Dono: ${escapeHtml(ev.owner_nickname)}</span>
          </div>
          <div class="event-timer" id="event-timer">${formatTimer(ev.elapsed_seconds || 0)}</div>
          <p class="event-live-hint">Evento ao vivo — contador rodando</p>
          ${
            isOwner(ev)
              ? `<button type="button" class="btn btn-primary" id="event-finish">Finalizar evento</button>`
              : `<p class="hint">Aguardando o dono finalizar…</p>`
          }
        </div>
      `;
      panelEl.querySelector("#event-finish")?.addEventListener("click", showFinishForm);
      startLocalTimer(ev);
      return;
    }

    if (ev.status === "voting") {
      clearEventTimer();
      const candidates = (ev.candidates || [])
        .slice()
        .sort((a, b) => b.votes - a.votes || a.nickname.localeCompare(b.nickname));
      panelEl.innerHTML = `
        <div class="event-card voting">
          <div class="event-card-head">
            <strong>${TYPE_LABEL[ev.event_type] || ev.event_type} · resultado</strong>
            <span>${formatTimer(ev.elapsed_seconds || 0)}</span>
          </div>
          <div class="event-results">
            <div><span>Colocação</span><strong>${ev.placement}º</strong></div>
            <div><span>Booyah</span><strong>${ev.booyah_count}</strong></div>
            <div><span>Kills</span><strong>${ev.kills}</strong></div>
            <div><span>Pontos</span><strong>${ev.points}</strong></div>
            <div><span>Vitória</span><strong>${ev.is_win ? "Sim ✓" : "Não"}</strong></div>
          </div>
          <h4 class="event-mvp-title">Vote no MVP do evento</h4>
          <div class="event-mvp-list">
            ${candidates
              .map(
                (c) => `
              <button type="button" class="event-mvp-row ${ev.my_vote_candidate_id === c.id ? "selected" : ""}" data-mvp="${c.id}">
                <span>${escapeHtml(c.nickname)}</span>
                <strong>${c.votes} voto${c.votes === 1 ? "" : "s"}</strong>
              </button>`
              )
              .join("")}
          </div>
          ${
            isOwner(ev)
              ? `<button type="button" class="btn btn-secondary" id="event-close-mvp">Encerrar votação MVP</button>`
              : ""
          }
        </div>
      `;
      panelEl.querySelectorAll("[data-mvp]").forEach((btn) => {
        btn.addEventListener("click", () => voteMvp(Number(btn.dataset.mvp)));
      });
      panelEl.querySelector("#event-close-mvp")?.addEventListener("click", closeMvp);
      return;
    }

    clearEventTimer();
    panelEl.innerHTML = `
      <div class="event-card closed">
        <div class="event-card-head">
          <strong>Evento encerrado</strong>
          <span>${TYPE_LABEL[ev.event_type] || ev.event_type}</span>
        </div>
        <div class="event-results">
          <div><span>Colocação</span><strong>${ev.placement}º</strong></div>
          <div><span>Booyah</span><strong>${ev.booyah_count}</strong></div>
          <div><span>Kills</span><strong>${ev.kills}</strong></div>
          <div><span>Pontos</span><strong>${ev.points}</strong></div>
          <div><span>MVP</span><strong>${escapeHtml(ev.mvp_nickname || "—")}</strong></div>
        </div>
        <button type="button" class="btn btn-secondary" id="event-new">Novo evento</button>
      </div>
    `;
    panelEl.querySelector("#event-new")?.addEventListener("click", () => {
      currentEvent = null;
      paintEvent();
    });
  }

  try {
    const token = await api("/api/voice/token", {
      method: "POST",
      body: { channel_id: channel.id },
    });
    const mod = await import("https://cdn.jsdelivr.net/npm/livekit-client@2.9.1/+esm");
    const room = new mod.Room({ adaptiveStream: true, dynacast: true });
    activeRoom = room;

    const displayName = (participant) =>
      participant.name || participant.identity || "Membro";

    const tileId = (participant, kind) => `${participant.identity}__${kind}`;

    const ensureTile = (participant, kind = "user") => {
      const id = tileId(participant, kind);
      let wrap = videosEl.querySelector(`[data-tile="${id}"]`);
      if (wrap) return wrap;
      wrap = document.createElement("div");
      wrap.className = `call-tile${kind === "screen" ? " screen" : ""}`;
      wrap.dataset.tile = id;
      wrap.dataset.identity = participant.identity;
      const label =
        kind === "screen"
          ? `${displayName(participant)} · tela`
          : displayName(participant);
      wrap.innerHTML = `
        <div class="call-tile-avatar" aria-hidden="true">${escapeHtml(
          String(displayName(participant)).slice(0, 1).toUpperCase()
        )}</div>
        ${
          kind === "user"
            ? `<div class="call-speak-bar" aria-hidden="true"><span></span><span></span><span></span></div>`
            : `<div class="screen-tools">
                <button type="button" data-screen="expand" title="Tela cheia">⛶</button>
                <button type="button" data-screen="min" title="Minimizar">—</button>
                <button type="button" data-screen="hide" title="Não assistir">✕</button>
              </div>
              <button type="button" class="screen-watch" data-screen="watch" hidden>Assistir tela</button>`
        }
        <span class="call-tile-name">${escapeHtml(label)}</span>
      `;
      if (kind === "screen") {
        videosEl.prepend(wrap);
      } else {
        videosEl.appendChild(wrap);
      }
      return wrap;
    };

    const removeTilesFor = (identity) => {
      videosEl
        .querySelectorAll(`[data-identity="${CSS.escape(identity)}"]`)
        .forEach((el) => el.remove());
      document
        .querySelectorAll(`audio[data-identity="${CSS.escape(identity)}"]`)
        .forEach((el) => el.remove());
    };

    const paintSpeakers = (speakers) => {
      const talking = new Set((speakers || []).map((p) => p.identity));
      videosEl.querySelectorAll(".call-tile:not(.screen)").forEach((tile) => {
        tile.classList.toggle("speaking", talking.has(tile.dataset.identity));
      });
    };

    const syncRoster = () => {
      if (!videosEl) return;
      ensureTile(room.localParticipant, "user");
      for (const p of room.remoteParticipants.values()) {
        ensureTile(p, "user");
      }
      const people = [room.localParticipant, ...room.remoteParticipants.values()].map((p) => ({
        identity: p.identity,
        name: displayName(p),
      }));
      statusEl.textContent = `${people.length} na call · ${channel.name}`;
      statusEl.title = people.map((p) => p.name).join(", ");
      publishRoster({ channelId: channel.id, people });
    };

    const screenPubs = new Map();
    let lightbox = null;

    const closeLightbox = () => {
      if (!lightbox) return;
      const video = lightbox.querySelector("video");
      const home = lightbox.dataset.home
        ? videosEl.querySelector(`[data-tile="${lightbox.dataset.home}"]`)
        : null;
      if (video && home) home.prepend(video);
      lightbox.remove();
      lightbox = null;
    };

    const expandScreen = (wrap) => {
      const video = wrap.querySelector("video");
      if (!video) return;
      closeLightbox();
      wrap.classList.remove("is-min", "is-off");
      lightbox = document.createElement("div");
      lightbox.className = "screen-lightbox";
      lightbox.dataset.home = wrap.dataset.tile;
      const bar = document.createElement("div");
      bar.className = "screen-lightbox-bar";
      bar.innerHTML = `<strong>${wrap.querySelector(".call-tile-name")?.textContent || "Tela"}</strong>`;
      const exit = document.createElement("button");
      exit.type = "button";
      exit.className = "btn btn-secondary";
      exit.textContent = "Sair da tela cheia";
      exit.addEventListener("click", closeLightbox);
      bar.appendChild(exit);
      lightbox.append(bar, video);
      document.body.appendChild(lightbox);
    };

    const setWatching = async (wrap, watch) => {
      const pub = screenPubs.get(wrap.dataset.tile);
      wrap.classList.toggle("is-off", !watch);
      wrap.classList.remove("is-min");
      const watchBtn = wrap.querySelector(".screen-watch");
      if (watchBtn) watchBtn.hidden = watch;
      if (!watch) closeLightbox();
      if (pub && typeof pub.setSubscribed === "function" && !pub.track?.isLocal) {
        try {
          await pub.setSubscribed(watch);
        } catch {
          /* preview local não desinscreve */
        }
      }
      const video = wrap.querySelector("video");
      if (video) video.style.display = watch ? "" : "none";
    };

    videosEl.addEventListener("click", (event) => {
      const button = event.target.closest("[data-screen]");
      if (!button) return;
      const wrap = button.closest(".call-tile.screen");
      if (!wrap) return;
      const action = button.dataset.screen;
      if (action === "expand") expandScreen(wrap);
      if (action === "min") {
        closeLightbox();
        wrap.classList.toggle("is-min");
        wrap.classList.remove("is-off");
      }
      if (action === "hide") setWatching(wrap, false);
      if (action === "watch") setWatching(wrap, true);
    });

    const attachTrack = (track, participant, publication) => {
      const source = publication?.source;
      const isScreen =
        source === mod.Track.Source.ScreenShare ||
        source === mod.Track.Source.ScreenShareAudio;

      if (track.kind === "audio") {
        // Áudio local já sai no sistema; não duplicar.
        if (participant.isLocal) return;
        const existing = document.querySelector(
          `audio[data-identity="${CSS.escape(participant.identity)}"][data-source="${source || "mic"}"]`
        );
        if (existing) return;
        const audio = track.attach();
        audio.dataset.identity = participant.identity;
        audio.dataset.source = String(source || "mic");
        audio.autoplay = true;
        audio.muted = deafened;
        document.body.appendChild(audio);
        return;
      }

      if (track.kind === "video") {
        const kind = isScreen ? "screen" : "user";
        const wrap = ensureTile(participant, kind);
        if (isScreen && publication) screenPubs.set(wrap.dataset.tile, publication);
        if (isScreen && wrap.classList.contains("is-off")) return;
        wrap.querySelectorAll("video").forEach((v) => v.remove());
        wrap.classList.toggle("has-video", true);
        const video = track.attach();
        video.playsInline = true;
        video.autoplay = true;
        video.muted = true;
        wrap.prepend(video);
      }
    };

    const detachTrack = (track, participant, publication) => {
      if (lightbox?.querySelector("video") && track.attachedElements?.includes(lightbox.querySelector("video"))) {
        closeLightbox();
      }
      track.detach().forEach((el) => el.remove());
      const source = publication?.source;
      if (
        source === mod.Track.Source.ScreenShare &&
        participant &&
        !participant.isLocal
      ) {
        videosEl
          .querySelector(`[data-tile="${tileId(participant, "screen")}"]`)
          ?.remove();
      }
      if (source === mod.Track.Source.ScreenShare && participant?.isLocal) {
        videosEl
          .querySelector(`[data-tile="${tileId(participant, "screen")}"]`)
          ?.remove();
      }
      if (source === mod.Track.Source.Camera && participant) {
        const wrap = videosEl.querySelector(
          `[data-tile="${tileId(participant, "user")}"]`
        );
        if (wrap) {
          wrap.querySelectorAll("video").forEach((v) => v.remove());
          wrap.classList.remove("has-video");
        }
      }
    };

    const attachExisting = (participant) => {
      ensureTile(participant, "user");
      for (const pub of participant.trackPublications.values()) {
        if (pub.track && (participant.isLocal || pub.isSubscribed)) {
          attachTrack(pub.track, participant, pub);
        }
      }
    };

    room.on(mod.RoomEvent.TrackSubscribed, (track, pub, participant) => {
      attachTrack(track, participant, pub);
      syncRoster();
    });
    room.on(mod.RoomEvent.TrackUnsubscribed, (track, pub, participant) => {
      detachTrack(track, participant, pub);
    });
    room.on(mod.RoomEvent.LocalTrackPublished, (pub, participant) => {
      if (pub.track) attachTrack(pub.track, participant, pub);
      syncRoster();
    });
    room.on(mod.RoomEvent.LocalTrackUnpublished, (pub, participant) => {
      if (pub.track) detachTrack(pub.track, participant, pub);
      else if (pub.source === mod.Track.Source.ScreenShare) {
        videosEl
          .querySelector(`[data-tile="${tileId(participant, "screen")}"]`)
          ?.remove();
      }
    });
    room.on(mod.RoomEvent.ParticipantConnected, (participant) => {
      ensureTile(participant, "user");
      syncRoster();
      toast(`${displayName(participant)} entrou na call.`);
    });
    room.on(mod.RoomEvent.ParticipantDisconnected, (participant) => {
      removeTilesFor(participant.identity);
      syncRoster();
    });
    room.on(mod.RoomEvent.ActiveSpeakersChanged, (speakers) => {
      paintSpeakers(speakers);
    });

    await room.connect(token.url, token.token);
    await room.localParticipant.setMicrophoneEnabled(true);

    attachExisting(room.localParticipant);
    for (const p of room.remoteParticipants.values()) {
      attachExisting(p);
    }
    syncRoster();
    playCallJoin();
    toast("Entrou na call.");

    try {
      currentEvent = await api(`/api/events/active?channel_id=${channel.id}`);
    } catch {
      currentEvent = null;
    }
    paintEvent();

    offEventWs = onWs((event) => {
      if (event.type !== "match_event" || !event.event) return;
      if (event.event.channel_id !== channel.id) return;
      currentEvent = event.event;
      paintEvent();
    });

    mountEl.querySelector("#call-mute").addEventListener("click", async () => {
      muted = !muted;
      await room.localParticipant.setMicrophoneEnabled(!muted);
      mountEl.querySelector("#call-mute").classList.toggle("off", muted);
      mountEl.querySelector("#call-mute").textContent = muted ? "🔇" : "🎤";
    });

    mountEl.querySelector("#call-deafen").addEventListener("click", () => {
      deafened = !deafened;
      document.querySelectorAll("audio[data-identity]").forEach((el) => {
        el.muted = deafened;
      });
      if (deafened && !muted) {
        muted = true;
        room.localParticipant.setMicrophoneEnabled(false);
        mountEl.querySelector("#call-mute").classList.add("off");
        mountEl.querySelector("#call-mute").textContent = "🔇";
      }
      mountEl.querySelector("#call-deafen").classList.toggle("off", deafened);
      mountEl.querySelector("#call-deafen").textContent = deafened ? "🙉" : "🎧";
    });

    mountEl.querySelector("#call-cam").addEventListener("click", async () => {
      try {
        camOn = !camOn;
        await room.localParticipant.setCameraEnabled(camOn);
        mountEl.querySelector("#call-cam").classList.toggle("on", camOn);
        if (camOn) {
          const pub = [...room.localParticipant.videoTrackPublications.values()].find(
            (p) => p.source === mod.Track.Source.Camera
          );
          if (pub?.track) attachTrack(pub.track, room.localParticipant, pub);
        } else {
          const wrap = videosEl.querySelector(
            `[data-tile="${tileId(room.localParticipant, "user")}"]`
          );
          wrap?.querySelectorAll("video").forEach((v) => v.remove());
          wrap?.classList.remove("has-video");
        }
      } catch (error) {
        camOn = false;
        toast(error.message || "Câmera indisponível.", true);
      }
    });

    mountEl.querySelector("#call-screen").addEventListener("click", async () => {
      try {
        screenOn = !screenOn;
        await room.localParticipant.setScreenShareEnabled(screenOn);
        mountEl.querySelector("#call-screen").classList.toggle("on", screenOn);
        if (screenOn) {
          const pub = [...room.localParticipant.videoTrackPublications.values()].find(
            (p) => p.source === mod.Track.Source.ScreenShare
          );
          if (pub?.track) attachTrack(pub.track, room.localParticipant, pub);
          toast("Compartilhando tela.");
        } else {
          videosEl
            .querySelector(`[data-tile="${tileId(room.localParticipant, "screen")}"]`)
            ?.remove();
          toast("Parou de compartilhar.");
        }
      } catch (error) {
        screenOn = false;
        mountEl.querySelector("#call-screen").classList.remove("on");
        toast(error.message || "Não foi possível compartilhar a tela.", true);
      }
    });

    mountEl.querySelector("#call-leave").addEventListener("click", async () => {
      await leaveVoiceCall();
      statusEl.textContent = "Saiu da call.";
      mountEl.querySelector(".call-controls")?.remove();
      panelEl.innerHTML = "";
      videosEl.innerHTML = "";
    });
  } catch (error) {
    statusEl.textContent = error.message;
    toast(error.message, true);
    paintEvent();
  }
}

export async function leaveVoiceCall() {
  clearEventTimer();
  if (offEventWs) {
    offEventWs();
    offEventWs = null;
  }
  document.querySelector(".screen-lightbox")?.remove();
  stageRoot?.remove();
  stageRoot = null;
  joinedChannelId = null;
  publishRoster(null);
  if (dockNode) {
    dockNode.hidden = true;
    dockNode.innerHTML = "";
  }
  if (!activeRoom) return;
  try {
    await activeRoom.disconnect();
  } catch {
    /* ignore */
  }
  activeRoom = null;
  document.querySelectorAll("audio[data-identity]").forEach((el) => el.remove());
}
