"""FastAPI server: indexes JSON, serves static UI, exposes progress API."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func

from app.db import Note, Progress, Session_, StudySession, get_session, init_db
from app.practice_viewer import asset_path as practice_asset_path, extract_to_html as practice_extract

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "data" / "index.json"

app = FastAPI(title="AEF Self-Study")
init_db()

# ---- Static UI ------------------------------------------------------
STATIC_DIR = ROOT / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/course")
def course_page():
    return FileResponse(STATIC_DIR / "course.html")


@app.get("/dashboard")
def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/favorites")
def favorites_page():
    return FileResponse(STATIC_DIR / "favorites.html")


# ---- Course files (PDFs, audio, video, docs) -----------------------
COURSE_DIRS = {
    "AEF 0 starter",
    "AEF 1 elementary",
    "AEF 2 pre-intermediate",
    "AEF 3 intermediate",
    "AEF 4 upper-intermediate",
    "AEF 5 advanced",
}


@app.get("/files/{full_path:path}")
def files(full_path: str):
    """Serve a file from the course folders. Strict allowlist by top-level dir."""
    p = (ROOT / full_path).resolve()
    if not str(p).startswith(str(ROOT)):
        raise HTTPException(403)
    if not p.exists() or not p.is_file():
        raise HTTPException(404)
    top = full_path.split("/", 1)[0]
    if top not in COURSE_DIRS:
        raise HTTPException(403)
    return FileResponse(p)


# ---- Index ----------------------------------------------------------
@app.get("/api/index")
def api_index():
    if not INDEX_PATH.exists():
        raise HTTPException(503, "Run scripts/build_index.py first")
    return JSONResponse(json.loads(INDEX_PATH.read_text()))


LESSONS_DIR = ROOT / "data" / "lessons"


@app.get("/api/lessons/{course_id}")
def api_lessons(course_id: str):
    f = LESSONS_DIR / f"{course_id}.json"
    if not f.exists():
        raise HTTPException(404, f"Sem plano de aula para {course_id}")
    return JSONResponse(json.loads(f.read_text()))


# ---- Progress -------------------------------------------------------
class ProgressIn(BaseModel):
    resource_id: str
    completed: bool | None = None
    favorite: bool | None = None


class PositionIn(BaseModel):
    resource_id: str
    position: float
    duration: float | None = None


class NoteIn(BaseModel):
    resource_id: str
    body: str


def _serialize_progress(p: Progress) -> dict:
    return {
        "resource_id": p.resource_id,
        "completed": bool(p.completed),
        "favorite": bool(p.favorite),
        "last_position": p.last_position or 0.0,
        "duration": p.duration or 0.0,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@app.get("/api/progress")
def list_progress():
    s = get_session()
    try:
        rows = s.query(Progress).all()
        notes = {n.resource_id: n.body for n in s.query(Note).all()}
        return {
            "progress": [_serialize_progress(p) for p in rows],
            "notes": notes,
        }
    finally:
        s.close()


@app.post("/api/progress")
def update_progress(p: ProgressIn):
    s = get_session()
    try:
        row = s.query(Progress).filter_by(resource_id=p.resource_id).one_or_none()
        if not row:
            row = Progress(resource_id=p.resource_id)
            s.add(row)
        if p.completed is not None:
            row.completed = 1 if p.completed else 0
        if p.favorite is not None:
            row.favorite = 1 if p.favorite else 0
        s.commit()
        return _serialize_progress(row)
    finally:
        s.close()


@app.post("/api/position")
def update_position(p: PositionIn):
    s = get_session()
    try:
        row = s.query(Progress).filter_by(resource_id=p.resource_id).one_or_none()
        if not row:
            row = Progress(resource_id=p.resource_id)
            s.add(row)
        row.last_position = max(p.position, 0)
        if p.duration:
            row.duration = p.duration
        s.commit()
        return _serialize_progress(row)
    finally:
        s.close()


@app.post("/api/note")
def save_note(n: NoteIn):
    s = get_session()
    try:
        row = s.query(Note).filter_by(resource_id=n.resource_id).one_or_none()
        if not row:
            row = Note(resource_id=n.resource_id)
            s.add(row)
        row.body = n.body
        s.commit()
        return {"resource_id": n.resource_id, "ok": True}
    finally:
        s.close()


# ---- Stats / dashboard ---------------------------------------------
def _streak(days: list[str]) -> int:
    if not days:
        return 0
    today = datetime.now().date()
    days_set = set(days)
    streak = 0
    d = today
    while d.isoformat() in days_set:
        streak += 1
        d -= timedelta(days=1)
    return streak


def _resources_related_to_lesson(course: dict, lesson: dict) -> list[dict]:
    """Mirror of store.findRelatedResources() on the server.  Used so the
    course % includes Listening/RC/Episodes/Practice/Tests/PE/Music."""
    file = lesson.get("file")
    code = lesson["code"]
    ltype = lesson.get("type")
    letter_match = (code.split("R", 1)[0])
    import re as _re
    m = _re.match(r"^(\d+)([A-D])$", code)
    letter = m.group(2) if m else None
    out: list[dict] = []
    for r in course.get("resources", []):
        s = r.get("section")
        if s in ("SB", "WB", "TG"):
            continue
        if s == "LISTENING" and r.get("unit") == file:
            out.append(r); continue
        if s == "PRACTICE":
            if r.get("unit") != file: continue
            if ltype == "lesson":
                rl = (r.get("meta") or {}).get("lesson")
                if rl is None or rl == letter:
                    out.append(r)
            continue
        if s == "TEST":
            if r.get("unit") == file:
                out.append(r)
            elif ltype == "review" and r.get("unit") in (lesson.get("covers_files") or []):
                out.append(r)
            continue
        if s == "PE" and ltype == "practical_english":
            if (r.get("meta") or {}).get("episode") == lesson.get("episode"):
                out.append(r)
            continue
        if s == "RC" and ltype == "review":
            covers = (r.get("meta") or {}).get("covers_units") or []
            if any(f in covers for f in (lesson.get("covers_files") or [])):
                out.append(r)
            continue
        if s == "EPISODE" and ltype == "practical_english":
            if (r.get("meta") or {}).get("episode") == lesson.get("episode"):
                out.append(r)
            continue
    return out


def _step_stats_for_course(course_id: str, progress: dict, index: dict | None = None) -> dict:
    """Counts steps + related resources (Listening/RC/Episodes/Practice/Tests/
    PE/Music) for one course."""
    f = LESSONS_DIR / f"{course_id}.json"
    if not f.exists():
        return {"total": 0, "done": 0}
    data = json.loads(f.read_text())
    course_idx = None
    if index is not None:
        course_idx = next((c for c in index["courses"] if c["id"] == course_id), None)
    total = done = 0
    for lesson in data["lessons"]:
        for step in lesson.get("steps", []):
            total += 1
            rid = f"{course_id}::step::{lesson['code']}::{step['id']}"
            row = progress.get(rid)
            if row and row.completed:
                done += 1
        # Related resources count too
        if course_idx is not None:
            for r in _resources_related_to_lesson(course_idx, lesson):
                total += 1
                row = progress.get(r["id"])
                if row and row.completed:
                    done += 1
        # Music synthetic resource
        if lesson.get("music"):
            total += 1
            mid = f"{course_id}::lesson::{lesson['code']}::music"
            row = progress.get(mid)
            if row and row.completed:
                done += 1
        # Workbook synthetic resource (one per lesson when wb_page is known)
        if lesson.get("wb_page"):
            total += 1
            wid = f"{course_id}::lesson::{lesson['code']}::wb"
            row = progress.get(wid)
            if row and row.completed:
                done += 1
        # ChatGPT optional conversation (always present)
        total += 1
        cid = f"{course_id}::lesson::{lesson['code']}::chatgpt"
        row = progress.get(cid)
        if row and row.completed:
            done += 1
    return {"total": total, "done": done}


@app.get("/api/stats")
def stats():
    if not INDEX_PATH.exists():
        return {"courses": [], "totals": {}}
    index = json.loads(INDEX_PATH.read_text())
    s = get_session()
    try:
        progress = {p.resource_id: p for p in s.query(Progress).all()}
        # Streak comes from days the user actually checked in to study.
        study_days = {row.day for row in s.query(StudySession.day).filter(StudySession.day.isnot(None)).all()}

        per_course = []
        for c in index["courses"]:
            res_total = len(c["resources"])
            res_done = sum(1 for r in c["resources"] if progress.get(r["id"]) and progress[r["id"]].completed)
            steps = _step_stats_for_course(c["id"], progress, index)
            if steps["total"]:
                done, total = steps["done"], steps["total"]
                pct = round(100 * done / total, 1)
            else:
                done, total = res_done, res_total
                pct = round(100 * done / total, 1) if total else 0.0
            per_course.append({
                "id": c["id"],
                "title": c["title"],
                "cefr": c["cefr"],
                "total": total,
                "completed": done,
                "pct": pct,
                "has_steps": bool(steps["total"]),
                "steps_total": steps["total"],
                "steps_done": steps["done"],
                "resources_total": res_total,
                "resources_done": res_done,
            })

        return {
            "courses": per_course,
            "streak": _streak(list(study_days)),
            "total_completed": sum(1 for p in progress.values() if p.completed),
            "total_favorites": sum(1 for p in progress.values() if p.favorite),
        }
    finally:
        s.close()


@app.post("/api/study/start")
def study_start():
    """Open a new study session.  If one is already open, return it as-is."""
    s = get_session()
    try:
        open_sess = s.query(StudySession).filter(StudySession.ended_at.is_(None)).first()
        if open_sess:
            return {"id": open_sess.id, "started_at": open_sess.started_at.isoformat(),
                    "running": True, "resumed": True}
        now = datetime.utcnow()
        row = StudySession(started_at=now, day=datetime.now().strftime("%Y-%m-%d"))
        s.add(row)
        s.commit()
        return {"id": row.id, "started_at": row.started_at.isoformat(),
                "running": True, "resumed": False}
    finally:
        s.close()


@app.post("/api/study/stop")
def study_stop():
    """Close the current open study session and record its duration."""
    s = get_session()
    try:
        row = s.query(StudySession).filter(StudySession.ended_at.is_(None)) \
                                   .order_by(StudySession.id.desc()).first()
        if not row:
            return {"running": False, "message": "no active session"}
        now = datetime.utcnow()
        row.ended_at = now
        delta = int((now - row.started_at).total_seconds())
        row.seconds = max(0, delta)
        s.commit()
        return {"id": row.id, "running": False,
                "started_at": row.started_at.isoformat(),
                "ended_at": row.ended_at.isoformat(),
                "seconds": row.seconds}
    finally:
        s.close()


@app.get("/api/study/active")
def study_active():
    """Return the currently running session if there is one."""
    s = get_session()
    try:
        row = s.query(StudySession).filter(StudySession.ended_at.is_(None)) \
                                   .order_by(StudySession.id.desc()).first()
        if not row:
            return {"running": False}
        return {"running": True, "id": row.id,
                "started_at": row.started_at.isoformat(),
                "elapsed": int((datetime.utcnow() - row.started_at).total_seconds())}
    finally:
        s.close()


def _local_day(dt: datetime) -> str:
    """Convert a UTC datetime to the local day string (YYYY-MM-DD)."""
    # SQLite stores naive UTC; we just use the stored 'day' column for the date.
    return dt.strftime("%Y-%m-%d")


@app.get("/api/study/stats")
def study_stats():
    s = get_session()
    try:
        rows = s.query(StudySession).filter(StudySession.ended_at.isnot(None)).all()
        total = sum(r.seconds or 0 for r in rows)
        by_day: dict[str, int] = {}
        for r in rows:
            day = r.day or (r.started_at.strftime("%Y-%m-%d") if r.started_at else None)
            if day:
                by_day[day] = by_day.get(day, 0) + (r.seconds or 0)

        today = datetime.now().strftime("%Y-%m-%d")
        # This week (Mon..Sun)
        today_dt = datetime.now()
        monday = today_dt - timedelta(days=today_dt.weekday())
        week_days = {(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)}
        # This month
        month_prefix = today_dt.strftime("%Y-%m-")

        today_seconds = by_day.get(today, 0)
        week_seconds = sum(v for d, v in by_day.items() if d in week_days)
        month_seconds = sum(v for d, v in by_day.items() if d.startswith(month_prefix))

        # Last 30 days bucketed by day
        last_30 = []
        for i in range(29, -1, -1):
            d = (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
            last_30.append({"day": d, "seconds": by_day.get(d, 0)})

        # Last 12 weeks bucketed by ISO week start
        last_12_weeks = []
        for i in range(11, -1, -1):
            wk_start = monday - timedelta(weeks=i)
            week_days_set = {(wk_start + timedelta(days=j)).strftime("%Y-%m-%d") for j in range(7)}
            wk_seconds = sum(v for d, v in by_day.items() if d in week_days_set)
            last_12_weeks.append({"week_start": wk_start.strftime("%Y-%m-%d"), "seconds": wk_seconds})

        # Last 12 months bucketed by year-month
        last_12_months = []
        cur_y, cur_m = today_dt.year, today_dt.month
        for i in range(11, -1, -1):
            y, m = cur_y, cur_m - i
            while m <= 0:
                m += 12
                y -= 1
            prefix = f"{y:04d}-{m:02d}-"
            mo_seconds = sum(v for d, v in by_day.items() if d.startswith(prefix))
            last_12_months.append({"month": f"{y:04d}-{m:02d}", "seconds": mo_seconds})

        return {
            "total_seconds": total,
            "today_seconds": today_seconds,
            "week_seconds": week_seconds,
            "month_seconds": month_seconds,
            "session_count": len(rows),
            "last_30_days": last_30,
            "last_12_weeks": last_12_weeks,
            "last_12_months": last_12_months,
        }
    finally:
        s.close()


@app.get("/api/practice")
def api_practice(path: str):
    """Convert a Practice .docx to inline HTML + extract embedded audios."""
    p = (ROOT / path).resolve()
    if not str(p).startswith(str(ROOT)) or not p.exists() or not p.is_file():
        raise HTTPException(404)
    if p.suffix.lower() != ".docx":
        raise HTTPException(400, "only .docx supported")
    try:
        return practice_extract(p)
    except Exception as e:
        raise HTTPException(500, f"failed to extract: {e}")


@app.get("/practice-asset/{cache_key}/{filename}")
def practice_asset(cache_key: str, filename: str):
    p = practice_asset_path(cache_key, filename)
    if not p:
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/favorites")
def list_favorites():
    """List every favorited resource, enriched with course + path data."""
    if not INDEX_PATH.exists():
        return {"items": []}
    index = json.loads(INDEX_PATH.read_text())
    # Build a lookup table resource_id -> (course, resource)
    lookup: dict[str, tuple[dict, dict]] = {}
    for c in index["courses"]:
        for r in c["resources"]:
            lookup[r["id"]] = (c, r)

    s = get_session()
    try:
        favs = s.query(Progress).filter(Progress.favorite == 1).order_by(Progress.updated_at.desc()).all()
        items = []
        for p in favs:
            ctx = lookup.get(p.resource_id)
            if not ctx:
                # Could be a step or a stale id; skip for the resources view.
                continue
            course, res = ctx
            items.append({
                "resource_id": p.resource_id,
                "course_id": course["id"],
                "course_title": course["title"],
                "title": res["title"],
                "type": res["type"],
                "section": res["section"],
                "unit": res.get("unit"),
                "track": res.get("track"),
                "path": res["path"],
                "completed": bool(p.completed),
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })
        return {"items": items, "total": len(items)}
    finally:
        s.close()


@app.get("/api/export")
def export_all():
    """Full JSON export for backup."""
    s = get_session()
    try:
        prog = [_serialize_progress(p) for p in s.query(Progress).all()]
        notes = [{"resource_id": n.resource_id, "body": n.body} for n in s.query(Note).all()]
        sessions = [{"day": x.day, "seconds_listening": x.seconds_listening, "seconds_other": x.seconds_other}
                    for x in s.query(Session_).all()]
        return {"exported_at": datetime.utcnow().isoformat(),
                "progress": prog, "notes": notes, "sessions": sessions}
    finally:
        s.close()
