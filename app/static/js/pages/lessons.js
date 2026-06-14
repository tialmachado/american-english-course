/* Renderiza a aba "Plano de Aula" com a sequência sugerida pelo Teacher's Guide.
   Para cada aula: título, badges de tópicos, checklist de momentos, links SB/TG. */
import { fileUrl } from "../api.js";
import { store } from "../store.js";
import { renderResource } from "../components/resource.js";

const TYPE_LABEL = {
  lesson: "Lesson",
  practical_english: "Practical English",
  review: "Review & Check",
};

const TOPIC_ORDER = ["grammar", "vocabulary", "pronunciation", "function", "speaking", "listening", "reading"];
const TOPIC_LABEL = {
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  pronunciation: "Pronunciation",
  function: "Function",
  speaking: "Speaking",
  listening: "Listening",
  reading: "Reading",
};
const TOPIC_ICON = {
  grammar: "📐",
  vocabulary: "📖",
  pronunciation: "🔤",
  function: "💬",
  speaking: "🗣",
  listening: "🎧",
  reading: "📰",
};

export async function renderLessons(container, courseId, navigateToSB, initialLessonCode, navigateToWB, navigateToTG) {
  container.innerHTML = `<div class="loading">Carregando plano de aula…</div>`;
  let data;
  try {
    const res = await fetch(`/api/lessons/${courseId}`);
    if (!res.ok) throw new Error(res.statusText);
    data = await res.json();
  } catch (e) {
    container.innerHTML = `
      <div class="empty-state">
        <p>Ainda não há plano de aula estruturado para este curso.</p>
        <p class="muted" style="margin-top:8px;">Por enquanto só o <strong>Starter</strong> está disponível.</p>
      </div>`;
    return;
  }

  container.innerHTML = "";

  // Header with intro + lesson selector
  const headerBox = document.createElement("div");
  headerBox.className = "lessons-header";
  container.appendChild(headerBox);

  const cardWrap = document.createElement("div");
  cardWrap.className = "lessons-card-wrap";
  container.appendChild(cardWrap);

  // State
  let activeIndex = 0;
  if (initialLessonCode) {
    const idx = data.lessons.findIndex(l => l.code === initialLessonCode);
    if (idx >= 0) activeIndex = idx;
  } else {
    // Try to resume from the first lesson that's not 100% done
    const firstIncomplete = data.lessons.findIndex(l => {
      const st = store.lessonStepStats(courseId, l);
      return st.total > 0 && st.done < st.total;
    });
    if (firstIncomplete > 0) activeIndex = firstIncomplete;
  }

  function rerender() {
    const lesson = data.lessons[activeIndex];
    renderHeader(headerBox, data, activeIndex, courseId, (idx) => {
      activeIndex = idx;
      rerender();
    });
    cardWrap.innerHTML = "";
    cardWrap.appendChild(renderLessonCard(lesson, data, navigateToSB, navigateToWB, navigateToTG));
    // Sync URL so refresh keeps the same lesson
    const u = new URLSearchParams(location.search);
    u.set("lesson", lesson.code);
    history.replaceState(null, "", `/course?${u}`);
  }

  document.addEventListener("progress-changed", () => {
    // Refresh the header counters/list because step pct may have changed
    renderHeader(headerBox, data, activeIndex, courseId, (idx) => {
      activeIndex = idx;
      rerender();
    });
  });

  rerender();
}

function renderHeader(headerBox, data, activeIndex, courseId, onChange) {
  const lessons = data.lessons;
  const lesson = lessons[activeIndex];
  const totalSteps = lessons.reduce((s, l) => s + (l.steps?.length || 0), 0);
  const doneSteps = lessons.reduce((s, l) => s + store.lessonStepStats(courseId, l).done, 0);
  const overallPct = totalSteps ? Math.round(100 * doneSteps / totalSteps) : 0;
  headerBox.innerHTML = `
    <div class="lessons-overall">
      <div>
        <strong>${lessons.length} aulas</strong>
        <span class="muted">· ${Math.max(...lessons.map(l => l.file))} Files · ${totalSteps} momentos</span>
      </div>
      <div class="lessons-overall-stats">
        <span class="muted">${doneSteps} / ${totalSteps} momentos concluídos</span>
        <div class="progress" style="width:120px;"><span style="width:${overallPct}%"></span></div>
        <span class="pct">${overallPct}%</span>
      </div>
    </div>
    <div class="lesson-selector">
      <button class="us-arrow" data-dir="prev" title="Aula anterior" ${activeIndex === 0 ? 'disabled' : ''}>‹</button>
      <button class="us-current" type="button">
        <span class="us-label">
          <span class="lc-code-inline">${escape(lesson.code)}</span>
          ${escape(lesson.title)}
        </span>
        <span class="us-meta">File ${lesson.file} · ${activeIndex + 1} / ${lessons.length}</span>
        <span class="us-caret">▾</span>
      </button>
      <button class="us-arrow" data-dir="next" title="Próxima aula" ${activeIndex === lessons.length - 1 ? 'disabled' : ''}>›</button>
    </div>
  `;
  headerBox.querySelector('[data-dir="prev"]').onclick = () => activeIndex > 0 && onChange(activeIndex - 1);
  headerBox.querySelector('[data-dir="next"]').onclick = () => activeIndex < lessons.length - 1 && onChange(activeIndex + 1);
  headerBox.querySelector(".us-current").onclick = () => toggleLessonDropdown(headerBox, lessons, activeIndex, courseId, onChange);
}

function toggleLessonDropdown(bar, lessons, activeIndex, courseId, onChange) {
  let dd = bar.querySelector(".us-dropdown");
  if (dd) { dd.remove(); return; }
  dd = document.createElement("div");
  dd.className = "us-dropdown lessons-dropdown";
  let lastFile = -1;
  lessons.forEach((lesson, idx) => {
    if (lesson.file !== lastFile) {
      const fh = document.createElement("div");
      fh.className = "us-dd-file-header";
      fh.textContent = `File ${lesson.file}`;
      dd.appendChild(fh);
      lastFile = lesson.file;
    }
    const stats = store.lessonStepStats(courseId, lesson);
    const row = document.createElement("button");
    row.className = "us-dd-item lesson-dd-item" + (idx === activeIndex ? " active" : "") + (stats.done === stats.total && stats.total > 0 ? " done" : "");
    row.innerHTML = `
      <span class="us-dd-code">${escape(lesson.code)}</span>
      <span class="us-dd-title">${escape(lesson.title)}</span>
      <span class="us-dd-meta">${stats.done}/${stats.total}</span>
    `;
    row.onclick = () => { onChange(idx); };
    dd.appendChild(row);
  });
  bar.appendChild(dd);
  setTimeout(() => {
    const closeOnOutside = (e) => {
      if (!bar.contains(e.target)) {
        dd.remove();
        document.removeEventListener("click", closeOnOutside);
      }
    };
    document.addEventListener("click", closeOnOutside);
  }, 0);
}

function renderLessonCard(lesson, courseData, navigateToSB, navigateToWB, navigateToTG) {
  const card = document.createElement("article");
  card.className = `lesson-card type-${lesson.type}`;
  card.dataset.lessonCode = lesson.code;

  const sbPdfPage = lesson.sb_page + (courseData.sb_pdf_offset || 0);
  const tgPdfPage = lesson.tg_page + (courseData.tg_pdf_offset || 0);
  const sbUrl = fileUrl(courseData.sb_pdf_path) + `#page=${sbPdfPage}&view=FitH`;
  const tgUrl = fileUrl(courseData.tg_pdf_path) + `#page=${tgPdfPage}&view=FitH`;

  const topics = lesson.topics || {};
  const topicEntries = TOPIC_ORDER
    .map(k => [k, topics[k]])
    .filter(([_, v]) => v && v.trim());

  const steps = lesson.steps || [];
  const stepStats = store.lessonStepStats(courseData.id, lesson);

  const summary = lesson.summary || "";
  const summarySource = lesson.summary_source || "topics";

  card.innerHTML = `
    <header>
      <div class="lc-meta">
        <span class="lc-code">${escape(lesson.code)}</span>
        <span class="lc-type">${TYPE_LABEL[lesson.type] || ""}</span>
      </div>
      <h4 class="lc-title">${escape(lesson.title)}</h4>
      <div class="lc-pages">
        SB p.${lesson.sb_page} · TG p.${lesson.tg_page}
      </div>
    </header>
    ${summary ? `
      <p class="lc-summary" data-source="${summarySource}">
        ${escape(summary)}
      </p>
    ` : ""}
    ${topicEntries.length ? `
      <div class="lc-topics">
        ${topicEntries.map(([k, v]) => `
          <div class="lc-topic">
            <span class="lc-topic-icon">${TOPIC_ICON[k] || "•"}</span>
            <div>
              <div class="lc-topic-label">${TOPIC_LABEL[k]}</div>
              <div class="lc-topic-text">${escape(v)}</div>
            </div>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${steps.length ? `
      <div class="lc-steps">
        <div class="lc-steps-header">
          <span class="lc-steps-title">Momentos da aula</span>
          <span class="lc-steps-count">
            <span class="lc-steps-done">${stepStats.done}</span> /
            <span class="lc-steps-total">${stepStats.total}</span> concluídos
          </span>
        </div>
        <div class="lc-progress"><span class="lc-progress-bar" style="width:${stepStats.pct}%"></span></div>
        <ul class="lc-step-list">
          ${steps.map(s => renderStep(s, courseData.id, lesson.code, lesson, courseData, navigateToWB)).join("")}
        </ul>
      </div>
    ` : ""}
    <div class="lc-related-mount"></div>
    <footer class="lc-actions">
      <button class="lc-btn primary lc-go-sb" type="button">Abrir SB p.${lesson.sb_page} →</button>
      <button class="lc-btn lc-go-tg" type="button">Ver plano no TG p.${lesson.tg_page} →</button>
    </footer>
  `;
  const relatedMount = card.querySelector(".lc-related-mount");
  const relatedEl = renderRelatedResources(lesson, courseData);
  if (relatedEl) relatedMount.replaceWith(relatedEl);
  else relatedMount.remove();
  card.querySelectorAll(".lc-step").forEach((row) => {
    row.addEventListener("click", async (e) => {
      // Skip if clicking interactive children (links, buttons, the checkbox).
      if (e.target.tagName === "INPUT") return;
      if (e.target.closest("a") || e.target.closest("button")) return;
      const checkbox = row.querySelector("input[type=checkbox]");
      checkbox.checked = !checkbox.checked;
      await applyStepToggle(row, checkbox.checked, courseData, lesson, card);
    });
    row.querySelector("input[type=checkbox]").addEventListener("change", async (e) => {
      await applyStepToggle(row, e.target.checked, courseData, lesson, card);
    });
  });

  // Workbook deep-link: switch to WB tab + page in-app
  card.querySelectorAll(".lc-go-wb").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const wbBookPage = parseInt(btn.dataset.wbPage);
      const wbPdfPage = wbBookPage + (courseData.wb_pdf_offset || 0);
      if (typeof navigateToWB === "function") {
        navigateToWB({ unit: lesson.file, pdfPage: wbPdfPage, bookPage: wbBookPage });
      }
    });
  });

  // Copy ChatGPT prompt
  const copyBtn = card.querySelector(".lc-copy-prompt");
  if (copyBtn) {
    copyBtn.onclick = async () => {
      const text = buildChatGPTPrompt(lesson, courseData.title);
      try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = "Copiado ✓";
        setTimeout(() => { copyBtn.textContent = "Copiar prompt"; }, 1500);
      } catch {
        copyBtn.textContent = "Erro ao copiar";
      }
    };
  }

  card.querySelector(".lc-go-sb").addEventListener("click", () => {
    if (typeof navigateToSB === "function") {
      navigateToSB({
        unit: lesson.file,
        pdfPage: sbPdfPage,
        bookPage: lesson.sb_page,
        lessonCode: lesson.code,
      });
    } else {
      window.open(sbUrl, "_blank");
    }
  });

  card.querySelector(".lc-go-tg").addEventListener("click", () => {
    if (typeof navigateToTG === "function") {
      navigateToTG({
        unit: lesson.file,
        pdfPage: tgPdfPage,
        bookPage: lesson.tg_page,
        lessonCode: lesson.code,
      });
    } else {
      window.open(tgUrl, "_blank");
    }
  });
  return card;
}

function renderStep(step, courseId, lessonCode, lesson, courseData, navigateToWB) {
  const done = store.isStepDone(courseId, lessonCode, step.id);
  const isLeadin = step.type === "leadin";
  const isWorkbook = step.type === "workbook";
  const isChatGPT = step.type === "chatgpt";
  let numLabel;
  if (isLeadin) numLabel = "○";
  else if (isWorkbook) numLabel = "📘";
  else if (isChatGPT) numLabel = "🎤";
  else numLabel = step.number != null ? String(step.number) : "•";

  let extra = "";
  if (isWorkbook && step.wb_page) {
    extra = `<button class="lc-step-action lc-go-wb" type="button" data-wb-page="${step.wb_page}">Abrir WB p.${step.wb_page} →</button>`;
  }
  if (isChatGPT) {
    extra = `
      <div class="lc-chatgpt-actions">
        <button class="lc-step-action lc-copy-prompt" type="button">Copiar prompt</button>
        <a class="lc-step-action" href="https://chat.openai.com/" target="_blank">Abrir ChatGPT ↗</a>
      </div>
    `;
  }

  return `
    <li class="lc-step ${isLeadin ? 'leadin' : ''} ${isWorkbook ? 'workbook' : ''} ${isChatGPT ? 'chatgpt optional' : ''} ${done ? 'done' : ''}" data-step-id="${escape(step.id)}">
      <label>
        <input type="checkbox" ${done ? 'checked' : ''}>
        <span class="lc-step-num">${escape(numLabel)}</span>
        <span class="lc-step-body">
          <span class="lc-step-label">${escape(step.label)}</span>
          ${step.subtitle ? `<span class="lc-step-sub">${escape(step.subtitle)}</span>` : ""}
        </span>
      </label>
      ${extra}
    </li>
  `;
}

function buildChatGPTPrompt(lesson, courseTitle) {
  const topics = lesson.topics || {};
  const bits = [];
  if (topics.grammar) bits.push(`grammar: ${topics.grammar}`);
  if (topics.vocabulary) bits.push(`vocabulary: ${topics.vocabulary}`);
  if (topics.function) bits.push(`function: ${topics.function}`);
  if (topics.pronunciation) bits.push(`pronunciation: ${topics.pronunciation}`);
  const topicLine = bits.length ? `\nTopic focus — ${bits.join("; ")}.` : "";
  const titleEsc = lesson.title.replace(/"/g, "'");
  return (
    `Hi! I've just studied lesson ${lesson.code} ("${titleEsc}") from American English File ${courseTitle}.${topicLine}` +
    `\n\nPlease have a 5–10 minute conversation with me in English about this lesson's topic.` +
    ` Ask me natural follow-up questions, gently correct any mistakes I make,` +
    ` and try to recycle the grammar and vocabulary from the lesson during our chat.` +
    ` Start with one short opening question and wait for my answer before continuing.`
  );
}

async function applyStepToggle(row, isChecked, courseData, lesson, card) {
  const stepId = row.dataset.stepId;
  const now = await store.toggleStep(courseData.id, lesson.code, stepId);
  row.classList.toggle("done", now);
  // Update the counts and progress bar in this card
  const stats = store.lessonStepStats(courseData.id, lesson);
  card.querySelector(".lc-steps-done").textContent = stats.done;
  card.querySelector(".lc-progress-bar").style.width = stats.pct + "%";
  // Notify the rest of the app so course/home pcts update
  document.dispatchEvent(new CustomEvent("progress-changed", { detail: { stepChange: true } }));
}

function renderRelatedResources(lesson, courseData) {
  const groups = store.findRelatedResources(courseData.id, lesson);
  if (!groups) return null;
  const totals = Object.entries(groups).filter(([, list]) => list.length);
  if (!totals.length) return null;

  const wrap = document.createElement("div");
  wrap.className = "lc-related";
  const labels = {
    LISTENING: "🎬 Listening (vídeos)",
    PE:        "💬 Practical English",
    EPISODE:   "📺 Episódio",
    RC:        "🔁 Review & Check",
    PRACTICE:  "📝 Practice",
    TEST:      "📋 Tests",
    WORKBOOK:  "📘 Workbook",
    MUSIC:     "🎵 Música complementar",
    CHATGPT:   "🎤 Conversa com ChatGPT (opcional)",
  };
  const totalCount = totals.reduce((s, [, l]) => s + l.length, 0);
  wrap.innerHTML = `
    <div class="lc-related-header">
      <span class="lc-related-title">Recursos desta aula</span>
      <span class="muted" style="font-size:11px;">${totalCount} itens</span>
    </div>
  `;
  for (const [key, list] of totals) {
    const groupEl = document.createElement("div");
    groupEl.className = "lc-related-group";
    groupEl.innerHTML = `<div class="lc-related-group-title">${labels[key] || key}</div>`;
    const rows = document.createElement("div");
    rows.className = "lc-related-rows";
    for (const r of list) {
      if (r.synthetic && r.type === "music") {
        rows.appendChild(renderMusicResource(r, courseData.id, lesson));
      } else if (r.synthetic && r.type === "workbook") {
        rows.appendChild(renderWorkbookResource(r, courseData, lesson));
      } else if (r.synthetic && r.type === "chatgpt") {
        rows.appendChild(renderChatGPTResource(r, courseData, lesson));
      } else {
        rows.appendChild(renderResource(r));
      }
    }
    groupEl.appendChild(rows);
    wrap.appendChild(groupEl);
  }
  return wrap;
}

function renderMusicResource(music, courseId, lesson) {
  const done = !!store.progress[music.id]?.completed;
  const fav = !!store.progress[music.id]?.favorite;
  const div = document.createElement("div");
  div.className = "resource music-row";
  const query = encodeURIComponent(`${music.title} ${music.artist} lyrics`);
  div.innerHTML = `
    <input type="checkbox" class="check" ${done ? "checked" : ""} title="Marcar concluído">
    <span class="icon">🎵</span>
    <div class="title">
      ${escape(music.title)} <span class="muted">— ${escape(music.artist)}</span>
      <small>${escape(music.why)}</small>
    </div>
    <button class="fav ${fav ? "on" : ""}" title="Favorito">★</button>
    <a class="open-btn" target="_blank"
       href="https://www.google.com/search?q=${query}">Buscar letra ↗</a>
  `;
  div.querySelector(".check").onchange = async () => {
    const cur = !!store.progress[music.id]?.completed;
    store.progress[music.id] = await (await fetch("/api/progress", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id: music.id, completed: !cur})
    })).json();
    document.dispatchEvent(new Event("progress-changed"));
  };
  div.querySelector(".fav").onclick = async () => {
    const cur = !!store.progress[music.id]?.favorite;
    store.progress[music.id] = await (await fetch("/api/progress", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id: music.id, favorite: !cur})
    })).json();
    div.querySelector(".fav").classList.toggle("on", !!store.progress[music.id]?.favorite);
  };
  return div;
}

function wireSyntheticToggle(checkbox, rid) {
  checkbox.onchange = async () => {
    const cur = !!store.progress[rid]?.completed;
    store.progress[rid] = await (await fetch("/api/progress", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id: rid, completed: !cur})
    })).json();
    document.dispatchEvent(new Event("progress-changed"));
  };
}

function renderWorkbookResource(wb, courseData, lesson) {
  const done = !!store.progress[wb.id]?.completed;
  const div = document.createElement("div");
  div.className = "resource";
  div.innerHTML = `
    <input type="checkbox" class="check" ${done ? "checked" : ""} title="Marcar concluído">
    <span class="icon">📘</span>
    <div class="title">
      Workbook
      <small>WB p.${wb.wb_page}</small>
    </div>
    <button class="open-btn lc-go-wb" type="button" data-wb-page="${wb.wb_page}">Abrir WB p.${wb.wb_page} →</button>
  `;
  wireSyntheticToggle(div.querySelector(".check"), wb.id);
  return div;
}

function renderChatGPTResource(gpt, courseData, lesson) {
  const done = !!store.progress[gpt.id]?.completed;
  const div = document.createElement("div");
  div.className = "resource";
  div.innerHTML = `
    <input type="checkbox" class="check" ${done ? "checked" : ""} title="Marcar concluído">
    <span class="icon">🎤</span>
    <div class="title">
      Conversar 5–10 min com ChatGPT em inglês (voz)
      <small>Pratica fala e escuta sobre o tópico da aula</small>
    </div>
    <button class="open-btn lc-copy-prompt" type="button">Copiar prompt</button>
    <a class="open-btn" href="https://chat.openai.com/" target="_blank">Abrir ChatGPT ↗</a>
  `;
  wireSyntheticToggle(div.querySelector(".check"), gpt.id);
  return div;
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));
}
