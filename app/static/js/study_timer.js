/* Study timer: check-in / pause button + running clock in the topbar.
   State lives on the backend; this module polls /api/study/active on load. */
import { fmtTime } from "./api.js";

let intervalId = null;
let elapsedAtStart = 0;
let tickStart = 0;
let running = false;

async function api(path, method = "POST") {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json" } });
  return res.json();
}

function renderDisplay(seconds) {
  const el = document.getElementById("study-time");
  if (el) el.textContent = fmtTime(seconds);
}

function setRunningUI(isRunning) {
  running = isRunning;
  const btn = document.getElementById("study-toggle");
  const wrap = document.getElementById("study-timer");
  if (!btn || !wrap) return;
  btn.textContent = isRunning ? "⏸ Pausar" : "▶ Check-in";
  wrap.classList.toggle("running", isRunning);
}

function tick() {
  const seconds = elapsedAtStart + Math.floor((Date.now() - tickStart) / 1000);
  renderDisplay(seconds);
}

function startTicking(initialElapsed) {
  elapsedAtStart = initialElapsed || 0;
  tickStart = Date.now();
  renderDisplay(elapsedAtStart);
  if (intervalId) clearInterval(intervalId);
  intervalId = setInterval(tick, 1000);
}

function stopTicking() {
  if (intervalId) clearInterval(intervalId);
  intervalId = null;
}

async function onToggle() {
  const btn = document.getElementById("study-toggle");
  if (btn) btn.disabled = true;
  try {
    if (running) {
      const res = await api("/api/study/stop");
      stopTicking();
      renderDisplay(0);
      setRunningUI(false);
      document.dispatchEvent(new CustomEvent("study-stats-changed", { detail: res }));
    } else {
      const res = await api("/api/study/start");
      setRunningUI(true);
      startTicking(0);
      document.dispatchEvent(new CustomEvent("study-stats-changed", { detail: res }));
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

export async function initStudyTimer() {
  const btn = document.getElementById("study-toggle");
  if (!btn) return;
  btn.addEventListener("click", onToggle);
  // Resume if there's an active session
  try {
    const res = await (await fetch("/api/study/active")).json();
    if (res.running) {
      setRunningUI(true);
      startTicking(res.elapsed || 0);
    } else {
      setRunningUI(false);
      renderDisplay(0);
    }
  } catch {
    renderDisplay(0);
  }
}
