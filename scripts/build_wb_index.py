"""
Lê o TOC do Workbook (p.2 de cada WB.pdf) e produz um mapeamento
lesson_code -> book_page para cada curso.

A saída é um dict que extract_lessons.py importa.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent

COURSE_FOLDERS = [
    ("starter",            "AEF 0 starter"),
    ("elementary",         "AEF 1 elementary"),
    ("pre-intermediate",   "AEF 2 pre-intermediate"),
    ("intermediate",       "AEF 3 intermediate"),
    ("upper-intermediate", "AEF 4 upper-intermediate"),
    ("advanced",           "AEF 5 advanced"),
]

# A linha do TOC parece com:
#   "4 \nA A cappuccino, please"
#   "8 \nPractical English Episode 1 How do you spell it?"
#   "10 \nA Are you on vacation?"
# Os File numbers às vezes aparecem como cabeçalhos isolados; vamos derivá-los
# da ordem (lesson A/B/C dentro do mesmo bloco = mesma File).


def parse_wb_toc(course_id: str, wb_path: Path) -> dict[str, int]:
    """Return a dict lesson_code -> book_page parsed from the WB TOC pages."""
    doc = fitz.open(wb_path)
    # Concatenate every page in the first 6 that looks like part of the TOC
    # (has "Practical English Episode" / "Colloquial English" or many
    # "Can you remember…?" review markers).  Some WBs split the TOC across
    # two pages.
    toc_pages = []
    for pi in range(0, min(6, len(doc))):
        t = doc[pi].get_text("text")
        if ("Practical English Episode" in t or "Colloquial English" in t
                or t.count("Can you remember") >= 1):
            toc_pages.append(t)
    if not toc_pages:
        toc_pages = [doc[pi].get_text("text") for pi in range(0, min(4, len(doc)))]
    doc.close()
    text = "\n".join(toc_pages)

    mapping: dict[str, int] = {}
    pe_count = 0
    ce_count = 0
    file_num = 0
    lesson_seq: list[str] = []  # letters seen so far in current File

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    def handle(book_page: int, marker: str) -> bool:
        nonlocal file_num, pe_count, ce_count, lesson_seq
        if file_num > 12:
            # Once we're past File 12, anything else is noise from later sections.
            return False
        # A lesson marker is a single letter A/B/C/D followed by anything that
        # ISN'T a lowercase letter (space, uppercase, symbol).
        ml = re.match(r"^([A-D])(?=$|\W|[A-Z])", marker)
        if ml:
            letter = ml.group(1)
            if letter == "A":
                file_num += 1
                lesson_seq = ["A"]
            else:
                lesson_seq.append(letter)
            mapping[f"{file_num}{letter}"] = book_page
            return True
        if marker.startswith("Practical English Episode"):
            pe_count += 1
            mapping[f"PE{pe_count}"] = book_page
            return True
        if marker.startswith("Colloquial English"):
            ce_count += 1
            mapping[f"CE{ce_count}"] = book_page
            return True
        return False

    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("Can you remember"):
            i += 1
            continue
        # Case A: "<page> <marker>" on the SAME line.
        m = re.match(r"^(\d{1,3})\s+(.+)$", ln)
        if m:
            page = int(m.group(1))
            rest = m.group(2).strip()
            if handle(page, rest):
                i += 1
                continue
        # Case B: "<page>" alone, then marker on the next line.
        if re.fullmatch(r"\d{1,3}", ln) and i + 1 < len(lines):
            page = int(ln)
            nxt = lines[i + 1]
            if handle(page, nxt):
                i += 2
                continue
        i += 1

    return mapping


def build_all() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for cid, folder in COURSE_FOLDERS:
        wb = ROOT / folder / "WB.pdf"
        if not wb.exists():
            print(f"skip {cid}: no WB.pdf")
            continue
        out[cid] = parse_wb_toc(cid, wb)
    return out


if __name__ == "__main__":
    data = build_all()
    for cid, mapping in data.items():
        print(f"\n=== {cid}: {len(mapping)} entries ===")
        for code, page in sorted(mapping.items(), key=lambda kv: (kv[1])):
            print(f"  {code:10s} → WB book p.{page}")
