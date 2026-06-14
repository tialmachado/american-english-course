/* Render one resource row. Audio uses the global floating player. */
import { api, fileUrl, fmtTime } from "../api.js";
import { store } from "../store.js";
import { initPlayer } from "../player/floating.js";
import { openPracticeDocx } from "../practice_modal.js";

const TYPE_ICON = { pdf: "📄", audio: "🎧", video: "🎬", doc: "📝", test: "📋" };
const noteSaveTimers = {};

export function renderResource(r) {
  const p = store.progress[r.id] || {};
  const note = store.notes[r.id] || "";
  const icon = TYPE_ICON[r.type] || "📁";

  if (r.type === "audio") return renderAudio(r, p, note, icon);
  if (r.type === "video") return renderVideo(r, p, note, icon);
  return renderFileRow(r, p, note, icon);
}

function renderFileRow(r, p, note, icon) {
  const div = document.createElement("div");
  div.className = "resource";
  const isPracticeDocx = r.type === "doc" && r.section === "PRACTICE" && r.path.toLowerCase().endsWith(".docx");
  const openCtl = isPracticeDocx
    ? `<button class="open-btn pv-open" type="button">Visualizar</button>`
    : `<a class="open-btn" href="${fileUrl(r.path)}" target="_blank">Abrir</a>`;
  div.innerHTML = `
    <input type="checkbox" class="check" ${p.completed ? "checked" : ""} title="Marcar concluído">
    <span class="icon">${icon}</span>
    <div class="title">
      ${escapeHTML(r.title)}
      ${r.unit ? `<small>Unit ${r.unit}${r.meta?.lesson ? " · Lesson " + r.meta.lesson : ""}</small>` : ""}
    </div>
    <button class="fav ${p.favorite ? "on" : ""}" title="Favorito">★</button>
    ${openCtl}
    <button class="notes-toggle" title="Notas">✎</button>
  `;
  wireCheck(div.querySelector(".check"), r);
  wireFav(div.querySelector(".fav"), r);
  if (isPracticeDocx) {
    div.querySelector(".pv-open").onclick = (e) => {
      e.stopPropagation();
      openPracticeDocx(r.path, r.title);
    };
  }
  const notesWrap = buildNotes(r.id, note);
  div.querySelector(".notes-toggle").onclick = () => notesWrap.classList.toggle("open");

  const wrap = document.createElement("div");
  wrap.appendChild(div);
  wrap.appendChild(notesWrap);
  return wrap;
}

function renderAudio(r, p, note, icon) {
  const player = initPlayer();
  const div = document.createElement("div");
  div.className = "resource audio-row";
  div.innerHTML = `
    <input type="checkbox" class="check" ${p.completed ? "checked" : ""} title="Marcar concluído">
    <button class="play-btn" title="Tocar">▶</button>
    <div class="title">
      ${escapeHTML(r.title)}
      ${r.unit ? `<small>Unit ${r.unit}${r.track ? " · " + r.track : ""}${p.duration ? " · " + fmtTime(p.duration) : ""}</small>` : ""}
    </div>
    <button class="fav ${p.favorite ? "on" : ""}" title="Favorito">★</button>
    <button class="notes-toggle" title="Notas">✎</button>
  `;
  const playBtn = div.querySelector(".play-btn");
  playBtn.onclick = () => player.toggle(r);
  player.registerButton(playBtn, r.id);

  wireCheck(div.querySelector(".check"), r);
  wireFav(div.querySelector(".fav"), r);
  const notesWrap = buildNotes(r.id, note);
  div.querySelector(".notes-toggle").onclick = () => notesWrap.classList.toggle("open");

  const wrap = document.createElement("div");
  wrap.appendChild(div);
  wrap.appendChild(notesWrap);
  return wrap;
}

function renderVideo(r, p, note, icon) {
  const wrap = document.createElement("div");
  wrap.className = "resource-media";
  wrap.innerHTML = `
    <div class="row1">
      <input type="checkbox" class="check" ${p.completed ? "checked" : ""} title="Marcar concluído">
      <span class="icon">${icon}</span>
      <div class="title">
        ${escapeHTML(r.title)}
        ${r.unit ? `<small class="muted">Unit ${r.unit}</small>` : ""}
      </div>
      <button class="fav ${p.favorite ? "on" : ""}" title="Favorito">★</button>
      <button class="notes-toggle" title="Notas">✎</button>
    </div>
    <video controls preload="metadata" src="${fileUrl(r.path)}"></video>
  `;
  const media = wrap.querySelector("video");
  if (p.last_position) {
    media.addEventListener("loadedmetadata", () => { media.currentTime = p.last_position; }, {once: true});
  }
  let lastSaved = 0;
  media.addEventListener("timeupdate", () => {
    const now = Date.now();
    if (now - lastSaved < 5000) return;
    lastSaved = now;
    api.setPosition(r.id, media.currentTime, media.duration || 0);
  });
  media.addEventListener("ended", async () => {
    if (!store.progress[r.id]?.completed) {
      await store.toggleCompleted(r.id);
      wrap.querySelector(".check").checked = true;
      document.dispatchEvent(new Event("progress-changed"));
    }
  });
  wireCheck(wrap.querySelector(".check"), r);
  wireFav(wrap.querySelector(".fav"), r);
  const notesWrap = buildNotes(r.id, note);
  notesWrap.classList.add("inside");
  wrap.appendChild(notesWrap);
  wrap.querySelector(".notes-toggle").onclick = () => notesWrap.classList.toggle("open");
  return wrap;
}

function wireCheck(checkbox, r) {
  const apply = async () => {
    await store.toggleCompleted(r.id);
    checkbox.checked = !!store.progress[r.id]?.completed;
    document.dispatchEvent(new Event("progress-changed"));
  };
  checkbox.onchange = apply;
}

function wireFav(btn, r) {
  btn.onclick = async () => {
    await store.toggleFavorite(r.id);
    btn.classList.toggle("on", store.progress[r.id]?.favorite);
  };
}

function buildNotes(resource_id, note) {
  const wrap = document.createElement("div");
  wrap.className = "notes-box" + (note ? " open" : "");
  wrap.innerHTML = `<textarea placeholder="Suas notas sobre este recurso…">${escapeHTML(note)}</textarea>`;
  const ta = wrap.querySelector("textarea");
  ta.addEventListener("input", () => {
    clearTimeout(noteSaveTimers[resource_id]);
    noteSaveTimers[resource_id] = setTimeout(async () => {
      await api.setNote(resource_id, ta.value);
      store.notes[resource_id] = ta.value;
    }, 800);
  });
  return wrap;
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));
}
