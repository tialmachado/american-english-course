"""
Constrói o syllabus dos níveis Elementary → Advanced lendo o TOC do TG.
Saída: lista de lessons compatível com STARTER em extract_lessons.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent


def _toc_text(tg_path: Path) -> str:
    """Concatenate the relevant TOC pages of a TG in reading order."""
    doc = fitz.open(tg_path)
    pages = []
    # Most TGs use pages 4-7. Upper-Int/Advanced have an overview on p.4 then
    # TOC on p.5-6. We grab 4..8 and let the parser ignore non-TOC content.
    for pi in range(3, min(9, len(doc))):
        pages.append(doc[pi].get_text("text"))
    doc.close()
    return "\n".join(pages)


def parse_syllabus(tg_path: Path, course_id: str) -> list[dict]:
    """Walk the TOC linearly and emit lesson rows."""
    text = _toc_text(tg_path)
    raw_lines = [ln.rstrip() for ln in text.split("\n")]
    # Clean: keep only non-empty lines; remember their indices
    lines = [ln.strip() for ln in raw_lines if ln.strip()]

    rows: list[dict] = []
    current_file = 0
    pe_count = 0
    rc_count = 0

    i = 0
    while i < len(lines):
        ln = lines[i]
        # File marker: a single small integer 1..12 immediately followed by a
        # (page number). We detect this contextually.
        if re.fullmatch(r"\d{1,2}", ln):
            n = int(ln)
            # If it looks like a File marker (small) and the next non-trivial
            # token will be a 2-3 digit page number, accept it.
            if 1 <= n <= 12 and i + 1 < len(lines):
                nxt = lines[i + 1]
                if re.fullmatch(r"\d{1,3}", nxt) and int(nxt) > n:
                    current_file = n
                    i += 1
                    continue
        # Page number line followed by a lesson marker on the next line.
        m_pg = re.fullmatch(r"(\d{1,3})", ln)
        if m_pg and i + 1 < len(lines):
            sb_page = int(m_pg.group(1))
            nxt = lines[i + 1]
            # Lesson: "<L> Title" or "<L>\tTitle"  (L is A-D)
            mlet = re.match(r"^([A-D])\s+(.+)$", nxt.replace("\t", " ").strip())
            if mlet and current_file:
                letter = mlet.group(1)
                title = _clean_title(mlet.group(2))
                # If the title was wrapped, peek at next lines that look like
                # continuation (not topic, not next marker)
                j = i + 2
                while j < len(lines) and _is_title_continuation(lines[j], title):
                    title += " " + lines[j].strip()
                    j += 1
                rows.append({
                    "file": current_file,
                    "code": f"{current_file}{letter}",
                    "type": "lesson",
                    "title": title,
                    "sb_page": sb_page,
                })
                i = j
                continue
            # Practical English Episode
            mpe = re.match(r"Practical\s+English\s+Episode\s*(\d+)?", nxt)
            if mpe:
                pe_count += 1
                ep = pe_count
                # The title is on the line after (the function description)
                desc = lines[i + 2] if i + 2 < len(lines) else ""
                title = _short_pe_title(desc)
                rows.append({
                    "file": current_file,
                    "code": f"PE{ep}",
                    "type": "practical_english",
                    "episode": ep,
                    "title": title or f"Practical English {ep}",
                    "sb_page": sb_page,
                })
                i += 2
                continue
            # Colloquial English (Upper-Int / Advanced).  Title is embedded on
            # the marker line: "Colloquial English 1  getting a job".
            mce = re.match(r"Colloquial\s+English\s*(\d+)\s*(.*)$", nxt)
            if mce:
                pe_count += 1
                ep = pe_count
                trailing = mce.group(2).strip()
                title = _short_pe_title(trailing) if trailing else ""
                rows.append({
                    "file": current_file,
                    "code": f"CE{ep}",
                    "type": "colloquial_english",
                    "episode": ep,
                    "title": title or f"Colloquial English {ep}",
                    "sb_page": sb_page,
                })
                i += 2
                continue
            # Review and Check
            mrc = re.match(r"Review\s+and\s+Check\s*(\d+)?\s*&\s*(\d+)?", nxt)
            if mrc:
                rc_count += 1
                if mrc.group(1) and mrc.group(2):
                    a, b = int(mrc.group(1)), int(mrc.group(2))
                else:
                    a, b = rc_count * 2 - 1, rc_count * 2
                rows.append({
                    "file": current_file or b,
                    "code": f"R&C {a}&{b}",
                    "type": "review",
                    "title": f"Review and Check {a} & {b}",
                    "sb_page": sb_page,
                    "covers_files": [a, b],
                })
                i += 2
                continue
        i += 1
    return rows


_REJECT_CHARS = set(".,/+()=:–—;'\"")
_GRAMMAR_TERMS = re.compile(
    r"\b(verbs?|nouns?|adjectives?|adverbs?|pronouns?|articles?|prepositions?|"
    r"simple|continuous|perfect|past|present|future|tenses?|"
    r"comparatives?|superlatives?|modals?|conditional|passive|"
    r"gerunds?|infinitives?|imperatives?|possessive|"
    r"sounds?|sentences?|stress|silent|consonants?|vowels?|linking|rhythm|"
    r"phrases?|expressions?|conjunctions?|countable|uncountable|"
    r"clauses?|questions?|negative|positive|connectors?|determiners?|quantifiers?|"
    r"colors?|adjective|family|jobs?|food|drink|clothes|months|"
    r"the alphabet|days of the week|word formation|word order)\b",
    re.IGNORECASE,
)


def _is_title_continuation(s: str, current_title: str) -> bool:
    s = s.strip()
    if not s or len(s) > 20:
        return False
    if re.search(r"\d", s):
        return False
    if any(c in s for c in _REJECT_CHARS):
        return False
    if re.match(r"^[A-D]\s", s):
        return False
    if s.startswith(("Practical English", "Review and Check", "Colloquial English")):
        return False
    if _GRAMMAR_TERMS.search(s):
        return False
    ct = current_title.rstrip()
    if not ct:
        return False
    # If the current title already ends decisively, stop appending.
    if ct[-1] in "!?…":
        return False
    return True


def _clean_title(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" \t,;.")
    return s


def _short_pe_title(desc: str) -> str:
    if not desc:
        return ""
    # The description starts with the functional context. Cut at "V " or "P "
    # which mark the vocab/pron sub-sections in the TOC.
    s = re.split(r"\s+[VP]\s+|\s{4,}", desc)[0]
    s = re.sub(r"\s+", " ", s).strip(" .,;:")
    # Capitalize first letter
    if s:
        s = s[0].upper() + s[1:]
    return s


if __name__ == "__main__":
    for cid, folder in [
        ("elementary", "AEF 1 elementary"),
        ("pre-intermediate", "AEF 2 pre-intermediate"),
        ("intermediate", "AEF 3 intermediate"),
        ("upper-intermediate", "AEF 4 upper-intermediate"),
        ("advanced", "AEF 5 advanced"),
    ]:
        tg = ROOT / folder / "TG.pdf"
        if not tg.exists():
            tg = ROOT / folder / "TB.pdf"
        rows = parse_syllabus(tg, cid)
        print(f"\n=== {cid}: {len(rows)} entries ===")
        for r in rows:
            print(f"  F{r['file']:2d}  {r['code']:11s}  SB p.{r['sb_page']:3d}  {r['title'][:60]}")
