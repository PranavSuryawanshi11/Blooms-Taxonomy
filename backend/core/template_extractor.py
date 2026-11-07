"""
Template Extractor
Reads an OLD question paper (text PDF, scanned PDF / photo via OCR, or Word file) and rebuilds the
college's template from it:

  * header lines (college, society, tagline, affiliation, regional-language title, programme, exam title ...)
    each with its own font size, bold / italic, alignment and colour, in the original order
  * logo(s) with their left / centre / right position and size
  * the row layout of the course / time / marks / roll-number block
  * instructions
  * section structure: questions per section, marks of each sub-question, which ones have an OR
  * numbering style (Q.1 (a) / Q1 a) / 1.), font family and size, page margins, header rule

Nothing here calls the network; OCR is used only when Tesseract is installed on the server.
"""

import io
import re
import base64
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from core.question_set_parser import (
    _find_marks, _detect_bloom, _RE_Q_PREFIX, _RE_NUM, _RE_SUB, _RE_ROMAN,
)

MAX_PAGES = 6
RENDER_DPI = 200
MAX_LOGO_BYTES = 140 * 1024

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
SUPPORTED_EXT = (".pdf", ".docx") + IMAGE_EXT

# ---------------------------------------------------------------------------
# Regular expressions used to understand the header and meta block
# ---------------------------------------------------------------------------
_LABEL_DEFS = [
    ("code", r"(?:course|subject|paper)\s*code"),
    ("course", r"(?:course|subject|paper)(?:\s*name|\s*title)?"),
    ("duration", r"time\s*allowed|time|duration"),
    ("marks", r"max(?:imum)?\.?\s*marks?|total\s*marks?|full\s*marks?"),
    ("roll", r"roll\s*(?:no|number)\.?|seat\s*(?:no|number)\.?|prn(?:\s*no\.?)?|enrol+ment\s*(?:no\.?)?|usn|reg(?:istration)?\.?\s*no\.?"),
    ("date", r"date(?:\s*of\s*exam(?:ination)?)?"),
    ("day", r"day"),
    ("class", r"class|year"),
    ("branch", r"branch|department|dept\.?|programme|program"),
    ("semester", r"sem(?:ester)?"),
    ("division", r"div(?:ision)?"),
    ("batch", r"batch"),
]
_LABEL_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(f"(?P<{k}>{p})" for k, p in _LABEL_DEFS) + r")\s*(?:[:\-–]|\.{2,})\s*", re.I)
_STOP_META_KEYS = {"code", "course", "duration", "marks", "roll", "date", "day"}
_DYNAMIC_KEYS = {"code", "course", "duration", "marks", "roll", "date"}

_RE_INSTR = re.compile(r"^\s*(?:general\s+)?(?:instructions?|notes?)\s*[:\-–]?\s*(.*)$", re.I)
_RE_SECTION = re.compile(r"^\s*(section|part)\s+([A-Za-z0-9]+)\b\s*[:\-–—.]?\s*(.*)$", re.I)
_RE_OR = re.compile(r"^[\-–\s(\[]*or[\-–\s)\]]*$", re.I)
_RE_ONLY_MARKS = re.compile(r"^[\[(]?\s*\d{1,2}\s*(?:marks?|m)?\s*[\])]?$", re.I)

_ORG_WORDS = r"institute|institution|college|university|engineering|technology|school|polytechnic|vidyalaya|mahavidyalaya|academy|faculty"
_SOCIETY_WORDS = r"society|trust|sansthan|foundation|mandal|sabha|samaj|education|charitable"
_TAGLINE_WORDS = r"autonomous|accredited|naac|nba|iso|minority|aided|empowered|approved by|nirf|grade|an institute|a\+|a\+\+"
_AFFIL_WORDS = r"affiliated|affiliation|approved by|recognized|recognised|aicte|ugc|university of|technological university"
_PROG_WORDS = r"b\.?\s?tech|b\.?\s?e\.?|m\.?\s?tech|m\.?\s?e\.?|mba|mca|bca|b\.?sc|m\.?sc|diploma|programme|program|branch|department of|dept\. of"
_YEAR_WORDS = r"semester|sem\b|sem-|academic year|exam year|year\s*:|\b20\d\d\s*[-–/]\s*(?:20)?\d\d\b"
_EXAM_WORDS = r"\bexamination|\bexam\b|\btest\b|\binternal\b|\bmid[- ]?sem|\bend[- ]?sem|\bunit test|\bc\.?a\.?t\b|\bassessment|\binsem|\bquiz"

_REGIONAL_RE = re.compile(r"[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0600-\u06FF]")

_SERIF_RE = re.compile(r"times|serif|roman|cambria|garamond|georgia|palatino|book|minion|century", re.I)
_SANS_RE = re.compile(r"arial|helvetica|calibri|verdana|tahoma|sans|segoe|roboto|open|lato|nirmala|mangal", re.I)


# ===========================================================================
# 1. Loading the document into "lines" (text + style + geometry) and raw logos
# ===========================================================================

def _hex_color(c) -> Optional[str]:
    """pdf colour tuple -> '#rrggbb' (None for near-black text)."""
    try:
        if c is None:
            return None
        if isinstance(c, (int, float)):
            c = (c,)
        c = list(c)
        if len(c) == 1:
            r = g = b = float(c[0])
        elif len(c) == 3:
            r, g, b = [float(x) for x in c]
        elif len(c) == 4:
            C, M, Y, K = [float(x) for x in c]
            r, g, b = (1 - C) * (1 - K), (1 - M) * (1 - K), (1 - Y) * (1 - K)
        else:
            return None
        if max(r, g, b) < 0.22:
            return None
        return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    except Exception:
        return None


def _clean_font(name: str) -> str:
    n = re.sub(r"^[A-Z]{6}\+", "", name or "")
    n = re.sub(r"(?i)(?:-|,)?(bold|italic|oblique|regular|mt|ps|semibold|black|demi|medium)+$", "", n)
    n = re.sub(r"(?i)(bold|italic|oblique|regular|mt|ps)", "", n)
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n).replace("-", " ").replace(",", " ")
    return re.sub(r"\s+", " ", n).strip()


def _family_of(font: str) -> Optional[str]:
    if not font:
        return None
    if _SANS_RE.search(font):
        return "sans"
    if _SERIF_RE.search(font):
        return "serif"
    return None


def _assign_align(lines: List[Dict[str, Any]], page_w: float) -> None:
    """Left / centre / right from geometry (PDF and OCR only)."""
    body = [l for l in lines if l.get("x0") is not None]
    if not body:
        return
    lm = sorted(l["x0"] for l in body)[max(0, int(len(body) * 0.1))]
    rm = sorted(l["x1"] for l in body)[min(len(body) - 1, int(len(body) * 0.9))]
    mid = (lm + rm) / 2.0
    tol = 0.035 * page_w
    for l in body:
        centre = (l["x0"] + l["x1"]) / 2.0
        if abs(centre - mid) < tol and (l["x0"] - lm) > 0.05 * page_w:
            l["align"] = "center"
        elif l["x0"] - lm < tol:
            l["align"] = "left"
        elif rm - l["x1"] < tol and (l["x0"] - lm) > 0.25 * page_w:
            l["align"] = "right"
        else:
            l["align"] = "center" if abs(centre - mid) < 0.12 * page_w else "left"


def _group_words(words: List[Dict[str, Any]], page_no: int) -> List[Dict[str, Any]]:
    """Group words into text lines, preserving per-line font info."""
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows: List[List[Dict[str, Any]]] = []
    for w in words:
        placed = False
        for row in rows[-3:]:
            ref = row[0]
            if abs(w["top"] - ref["top"]) <= max(2.5, 0.45 * min(w["size"], ref["size"])):
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])
    lines = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in row).strip()
        if not text:
            continue
        chars = sum(len(w["text"]) for w in row) or 1
        bold_chars = sum(len(w["text"]) for w in row if w.get("bold"))
        ital_chars = sum(len(w["text"]) for w in row if w.get("italic"))
        size = max(w["size"] for w in row)
        fonts = Counter(w.get("font") for w in row for _ in range(len(w["text"])))
        colors = Counter(w.get("color") for w in row if w.get("color"))
        lines.append({
            "text": text, "size": round(size * 2) / 2.0, "bold": bold_chars / chars >= 0.6,
            "italic": ital_chars / chars >= 0.6, "font": fonts.most_common(1)[0][0] if fonts else "",
            "color": colors.most_common(1)[0][0] if colors else None,
            "x0": min(w["x0"] for w in row), "x1": max(w["x1"] for w in row),
            "top": min(w["top"] for w in row), "bottom": max(w["bottom"] for w in row),
            "page": page_no, "align": "left", "table": False,
        })
    lines.sort(key=lambda l: (l["page"], l["top"]))
    return lines


# ---- logo detection from pixels --------------------------------------------

def _find_blobs(img: Image.Image, text_boxes: List[Tuple[float, float, float, float]], zone_bottom: float,
                scale: float) -> List[Tuple[int, int, int, int]]:
    """Locate logo-like ink clusters in the header zone (pixel boxes), ignoring text and thin rules."""
    W, H = img.size
    zone_h = int(min(H, zone_bottom * scale))
    if zone_h < 40:
        return []
    f = 4
    small = img.convert("L").crop((0, 0, W, zone_h)).resize((max(1, W // f), max(1, zone_h // f)), Image.BILINEAR)
    gw, gh = small.size
    px = small.load()
    ink = [[px[x, y] < 238 for x in range(gw)] for y in range(gh)]
    for (x0, t, x1, b) in text_boxes:                       # blank out recognised text
        for y in range(max(0, int((t * scale - 3) / f)), min(gh, int((b * scale + 3) / f) + 1)):
            for x in range(max(0, int((x0 * scale - 3) / f)), min(gw, int((x1 * scale + 3) / f) + 1)):
                ink[y][x] = False
    seen = [[False] * gw for _ in range(gh)]
    comps = []
    for y in range(gh):
        for x in range(gw):
            if ink[y][x] and not seen[y][x]:
                stack = [(x, y)]
                seen[y][x] = True
                minx = maxx = x
                miny = maxy = y
                count = 0
                while stack:
                    cx, cy = stack.pop()
                    count += 1
                    minx, maxx, miny, maxy = min(minx, cx), max(maxx, cx), min(miny, cy), max(maxy, cy)
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < gw and 0 <= ny < gh and ink[ny][nx] and not seen[ny][nx]:
                                seen[ny][nx] = True
                                stack.append((nx, ny))
                if count >= 6:
                    comps.append([minx, miny, maxx, maxy])
    # merge components that are close (logos are made of several pieces)
    gap = max(3, int(0.12 * RENDER_DPI / f))
    merged = True
    while merged and len(comps) > 1:
        merged = False
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                a, b = comps[i], comps[j]
                if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                    comps[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    comps.pop(j)
                    merged = True
                    break
            if merged:
                break
    dpi_px = RENDER_DPI / f
    out = []
    for x0, y0, x1, y1 in comps:
        w, h = (x1 - x0 + 1) / dpi_px, (y1 - y0 + 1) / dpi_px      # inches
        if w < 0.35 or h < 0.35 or w > 2.3 or h > 2.3:
            continue
        if not (0.35 <= w / h <= 2.8):
            continue
        out.append((x0 * f, y0 * f, (x1 + 1) * f, (y1 + 1) * f))
    return out


def _clip_logo(img: Image.Image, box: Tuple[int, int, int, int]) -> Optional[Image.Image]:
    x0, y0, x1, y1 = box
    pad = 4
    crop = img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))).convert("RGBA")
    # trim white margins
    bg = Image.new("RGBA", crop.size, (255, 255, 255, 255))
    from PIL import ImageChops
    diff = ImageChops.difference(crop.convert("RGB"), bg.convert("RGB")).convert("L").point(lambda p: 255 if p > 18 else 0)
    bbox = diff.getbbox()
    if not bbox:
        return None
    return crop.crop(bbox)


def _encode_logo(img: Image.Image) -> Optional[str]:
    """Return a compact data URL (PNG, or JPEG when large)."""
    im = img.convert("RGBA")
    max_side = 360
    if max(im.size) > max_side:
        ratio = max_side / max(im.size)
        im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))), Image.LANCZOS)
    for side in (360, 300, 240, 180):
        cur = im
        if max(cur.size) > side:
            r = side / max(cur.size)
            cur = cur.resize((max(1, int(cur.width * r)), max(1, int(cur.height * r))), Image.LANCZOS)
        buf = io.BytesIO()
        cur.save(buf, format="PNG", optimize=True)
        if buf.tell() <= MAX_LOGO_BYTES:
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        flat = Image.new("RGB", cur.size, (255, 255, 255))
        flat.paste(cur, mask=cur.split()[3])
        buf = io.BytesIO()
        flat.save(buf, format="JPEG", quality=86)
        if buf.tell() <= MAX_LOGO_BYTES:
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return None


def _position_of(cx: float, page_w: float) -> str:
    r = cx / page_w
    return "left" if r < 0.36 else "right" if r > 0.64 else "center"


# ---- PDF -------------------------------------------------------------------

def _load_pdf(data: bytes) -> Dict[str, Any]:
    import pdfplumber
    lines: List[Dict[str, Any]] = []
    doc: Dict[str, Any] = {"source": "pdf", "logos_raw": [], "page_w": 595.0, "page_h": 842.0,
                           "rule_below_header": False, "box_header": False}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = pdf.pages[:MAX_PAGES]
        if not pages:
            raise ValueError("The PDF has no pages.")
        doc["page_w"], doc["page_h"] = float(pages[0].width), float(pages[0].height)
        total_chars = 0
        for pi, page in enumerate(pages):
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=2, y_tolerance=3,
                                       extra_attrs=["fontname", "size", "non_stroking_color"])
            ws = []
            for w in words:
                font = _clean_font(w.get("fontname", ""))
                fn = w.get("fontname", "")
                ws.append({"text": w["text"], "x0": w["x0"], "x1": w["x1"], "top": w["top"], "bottom": w["bottom"],
                           "size": float(w.get("size") or 10), "font": font,
                           "bold": bool(re.search(r"bold|black|heavy|semibold|demi|[-,]B\b", fn, re.I)),
                           "italic": bool(re.search(r"italic|oblique|[-,]I\b", fn, re.I)),
                           "color": _hex_color(w.get("non_stroking_color"))})
            total_chars += sum(len(w["text"]) for w in ws)
            lines.extend(_group_words(ws, pi))
        if total_chars < 40:
            doc.update(_load_ocr_from_pdf(pdf))
            return doc
        # geometry of the first page: images, rules, boxes
        first = pages[0]
        doc["_first_page"] = first
        _assign_align([l for l in lines if l["page"] == 0], doc["page_w"])
        for pi in range(1, len(pages)):
            _assign_align([l for l in lines if l["page"] == pi], doc["page_w"])
        doc["lines"] = lines
        # Render page 1 while the PDF is still open (needed for logo crops)
        try:
            doc["page_img"] = first.to_image(resolution=RENDER_DPI).original.convert("RGB")
        except Exception:
            doc["page_img"] = None
        doc["images_bbox"] = [(im["x0"], im["top"], im["x1"], im["bottom"]) for im in (first.images or [])]
        doc["hrules"] = [(l["x0"], l["top"], l["x1"]) for l in (first.lines or []) if abs(l["top"] - l["bottom"]) < 2]
        doc["hrules"] += [(r["x0"], r["top"], r["x1"]) for r in (first.rects or []) if (r["bottom"] - r["top"]) < 3]
        doc["rects"] = [(r["x0"], r["top"], r["x1"], r["bottom"]) for r in (first.rects or [])]
    return doc


# ---- OCR (scanned PDF / photo) ----------------------------------------------

def _ocr_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_lines(img: Image.Image, page_no: int) -> List[Dict[str, Any]]:
    import pytesseract
    langs = "eng"
    try:
        have = set(pytesseract.get_languages(config=""))
        extra = [l for l in ("hin", "mar", "guj", "tam", "tel", "kan", "ben") if l in have]
        langs = "+".join(["eng"] + extra)
    except Exception:
        pass
    d = pytesseract.image_to_data(img, lang=langs, config="--psm 4", output_type=pytesseract.Output.DICT)
    groups: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    gray = img.convert("L")
    for i, txt in enumerate(d["text"]):
        txt = (txt or "").strip()
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if not txt or conf < 25:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        crop = gray.crop((x, y, x + max(w, 1), y + max(h, 1)))
        hist = crop.histogram()
        dark = sum(hist[:110]) / max(1, w * h)
        groups.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append({
            "text": txt, "x0": x, "x1": x + w, "top": y, "bottom": y + h, "size": h * 72.0 / RENDER_DPI * 1.15,
            "dark": dark, "bold": False, "italic": False, "font": "", "color": None})
    lines = []
    all_dark = [w["dark"] for ws in groups.values() for w in ws]
    med_dark = sorted(all_dark)[len(all_dark) // 2] if all_dark else 0.3
    for ws in groups.values():
        for w in ws:
            w["bold"] = w["dark"] > med_dark * 1.35
    for ws in groups.values():
        for ln in _group_words(ws, page_no):
            # coordinates stay in pixels; convert to points for uniformity
            k = 72.0 / RENDER_DPI
            for key in ("x0", "x1", "top", "bottom"):
                ln[key] *= k
            lines.append(ln)
    return lines


def _load_ocr_from_pdf(pdf) -> Dict[str, Any]:
    if not _ocr_available():
        raise ValueError("This PDF is a scan (no text inside) and OCR is not installed on this server. "
                         "Upload the Word or text-based PDF version, or install Tesseract (see README).")
    pages = pdf.pages[:MAX_PAGES]
    lines, first_img = [], None
    for pi, page in enumerate(pages):
        img = page.to_image(resolution=RENDER_DPI).original.convert("RGB")
        if pi == 0:
            first_img = img
        lines.extend(_ocr_lines(img, pi))
    pw, ph = float(pages[0].width), float(pages[0].height)
    for pi in range(len(pages)):
        _assign_align([l for l in lines if l["page"] == pi], pw)
    return {"source": "ocr", "lines": lines, "page_img": first_img, "page_w": pw, "page_h": ph,
            "images_bbox": [], "hrules": [], "rects": [], "logos_raw": []}


def _load_image(data: bytes) -> Dict[str, Any]:
    if not _ocr_available():
        raise ValueError("Reading photos or scans needs OCR (Tesseract), which is not installed on this server. "
                         "Upload a Word or text-based PDF instead.")
    img = Image.open(io.BytesIO(data)).convert("RGB")
    # normalise to ~A4 at RENDER_DPI so size heuristics hold
    target_w = int(8.27 * RENDER_DPI)
    if img.width != target_w:
        img = img.resize((target_w, int(img.height * target_w / img.width)), Image.LANCZOS)
    lines = _ocr_lines(img, 0)
    pw, ph = img.width * 72.0 / RENDER_DPI, img.height * 72.0 / RENDER_DPI
    _assign_align(lines, pw)
    return {"source": "ocr", "lines": lines, "page_img": img, "page_w": pw, "page_h": ph,
            "images_bbox": [], "hrules": [], "rects": [], "logos_raw": []}


# ---- DOCX ------------------------------------------------------------------

def _emu_to_pt(v) -> float:
    return float(v) / 12700.0


def _docx_run_style(par, doc_default_size: float) -> Dict[str, Any]:
    chars = bold = ital = 0
    size = None
    font = None
    color = None
    for r in par.runs:
        t = r.text or ""
        if not t.strip():
            continue
        n = len(t)
        chars += n
        b = r.bold if r.bold is not None else (par.style.font.bold if par.style is not None else None)
        i = r.italic if r.italic is not None else (par.style.font.italic if par.style is not None else None)
        bold += n if b else 0
        ital += n if i else 0
        s = r.font.size or (par.style.font.size if par.style is not None else None)
        if s:
            size = max(size or 0, s.pt)
        font = font or r.font.name or (par.style.font.name if par.style is not None else None)
        try:
            if r.font.color is not None and r.font.color.rgb is not None:
                rgb = str(r.font.color.rgb)
                color = color or ("#" + rgb.lower())
                if color in ("#000000", "#auto"):
                    color = None
        except Exception:
            pass
    chars = chars or 1
    return {"size": size or doc_default_size, "bold": bold / chars >= 0.6, "italic": ital / chars >= 0.6,
            "font": font or "", "color": color}


def _load_docx(data: bytes) -> Dict[str, Any]:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(io.BytesIO(data))
    sec = document.sections[0] if document.sections else None
    page_w = _emu_to_pt(sec.page_width) if sec and sec.page_width else 595.0
    page_h = _emu_to_pt(sec.page_height) if sec and sec.page_height else 842.0
    margin_in = (_emu_to_pt(sec.left_margin) / 72.0) if sec and sec.left_margin else 0.8
    default_size = 11.0
    try:
        if document.styles["Normal"].font.size:
            default_size = document.styles["Normal"].font.size.pt
    except Exception:
        pass

    lines: List[Dict[str, Any]] = []
    logos: List[Dict[str, Any]] = []
    seen_blobs = set()
    align_map = {0: "left", 1: "center", 2: "right", 3: "left"}

    def para_images(par, force_pos=None):
        blips = par._p.xpath(".//a:blip")
        for blip in blips:
            rid = blip.get(qn("r:embed"))
            if not rid:
                continue
            try:
                blob = par.part.related_parts[rid].blob
                key = hash(blob)
                if key in seen_blobs:
                    continue
                img = Image.open(io.BytesIO(blob))
                img.load()
            except Exception:
                continue
            seen_blobs.add(key)
            pos = force_pos
            height_pt = None
            drawing = blip.getparent()
            while drawing is not None and drawing.tag.rsplit("}", 1)[-1] not in ("inline", "anchor"):
                drawing = drawing.getparent()
            if drawing is not None:
                ext = drawing.xpath("./wp:extent")
                if ext:
                    height_pt = _emu_to_pt(int(ext[0].get("cy", 0)))
                if drawing.tag.endswith("anchor") and not pos:
                    al = drawing.xpath("./wp:positionH/wp:align")
                    if al and al[0].text in ("left", "right", "center"):
                        pos = al[0].text
                    else:
                        off = drawing.xpath("./wp:positionH/wp:posOffset")
                        if off:
                            pos = _position_of(_emu_to_pt(int(off[0].text)) + 40, page_w)
            if not pos:
                pos = align_map.get(par.alignment if par.alignment is not None else 0, "left")
                if par.alignment is None:
                    pos = "center"
            logos.append({"img": img.convert("RGBA"), "position": pos, "height_pt": height_pt})

    def emit_par(par, in_table=False):
        text = (par.text or "").strip()
        if not text:
            return
        st = _docx_run_style(par, default_size)
        al = par.alignment if par.alignment is not None else (par.style.paragraph_format.alignment if par.style is not None else None)
        lines.append({"text": re.sub(r"\s+", " ", text), "size": round(st["size"] * 2) / 2.0, "bold": st["bold"],
                      "italic": st["italic"], "font": st["font"], "color": st["color"],
                      "x0": None, "x1": None, "top": None, "bottom": None, "page": 0,
                      "align": align_map.get(al if al is not None else 0, "left"), "table": in_table})

    def walk_table(tbl):
        for row in tbl.rows:
            cells = []
            for c in row.cells:
                if not cells or cells[-1]._tc is not c._tc:
                    cells.append(c)
            has_img = any(c._tc.xpath(".//a:blip") for c in cells)
            if has_img:                                           # header table: logo | text | logo
                n = len(cells)
                for ci, c in enumerate(cells):
                    pos = "left" if ci == 0 else "right" if ci == n - 1 else "center"
                    for p in c.paragraphs:
                        para_images(p, force_pos=pos if n > 1 else None)
                        emit_par(p, in_table=False)
            else:
                texts = [" ".join(c.text.split()) for c in cells]
                texts = [t for t in texts if t]
                if not texts:
                    continue
                first_par = next((p for c in cells for p in c.paragraphs if p.text.strip()), None)
                st = _docx_run_style(first_par, default_size) if first_par is not None else {"size": default_size, "bold": False, "italic": False, "font": "", "color": None}
                lines.append({"text": " | ".join(texts), "size": round(st["size"] * 2) / 2.0, "bold": st["bold"],
                              "italic": st["italic"], "font": st["font"], "color": st["color"], "x0": None,
                              "x1": None, "top": None, "bottom": None, "page": 0, "align": "left", "table": True})

    # images placed in the page header part count too
    if sec is not None:
        try:
            for p in sec.header.paragraphs:
                para_images(p)
                emit_par(p)
            for t in sec.header.tables:
                walk_table(t)
        except Exception:
            pass

    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            par = Paragraph(child, document)
            para_images(par)
            emit_par(par)
        elif tag == "tbl":
            walk_table(Table(child, document))

    # keep only logos from the top of the document (first ~14 lines worth)
    fonts = Counter(l["font"] for l in lines if l["font"])
    return {"source": "docx", "lines": lines, "logos_raw": logos[:3], "page_w": page_w, "page_h": page_h,
            "images_bbox": [], "hrules": [], "rects": [], "page_img": None, "margin_in": margin_in,
            "docx_font": fonts.most_common(1)[0][0] if fonts else "", "docx_default_size": default_size}


# ===========================================================================
# 2. Understanding the lines
# ===========================================================================

def _labels_in(text: str) -> List[Tuple[str, str, int, int]]:
    """Return [(key, printed_label, start, end_of_label)] for every 'Label:' found in the line."""
    out = []
    for m in _LABEL_RE.finditer(text):
        key = next((k for k, _p in _LABEL_DEFS if m.group(k)), None)
        if key:
            out.append((key, m.group(1).strip(), m.start(), m.end()))
    return out


def _is_question_start(text: str) -> bool:
    return bool(_RE_Q_PREFIX.match(text) or (_RE_NUM.match(text) and len(text.split()) > 3))


def _header_end(lines: List[Dict[str, Any]]) -> int:
    """Index of the first line that is no longer part of the institution header."""
    centered = sum(1 for l in lines[:12] if l["align"] == "center")
    for i, l in enumerate(lines):
        t = l["text"]
        if i > 0 and (_is_question_start(t) or _RE_SECTION.match(t) or _RE_INSTR.match(t)):
            return i
        labs = _labels_in(t)
        stop_labels = [x for x in labs if x[0] in _STOP_META_KEYS]
        if i > 0 and (len(labs) >= 2 or stop_labels) and (t.strip().lower() != "") and l.get("table", False) is False:
            if l["align"] != "center" or centered < 2 or len(stop_labels) >= 2 or (stop_labels and labs[0][2] == 0 and l["align"] != "center"):
                return i
        if i > 0 and l.get("table") and labs:
            return i
        if i >= 14:
            return i
    return min(len(lines), 14)


def _classify_header(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign a role to every header line while keeping its exact style and order."""
    sizes = [l["size"] for l in lines] or [12]
    big = max(sizes)
    roles_used = set()
    out = []
    for idx, l in enumerate(lines):
        t = l["text"]
        low = t.lower()
        role = "other"
        non_latin = len(_REGIONAL_RE.findall(t)) / max(1, len(re.sub(r"\s", "", t)))
        if non_latin > 0.4:
            role = "regional_title"
        elif "exam_title" not in roles_used and not re.search(_ORG_WORDS, low) and re.search(_EXAM_WORDS, low) \
                and (t.isupper() or l["bold"] or l["size"] >= big * 0.8):
            role = "exam_title"
        elif re.search(_YEAR_WORDS, low) and "year_semester" not in roles_used and not re.search(_ORG_WORDS, low):
            role = "year_semester"
        elif re.search(_AFFIL_WORDS, low) and "affiliation" not in roles_used and l["size"] <= big * 0.85:
            role = "affiliation"
        elif re.search(_TAGLINE_WORDS, low) and l["size"] < big * 0.9 and "tagline" not in roles_used:
            role = "tagline"
        elif re.search(_SOCIETY_WORDS, low) and not re.search(r"institute|college|university|school", low) and "society" not in roles_used:
            role = "society"
        elif re.search(_PROG_WORDS, low) and "programme" not in roles_used and l["size"] <= big * 0.9:
            role = "programme"
        elif re.search(_ORG_WORDS, low) and "college" not in roles_used and l["size"] >= big * 0.7:
            role = "college"
        roles_used.add(role) if role != "other" else None
        out.append(dict(l, role=role))
    # biggest line fallback for the college name
    if "college" not in roles_used and out:
        j = max(range(len(out)), key=lambda k: (out[k]["size"], out[k]["bold"]))
        if out[j]["role"] == "other":
            out[j]["role"] = "college"
    return out


def _parse_meta(lines: List[Dict[str, Any]]) -> Tuple[List[List[Dict[str, Any]]], Dict[str, str]]:
    """Rows of meta cells (label as printed, key, default) plus detected values."""
    rows: List[List[Dict[str, Any]]] = []
    values: Dict[str, str] = {}
    for l in lines:
        t = l["text"].replace(" | ", "   ")
        labs = _labels_in(t)
        if not labs:
            continue
        row = []
        for n, (key, label, s, e) in enumerate(labs):
            end = labs[n + 1][2] if n + 1 < len(labs) else len(t)
            val = t[e:end].strip(" |:-–\t")
            printed = re.sub(r"\s+", " ", label).strip()
            cell = {"key": key, "label": printed[:1].upper() + printed[1:] if printed.islower() else printed}
            if key not in _DYNAMIC_KEYS and val:
                cell["default"] = val[:80]
            row.append(cell)
            if val:
                values.setdefault(key, val)
        # drop a 'code' cell that is just the tail of a 'course code' pair we already have
        keys = [c["key"] for c in row]
        row = [c for i, c in enumerate(row) if keys.index(c["key"]) == i or c["key"] in ("day",)]
        if row:
            rows.append(row)
    return rows, values


def _parse_duration(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    m = re.search(r"\d+(?:[:.]\d+)?\s*(?:hours?|hrs?\.?|h\b|minutes?|mins?\.?)", val, re.I)
    return m.group(0).strip() if m else None


def _parse_marks_value(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    m = re.search(r"\d{1,3}", val)
    return int(m.group(0)) if m else None


def _table_question(text: str) -> Optional[Dict[str, Any]]:
    """Handle 'Q.1 | Explain ... | CO1 | L2 | 5' rows produced from Word tables."""
    if " | " not in text:
        return None
    cells = [c.strip() for c in text.split(" | ") if c.strip()]
    if len(cells) < 2:
        return None
    m = re.match(r"^(?:Q(?:uestion)?\s*\.?\s*)?(\d{1,3})\s*[\.\)]?\s*(?:\(?([a-z])\)?)?$", cells[0], re.I)
    s = re.match(r"^\(?([a-z])\)$", cells[0], re.I)
    if not (m or s):
        return None
    body = max(cells[1:], key=lambda c: len(c.split()))
    marks = None
    for c in reversed(cells[1:]):
        if c is not body and re.fullmatch(r"\d{1,2}", c) and 1 <= int(c) <= 50:
            marks = int(c)
            break
    return {"group": int(m.group(1)) if m else None, "sub": (m.group(2) if m and m.group(2) else (s.group(1) if s else None)),
            "text": body, "marks": marks}


# ---- structure: sections, questions, OR ---------------------------------------

def _extract_structure(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Walk the body once and build sections of leaf questions."""
    toks: List[Dict[str, Any]] = []
    first_q_fmt: Dict[str, Any] = {}
    has_heading = any(_RE_SECTION.match(l["text"]) for l in lines)
    cur: Optional[Dict[str, Any]] = None

    def flush():
        nonlocal cur
        if cur is not None:
            cur["text"] = " ".join(cur.pop("buf")).strip()
            toks.append(cur)
        cur = None

    for l in lines:
        t = l["text"].strip()
        if not t:
            continue
        sm = _RE_SECTION.match(t)
        if sm and len(t.split()) <= 16 and not _is_question_start(t):
            flush()
            toks.append({"kind": "section", "name": f"{sm.group(1).title()} {sm.group(2).upper()}", "rest": sm.group(3).strip(),
                         "full": t, "style": l})
            continue
        if _RE_OR.match(t):
            flush()
            toks.append({"kind": "or"})
            continue
        tq = _table_question(t)
        if tq:
            flush()
            toks.append({"kind": "q", "group": tq["group"], "sub": tq["sub"], "text": tq["text"], "marks_row": tq["marks"], "style": l,
                         "label_raw": t.split(" | ")[0]})
            continue
        mq = _RE_Q_PREFIX.match(t) or _RE_NUM.match(t)
        if mq:
            flush()
            rest = mq.group(2)
            inline = _RE_SUB.match(rest) or None
            if not first_q_fmt:
                first_q_fmt = {"raw": t[:14], "kind": "group", "sub_raw": inline.group(0)[:4] if inline else None}
            cur = {"kind": "q", "group": int(mq.group(1)), "sub": inline.group(1).lower() if inline else None,
                   "buf": [inline.group(2) if inline else rest], "style": l, "label_raw": t[:mq.start(2)] if mq.start(2) > 0 else t[:6]}
            continue
        ms = _RE_SUB.match(t) or _RE_ROMAN.match(t)
        if ms and toks is not None and (cur is not None or any(x["kind"] == "q" for x in toks)):
            flush()
            if first_q_fmt and not first_q_fmt.get("sub_raw"):
                first_q_fmt["sub_raw"] = t[:4]
            cur = {"kind": "q", "group": None, "sub": ms.group(1).lower(), "buf": [ms.group(2)], "style": l, "label_raw": t[:ms.start(2)]}
            continue
        if _RE_ONLY_MARKS.match(t) and cur is not None:
            cur["buf"].append(t)
            continue
        if cur is not None:
            cur["buf"].append(t)
        elif toks and toks[-1]["kind"] == "or":           # un-numbered alternative right after "OR"
            cur = {"kind": "q", "group": None, "sub": None, "buf": [t], "style": l, "label_raw": ""}
        else:
            toks.append({"kind": "text", "text": t, "style": l})
    flush()

    # ---- assemble slots ---------------------------------------------------------
    sections: List[Dict[str, Any]] = []
    sec: Optional[Dict[str, Any]] = None
    pending_or = False
    alt_target: Optional[Dict[str, Any]] = None      # section whose slots the current group is an alternative to
    alt_cursor = 0
    current_group_no = None

    def new_section(name, instr="", heading=False):
        nonlocal sec
        sec = {"name": name, "instr": instr, "slots": [], "heading": heading, "stem": ""}
        sections.append(sec)

    qtoks = [t for t in toks if t["kind"] == "q"]
    for i, t in enumerate(qtoks):
        if t["group"] is not None and not t["sub"] and i + 1 < len(qtoks) and qtoks[i + 1]["sub"] and qtoks[i + 1]["group"] is None:
            t["is_stem"] = True

    for t in toks:
        k = t["kind"]
        if k == "section":
            new_section(t["name"], t["rest"], heading=True)
            alt_target = None
            pending_or = False
            continue
        if k == "text":
            if sec is not None and not sec["slots"] and len(t["text"].split()) > 2:
                sec["instr"] = (sec["instr"] + " " + t["text"]).strip()
            continue
        if k == "or":
            pending_or = True
            continue

        marks, clean = _find_marks(t.get("text", ""))
        if marks is None and t.get("marks_row"):
            marks = t["marks_row"]
        new_group = t["group"] is not None
        if new_group:
            current_group_no = t["group"]
            if pending_or and not has_heading and sections:
                alt_target, alt_cursor = sections[-1], 0          # "Q.2 ... OR Q.3 ..." : Q.3 is the choice for Q.2
            else:
                alt_target = None
                if not has_heading or sec is None:
                    new_section(f"Question {t['group']}")
            if alt_target is not None:
                pending_or = False
        if sec is None:
            new_section("Questions", heading=True)

        if t.get("is_stem"):
            if alt_target is None:
                sec["stem"] = clean
            pending_or = False
            continue
        if alt_target is not None:                                   # leaves of an alternative group
            if alt_cursor < len(alt_target["slots"]) and alt_target["slots"][alt_cursor].get("or") is None:
                alt_target["slots"][alt_cursor]["or"] = {"marks": marks, "text": clean}
            alt_cursor += 1
            continue
        if pending_or and sec["slots"] and sec["slots"][-1].get("or") is None:
            sec["slots"][-1]["or"] = {"marks": marks, "text": clean}  # "... OR ..." inside one question
            pending_or = False
            continue
        pending_or = False
        sec["slots"].append({"text": clean, "marks": marks, "style": t["style"], "sub": t.get("sub"),
                             "group": current_group_no, "or": None})

    # fill missing marks using the stem marks / neighbours
    for s in sections:
        known = [x["marks"] for x in s["slots"] if x["marks"]]
        fallback = Counter(known).most_common(1)[0][0] if known else None
        for x in s["slots"]:
            if not x["marks"]:
                x["marks"] = fallback
    sections = [s for s in sections if s["slots"]]
    return {"sections": sections, "has_heading": has_heading, "first_q": first_q_fmt}


def _numbering_format(first_q: Dict[str, Any], uses_sub: bool) -> Dict[str, Any]:
    raw = (first_q.get("raw") or "").strip()
    prefix = "Q"
    if re.match(r"(?i)question", raw):
        prefix = "Question "
    elif re.match(r"(?i)q\s*\.", raw):
        prefix = "Q."
    elif re.match(r"(?i)q\s*\d", raw):
        prefix = "Q"
    elif re.match(r"\d", raw):
        prefix = ""
    sub = "paren"
    sraw = (first_q.get("sub_raw") or "").strip()
    if re.match(r"^\([a-z]\)", sraw, re.I):
        sub = "paren"
    elif re.match(r"^[a-z]\)", sraw, re.I):
        sub = "close"
    elif re.match(r"^[a-z]\.", sraw, re.I):
        sub = "dot"
    return {"prefix": prefix, "sub": sub}


# ===========================================================================
# 3. Assemble the template
# ===========================================================================

def _marks_format(lines: List[Dict[str, Any]]) -> str:
    for l in lines:
        m = re.search(r"([\[\(]\s*\d{1,2}\s*(?:marks?|m)?\s*[\]\)])\s*$", l["text"], re.I)
        if m:
            s = m.group(1).lower()
            if "marks" in s:
                return "(N Marks)" if s.startswith("(") else "[N Marks]"
            if s.startswith("["):
                return "[N]"
            return "(N)"
        if re.search(r"\b\d{1,2}\s*m\s*$", l["text"], re.I):
            return "NM"
    return "[N]"


def _style_summary(doc: Dict[str, Any], body_lines: List[Dict[str, Any]], header: List[Dict[str, Any]],
                   sections_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
    fonts = Counter(l["font"] for l in body_lines if l.get("font"))
    font_name = (doc.get("docx_font") or (fonts.most_common(1)[0][0] if fonts else "")) or ""
    family = _family_of(font_name) or "serif"
    sizes = [l["size"] for l in body_lines if l["size"]]
    base = sorted(sizes)[len(sizes) // 2] if sizes else 11.0
    base = max(8.0, min(14.0, base))
    margin = doc.get("margin_in")
    if margin is None:
        xs = [l["x0"] for l in body_lines if l.get("x0") is not None]
        margin = (sorted(xs)[max(0, int(len(xs) * 0.1))] / 72.0) if xs else 0.8
    margin = round(max(0.4, min(1.5, margin)), 2)

    border = "none"
    if doc.get("hrules") and header:
        hb = max((l["bottom"] for l in header if l.get("bottom") is not None), default=None)
        if hb is not None:
            for (x0, top, x1) in doc["hrules"]:
                if hb - 4 <= top <= hb + 28 and (x1 - x0) > 0.5 * doc["page_w"]:
                    border = "bottom"
                    break
    sec_style = {"align": "left", "bold": True, "uppercase": False}
    heads = [s["style"] for s in sections_raw if s.get("style")]
    if heads:
        sec_style = {"align": Counter(h["align"] for h in heads).most_common(1)[0][0],
                     "bold": sum(1 for h in heads if h["bold"]) >= len(heads) / 2,
                     "uppercase": sum(1 for h in heads if h["text"].isupper()) >= len(heads) / 2}
    return {"font_family": family, "font_name": _clean_font(font_name), "base_font_size_pt": base,
            "page_size": "Letter" if abs(doc["page_w"] - 612) < 8 else "A4", "margin_in": margin,
            "header_border": border, "section_title": sec_style}


def _logos_from_doc(doc: Dict[str, Any], header_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page_w = doc["page_w"]
    if doc["source"] == "docx":
        for lg in doc["logos_raw"]:
            url = _encode_logo(lg["img"])
            if url:
                out.append({"data_url": url, "position": lg["position"],
                            "height_pt": round(min(max(lg["height_pt"] or 56, 28), 110), 1)})
        return out[:2]

    img = doc.get("page_img")
    if img is None:
        return out
    scale = RENDER_DPI / 72.0
    hb = max((l["bottom"] for l in header_lines if l.get("bottom") is not None), default=130.0)
    zone = min(doc["page_h"] * 0.33, hb + 30)
    boxes: List[Tuple[int, int, int, int]] = []
    for (x0, top, x1, bottom) in doc.get("images_bbox", []):           # embedded pictures
        w, h = x1 - x0, bottom - top
        if top < zone and 22 <= w <= 0.4 * page_w and 22 <= h <= 0.2 * doc["page_h"]:
            boxes.append((int(x0 * scale), int(top * scale), int(x1 * scale), int(bottom * scale)))
    if not boxes:                                                        # vector / scanned logos
        tboxes = [(l["x0"], l["top"], l["x1"], l["bottom"]) for l in doc["lines"] if l["page"] == 0 and l.get("x0") is not None]
        boxes = _find_blobs(img, tboxes, zone, scale)
    boxes = sorted(boxes, key=lambda b: b[0])
    if len(boxes) > 2:
        boxes = [boxes[0], boxes[-1]]
    from PIL import ImageDraw
    if boxes and doc.get("images_bbox"):
        # picture logos can be overlapped by header text: paint recognised text white inside the crop areas
        img = img.copy()
        draw = ImageDraw.Draw(img)
        for l in doc["lines"]:
            if l["page"] != 0 or l.get("x0") is None:
                continue
            lb = (l["x0"] * scale, l["top"] * scale, l["x1"] * scale, l["bottom"] * scale)
            for b in boxes:
                ix0, iy0, ix1, iy1 = max(lb[0], b[0]), max(lb[1], b[1]), min(lb[2], b[2]), min(lb[3], b[3])
                if ix1 > ix0 and iy1 > iy0:
                    draw.rectangle((ix0, iy0, ix1, iy1), fill=(255, 255, 255))
    for b in boxes:
        clip = _clip_logo(img, b)
        if clip is None:
            continue
        url = _encode_logo(clip)
        if not url:
            continue
        cx = (b[0] + b[2]) / 2.0 / scale
        out.append({"data_url": url, "position": _position_of(cx, page_w),
                    "height_pt": round(min(max((b[3] - b[1]) / scale, 28), 110), 1)})
    return out


def extract_template(filename: str, data: bytes) -> Dict[str, Any]:
    name = (filename or "paper").strip()
    low = name.lower()
    if not low.endswith(SUPPORTED_EXT):
        raise ValueError("Unsupported file. Upload a PDF, Word (.docx) file, or a photo/scan (PNG, JPG).")
    try:
        if low.endswith(".pdf"):
            doc = _load_pdf(data)
        elif low.endswith(".docx"):
            doc = _load_docx(data)
        else:
            doc = _load_image(data)
    except ValueError:
        raise
    except Exception:
        raise ValueError("That file could not be opened. Please check it is a valid PDF, Word (.docx) or image file.")

    lines = [l for l in doc.get("lines", []) if l["text"].strip()]
    # drop page-number / footer noise
    lines = [l for l in lines if not re.fullmatch(r"(?i)(page\s*)?\d+(\s*(of|/)\s*\d+)?", l["text"].strip())]
    if len(lines) < 5:
        raise ValueError("Could not find enough text in this file to build a template.")

    h_end = _header_end(lines)
    header_raw = [l for l in lines[:h_end] if l["page"] == 0
                  and (len(re.findall(r"\w", l["text"])) >= 3 or _REGIONAL_RE.search(l["text"]))]
    header = _classify_header(header_raw)
    rest = lines[h_end:]

    # --- meta block and instructions ------------------------------------------------
    meta_lines, instr_lines, body_lines = [], [], []
    mode = "meta"
    for l in rest:
        t = l["text"]
        if mode == "meta":
            im = _RE_INSTR.match(t)
            if im:
                mode = "instr"
                if im.group(1).strip():
                    instr_lines.append(im.group(1).strip())
                continue
            if _is_question_start(t) or _RE_SECTION.match(t):
                mode = "body"
                body_lines.append(l)
                continue
            if _labels_in(t):
                meta_lines.append(l)
                continue
            # un-labelled line between meta and questions: treat as instruction text
            instr_lines.append(t)
            continue
        if mode == "instr":
            if _is_question_start(t) and (_find_marks(t)[0] is not None or _RE_Q_PREFIX.match(t)) or _RE_SECTION.match(t):
                mode = "body"
                body_lines.append(l)
                continue
            if _RE_NUM.match(t) and not _find_marks(t)[0] and len(t.split()) <= 40:
                instr_lines.append(re.sub(r"^\s*\d+[\.\)]\s*", "", t))
                continue
            if re.match(r"^\s*[•\-\*▪●]\s+", t):
                instr_lines.append(re.sub(r"^\s*[•\-\*▪●]\s+", "", t))
                continue
            if instr_lines and not _is_question_start(t) and not _RE_SUB.match(t):
                instr_lines[-1] = (instr_lines[-1] + " " + t).strip()
                continue
            mode = "body"
        body_lines.append(l)

    meta_rows, meta_values = _parse_meta(meta_lines)
    # header lines can also carry labels that matter (e.g. 'Max Marks: 65' on a centred line) - keep them only as text
    structure = _extract_structure(body_lines)
    secs_raw = structure["sections"]
    if not secs_raw:
        raise ValueError("Could not find any numbered questions in this paper, so the section structure could not be copied. "
                         "The header and logo can still be copied from a paper with questions on it.")

    uses_sub = (not structure["has_heading"]) and any(s["slots"] and any(x["sub"] for x in s["slots"]) for s in secs_raw)
    group_mode = not structure["has_heading"]
    numbering_style = "sub" if group_mode else "sequential"
    if group_mode and not uses_sub and len(secs_raw) > 6:
        numbering_style = "sequential"
    fmt = _numbering_format(structure["first_q"], uses_sub)

    sections = []
    for i, s in enumerate(secs_raw, 1):
        slots = s["slots"]
        marks = [int(x["marks"] or 5) for x in slots]
        choices = [bool(x.get("or")) for x in slots]
        or_marks = [int((x.get("or") or {}).get("marks") or m) for x, m in zip(slots, marks)]
        lvls = sorted({_detect_bloom(x["text"], x["marks"]) for x in slots} | {_detect_bloom(x["or"]["text"], x["or"].get("marks")) for x in slots if x.get("or")})
        if len(lvls) == 1:
            n = int(lvls[0][1])
            lvls = sorted({lvls[0], f"L{min(6, n + 1)}", f"L{max(1, n - 1)}"})
        stem = (s.get("stem") or "").strip()
        instr = (s.get("instr") or "").strip() or stem
        if not instr:
            instr = "Answer all questions." if not any(choices) else "Answer all questions. Internal choice (OR) is provided where indicated."
        pm = Counter(marks).most_common(1)[0][0]
        sections.append({
            "id": f"sec_{i}",
            "name": (s["name"] if s.get("heading") else f"Question {i}") + (f" - {instr[:60]}" if False else ""),
            "instructions": instr[:240],
            "type": "choice" if any(choices) else "compulsory",
            "question_count": len(slots), "marks_per_question": pm,
            "question_marks": marks, "question_choices": choices, "or_marks": or_marks,
            "total_section_marks": sum(marks), "allowed_levels": lvls or ["L2", "L3"],
            "has_internal_choice": any(choices),
        })

    declared_marks = _parse_marks_value(meta_values.get("marks"))
    paper_marks = sum(sum(s["question_marks"]) for s in sections)
    warnings: List[str] = []
    total_marks = declared_marks or paper_marks
    if declared_marks and declared_marks != paper_marks:
        warnings.append(f"The paper says {declared_marks} marks but the questions add up to {paper_marks}. "
                        "Check the sections below (questions to attempt 'any N' are counted fully).")
    duration = _parse_duration(meta_values.get("duration")) or "02:00 Hrs."
    if not _parse_duration(meta_values.get("duration")):
        warnings.append("Duration was not found; set it below.")

    # --- header output -----------------------------------------------------------------
    header_out = []
    for h in header:
        header_out.append({"text": h["text"][:200], "role": h["role"], "size": h["size"], "bold": h["bold"],
                           "italic": h["italic"], "align": h["align"], "color": h.get("color"),
                           "uppercase": h["text"].isupper()})
    profile = {"society": "", "college": "", "tagline": "", "affiliation": "", "regional_title": "",
               "programme": "", "year_semester": "", "exam_title": ""}
    for h in header_out:
        if h["role"] in profile and not profile[h["role"]]:
            profile[h["role"]] = h["text"]
    if not profile["college"]:
        warnings.append("The college name could not be recognised. Check the header lines below.")
    profile["logo_text"] = ""

    style = _style_summary(doc, body_lines or lines, header_raw, [{"style": s["style"]} for s in
                           [t for t in _tok_sections(body_lines)]])
    style["marks_format"] = _marks_format(body_lines)
    style["meta_align"] = "spread"

    logos = _logos_from_doc(doc, header_raw)
    if not logos:
        warnings.append("No logo was detected. You can add one in the review step.")

    # roll number box
    all_keys = {c["key"] for r in meta_rows for c in r}
    college = profile["college"] or "Custom College"
    exam = profile["exam_title"] or "Examination"
    template = {
        "id": f"custom_{uuid.uuid4().hex[:10]}",
        "name": f"{college.title() if college.isupper() else college} - {exam.title() if exam.isupper() else exam}"[:120],
        "duration": duration, "total_marks": total_marks,
        "numbering_style": numbering_style, "numbering_format": fmt,
        "college_profile": profile, "header_lines": header_out, "logos": logos,
        "meta_layout": meta_rows, "show_roll_box": "roll" in all_keys,
        "style": style,
        "instructions": [i[:300] for i in instr_lines if i.strip()][:14],
        "sections": sections, "is_custom": True, "source_file": name,
    }
    return {
        "template": template, "warnings": warnings, "source": doc["source"],
        "stats": {"header_lines": len(header_out), "logos": len(logos), "sections": len(sections),
                  "questions": sum(s["question_count"] for s in sections),
                  "or_questions": sum(sum(1 for c in s["question_choices"] if c) for s in sections),
                  "instructions": len(template["instructions"]), "meta_rows": len(meta_rows)},
    }


def _tok_sections(body_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for l in body_lines:
        if _RE_SECTION.match(l["text"]):
            out.append({"style": l})
    return out
