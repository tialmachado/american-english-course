"""
Walk the AEF course folders and emit data/index.json.
Re-runnable; reads file names only, never modifies the course folders.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSES = [
    ("starter",         "AEF 0 starter",          "Starter",          "A1"),
    ("elementary",      "AEF 1 elementary",       "Elementary",       "A1/A2"),
    ("pre-intermediate","AEF 2 pre-intermediate", "Pre-Intermediate", "A2/B1"),
    ("intermediate",    "AEF 3 intermediate",     "Intermediate",     "B1"),
    ("upper-intermediate","AEF 4 upper-intermediate","Upper-Intermediate","B2"),
    ("advanced",        "AEF 5 advanced",         "Advanced",         "C1"),
]

# Patterns ------------------------------------------------------------
RE_SB_AUDIO   = re.compile(r"_(?:SB|sb)_(\d{1,2})\.(\d{1,3})", re.IGNORECASE)
RE_WB_AUDIO   = re.compile(r"_(?:WB|wb)_(\d{1,2})\.(\d{1,3})", re.IGNORECASE)
RE_PE_VIDEO   = re.compile(r"PE_Ep(\d+)_?(.*)", re.IGNORECASE)
RE_RC_VIDEO   = re.compile(r"Review_?(?:and|&)_?Check_?(\d+)[&_](\d+)", re.IGNORECASE)
RE_PRACTICE   = re.compile(r"^(\d{1,2})([A-D])\s+(.+?)\.(docx?|pdf)$", re.IGNORECASE)
RE_FILETEST   = re.compile(r"filetest_?(\d{1,2})([ab])(?:_(answer_key|answer_sheet|script))?", re.IGNORECASE)
RE_PROGRESS   = re.compile(r"progresstest_?(\d{1,2})_(\d{1,2})([ab])(?:_(AK|answer_key|answer_sheet|script))?", re.IGNORECASE)
RE_QUICKTEST  = re.compile(r"quicktest_?(\d{1,2})(?:_(answer_key))?", re.IGNORECASE)


@dataclass
class Resource:
    id: str
    title: str
    type: str            # pdf | audio | video | doc | test
    path: str            # POSIX path relative to project root
    section: str         # SB | WB | PE | LISTENING | RC | PRACTICE | TEST | TG | EPISODE | EXTRA
    unit: int | None = None
    track: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Course:
    id: str
    title: str
    cefr: str
    folder: str
    resources: list[Resource] = field(default_factory=list)


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def make_id(*parts: str) -> str:
    return "::".join(str(p) for p in parts)


def add_unit_audio(course: Course, file: Path, kind: str) -> None:
    """kind: 'SB' or 'WB'. Parse unit/track from filename."""
    pat = RE_SB_AUDIO if kind == "SB" else RE_WB_AUDIO
    m = pat.search(file.stem)
    if not m:
        return
    unit = int(m.group(1))
    track = f"{m.group(1)}.{m.group(2)}"
    course.resources.append(Resource(
        id=make_id(course.id, kind.lower(), "audio", track),
        title=f"{kind} Audio {track}",
        type="audio",
        path=rel(file),
        section=kind,
        unit=unit,
        track=track,
    ))


def scan_audio_dir(course: Course, base: Path, kind: str) -> None:
    """Walk base directory recursively for mp3 files."""
    if not base.exists():
        return
    for mp3 in sorted(base.rglob("*.mp3")):
        # Try filename-based first
        m_sb = RE_SB_AUDIO.search(mp3.stem)
        m_wb = RE_WB_AUDIO.search(mp3.stem)
        if m_sb and kind == "SB":
            add_unit_audio(course, mp3, "SB")
            continue
        if m_wb and kind == "WB":
            add_unit_audio(course, mp3, "WB")
            continue
        # Fallback: use parent dir "Unit N" if present
        unit = None
        for parent in mp3.parents:
            m = re.match(r"Unit\s*(\d+)", parent.name, re.IGNORECASE)
            if m:
                unit = int(m.group(1))
                break
        course.resources.append(Resource(
            id=make_id(course.id, kind.lower(), "audio", mp3.stem),
            title=f"{kind} Audio — {mp3.stem}",
            type="audio",
            path=rel(mp3),
            section=kind,
            unit=unit,
        ))


def scan_videos(course: Course, video_dir: Path) -> None:
    if not video_dir.exists():
        return
    for mp4 in sorted(video_dir.rglob("*.mp4")):
        rel_parents = [p.name for p in mp4.relative_to(video_dir).parents][:-1]
        parent_chain = " / ".join(reversed(rel_parents)) if rel_parents else ""
        section = "EXTRA"
        unit = None
        meta: dict = {}
        # Practical English
        m = RE_PE_VIDEO.search(mp4.stem)
        if m or "Practical_English" in parent_chain or "Practical English" in parent_chain:
            section = "PE"
            if m:
                ep = int(m.group(1))
                meta["episode"] = ep
                # PE Ep N typically follows units 2N-1 / 2N
                unit = ep * 2  # associate with the second unit of the pair
                meta["covers_units"] = [ep * 2 - 1, ep * 2]
        # Review and Check
        if section == "EXTRA":
            mrc = RE_RC_VIDEO.search(mp4.stem)
            if mrc or "Review" in parent_chain:
                section = "RC"
                if mrc:
                    a, b = int(mrc.group(1)), int(mrc.group(2))
                    meta["covers_units"] = [a, b]
                    unit = b
        # Listening
        if section == "EXTRA" and ("Listening" in parent_chain or "Video_Listening" in mp4.stem or "Video Listening" in parent_chain):
            section = "LISTENING"
        # Episode folder (Starter / L4)
        if section == "EXTRA":
            for p in mp4.parents:
                m_ep = re.match(r"Episode\s*(\d+)", p.name, re.IGNORECASE)
                if m_ep:
                    section = "EPISODE"
                    meta["episode"] = int(m_ep.group(1))
                    break

        title = mp4.stem.replace("AEF3e_", "").replace("_", " ").strip()
        course.resources.append(Resource(
            id=make_id(course.id, "video", str(mp4.relative_to(video_dir).as_posix())),
            title=title,
            type="video",
            path=rel(mp4),
            section=section,
            unit=unit,
            meta=meta,
        ))


def scan_practice(course: Course, practice_dir: Path) -> None:
    if not practice_dir.exists():
        return
    for f in sorted(practice_dir.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".docx", ".doc", ".pdf"}:
            continue
        m = RE_PRACTICE.match(f.name)
        unit = None
        lesson = None
        if m:
            unit = int(m.group(1))
            lesson = m.group(2).upper()
        course.resources.append(Resource(
            id=make_id(course.id, "practice", f.stem),
            title=f.stem,
            type="doc",
            path=rel(f),
            section="PRACTICE",
            unit=unit,
            meta={"lesson": lesson} if lesson else {},
        ))


def scan_tests(course: Course, course_dir: Path) -> None:
    """Tests live in various places depending on the level."""
    # Starter: EndofСourseTest/* (Cyrillic 'С') — files at root + Unit N folders contain SB audio
    starter_dir = course_dir / "EndofСourseTest"
    if starter_dir.exists():
        for f in sorted(starter_dir.iterdir()):
            if f.is_file() and "endtest" in f.name.lower():
                course.resources.append(Resource(
                    id=make_id(course.id, "test", f.stem),
                    title=f.stem.replace("_", " "),
                    type="test" if f.suffix.lower() in {".pdf", ".doc", ".docx"} else "audio",
                    path=rel(f),
                    section="TEST",
                    meta={"category": "End-of-course"},
                ))
        # The 'Unit N' folders inside EndofСourseTest contain SB audio for Starter
        for d in sorted(starter_dir.iterdir()):
            if not d.is_dir():
                continue
            m = re.match(r"Unit\s*(\d+)", d.name, re.IGNORECASE)
            if not m:
                continue
            unit = int(m.group(1))
            for mp3 in sorted(d.glob("*.mp3")):
                m_sb = RE_SB_AUDIO.search(mp3.stem)
                track = f"{m_sb.group(1)}.{m_sb.group(2)}" if m_sb else mp3.stem
                course.resources.append(Resource(
                    id=make_id(course.id, "sb", "audio", track),
                    title=f"SB Audio {track}",
                    type="audio",
                    path=rel(mp3),
                    section="SB",
                    unit=unit,
                    track=track,
                ))

    tests_dir = course_dir / "Tests"
    if not tests_dir.exists():
        return
    category_map = {
        "Entry_Test": "Entry",
        "File_Tests": "File",
        "Progress_Tests": "Progress",
        "Quick_Tests": "Quick",
        "End-of-course_Test": "End-of-course",
    }
    for sub in sorted(tests_dir.iterdir()):
        if sub.is_file():
            # e.g. AEF3e_Level_1_Howto_tests.pdf
            course.resources.append(Resource(
                id=make_id(course.id, "test", sub.stem),
                title=sub.stem.replace("_", " "),
                type="test",
                path=rel(sub),
                section="TEST",
                meta={"category": "How to"},
            ))
            continue
        if not sub.is_dir():
            continue
        cat = category_map.get(sub.name, sub.name.replace("_", " "))
        for f in sorted(sub.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix.lower() not in {".pdf", ".doc", ".docx", ".mp3"}:
                continue
            unit = None
            m = RE_FILETEST.search(f.stem) or RE_PROGRESS.search(f.stem) or RE_QUICKTEST.search(f.stem)
            if m:
                try:
                    unit = int(m.group(1))
                except (ValueError, IndexError):
                    pass
            kind = "audio" if f.suffix.lower() == ".mp3" else "test"
            course.resources.append(Resource(
                id=make_id(course.id, "test", cat, f.stem),
                title=f.stem.replace("_", " "),
                type=kind,
                path=rel(f),
                section="TEST",
                unit=unit,
                meta={"category": cat},
            ))


def scan_root_pdfs(course: Course, course_dir: Path) -> None:
    mapping = {
        "SB.pdf": ("Student Book", "SB"),
        "WB.pdf": ("Workbook", "WB"),
        "WB key.pdf": ("Workbook Answer Key", "WB"),
        "TG.pdf": ("Teacher's Guide", "TG"),
        "TB.pdf": ("Teacher's Guide", "TG"),
    }
    for name, (title, section) in mapping.items():
        f = course_dir / name
        if f.exists():
            course.resources.append(Resource(
                id=make_id(course.id, "pdf", section, name),
                title=title,
                type="pdf",
                path=rel(f),
                section=section,
            ))
    # Video scripts: PDF files inside Video/ root
    video_dir = course_dir / "Video"
    if video_dir.exists():
        for f in sorted(video_dir.iterdir()):
            if f.is_file() and f.suffix.lower() == ".pdf":
                course.resources.append(Resource(
                    id=make_id(course.id, "pdf", "script", f.name),
                    title=f.stem.replace("_", " "),
                    type="pdf",
                    path=rel(f),
                    section="EXTRA",
                    meta={"category": "Script"},
                ))


def build() -> dict:
    out_courses = []
    for cid, folder, title, cefr in COURSES:
        cdir = ROOT / folder
        if not cdir.exists():
            print(f"  skip {folder}: not found")
            continue
        course = Course(id=cid, title=title, cefr=cefr, folder=folder)
        scan_root_pdfs(course, cdir)

        # SB Audio
        sb_audio = cdir / "SB Audio"
        if sb_audio.exists():
            scan_audio_dir(course, sb_audio, "SB")

        # WB Audio
        wb_audio = cdir / "WB Audio"
        if wb_audio.exists():
            scan_audio_dir(course, wb_audio, "WB")

        # Video
        scan_videos(course, cdir / "Video")

        # Practice docs (live inside Video/Practice for L1-3, Video/Practice for L4)
        for practice_path in [cdir / "Video" / "Practice"]:
            scan_practice(course, practice_path)

        # Tests
        scan_tests(course, cdir)

        # Determine number of units
        units = {r.unit for r in course.resources if r.unit}
        max_unit = max(units) if units else 0

        # Build the JSON-friendly structure
        out_courses.append({
            "id": course.id,
            "title": course.title,
            "cefr": course.cefr,
            "folder": course.folder,
            "max_unit": max_unit,
            "resources": [asdict(r) for r in course.resources],
        })
        print(f"  {folder}: {len(course.resources)} resources, {max_unit} units")
    return {"version": 1, "courses": out_courses}


def main() -> None:
    print(f"Scanning {ROOT}...")
    data = build()
    out = ROOT / "data" / "index.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    total = sum(len(c["resources"]) for c in data["courses"])
    print(f"Wrote {out} ({total} resources across {len(data['courses'])} courses)")


if __name__ == "__main__":
    main()
