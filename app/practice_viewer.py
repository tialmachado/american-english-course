"""
Converte os arquivos Practice (.docx) em HTML estruturado + áudios extraídos.

Cada DOCX é um ZIP com:
  - word/document.xml: texto e estrutura (parágrafos, tabelas, OLE objects)
  - word/embeddings/oleObject*.bin: objetos OLE com MP3 embedado
  - word/media/*.emf|.png: imagens

O HTML preserva a estrutura visível do Word:
  - parágrafos em negrito grandes viram <h3 class="pv-heading">
  - parágrafos abaixo de um heading viram <p class="pv-instruction"> (itálico, dim)
  - tabelas contendo "Grammar Bank" viram <div class="pv-grammar">
  - tabelas contendo OLE viram <div class="pv-exercise"> com áudio inline
  - outras tabelas viram <div class="pv-block">

Cache em data/practice_cache/<hash>/.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import olefile

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "practice_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
W = f"{{{W_NS}}}"
R = f"{{{R_NS}}}"

DISPLAYABLE_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def _cache_key(docx_path: Path) -> str:
    rel = str(docx_path.relative_to(ROOT))
    return hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16]


# ---------- OLE → MP3 ----------

def _extract_mp3_from_ole(ole_bytes: bytes) -> bytes | None:
    try:
        ole = olefile.OleFileIO(io.BytesIO(ole_bytes))
    except Exception:
        return None
    try:
        if not ole.exists("\x01Ole10Native"):
            return None
        data = ole.openstream("\x01Ole10Native").read()
        idx = data.find(b"ID3")
        if idx < 0:
            idx = data.find(b"\xff\xfb")
        if idx < 0:
            return None
        return data[idx:]
    finally:
        ole.close()


def _build_rel_map(rels_xml: bytes) -> dict[str, str]:
    root = ET.fromstring(rels_xml)
    out = {}
    for rel in root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
        out[rel.attrib["Id"]] = rel.attrib["Target"]
    return out


# ---------- Walker ----------

def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _is_heading_paragraph(p: ET.Element) -> bool:
    """All visible runs are bold and at heading font size (>=30 half-points)."""
    runs = p.findall(f"{W}r")
    if not runs:
        return False
    text_run_count = 0
    bold_big_count = 0
    for r in runs:
        t = r.find(f"{W}t")
        if t is None or not (t.text or "").strip():
            continue
        text_run_count += 1
        rpr = r.find(f"{W}rPr")
        if rpr is None:
            continue
        bold = rpr.find(f"{W}b") is not None
        sz = rpr.find(f"{W}sz")
        size = int(sz.attrib.get(f"{W}val", "0")) if sz is not None else 0
        if bold and size >= 30:
            bold_big_count += 1
    return text_run_count > 0 and bold_big_count == text_run_count


def _paragraph_content(p: ET.Element) -> tuple[str, list[str], list[str]]:
    """Return (text, [ole rIds], [image rIds]) of a paragraph in document order."""
    chunks: list[str] = []
    ole_rids: list[str] = []
    image_rids: list[str] = []
    for el in p.iter():
        name = _local(el.tag)
        if name == "t":
            chunks.append(el.text or "")
        elif name == "tab":
            chunks.append("\t")
        elif name == "br":
            chunks.append("\n")
        elif name == "OLEObject":
            rid = el.attrib.get(f"{R}id")
            if rid:
                ole_rids.append(rid)
        elif name == "blip":  # DrawingML <a:blip r:embed="..."/>
            rid = el.attrib.get(f"{R}embed")
            if rid:
                image_rids.append(rid)
        elif name == "imagedata":  # VML <v:imagedata r:id="..."/>
            rid = el.attrib.get(f"{R}id")
            if rid:
                image_rids.append(rid)
    text = "".join(chunks)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text, ole_rids, image_rids


def _block_from_paragraph(p: ET.Element) -> dict | None:
    text, ole_rids, image_rids = _paragraph_content(p)
    if not text and not ole_rids and not image_rids:
        return None
    return {
        "type": "p",
        "text": text,
        "ole_rids": ole_rids,
        "image_rids": image_rids,
        "is_heading": _is_heading_paragraph(p) if text else False,
    }


def _block_from_table(tbl: ET.Element) -> dict:
    """Collect paragraphs (text + OLE + image refs) from a table in row+cell order."""
    rows: list[list[list[dict]]] = []
    all_ole_rids: list[str] = []
    all_image_rids: list[str] = []
    plain_text = ""
    for tr in tbl.findall(f"{W}tr"):
        row_cells: list[list[dict]] = []
        for tc in tr.findall(f"{W}tc"):
            cell_blocks: list[dict] = []
            for child in tc:
                if _local(child.tag) == "p":
                    b = _block_from_paragraph(child)
                    if b:
                        cell_blocks.append(b)
                        all_ole_rids.extend(b["ole_rids"])
                        all_image_rids.extend(b["image_rids"])
                        if not plain_text and b["text"]:
                            plain_text = b["text"][:120]
            row_cells.append(cell_blocks)
        rows.append(row_cells)
    kind = "exercise" if all_ole_rids else "block"
    for cell_blocks in (rows[0] if rows else []):
        for b in cell_blocks:
            if "Grammar Bank" in b["text"]:
                kind = "grammar"
                break
        if kind == "grammar":
            break
    return {
        "type": "tbl",
        "kind": kind,
        "rows": rows,
        "ole_rids": all_ole_rids,
        "image_rids": all_image_rids,
    }


def _walk_body(body: ET.Element) -> list[dict]:
    out: list[dict] = []
    for child in body:
        name = _local(child.tag)
        if name == "p":
            b = _block_from_paragraph(child)
            if b:
                out.append(b)
        elif name == "tbl":
            out.append(_block_from_table(child))
    return out


# ---------- HTML rendering ----------

# Marker → badge HTML.  The "negative" marker uses several dash variants
# because the AEF source files mix hyphen-minus (-), en-dash (–) and minus (−).
_FORM_BADGE = {
    "pos": '<span class="pv-mark pv-mark-pos" title="forma positiva">+</span>',
    "neg": '<span class="pv-mark pv-mark-neg" title="forma negativa">–</span>',
    "q":   '<span class="pv-mark pv-mark-q"   title="forma interrogativa">?</span>',
}
_MARKER_RE = re.compile(r"\[\s*([+\-–—−?])\s*\]")


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace("\n", "<br>"))


# Speakers may be separated from the rest by space, colon, or both.
# Number may be followed by ".", " " or both.
_DIALOG_NUM_SPEAKER_RE = re.compile(r"^(\d+)\s*\.?\s*([A-D])[\s:]+(.+)$", re.DOTALL)
_DIALOG_SPEAKER_RE     = re.compile(r"^([A-D])[\s:]+(.+)$", re.DOTALL)
_NUMBERED_RE           = re.compile(r"^(\d+)\s*\.\s*(.+)$", re.DOTALL)


def _decorate_exercise_line(line: str) -> str:
    """Apply number/speaker badges to a single line."""
    line = line.strip()
    m = _DIALOG_NUM_SPEAKER_RE.match(line)
    if m:
        return (
            f'<span class="pv-num">{m.group(1)}.</span>'
            f'<span class="pv-speaker pv-speaker-{m.group(2)}">{m.group(2)}</span> '
            f'{_escape(m.group(3))}'
        )
    m = _DIALOG_SPEAKER_RE.match(line)
    if m:
        return (
            f'<span class="pv-speaker pv-speaker-{m.group(1)}">{m.group(1)}</span> '
            f'{_escape(m.group(2))}'
        )
    m = _NUMBERED_RE.match(line)
    if m:
        return f'<span class="pv-num">{m.group(1)}.</span> {_escape(m.group(2))}'
    return _escape(line)


def _decorate_exercise_text(s: str) -> str:
    """Exercise text often has multiple dialogue lines joined by line breaks
    inside a single <w:p>.  Decorate each line independently."""
    lines = s.split("\n")
    return "<br>".join(_decorate_exercise_line(ln) for ln in lines)


def _decorate_grammar_text(s: str) -> str:
    """After HTML escaping, swap [+], [-/–/−], [?] markers for colored badges
    and turn all-caps sub-headings (EXAMPLES, FORM, etc.) into emphasised labels."""
    def repl(m: re.Match) -> str:
        ch = m.group(1)
        if ch == "+":
            return _FORM_BADGE["pos"]
        if ch == "?":
            return _FORM_BADGE["q"]
        return _FORM_BADGE["neg"]  # any dash variant
    out = _escape(s)
    out = _MARKER_RE.sub(repl, out)
    if re.fullmatch(r"[A-Z][A-Z &]{2,40}", s):
        return f'<span class="pv-sub">{out}</span>'
    return out


def _render_paragraph_block(b: dict, rid_to_audio: dict, audio_url,
                             image_files: dict | None = None, cache_key: str = "") -> str:
    parts: list[str] = []
    if b["text"]:
        if b["is_heading"]:
            parts.append(f'<h3 class="pv-heading">{_escape(b["text"])}</h3>')
        else:
            parts.append(f'<p>{_escape(b["text"])}</p>')
    if image_files:
        for rid in b.get("image_rids", []):
            url = _img_url(rid, image_files, cache_key)
            if url:
                parts.append(f'<img class="pv-img" src="{url}" alt="">')
    return "\n".join(parts)


def _img_url(rid: str, image_files: dict, cache_key: str) -> str | None:
    fname = image_files.get(rid)
    if not fname:
        return None
    return f"/practice-asset/{cache_key}/{fname}"


def _render_cell_blocks(cell: list[dict], rid_to_audio: dict, audio_url,
                        image_files: dict | None = None, cache_key: str = "",
                        decorate: str | None = None) -> str:
    """decorate ∈ {None, "grammar", "exercise"}"""
    out: list[str] = []
    for b in cell:
        if b["text"]:
            if decorate == "grammar":
                text_html = _decorate_grammar_text(b["text"])
            elif decorate == "exercise":
                text_html = _decorate_exercise_text(b["text"])
            else:
                text_html = _escape(b["text"])
            if b["is_heading"]:
                out.append(f'<div class="pv-cell-heading">{text_html}</div>')
            else:
                out.append(f'<p>{text_html}</p>')
        if image_files:
            for rid in b.get("image_rids", []):
                url = _img_url(rid, image_files, cache_key)
                if url:
                    out.append(f'<img class="pv-img" src="{url}" alt="">')
    return "\n".join(out)


def _render_audio_row(ole_rids: list[str], rid_to_audio: dict, audio_url) -> str:
    parts: list[str] = []
    n = 0
    for rid in ole_rids:
        idx = rid_to_audio.get(rid)
        if idx is None:
            continue
        n += 1
        url = audio_url(idx)
        label = f"Áudio {n}" if len(ole_rids) > 1 else "Áudio"
        parts.append(
            f'<div class="pv-audio-item">'
            f'<span class="pv-audio-label">🎧 {label}</span>'
            f'<audio controls preload="metadata" src="{url}"></audio>'
            f'</div>'
        )
    if not parts:
        return ""
    return f'<div class="pv-audios">{"".join(parts)}</div>'


def _render_table_block(b: dict, rid_to_audio: dict, audio_url,
                         image_files: dict | None = None, cache_key: str = "") -> str:
    def rcb(cell, decorate=None):
        return _render_cell_blocks(cell, rid_to_audio, audio_url,
                                    image_files=image_files, cache_key=cache_key,
                                    decorate=decorate)

    if b["kind"] == "grammar":
        inner: list[str] = ['<div class="pv-grammar-title">Grammar Bank</div>']
        for row in b["rows"]:
            for cell in row:
                inner.append(rcb(cell, decorate="grammar"))
        return f'<div class="pv-grammar">{"".join(inner)}</div>'

    klass = "pv-exercise" if b["kind"] == "exercise" else "pv-block"
    exercise_mode = "exercise" if b["kind"] == "exercise" else None

    # If there are no audios anywhere, just render simple stacked cells.
    if not b["ole_rids"]:
        inner = []
        for row in b["rows"]:
            for cell in row:
                inner.append(rcb(cell, decorate=exercise_mode))
        return f'<div class="{klass}">{"".join(inner)}</div>'

    # Render as a real HTML table so each row's content and its audio cell
    # stay side-by-side, preserving the original layout.
    rows_html: list[str] = []
    for row in b["rows"]:
        # Detect cell roles in this row.
        cell_cols = []
        for cell in row:
            has_text   = any(blk["text"] for blk in cell)
            has_image  = any(blk.get("image_rids") for blk in cell)
            has_audio  = any(blk.get("ole_rids")  for blk in cell)
            cell_cols.append((cell, has_text, has_image, has_audio))

        tds: list[str] = []
        for cell, has_text, has_image, has_audio in cell_cols:
            content = rcb(cell, decorate=exercise_mode)
            audios: list[str] = []
            for blk in cell:
                for rid in blk.get("ole_rids", []):
                    idx = rid_to_audio.get(rid)
                    if idx is None:
                        continue
                    audios.append(
                        f'<audio controls preload="metadata" src="{audio_url(idx)}"></audio>'
                    )
            audio_html = "".join(audios)
            # Audio-only cell = has audio + no text (image icon is usually the
            # WMP audio icon which the browser can't render anyway).
            audio_only = has_audio and not has_text
            cls = "pv-td-audio" if audio_only else "pv-td"
            tds.append(f'<td class="{cls}">{content}{audio_html}</td>')
        rows_html.append(f'<tr>{"".join(tds)}</tr>')
    return f'<div class="{klass}"><table class="pv-table">{"".join(rows_html)}</table></div>'


# ---------- Top-level ----------

def extract_to_html(docx_path: Path, force: bool = False) -> dict:
    docx_path = docx_path.resolve()
    key = _cache_key(docx_path)
    cache_path = CACHE_DIR / key
    manifest = cache_path / "manifest.json"
    if not force and manifest.exists():
        return json.loads(manifest.read_text())

    cache_path.mkdir(parents=True, exist_ok=True)
    image_files: dict[str, str] = {}   # rid -> cached filename
    with zipfile.ZipFile(docx_path, "r") as z:
        document_xml = z.read("word/document.xml")
        try:
            rels_xml = z.read("word/_rels/document.xml.rels")
            rel_map = _build_rel_map(rels_xml)
        except KeyError:
            rel_map = {}
        ole_payloads: dict[str, bytes] = {}
        for rid, target in rel_map.items():
            if "oleObject" in target and target.endswith(".bin"):
                full = f"word/{target}" if not target.startswith("word/") else target
                try:
                    ole_payloads[rid] = z.read(full)
                except KeyError:
                    pass
                continue
            # Image relationships: extract supported formats only.
            tlow = target.lower()
            ext = Path(tlow).suffix
            if ext in DISPLAYABLE_IMAGE_EXTS:
                full = f"word/{target}" if not target.startswith("word/") else target
                try:
                    data = z.read(full)
                except KeyError:
                    continue
                idx = len(image_files)
                fname = f"img_{idx:03d}{ext}"
                (cache_path / fname).write_bytes(data)
                image_files[rid] = fname

    doc_root = ET.fromstring(document_xml)
    body = doc_root.find(f"{W}body")
    blocks = _walk_body(body) if body is not None else []

    # Materialize audios in order of first appearance.
    audio_files: list[str] = []
    rid_to_audio: dict[str, int] = {}

    def _walk_rids(blocks):
        for b in blocks:
            if b["type"] == "p":
                for rid in b["ole_rids"]:
                    yield rid
            else:  # table
                for row in b["rows"]:
                    for cell in row:
                        for blk in cell:
                            for rid in blk["ole_rids"]:
                                yield rid

    for rid in _walk_rids(blocks):
        if rid in rid_to_audio:
            continue
        payload = ole_payloads.get(rid)
        if not payload:
            continue
        mp3 = _extract_mp3_from_ole(payload)
        if not mp3:
            continue
        idx = len(audio_files)
        fname = f"audio_{idx:03d}.mp3"
        (cache_path / fname).write_bytes(mp3)
        audio_files.append(fname)
        rid_to_audio[rid] = idx

    def audio_url(idx: int) -> str:
        return f"/practice-asset/{key}/{audio_files[idx]}"

    html_parts: list[str] = []
    last_was_heading = False
    for b in blocks:
        if b["type"] == "p":
            if b["is_heading"]:
                html_parts.append(_render_paragraph_block(b, rid_to_audio, audio_url,
                                                         image_files=image_files, cache_key=key))
                last_was_heading = True
                continue
            if last_was_heading and b["text"] and not b["ole_rids"] and not b.get("image_rids"):
                html_parts.append(f'<p class="pv-instruction">{_escape(b["text"])}</p>')
                last_was_heading = False
                continue
            html_parts.append(_render_paragraph_block(b, rid_to_audio, audio_url,
                                                     image_files=image_files, cache_key=key))
            if b["ole_rids"]:
                html_parts.append(_render_audio_row(b["ole_rids"], rid_to_audio, audio_url))
        else:
            html_parts.append(_render_table_block(b, rid_to_audio, audio_url,
                                                 image_files=image_files, cache_key=key))
        last_was_heading = False

    html = "\n".join(html_parts) or "<p><em>(documento vazio)</em></p>"

    result = {
        "html": html,
        "audio_count": len(audio_files),
        "cache_key": key,
    }
    manifest.write_text(json.dumps(result, ensure_ascii=False))
    return result


def asset_path(cache_key: str, filename: str) -> Path | None:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "", filename)
    p = CACHE_DIR / cache_key / safe
    if p.exists():
        return p
    return None
