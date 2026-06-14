/* Thin wrapper around fetch() for the local API. */
export const api = {
  async index()    { return (await fetch("/api/index")).json(); },
  async stats()    { return (await fetch("/api/stats")).json(); },
  async progress() { return (await fetch("/api/progress")).json(); },
  async setProgress(resource_id, fields) {
    return (await fetch("/api/progress", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id, ...fields})
    })).json();
  },
  async setPosition(resource_id, position, duration) {
    return (await fetch("/api/position", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id, position, duration})
    })).json();
  },
  async setNote(resource_id, body) {
    return (await fetch("/api/note", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resource_id, body})
    })).json();
  },
  async export() { return (await fetch("/api/export")).json(); },
};

export function fileUrl(path) {
  // path is "AEF X .../something.pdf" — encode but preserve slashes
  return "/files/" + path.split("/").map(encodeURIComponent).join("/");
}

export function fmtTime(s) {
  if (!s || isNaN(s)) return "0:00";
  s = Math.floor(s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h) return `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  return `${m}:${String(sec).padStart(2,"0")}`;
}

export function fmtMinutes(seconds) {
  if (!seconds) return "0 min";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), rem = m % 60;
  return `${h}h ${rem}m`;
}
