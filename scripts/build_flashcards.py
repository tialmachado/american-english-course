"""
Gera flashcards SRS a partir do material do Starter.

Estratégia para o Starter:
  - WB.pdf de cada lição tem uma seção "WORDS AND PHRASES TO LEARN"
    com palavras/frases curadas + exercícios de fill-in que servem
    como exemplos de uso.
  - TG.pdf body marca "VOCABULARY <topic>" + audio refs "e X.YY" que
    apontam para o SB Audio do mesmo número (track).
  - Backreference do SB Audio é montada via data/index.json.

Saída: data/flashcards/starter.json com lista de cards.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "flashcards"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _audio_path_for_track(course_id: str, track: str) -> str:
    """Look up the SB Audio resource for a given track number.  Tracks in the
    TG appear as '1.4' while the index stores '1.04' (zero-padded).  Try both."""
    if not track:
        return ""
    idx_path = ROOT / "data" / "index.json"
    if not idx_path.exists():
        return ""
    idx = json.loads(idx_path.read_text())
    course = next((c for c in idx["courses"] if c["id"] == course_id), None)
    if not course:
        return ""
    candidates = {track}
    a, b = track.split(".")
    candidates.add(f"{a}.{b.zfill(2)}")
    candidates.add(f"{a}.{b.zfill(3)}")
    for r in course["resources"]:
        if r.get("section") == "SB" and r.get("type") == "audio" and r.get("track") in candidates:
            return r["path"]
    return ""


def _extract_starter_wb_words(wb_path: Path, lesson_page_map: dict[str, int]) -> dict[str, list[str]]:
    """For each Starter lesson, extract the words/phrases listed in
    'WORDS AND PHRASES TO LEARN' on the WB page."""
    doc = fitz.open(wb_path)
    result: dict[str, list[str]] = {}
    # We walk pages and detect WORDS AND PHRASES TO LEARN blocks.
    # Each block is followed by a list of items used to complete numbered
    # conversations.  We capture the items literally.
    current_lesson = None
    page_to_lesson = {}
    for code, page in lesson_page_map.items():
        page_to_lesson[page] = code
        # WB pages span 2 pages per lesson roughly; the section is on the
        # second page typically (e.g. 1A on book pp.4-5, section on p.5).
        page_to_lesson.setdefault(page + 1, code)

    for i in range(len(doc)):
        book_page = i + 1   # WB book pages match PDF pages for Starter
        if book_page not in page_to_lesson:
            continue
        code = page_to_lesson[book_page]
        text = doc[i].get_text("text")
        # Find a WORDS AND PHRASES TO LEARN section
        m = re.search(r"WORDS\s*AND\s*PHRASES\s*TO\s*LEARN", text, re.IGNORECASE)
        if not m:
            continue
        # The next chunk contains a small list of items separated by lines
        chunk = text[m.end():m.end() + 600]
        items: list[str] = []
        for ln in chunk.split("\n"):
            ln = _normalize(ln)
            if not ln:
                continue
            if re.match(r"^\d+\s*[A-Z]\b", ln):  # "1 A …" — start of exercise
                break
            if re.match(r"^(complete|the|with|from|use|listen|write)\b", ln, re.IGNORECASE):
                continue
            if ln.lower().endswith("from the list."):
                continue
            if len(ln) < 2 or len(ln) > 80:
                continue
            if ln.endswith(":") or ln.endswith("?"):
                continue
            if ln.lower() in {"rad time", "go online for more practice"}:
                continue
            # A line can pack multiple phrases (PDF column collapse).
            # Split before each capital letter that starts a new word, if
            # the previous text is at least 3 chars.
            parts = re.split(r"(?<=[a-z!?\.])\s+(?=[A-Z])", ln)
            for p in parts:
                p = _normalize(p).strip(".,;")
                if not p or len(p) > 60:
                    continue
                if p.lower() in {"sorry", "thanks", "thank you"} or len(p) >= 3:
                    items.append(p)
            if len(items) >= 12:
                break
        if items:
            result.setdefault(code, []).extend(items)
    doc.close()
    return result


def _extract_starter_tg_audio_refs(tg_path: Path, lesson_tg_pages: dict[str, int]) -> dict[str, str]:
    """For each lesson, find the FIRST audio reference 'e X.YY' inside the
    VOCABULARY section.  Used as the default audio for that lesson's deck."""
    doc = fitz.open(tg_path)
    result: dict[str, str] = {}
    pages = list(lesson_tg_pages.items())
    pages_sorted = sorted(pages, key=lambda kv: kv[1])
    for i, (code, start) in enumerate(pages_sorted):
        end = pages_sorted[i + 1][1] if i + 1 < len(pages_sorted) else len(doc)
        for p in range(start - 1, min(end, len(doc))):
            txt = doc[p].get_text("text")
            # Find first audio ref in this lesson
            m = re.search(r"e\s+(\d+)\.(\d{1,3})", txt)
            if m:
                result[code] = f"{m.group(1)}.{m.group(2)}"
                break
    doc.close()
    return result


def build_starter() -> list[dict]:
    """Curated Starter deck: uses the hand-translated fixture when present
    (drops parser noise), otherwise falls back to raw WB extraction."""
    try:
        from starter_flashcards_translations import STARTER_CARDS
    except Exception:
        STARTER_CARDS = None

    lessons_json = ROOT / "data" / "lessons" / "starter.json"
    if not lessons_json.exists():
        print("starter.json not found — run extract_lessons.py first")
        return []
    data = json.loads(lessons_json.read_text())

    # Fast path: curated fixture wins.
    if STARTER_CARDS:
        tg_audio = _extract_starter_tg_audio_refs(
            ROOT / "AEF 0 starter/TG.pdf",
            {l["code"]: l["tg_page"] for l in data["lessons"] if l["type"] != "review"})
        lesson_file = {l["code"]: l["file"] for l in data["lessons"]}
        out: list[dict] = []
        for code, front, back in STARTER_CARDS:
            track = tg_audio.get(code, "")
            audio_path = _audio_path_for_track("starter", track) if track else ""
            out.append({
                "lesson_code": code,
                "front": front,
                "back": back,
                "example": "",
                "audio_path": audio_path,
                "tags": ["vocab", code, f"file-{lesson_file.get(code, 0)}"],
            })
        return out
    lesson_page_map = {l["code"]: l["sb_page"] for l in data["lessons"] if l["type"] != "review"}
    lesson_tg_pages = {l["code"]: l["tg_page"] for l in data["lessons"] if l["type"] != "review"}

    wb_words = _extract_starter_wb_words(ROOT / "AEF 0 starter/WB.pdf",
                                          {l["code"]: l["wb_page"] for l in data["lessons"]
                                           if l.get("wb_page") and l["type"] != "review"})
    tg_audio = _extract_starter_tg_audio_refs(ROOT / "AEF 0 starter/TG.pdf",
                                              lesson_tg_pages)

    cards: list[dict] = []
    for lesson in data["lessons"]:
        if lesson["type"] == "review":
            continue
        code = lesson["code"]
        items = wb_words.get(code, [])
        if not items:
            continue
        track = tg_audio.get(code, "")
        audio_path = _audio_path_for_track("starter", track) if track else ""
        seen_in_lesson: set[str] = set()
        for w in items:
            w = w.strip(" -_,.")
            if not w:
                continue
            # Reject obvious noise: pure punctuation, very short, or repeated.
            if not re.search(r"[A-Za-z]", w):
                continue
            if len(w) < 2:
                continue
            key = w.lower()
            if key in seen_in_lesson:
                continue
            seen_in_lesson.add(key)
            cards.append({
                "lesson_code": code,
                "front": w,
                "back": "",
                "example": "",
                "audio_path": audio_path,
                "tags": ["vocab", code, f"file-{lesson['file']}"],
            })
    return cards


def main() -> None:
    cards = build_starter()
    if not cards:
        print("No cards generated.")
        return
    out = OUT_DIR / "starter.json"
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=2))
    print(f"Wrote {out} ({len(cards)} cards)")


if __name__ == "__main__":
    main()
