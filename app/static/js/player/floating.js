/* Global persistent audio player.
   - Single <audio> element rendered once in the page.
   - Inline audio rows just call player.toggle(resource).
   - Position auto-saves to /api/position.
   - State (resource_id + currentTime + speed) survives full page reloads via localStorage. */
import { api, fileUrl, fmtTime } from "../api.js";
import { store } from "../store.js";

const LS_KEY = "aef:player";

class FloatingPlayer {
  constructor() {
    this.el = document.getElementById("floating-player");
    if (!this.el) return; // page without player markup
    this.audio   = this.el.querySelector("audio");
    this.titleEl = this.el.querySelector(".fp-title");
    this.timeEl  = this.el.querySelector(".fp-time");
    this.speedEl = this.el.querySelector(".fp-speed");
    this.closeBtn= this.el.querySelector(".fp-close");
    this.subs = new Set();           // play-button DOM nodes to keep in sync
    this.current = null;             // current Resource object
    this.lastPing = 0;
    this.lastSaved = 0;
    this._wireEvents();
    this._restoreFromStorage();
  }

  _wireEvents() {
    this.audio.addEventListener("play",  () => this._notifySubs());
    this.audio.addEventListener("pause", () => this._notifySubs());
    this.audio.addEventListener("timeupdate", () => {
      if (!this.current) return;
      this.timeEl.textContent = `${fmtTime(this.audio.currentTime)} / ${fmtTime(this.audio.duration || 0)}`;
      const now = Date.now();
      if (now - this.lastSaved > 5000) {
        this.lastSaved = now;
        api.setPosition(this.current.id, this.audio.currentTime, this.audio.duration || 0);
        this._saveStorage();
      }
    });
    this.audio.addEventListener("ended", async () => {
      if (this.current && !store.progress[this.current.id]?.completed) {
        await store.toggleCompleted(this.current.id);
        document.dispatchEvent(new Event("progress-changed"));
      }
      this._notifySubs();
    });
    this.speedEl.addEventListener("change", () => {
      this.audio.playbackRate = parseFloat(this.speedEl.value);
      this._saveStorage();
    });
    this.closeBtn.addEventListener("click", () => this.close());
    window.addEventListener("beforeunload", () => this._saveStorage());
    window.addEventListener("keydown", (e) => {
      if (!this.current) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === "Space") { e.preventDefault(); this.audio.paused ? this.audio.play() : this.audio.pause(); }
      else if (e.code === "ArrowLeft")  { this.audio.currentTime = Math.max(0, this.audio.currentTime - 5); }
      else if (e.code === "ArrowRight") { this.audio.currentTime = this.audio.currentTime + 5; }
    });
  }

  load(resource, autoplay = true) {
    this.current = resource;
    this.audio.src = fileUrl(resource.path);
    this.titleEl.textContent = resource.title;
    this.el.classList.add("show");
    document.body.classList.add("has-player");
    const saved = store.progress[resource.id]?.last_position || 0;
    this.audio.addEventListener("loadedmetadata", () => {
      if (saved && saved < (this.audio.duration - 1)) this.audio.currentTime = saved;
      if (autoplay) this.audio.play().catch(() => {});
    }, {once: true});
    this._saveStorage();
    this._notifySubs();
  }

  toggle(resource) {
    if (this.current?.id === resource.id) {
      this.audio.paused ? this.audio.play() : this.audio.pause();
    } else {
      this.load(resource, true);
    }
  }

  isPlaying(resource_id) {
    return this.current?.id === resource_id && !this.audio.paused;
  }

  isActive(resource_id) {
    return this.current?.id === resource_id;
  }

  close() {
    this.audio.pause();
    this.audio.removeAttribute("src");
    this.current = null;
    this.el.classList.remove("show");
    document.body.classList.remove("has-player");
    localStorage.removeItem(LS_KEY);
    this._notifySubs();
  }

  /* Register a play button (or any DOM node) to receive UI updates. */
  registerButton(btn, resource_id) {
    btn.dataset.playerSub = resource_id;
    this.subs.add(btn);
    this._updateButton(btn);
    return () => this.subs.delete(btn);
  }

  _updateButton(btn) {
    const id = btn.dataset.playerSub;
    if (!id) return;
    if (this.isPlaying(id))      btn.textContent = "⏸";
    else if (this.isActive(id))  btn.textContent = "▶";
    else                          btn.textContent = "▶";
    btn.classList.toggle("active", this.isActive(id));
  }

  _notifySubs() {
    for (const btn of this.subs) {
      if (!document.body.contains(btn)) { this.subs.delete(btn); continue; }
      this._updateButton(btn);
    }
  }

  _saveStorage() {
    if (!this.current) return;
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        resource: this.current,
        currentTime: this.audio.currentTime,
        speed: this.audio.playbackRate,
      }));
    } catch {}
  }

  _restoreFromStorage() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      if (!s.resource) return;
      this.current = s.resource;
      this.audio.src = fileUrl(s.resource.path);
      this.titleEl.textContent = s.resource.title;
      this.audio.addEventListener("loadedmetadata", () => {
        if (s.currentTime) this.audio.currentTime = s.currentTime;
        if (s.speed) { this.audio.playbackRate = s.speed; this.speedEl.value = s.speed; }
      }, {once: true});
      this.el.classList.add("show");
      document.body.classList.add("has-player");
    } catch {}
  }
}

export let player = null;
export function initPlayer() {
  if (!player) player = new FloatingPlayer();
  return player;
}
