/* Renders the global favorites view: every resource the user starred,
   grouped by course.  Each row links back to the resource's course context. */
import { api, fileUrl } from "../api.js";
import { store } from "../store.js";
import { initPlayer } from "../player/floating.js";

const TYPE_ICON = { pdf: "📄", audio: "🎧", video: "🎬", doc: "📝", test: "📋" };
const SECTION_LABEL = {
  SB: "Student Book", WB: "Workbook", PE: "Practical English",
  LISTENING: "Listening", RC: "Review & Check", EPISODE: "Episode",
  PRACTICE: "Practice", TEST: "Test", TG: "Teacher's Guide", EXTRA: "Extra",
};

export async function renderFavorites(main) {
  await store.load();
  main.innerHTML = `<div class="loading">Carregando favoritos…</div>`;
  const data = await (await fetch("/api/favorites")).json();

  if (!data.items.length) {
    main.innerHTML = `
      <h2 style="margin-bottom:10px;">Favoritos</h2>
      <div class="empty-state">
        <p>Você ainda não favoritou nenhum recurso.</p>
        <p class="muted" style="margin-top:8px;">Clique no <strong>★</strong> ao lado de qualquer áudio, vídeo, PDF, etc. dentro de um curso para marcá-lo como favorito.</p>
      </div>
    `;
    return;
  }

  // Group by course in the order of the index
  const byCourse = new Map();
  for (const it of data.items) {
    if (!byCourse.has(it.course_id)) byCourse.set(it.course_id, { title: it.course_title, items: [] });
    byCourse.get(it.course_id).items.push(it);
  }

  main.innerHTML = `
    <h2 style="margin-bottom:6px;">Favoritos ⭐</h2>
    <p class="muted" style="margin-bottom:18px;">${data.total} recursos favoritados em ${byCourse.size} cursos.</p>
    <div id="fav-groups"></div>
  `;
  const groupsEl = main.querySelector("#fav-groups");

  const player = initPlayer();

  for (const [cid, group] of byCourse) {
    const section = document.createElement("section");
    section.className = "fav-group";
    section.innerHTML = `
      <h3 class="fav-group-title">
        <span>${group.title}</span>
        <span class="muted" style="font-size:12px;">${group.items.length} favoritos</span>
      </h3>
      <div class="fav-rows" data-course="${cid}"></div>
    `;
    const rowsEl = section.querySelector(".fav-rows");
    for (const it of group.items) {
      rowsEl.appendChild(buildRow(it, cid, player));
    }
    groupsEl.appendChild(section);
  }
}

function buildRow(item, courseId, player) {
  const icon = TYPE_ICON[item.type] || "📁";
  const sectionLabel = SECTION_LABEL[item.section] || item.section;
  const subtitle = [
    sectionLabel,
    item.unit ? `Unit ${item.unit}` : null,
    item.track ? `Track ${item.track}` : null,
  ].filter(Boolean).join(" · ");

  const row = document.createElement("div");
  row.className = "resource";
  row.innerHTML = `
    <input type="checkbox" class="check" ${item.completed ? "checked" : ""} title="Marcar concluído">
    <span class="icon">${icon}</span>
    <div class="title">
      ${escape(item.title)}
      <small class="muted">${escape(subtitle)}</small>
    </div>
    <button class="fav on" title="Remover dos favoritos">★</button>
    ${item.type === "audio"
      ? `<button class="play-btn" title="Tocar">▶</button>`
      : item.type === "pdf"
        ? `<a class="open-btn" href="${fileUrl(item.path)}" target="_blank">Abrir</a>`
        : `<a class="open-btn" href="${fileUrl(item.path)}" target="_blank">Abrir</a>`}
  `;

  // Toggle completed
  row.querySelector(".check").onchange = async () => {
    await store.toggleCompleted(item.resource_id);
    row.querySelector(".check").checked = !!store.progress[item.resource_id]?.completed;
  };

  // Remove from favorites
  row.querySelector(".fav").onclick = async () => {
    await store.toggleFavorite(item.resource_id);
    row.style.transition = "opacity .2s, transform .2s";
    row.style.opacity = "0";
    row.style.transform = "translateX(-12px)";
    setTimeout(() => row.remove(), 200);
  };

  // Audio: play through the floating player
  const playBtn = row.querySelector(".play-btn");
  if (playBtn) {
    const resource = {
      id: item.resource_id,
      title: item.title,
      path: item.path,
      type: item.type,
    };
    playBtn.onclick = () => player.toggle(resource);
    player.registerButton(playBtn, item.resource_id);
  }
  return row;
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));
}
