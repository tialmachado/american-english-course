import { store } from "../store.js";

export async function renderHome(main) {
  await store.load();
  const grid = document.createElement("div");
  grid.className = "course-grid";
  for (const c of store.index.courses) {
    const pct = store.coursePct(c);
    const step = store.stepProgress(c.id);
    const card = document.createElement("div");
    card.className = "course-card";
    let metaLine;
    if (step && step.total > 0) {
      metaLine = `<strong style="color:var(--good)">${step.done}</strong> / ${step.total} momentos concluídos`;
    } else {
      const total = c.resources.length;
      const done = c.resources.filter(r => store.progress[r.id]?.completed).length;
      metaLine = `${done} de ${total} recursos concluídos`;
    }
    card.innerHTML = `
      <span class="badge">${c.cefr}</span>
      <h2>${c.title}</h2>
      <div class="meta">${c.resources.length} recursos · ${c.max_unit} units${step ? ` · ${step.total} momentos` : ""}</div>
      <div class="progress-row">
        <div class="progress"><span style="width:${pct}%"></span></div>
        <div class="pct">${pct}%</div>
      </div>
      <div class="meta" style="margin-top:8px;">${metaLine}</div>
    `;
    card.onclick = () => { location.href = `/course?id=${c.id}`; };
    grid.appendChild(card);
  }
  main.innerHTML = "";
  main.appendChild(grid);

  // Welcome / hint
  const hint = document.createElement("div");
  hint.className = "muted";
  hint.style.marginTop = "32px";
  hint.style.textAlign = "center";
  hint.innerHTML = `Total: ${store.index.courses.reduce((s,c)=>s+c.resources.length,0)} recursos indexados.
    <a href="/dashboard">Ver dashboard →</a>`;
  main.appendChild(hint);
}
