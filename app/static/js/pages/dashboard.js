import { api } from "../api.js";
import { store } from "../store.js";

function fmtHours(seconds) {
  if (!seconds) return "0h";
  const h = seconds / 3600;
  if (h < 1) return `${Math.round(seconds / 60)} min`;
  if (h < 10) return `${h.toFixed(1)} h`;
  return `${Math.round(h)} h`;
}

export async function renderDashboard(main) {
  await store.load();
  const stats = await api.stats();
  const study = await (await fetch("/api/study/stats")).json();

  main.innerHTML = `
    <h2 style="margin-bottom:16px;">Dashboard</h2>

    <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-dim);margin-bottom:10px;">Tempo de estudo</h3>
    <div class="dash-grid">
      <div class="stat-card">
        <div class="label">Hoje</div>
        <div class="value">${fmtHours(study.today_seconds)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Esta semana</div>
        <div class="value">${fmtHours(study.week_seconds)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Este mês</div>
        <div class="value">${fmtHours(study.month_seconds)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Acumulado total</div>
        <div class="value">${fmtHours(study.total_seconds)}<small> · ${study.session_count} sessões</small></div>
      </div>
    </div>

    <div class="listening-chart">
      <div class="label muted" style="font-size:12px;text-transform:uppercase;letter-spacing:.8px;">Últimos 30 dias de estudo</div>
      <div class="bars" id="study-bars"></div>
    </div>

    <div class="dash-grid" style="margin-top:8px;">
      <div class="listening-chart" style="margin:0;">
        <div class="label muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;">12 semanas</div>
        <div class="bars" id="study-weeks"></div>
      </div>
      <div class="listening-chart" style="margin:0;">
        <div class="label muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;">12 meses</div>
        <div class="bars" id="study-months"></div>
      </div>
    </div>

    <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-dim);margin:28px 0 10px;">Progresso & engajamento</h3>
    <div class="dash-grid">
      <div class="stat-card">
        <div class="label">Streak</div>
        <div class="value">${stats.streak}<small> dias</small></div>
      </div>
      <div class="stat-card">
        <div class="label">Concluídos</div>
        <div class="value">${stats.total_completed}<small> recursos</small></div>
      </div>
      <a class="stat-card" href="/favorites" style="text-decoration:none;color:inherit;cursor:pointer;">
        <div class="label">Favoritos</div>
        <div class="value">${stats.total_favorites}<small> ⭐</small></div>
      </a>
    </div>

    <h3 style="margin:24px 0 12px;">Progresso por curso</h3>
    <div id="courses"></div>

    <div style="margin-top:32px;display:flex;gap:8px;">
      <button id="export">Exportar progresso (JSON)</button>
    </div>
  `;

  // Study time: last 30 days
  renderBars(main.querySelector("#study-bars"), study.last_30_days,
    d => d.day, d => d.seconds, fmtHours);
  // Study time: last 12 weeks
  renderBars(main.querySelector("#study-weeks"), study.last_12_weeks,
    d => `sem. de ${d.week_start}`, d => d.seconds, fmtHours);
  // Study time: last 12 months
  renderBars(main.querySelector("#study-months"), study.last_12_months,
    d => d.month, d => d.seconds, fmtHours);

  const coursesEl = main.querySelector("#courses");
  for (const c of stats.courses) {
    const row = document.createElement("div");
    row.style.cssText = "background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:8px;display:flex;align-items:center;gap:12px;cursor:pointer;";
    row.innerHTML = `
      <div style="flex:1;">
        <strong>${c.title}</strong>
        <div class="muted" style="font-size:12px;">${c.completed} / ${c.total} concluídos · ${c.cefr}</div>
      </div>
      <div style="width:200px;">
        <div class="progress"><span style="width:${c.pct}%"></span></div>
      </div>
      <div class="pct" style="min-width:50px;text-align:right;">${c.pct}%</div>
    `;
    row.onclick = () => { location.href = `/course?id=${c.id}`; };
    coursesEl.appendChild(row);
  }

  main.querySelector("#export").onclick = async () => {
    const data = await api.export();
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `aef-progress-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
  };

  // Re-render the dashboard whenever the user starts/stops the timer
  document.addEventListener("study-stats-changed", () => renderDashboard(main), { once: true });
}

function renderBars(container, items, labelFn, valueFn, fmt) {
  if (!container || !items) return;
  const values = items.map(valueFn);
  const max = Math.max(60, ...values);
  for (const it of items) {
    const v = valueFn(it);
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max(2, Math.round(98 * v / max))}px`;
    bar.title = `${labelFn(it)}: ${fmt(v)}`;
    container.appendChild(bar);
  }
}
