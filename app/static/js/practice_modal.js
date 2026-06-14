/* Inline DOCX viewer for Practice files.
   Fetches /api/practice?path=... and shows it in a fullscreen modal. */

function ensureModal() {
  let modal = document.getElementById("practice-modal");
  if (modal) return modal;
  modal = document.createElement("div");
  modal.id = "practice-modal";
  modal.className = "pv-modal";
  modal.innerHTML = `
    <div class="pv-modal-backdrop"></div>
    <div class="pv-modal-window">
      <header class="pv-modal-header">
        <span class="pv-modal-title">Practice</span>
        <button class="pv-modal-close" type="button" title="Fechar (Esc)" aria-label="Fechar">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
            <line x1="6" y1="6" x2="18" y2="18"/>
            <line x1="18" y1="6" x2="6" y2="18"/>
          </svg>
        </button>
      </header>
      <div class="pv-modal-body"><div class="loading">Carregando…</div></div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.querySelector(".pv-modal-close").onclick = () => modal.classList.remove("open");
  modal.querySelector(".pv-modal-backdrop").onclick = () => modal.classList.remove("open");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") modal.classList.remove("open");
  });
  return modal;
}

export async function openPracticeDocx(relativePath, title) {
  const modal = ensureModal();
  modal.querySelector(".pv-modal-title").textContent = title || "Practice";
  modal.querySelector(".pv-modal-body").innerHTML = `<div class="loading">Carregando…</div>`;
  modal.classList.add("open");
  try {
    const res = await fetch(`/api/practice?path=${encodeURIComponent(relativePath)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const meta = data.audio_count
      ? `<div class="pv-meta muted">${data.audio_count} áudios embedados</div>`
      : "";
    modal.querySelector(".pv-modal-body").innerHTML = meta + data.html;
  } catch (e) {
    modal.querySelector(".pv-modal-body").innerHTML = `
      <div class="empty-state">
        <p>Não consegui abrir este arquivo.</p>
        <p class="muted" style="font-size:12px;">${String(e)}</p>
      </div>
    `;
  }
}
