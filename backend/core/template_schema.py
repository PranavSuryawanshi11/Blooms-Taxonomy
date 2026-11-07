"""
Template schema validation. Every college template saved by a user passes through `sanitize_template`,
so the data that later reaches the paper header / Word export is always well-formed and bounded.
"""

import re
import io
import base64
import uuid
from typing import Any, Dict, List, Optional

from PIL import Image

from config import BLOOM_ORDER

MAX_LOGO_BYTES = 220 * 1024
HEADER_ROLES = {"society", "college", "tagline", "affiliation", "regional_title", "programme",
                "year_semester", "exam_title", "other"}
META_KEYS = {"code", "course", "duration", "marks", "roll", "date", "day", "class", "branch",
             "semester", "division", "batch", "other"}
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_DATA_URL_RE = re.compile(r"^data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+$")


def _s(v: Any, n: int) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v if v is not None else "")).strip()[:n]


def _num(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


def _logo(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    url = raw.get("data_url")
    if not isinstance(url, str) or len(url) > MAX_LOGO_BYTES * 4 // 3 + 64 or not _DATA_URL_RE.match(url):
        return None
    try:
        blob = base64.b64decode(url.split("base64,", 1)[1], validate=True)
        if len(blob) > MAX_LOGO_BYTES:
            return None
        im = Image.open(io.BytesIO(blob))
        im.verify()
        if im.width > 2000 or im.height > 2000:
            return None
    except Exception:
        return None
    pos = raw.get("position") if raw.get("position") in ("left", "center", "right") else "left"
    return {"data_url": url, "position": pos, "height_pt": round(_num(raw.get("height_pt"), 20, 140, 60), 1)}


def sanitize_template(raw: Dict[str, Any], template_id: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Template data is invalid.")
    out: Dict[str, Any] = {}
    out["id"] = template_id or f"custom_{uuid.uuid4().hex[:10]}"
    out["name"] = _s(raw.get("name"), 120) or "My College Template"
    out["duration"] = _s(raw.get("duration"), 24) or "02:00 Hrs."
    out["total_marks"] = int(_num(raw.get("total_marks"), 1, 500, 60))
    out["numbering_style"] = "sub" if raw.get("numbering_style") == "sub" else "sequential"
    nf = raw.get("numbering_format") if isinstance(raw.get("numbering_format"), dict) else {}
    out["numbering_format"] = {
        "prefix": nf.get("prefix") if nf.get("prefix") in ("Q.", "Q", "Question ", "") else "Q.",
        "sub": nf.get("sub") if nf.get("sub") in ("paren", "close", "dot") else "paren",
    }

    # ---- header lines (the single source of truth for the college profile) ----
    lines: List[Dict[str, Any]] = []
    for h in (raw.get("header_lines") or [])[:14]:
        if not isinstance(h, dict) or not _s(h.get("text"), 200):
            continue
        lines.append({
            "text": _s(h.get("text"), 200),
            "role": h.get("role") if h.get("role") in HEADER_ROLES else "other",
            "size": round(_num(h.get("size"), 6, 40, 11) * 2) / 2,
            "bold": bool(h.get("bold")), "italic": bool(h.get("italic")),
            "uppercase": bool(h.get("uppercase")),
            "align": h.get("align") if h.get("align") in ("left", "center", "right") else "center",
            "color": h.get("color") if isinstance(h.get("color"), str) and _COLOR_RE.match(h["color"]) else None,
        })
    out["header_lines"] = lines
    profile = {k: "" for k in ("society", "college", "tagline", "affiliation", "regional_title",
                              "programme", "year_semester", "exam_title")}
    for h in lines:
        if h["role"] in profile and not profile[h["role"]]:
            profile[h["role"]] = h["text"]
    profile["logo_text"] = ""
    out["college_profile"] = profile

    out["logos"] = [lg for lg in (_logo(x) for x in (raw.get("logos") or [])[:2]) if lg]

    # ---- meta rows ----
    rows = []
    for row in (raw.get("meta_layout") or [])[:6]:
        cells = []
        for c in (row or [])[:5]:
            if not isinstance(c, dict):
                continue
            key = c.get("key") if c.get("key") in META_KEYS else "other"
            cell = {"key": key, "label": _s(c.get("label"), 30) or key.title()}
            if c.get("default"):
                cell["default"] = _s(c.get("default"), 80)
            cells.append(cell)
        if cells:
            rows.append(cells)
    out["meta_layout"] = rows
    out["show_roll_box"] = bool(raw.get("show_roll_box")) or any(c["key"] == "roll" for r in rows for c in r)

    # ---- style ----
    st = raw.get("style") if isinstance(raw.get("style"), dict) else {}
    sec_title = st.get("section_title") if isinstance(st.get("section_title"), dict) else {}
    out["style"] = {
        "font_family": "sans" if st.get("font_family") == "sans" else "serif",
        "font_name": _s(st.get("font_name"), 40),
        "base_font_size_pt": _num(st.get("base_font_size_pt"), 8, 16, 11),
        "page_size": "Letter" if st.get("page_size") == "Letter" else "A4",
        "margin_in": _num(st.get("margin_in"), 0.4, 1.6, 0.8),
        "header_border": st.get("header_border") if st.get("header_border") in ("none", "bottom", "box") else "bottom",
        "section_title": {
            "align": sec_title.get("align") if sec_title.get("align") in ("left", "center", "right") else "left",
            "bold": bool(sec_title.get("bold", True)), "uppercase": bool(sec_title.get("uppercase")),
        },
        "marks_format": st.get("marks_format") if st.get("marks_format") in ("[N]", "(N)", "[N Marks]", "(N Marks)", "NM") else "[N]",
    }

    out["instructions"] = [_s(i, 300) for i in (raw.get("instructions") or [])[:14] if _s(i, 300)]

    # ---- sections ----
    sections = []
    for i, s in enumerate((raw.get("sections") or [])[:12], 1):
        if not isinstance(s, dict):
            continue
        n = int(_num(s.get("question_count"), 1, 26, 1))
        dflt = int(_num(s.get("marks_per_question"), 1, 100, 5))
        marks = []
        for q in range(n):
            arr = s.get("question_marks") if isinstance(s.get("question_marks"), list) else []
            marks.append(int(_num(arr[q] if q < len(arr) else dflt, 1, 100, dflt)))
        ch = s.get("question_choices") if isinstance(s.get("question_choices"), list) else []
        choices = [bool(ch[q]) if q < len(ch) else False for q in range(n)]
        om = s.get("or_marks") if isinstance(s.get("or_marks"), list) else []
        or_marks = [int(_num(om[q] if q < len(om) else marks[q], 1, 100, marks[q])) for q in range(n)]
        levels = [l for l in (s.get("allowed_levels") or []) if l in BLOOM_ORDER] or ["L2", "L3"]
        sections.append({
            "id": f"sec_{i}", "name": _s(s.get("name"), 120) or f"Question {i}",
            "instructions": _s(s.get("instructions"), 240),
            "type": "choice" if any(choices) else "compulsory",
            "question_count": n, "marks_per_question": dflt, "question_marks": marks,
            "question_choices": choices, "or_marks": or_marks, "total_section_marks": sum(marks),
            "allowed_levels": levels, "has_internal_choice": any(choices),
        })
    if not sections:
        raise ValueError("A template needs at least one section with questions.")
    out["sections"] = sections
    out["is_custom"] = True
    out["source_file"] = _s(raw.get("source_file"), 120)
    return out


def paper_style_payload(tmpl: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The part of a template that the paper sheet and Word export need to reproduce the college layout."""
    if not tmpl or not (tmpl.get("header_lines") or tmpl.get("logos") or tmpl.get("meta_layout")):
        return None
    return {
        "header_lines": tmpl.get("header_lines") or [], "logos": tmpl.get("logos") or [],
        "meta_layout": tmpl.get("meta_layout") or [], "show_roll_box": tmpl.get("show_roll_box", False),
        "style": tmpl.get("style") or {}, "template_name": tmpl.get("name", ""),
    }
