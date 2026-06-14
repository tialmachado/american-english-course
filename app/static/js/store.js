/* In-memory cache + grouping helpers. */
import { api } from "./api.js";

export const store = {
  index: null,    // {courses:[...]}
  progress: {},   // resource_id -> {completed, favorite, last_position, duration}
  notes: {},      // resource_id -> string
  stats: null,
  lessonsByCourse: {},  // course_id -> {lessons:[...]}

  async load() {
    if (this.index) return;
    const [idx, p, stats] = await Promise.all([api.index(), api.progress(), api.stats()]);
    this.index = idx;
    for (const row of p.progress) this.progress[row.resource_id] = row;
    this.notes = p.notes || {};
    this.stats = stats;
    // Pre-load lessons for every course in parallel (most will 404 today).
    const results = await Promise.all(idx.courses.map(async (c) => {
      try {
        const res = await fetch(`/api/lessons/${c.id}`);
        if (!res.ok) return null;
        return [c.id, await res.json()];
      } catch { return null; }
    }));
    for (const r of results) if (r) this.lessonsByCourse[r[0]] = r[1];
  },

  stepProgress(courseId) {
    const data = this.lessonsByCourse[courseId];
    if (!data) return null;
    let total = 0, done = 0;
    for (const l of data.lessons) {
      for (const s of l.steps || []) {
        total++;
        const rid = `${courseId}::step::${l.code}::${s.id}`;
        if (this.progress[rid]?.completed) done++;
      }
    }
    return { total, done, pct: total ? Math.round(100 * done / total) : 0 };
  },

  async toggleStep(courseId, lessonCode, stepId) {
    const rid = `${courseId}::step::${lessonCode}::${stepId}`;
    const cur = this.progress[rid]?.completed || false;
    this.progress[rid] = await api.setProgress(rid, { completed: !cur });
    return this.progress[rid].completed;
  },

  isStepDone(courseId, lessonCode, stepId) {
    const rid = `${courseId}::step::${lessonCode}::${stepId}`;
    return !!this.progress[rid]?.completed;
  },

  course(id) {
    return this.index.courses.find(c => c.id === id);
  },

  // Returns {SB:[…], WB:[…], PE:[…], LISTENING:[…], RC:[…], PRACTICE:[…], TEST:[…], TG:[…], EPISODE:[…], EXTRA:[…]}
  resourcesByTab(course) {
    const tabs = {SB:[], WB:[], PE:[], LISTENING:[], RC:[], PRACTICE:[], TEST:[], TG:[], EPISODE:[], EXTRA:[]};
    for (const r of course.resources) {
      (tabs[r.section] || tabs.EXTRA).push(r);
    }
    return tabs;
  },

  resourcesForTabAndUnit(course, tab, unit) {
    const list = course.resources.filter(r => r.section === tab);
    if (unit == null) return list;
    return list.filter(r =>
      r.unit === unit ||
      (r.meta && Array.isArray(r.meta.covers_units) && r.meta.covers_units.includes(unit))
    );
  },

  unitsForTab(course, tab) {
    const set = new Set();
    for (const r of course.resources) {
      if (r.section !== tab) continue;
      if (r.unit) set.add(r.unit);
      if (r.meta && Array.isArray(r.meta.covers_units)) r.meta.covers_units.forEach(u => set.add(u));
    }
    return [...set].sort((a,b) => a - b);
  },

  unitProgress(course, unit) {
    const units = course.resources.filter(r => r.unit === unit);
    if (!units.length) return 0;
    const done = units.filter(r => this.progress[r.id]?.completed).length;
    return Math.round(100 * done / units.length);
  },

  coursePct(course) {
    const step = this.stepProgress(course.id);
    if (step && step.total > 0) return step.pct;
    const total = course.resources.length;
    if (!total) return 0;
    const done = course.resources.filter(r => this.progress[r.id]?.completed).length;
    return Math.round(100 * done / total);
  },

  /** Stats for a lesson: steps + related resources (Listening, RC, Episodes,
      Practice, Tests, PE videos, Music).  Each related resource counts as one
      additional "momento" toward the lesson's completion %. */
  lessonStepStats(courseId, lesson) {
    let total = 0, done = 0;
    for (const s of lesson.steps || []) {
      total++;
      if (this.isStepDone(courseId, lesson.code, s.id)) done++;
    }
    const groups = this.findRelatedResources(courseId, lesson) || {};
    for (const list of Object.values(groups)) {
      for (const r of list) {
        total++;
        if (this.progress[r.id]?.completed) done++;
      }
    }
    return { total, done, pct: total ? Math.round(100 * done / total) : 0 };
  },

  musicResourceId(courseId, lessonCode) {
    return `${courseId}::lesson::${lessonCode}::music`;
  },

  workbookResourceId(courseId, lessonCode) {
    return `${courseId}::lesson::${lessonCode}::wb`;
  },

  chatgptResourceId(courseId, lessonCode) {
    return `${courseId}::lesson::${lessonCode}::chatgpt`;
  },

  /** Group related resources for a lesson.  Music shows up as a synthetic
      resource so it can be checked / favorited like the others. */
  findRelatedResources(courseId, lesson) {
    const courseIndex = this.course(courseId);
    if (!courseIndex) return null;
    const file = lesson.file;
    const code = lesson.code;
    const type = lesson.type;
    const letter = (code.match(/^\d+([A-D])$/) || [])[1] || null;
    const groups = {
      LISTENING: [], PE: [], RC: [], EPISODE: [],
      PRACTICE: [], TEST: [], MUSIC: [],
      WORKBOOK: [], CHATGPT: [],
    };
    for (const r of courseIndex.resources || []) {
      const s = r.section;
      if (s === "SB" || s === "WB" || s === "TG") continue;
      if (s === "LISTENING") {
        if (r.unit === file) groups.LISTENING.push(r);
        continue;
      }
      if (s === "PRACTICE") {
        if (r.unit !== file) continue;
        if (type === "lesson") {
          if (!r.meta?.lesson || r.meta.lesson === letter) groups.PRACTICE.push(r);
        }
        continue;
      }
      if (s === "TEST") {
        if (r.unit === file) groups.TEST.push(r);
        else if (type === "review" && lesson.covers_files?.includes(r.unit)) {
          groups.TEST.push(r);
        }
        continue;
      }
      if (s === "PE") {
        if (type === "practical_english" && r.meta?.episode === lesson.episode) {
          groups.PE.push(r);
        }
        continue;
      }
      if (s === "RC") {
        if (type === "review") {
          const covers = r.meta?.covers_units || [];
          const overlap = (lesson.covers_files || []).some((f) => covers.includes(f));
          if (overlap) groups.RC.push(r);
        }
        continue;
      }
      if (s === "EPISODE") {
        if (type === "practical_english" && r.meta?.episode === lesson.episode) {
          groups.EPISODE.push(r);
        }
        continue;
      }
    }
    // Synthetic music resource
    if (lesson.music) {
      groups.MUSIC.push({
        id: this.musicResourceId(courseId, lesson.code),
        title: lesson.music.title,
        artist: lesson.music.artist,
        why: lesson.music.why,
        type: "music",
        section: "MUSIC",
        synthetic: true,
      });
    }
    // Workbook deep-link (synthetic)
    if (lesson.wb_page) {
      const data = this.lessonsByCourse[courseId];
      groups.WORKBOOK.push({
        id: this.workbookResourceId(courseId, lesson.code),
        title: "Workbook",
        wb_page: lesson.wb_page,
        wb_pdf_path: data?.wb_pdf_path,
        wb_pdf_offset: data?.wb_pdf_offset || 0,
        unit: lesson.file,
        type: "workbook",
        section: "WORKBOOK",
        synthetic: true,
      });
    }
    // ChatGPT optional conversation (synthetic, always present)
    groups.CHATGPT.push({
      id: this.chatgptResourceId(courseId, lesson.code),
      title: "Conversar 5–10 min com ChatGPT em inglês (voz)",
      why: "Atividade opcional — pratica fala e escuta sobre o tópico da aula.",
      type: "chatgpt",
      section: "CHATGPT",
      synthetic: true,
    });
    return groups;
  },

  async toggleCompleted(resource_id) {
    const cur = this.progress[resource_id]?.completed || false;
    this.progress[resource_id] = await api.setProgress(resource_id, {completed: !cur});
  },

  async toggleFavorite(resource_id) {
    const cur = this.progress[resource_id]?.favorite || false;
    this.progress[resource_id] = await api.setProgress(resource_id, {favorite: !cur});
  },
};
