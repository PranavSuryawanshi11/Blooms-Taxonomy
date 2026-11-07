"""
Single source of truth for the Academic Year (A.Y.) printed on a question paper.

The A.Y. is entered once in the UI and applied to every place it can appear:
the college header line (e.g. "Year: II / Semester IV (Exam Year: 2024-2025)"),
the exam title (e.g. "FINAL EXAMINATION (2024-2025)") and the layout session line.
"""
import copy
import re
from typing import Any, Dict, Optional

# 2025-2026, 2025-26, 2025/26, 2025 - 2026 ...
AY_RE = re.compile(r"\b20\d\d\s*[-\u2013\u2014/]\s*(?:20)?\d\d\b")


def normalize_ay(value: Any) -> str:
    """Trim and tidy the user's A.Y. text. Empty string when nothing was given."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def replace_ay(text: str, ay: str) -> str:
    """Swap any year range inside `text` for `ay`; text without a year range is returned unchanged."""
    if not text or not ay:
        return text
    return AY_RE.sub(lambda _m: ay, text)


def ensure_ay(text: str, ay: str) -> str:
    """Like replace_ay, but appends '(A.Y.: ...)' when the text has no year range at all."""
    if not ay:
        return text
    text = text or ""
    if AY_RE.search(text):
        return replace_ay(text, ay)
    return f"{text} (A.Y.: {ay})".strip()


def apply_academic_year_to_config(exam_config: Dict[str, Any], ay: str, year_semester: str = "") -> Dict[str, Any]:
    """Return a copy of exam_config whose college header / exam title carry the given A.Y."""
    ay = normalize_ay(ay)
    year_semester = normalize_ay(year_semester)
    cfg = dict(exam_config or {})
    if not ay and not year_semester:
        return cfg
    profile = copy.deepcopy(cfg.get("college_profile") or {})   # never mutate the shared built-in templates
    if profile:
        if year_semester:      # user typed "Year: III / Semester V": it replaces the template's wording
            profile["year_semester"] = f"{year_semester} (A.Y.: {ay})" if ay else year_semester
        elif ay:
            profile["year_semester"] = ensure_ay(profile.get("year_semester", ""), ay)
        if ay and profile.get("exam_title"):
            profile["exam_title"] = replace_ay(profile["exam_title"], ay)
        cfg["college_profile"] = profile
    if ay and cfg.get("exam_title"):
        cfg["exam_title"] = replace_ay(cfg["exam_title"], ay)
    cfg["academic_year"] = ay
    cfg["year_semester"] = year_semester
    return cfg


def apply_academic_year_to_style(style_payload: Optional[Dict[str, Any]], ay: str, year_semester: str = "") -> Optional[Dict[str, Any]]:
    """
    Custom / imported college templates draw their header from `header_lines` (plain text), so the A.Y. and
    Year/Semester typed in the app must be stamped on those lines too. Returns an updated copy.
    """
    ay = normalize_ay(ay)
    year_semester = normalize_ay(year_semester)
    if not style_payload or not (ay or year_semester):
        return style_payload
    out = copy.deepcopy(style_payload)
    lines = out.get("header_lines") or []
    ys_text = (f"{year_semester} (A.Y.: {ay})" if ay else year_semester) if year_semester else ""
    found_ys = False
    for h in lines:
        role = h.get("role")
        if role == "year_semester":
            found_ys = True
            if ys_text:
                h["text"] = ys_text
            elif ay:
                h["text"] = ensure_ay(h.get("text", ""), ay)
        elif role == "exam_title" and ay:
            h["text"] = replace_ay(h.get("text", ""), ay)
    if not found_ys and lines:
        text = ys_text or (f"A.Y.: {ay}" if ay else "")
        if text:
            lines.append({"text": text, "role": "year_semester", "size": 10.5, "bold": False, "italic": False,
                          "uppercase": False, "align": "center", "color": None})
    out["header_lines"] = lines
    return out
