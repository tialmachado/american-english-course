import { store } from "../store.js";
import { renderResource } from "../components/resource.js";
import { renderLessons } from "./lessons.js";

const TAB_DEFS = [
  {id: "PLAN",      label: "Plano de Aula"},
  {id: "SB",        label: "Student Book"},
  {id: "WB",        label: "Workbook"},
  {id: "PE",        label: "Practical English"},
  {id: "LISTENING", label: "Listening"},
  {id: "EPISODE",   label: "Episodes"},
  {id: "TEST",      label: "Tests"},
  {id: "TG",        label: "Teacher's Guide"},
  {id: "EXTRA",     label: "Extras"},
];

/* Tabs that keep the main PDF persistent across unit changes. */
const PDF_TABS = new Set(["SB", "WB", "TG"]);

export async function renderCourse(main) {
  await store.load();
  const params = new URLSearchParams(location.search);
  const course = store.course(params.get("id"));
  if (!course) {
    main.innerHTML = `<p class="empty-state">Curso não encontrado. <a href="/">Voltar</a></p>`;
    return;
  }
  const tabs = store.resourcesByTab(course);
  const availableTabs = TAB_DEFS.filter(t => {
    if (t.id === "PLAN") return !!store.lessonsByCourse[course.id];
    return (tabs[t.id]?.length || 0) > 0;
  });
  let activeTab = params.get("tab") || availableTabs[0]?.id || "SB";
  if (!availableTabs.find(t => t.id === activeTab)) activeTab = availableTabs[0]?.id;
  let activeUnit = parseInt(params.get("unit")) || null;
  let pendingPdfPage = parseInt(params.get("page")) || null;

  document.title = `${course.title} · AEF`;

  main.innerHTML = `
    <div class="unit-header">
      <h2>${course.title} <small class="muted" style="font-size:14px;">${course.cefr}</small></h2>
      <div class="progress-row">
        <div class="progress"><span style="width:${store.coursePct(course)}%"></span></div>
        <div class="pct">${store.coursePct(course)}%</div>
      </div>
    </div>
    <div class="tabs" id="tabs"></div>
    <section id="content"></section>
  `;

  const tabsEl = main.querySelector("#tabs");
  const contentEl = main.querySelector("#content");

  function renderTabs() {
    tabsEl.innerHTML = "";
    for (const t of availableTabs) {
      const el = document.createElement("div");
      el.className = "tab" + (t.id === activeTab ? " active" : "");
      const count = t.id === "PLAN" ? "" : ` (${tabs[t.id].length})`;
      el.textContent = `${t.label}${count}`;
      el.onclick = () => {
        activeTab = t.id;
        activeUnit = null;
        updateUrl();
        renderContentShell();
        renderUnitPanel();
        renderTabs();
      };
      tabsEl.appendChild(el);
    }
  }

  /* Build the persistent shell for the current tab.
     PLAN: lesson plan view (no units).
     PDF tabs: PDF iframe left + scrollable unit panel right.
     Other tabs: single full-width panel. */
  function renderContentShell() {
    contentEl.innerHTML = "";
    if (activeTab === "PLAN") {
      const wrap = document.createElement("div");
      wrap.className = "lessons-pane";
      wrap.id = "lessons-pane";
      contentEl.appendChild(wrap);
      const initialLesson = new URLSearchParams(location.search).get("lesson");
      renderLessons(wrap, course.id, navigateToSB, initialLesson, navigateToWB, navigateToTG);
      return;
    }
    if (PDF_TABS.has(activeTab)) {
      const list = tabs[activeTab];
      const mainPDF = list.find(r => r.type === "pdf");
      // Teacher's Guide has no audio/video, so the PDF takes the full width.
      if (activeTab === "TG") {
        const wrap = document.createElement("div");
        wrap.className = "pdf-pane pdf-pane-full";
        contentEl.appendChild(wrap);
        if (mainPDF) {
          const initialPage = pendingPdfPage;
          pendingPdfPage = null;
          wrap.appendChild(renderPDFViewer(mainPDF, initialPage));
        } else {
          wrap.innerHTML = `<p class="empty-state">Sem PDF nesta aba.</p>`;
        }
        return;
      }
      const split = document.createElement("div");
      split.className = "split-view";
      split.innerHTML = `
        <div class="pdf-pane" id="pdf-pane"></div>
        <div class="unit-pane" id="unit-pane"></div>
      `;
      contentEl.appendChild(split);
      if (mainPDF) {
        const initialPage = pendingPdfPage;
        pendingPdfPage = null; // consume
        split.querySelector("#pdf-pane").appendChild(renderPDFViewer(mainPDF, initialPage));
      }
      else split.querySelector("#pdf-pane").innerHTML = `<p class="empty-state">Sem PDF nesta aba.</p>`;
    } else {
      const single = document.createElement("div");
      single.className = "unit-pane single";
      single.id = "unit-pane";
      contentEl.appendChild(single);
    }
  }

  function renderUnitPanel() {
    if (activeTab === "PLAN") return;
    const panel = contentEl.querySelector("#unit-pane");
    if (!panel) return;
    panel.innerHTML = "";

    const units = store.unitsForTab(course, activeTab);
    // If user has no unit selected and units exist, default to Unit 1 (better UX).
    if (units.length && activeUnit == null && PDF_TABS.has(activeTab)) {
      activeUnit = units[0];
      updateUrl();
    }

    panel.appendChild(buildUnitSelector(units));

    const list = store.resourcesForTabAndUnit(course, activeTab, activeUnit)
      .filter(r => !(PDF_TABS.has(activeTab) && r.type === "pdf"));
    if (!list.length) {
      panel.appendChild(Object.assign(document.createElement("p"),
        {className: "empty-state", textContent: "Nenhum recurso nesta seleção."}));
      return;
    }
    groupAndRender(panel, list);
  }

  function buildUnitSelector(units) {
    const bar = document.createElement("div");
    bar.className = "unit-selector";
    const total = store.resourcesForTabAndUnit(course, activeTab, activeUnit).length;
    const pct = activeUnit ? store.unitProgress(course, activeUnit) : store.coursePct(course);
    const label = activeUnit ? `Unit ${activeUnit}` : "Todas as unidades";
    bar.innerHTML = `
      <button class="us-arrow" data-dir="prev" title="Anterior">‹</button>
      <button class="us-current" title="Escolher unidade">
        <span class="us-label">${label}</span>
        <span class="us-meta">${pct}% · ${total} recursos</span>
        <span class="us-caret">▾</span>
      </button>
      <button class="us-arrow" data-dir="next" title="Próxima">›</button>
    `;
    const idx = activeUnit ? units.indexOf(activeUnit) : -1;
    const prev = bar.querySelector('[data-dir="prev"]');
    const next = bar.querySelector('[data-dir="next"]');
    if (!units.length || idx <= 0) prev.disabled = true;
    if (!units.length || idx === units.length - 1) next.disabled = true;
    prev.onclick = () => {
      if (idx > 0) { activeUnit = units[idx - 1]; updateUrl(); renderUnitPanel(); }
    };
    next.onclick = () => {
      if (units.length && idx < units.length - 1) { activeUnit = units[idx + 1]; updateUrl(); renderUnitPanel(); }
    };
    bar.querySelector(".us-current").onclick = () => toggleDropdown(bar, units);
    return bar;
  }

  function toggleDropdown(bar, units) {
    let dd = bar.querySelector(".us-dropdown");
    if (dd) { dd.remove(); return; }
    dd = document.createElement("div");
    dd.className = "us-dropdown";
    const items = [
      {unit: null, label: "Todas as unidades", pct: store.coursePct(course),
       count: tabs[activeTab].length},
      ...units.map(u => ({unit: u, label: `Unit ${u}`,
                          pct: store.unitProgress(course, u),
                          count: tabs[activeTab].filter(r =>
                            r.unit === u ||
                            (r.meta?.covers_units?.includes(u))).length})),
    ];
    for (const it of items) {
      const row = document.createElement("button");
      row.className = "us-dd-item" + (activeUnit === it.unit ? " active" : "");
      row.innerHTML = `
        <span>${it.label}</span>
        <span class="us-dd-meta">${it.pct}% · ${it.count}</span>
      `;
      row.onclick = () => { activeUnit = it.unit; updateUrl(); renderUnitPanel(); };
      dd.appendChild(row);
    }
    bar.appendChild(dd);
    // Close when clicking outside
    const closeOnOutside = (e) => {
      if (!bar.contains(e.target)) {
        dd.remove();
        document.removeEventListener("click", closeOnOutside);
      }
    };
    setTimeout(() => document.addEventListener("click", closeOnOutside), 0);
  }

  function updateUrl(extras = {}) {
    const u = new URLSearchParams();
    u.set("id", course.id);
    u.set("tab", activeTab);
    if (activeUnit) u.set("unit", activeUnit);
    if (extras.page) u.set("page", extras.page);
    history.replaceState(null, "", `/course?${u}`);
  }

  function navigateToSB({ unit, pdfPage }) {
    activeTab = "SB";
    activeUnit = unit;
    pendingPdfPage = pdfPage;
    updateUrl({ page: pdfPage });
    renderTabs();
    renderContentShell();
    renderUnitPanel();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function navigateToWB({ unit, pdfPage }) {
    activeTab = "WB";
    activeUnit = unit;
    pendingPdfPage = pdfPage;
    updateUrl({ page: pdfPage });
    renderTabs();
    renderContentShell();
    renderUnitPanel();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function navigateToTG({ unit, pdfPage }) {
    activeTab = "TG";
    activeUnit = unit;
    pendingPdfPage = pdfPage;
    updateUrl({ page: pdfPage });
    renderTabs();
    renderContentShell();
    renderUnitPanel();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  document.addEventListener("progress-changed", () => {
    const pct = store.coursePct(course);
    main.querySelector(".progress-row span").style.width = pct + "%";
    main.querySelector(".progress-row .pct").textContent = pct + "%";
    // Update unit selector's pct without rebuilding the list
    const meta = contentEl.querySelector(".us-meta");
    if (meta && activeUnit) {
      const total = store.resourcesForTabAndUnit(course, activeTab, activeUnit).length;
      meta.textContent = `${store.unitProgress(course, activeUnit)}% · ${total} recursos`;
    }
  });

  renderTabs();
  renderContentShell();
  renderUnitPanel();
}

function groupAndRender(parent, list) {
  const groups = {};
  for (const r of list) {
    const key = r.meta?.category || "";
    (groups[key] ||= []).push(r);
  }
  const keys = Object.keys(groups);
  if (keys.length === 1 && keys[0] === "") {
    for (const r of list) parent.appendChild(renderResource(r));
    return;
  }
  for (const key of keys.sort()) {
    if (key) {
      const h = document.createElement("h4");
      h.className = "group-heading";
      h.textContent = key;
      parent.appendChild(h);
    }
    for (const r of groups[key]) parent.appendChild(renderResource(r));
  }
}

function renderPDFViewer(r, initialPage = null) {
  const wrap = document.createElement("div");
  wrap.className = "pdf-wrap";
  const url = "/files/" + r.path.split("/").map(encodeURIComponent).join("/");
  const startPage = initialPage && initialPage > 0 ? initialPage : 1;
  const hash = initialPage ? `#page=${startPage}&view=FitH` : "#view=FitH";
  wrap.innerHTML = `
    <div class="bar">
      <span class="title">${r.title}</span>
      <label class="muted" style="font-size:12px;">Página
        <input type="number" min="1" value="${startPage}" class="page-input">
      </label>
      <button class="go-btn">Ir</button>
      <a href="${url}" target="_blank">Abrir ↗</a>
    </div>
    <iframe src="${url}${hash}"></iframe>
  `;
  const input = wrap.querySelector("input");
  const iframe = wrap.querySelector("iframe");
  const go = () => {
    const page = parseInt(input.value) || 1;
    iframe.src = `${url}#page=${page}&view=FitH`;
  };
  wrap.querySelector(".go-btn").onclick = go;
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  return wrap;
}
