"""
Paper Structure Layer
Optional refinements that run AROUND the (unchanged) blueprint builder and question generator:

  * apply_unit_plan          - unit-wise marks weightage + unit-wise Bloom levels
  * apply_or_configuration   - choose which questions get an OR alternative and set the OR marks
  * apply_numbering          - label questions as Q.1 (a), (b), (c) ... instead of Q1, Q2, Q3
  * summarize_units          - per-unit marks actually used in the final paper

Every function is a no-op unless the faculty member supplied the matching option, so papers built
without these options are identical to the original generator output.
"""

import copy
from typing import Any, Dict, List, Optional

from config import BLOOM_LEVELS, BLOOM_ORDER


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _unit_lookup(syllabus: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {int(u.get("unit_num", i + 1)): u for i, u in enumerate(syllabus.get("units", []))}


def _co_description(syllabus: Dict[str, Any], co_id: str, unit: Dict[str, Any]) -> str:
    co_map = {c["id"]: c.get("description", "") for c in syllabus.get("course_outcomes", [])}
    return co_map.get(co_id, f"Understand and apply core principles in {unit.get('title', 'Module')}.")


def _make_or_slot(slot: Dict[str, Any], unit: Optional[Dict[str, Any]], marks: Optional[int] = None) -> Dict[str, Any]:
    """Build the OR alternative of a slot (same unit / Bloom level / CO, different topic)."""
    topics = (unit or {}).get("topics") or [slot.get("topic", "Core Topic")]
    try:
        idx = topics.index(slot.get("topic"))
    except ValueError:
        idx = 0
    alt = topics[(idx + 1) % len(topics)] if len(topics) > 1 else slot.get("topic")
    return {
        "slot_id": f"{slot['slot_id']}_or",
        "display_num": f"{slot['display_num']} (OR)",
        "section_id": slot.get("section_id"),
        "marks": int(marks if marks else slot["marks"]),
        "bloom_level": slot["bloom_level"],
        "bloom_name": slot.get("bloom_name"),
        "unit_num": slot.get("unit_num"),
        "unit_title": slot.get("unit_title"),
        "topic": alt,
        "co": slot.get("co"),
        "co_description": slot.get("co_description"),
        "po": slot.get("po"),
        "pi_code": slot.get("pi_code"),
        "is_choice": True,
    }


def _closest_level(original: str, allowed: List[str]) -> str:
    oi = BLOOM_ORDER.index(original) if original in BLOOM_ORDER else 1
    return min(allowed, key=lambda l: (abs(BLOOM_ORDER.index(l) - oi), BLOOM_ORDER.index(l)))


def _clean_levels(levels) -> List[str]:
    return [l for l in (levels or []) if l in BLOOM_LEVELS]


# ---------------------------------------------------------------------------
# 1. unit-wise marks weightage and Bloom levels
# ---------------------------------------------------------------------------
def apply_unit_plan(blueprint: Dict[str, Any], syllabus: Dict[str, Any], unit_plan: Optional[Dict[str, Any]],
                    sections_config: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Re-assign blueprint slots to units so each unit receives (approximately) its requested share of marks,
    and restrict Bloom levels of a unit's questions to the levels ticked for that unit.
    A unit with NO Bloom level ticked is unrestricted (the default).
    """
    if not unit_plan or not unit_plan.get("units"):
        return blueprint
    units = _unit_lookup(syllabus)
    if not units:
        return blueprint

    weights: Dict[int, float] = {}
    levels: Dict[int, List[str]] = {}
    for entry in unit_plan["units"]:
        try:
            n = int(entry.get("unit_num"))
        except (TypeError, ValueError):
            continue
        if n not in units:
            continue
        try:
            w = float(entry.get("marks") or 0)
        except (TypeError, ValueError):
            w = 0.0
        if w > 0 and unit_plan.get("use_weightage", True):
            weights[n] = w
        lv = _clean_levels(entry.get("levels"))
        if lv:
            levels[n] = lv
    if not weights and not levels:
        return blueprint

    slots = [(si, slot) for si, sec in enumerate(blueprint.get("sections", [])) for slot in sec.get("slots", [])]
    total_marks = sum(s["marks"] for _si, s in slots) or 1

    # ---- assign units -------------------------------------------------------
    assignment: Dict[str, int] = {}
    if weights:
        wsum = sum(weights.values())
        remaining = {n: w / wsum * total_marks for n, w in weights.items()}
        for _si, slot in sorted(slots, key=lambda t: -t[1]["marks"]):      # big questions first
            candidates = sorted(remaining, key=lambda n: (-remaining[n], n))
            pick = candidates[0]
            lvl = slot["bloom_level"]
            for n in candidates:                      # prefer a unit whose chosen levels already fit this slot
                if remaining[n] >= slot["marks"] * 0.5 and (n not in levels or lvl in levels[n]):
                    pick = n
                    break
            assignment[slot["slot_id"]] = pick
            remaining[pick] -= slot["marks"]
    # ---- apply to slots ------------------------------------------------------
    topic_cursor: Dict[int, int] = {}
    pi_counter: Dict[int, int] = {}
    sec_allowed: Dict[int, List[str]] = {}
    for si, cfg in enumerate(sections_config or []):
        sec_allowed[si] = _clean_levels(cfg.get("allowed_levels")) or list(BLOOM_ORDER)

    for si, slot in slots:
        had_or = bool(slot.get("has_or_option") and slot.get("or_slot"))
        or_marks = slot["or_slot"]["marks"] if had_or else None
        un = assignment.get(slot["slot_id"], slot.get("unit_num"))
        unit = units.get(un)
        if unit is None:
            continue
        if slot["slot_id"] in assignment:
            topics = unit.get("topics") or ["Core Topic"]
            cur = topic_cursor.get(un, 0)
            topic_cursor[un] = cur + 1
            co_id = unit.get("co", f"CO{min(un, 5)}")
            k = pi_counter.get(un, 0)
            pi_counter[un] = k + 1
            slot.update({
                "unit_num": un,
                "unit_title": unit.get("title", ""),
                "topic": topics[cur % len(topics)],
                "co": co_id,
                "co_description": _co_description(syllabus, co_id, unit),
                "po": f"PO{min(un, 12)}",
                "pi_code": f"{un}.{(k % 3) + 1}",
            })
        # Bloom restriction for this unit
        if un in levels and slot["bloom_level"] not in levels[un]:
            allowed_here = [l for l in levels[un] if l in sec_allowed.get(si, BLOOM_ORDER)] or levels[un]
            new_lvl = _closest_level(slot["bloom_level"], allowed_here)
            slot["bloom_level"] = new_lvl
            slot["bloom_name"] = BLOOM_LEVELS[new_lvl]["name"]
        if had_or:
            slot["or_slot"] = _make_or_slot(slot, unit, or_marks)
    return blueprint


# ---------------------------------------------------------------------------
# 2. OR (internal choice) configuration
# ---------------------------------------------------------------------------
def apply_or_configuration(blueprint: Dict[str, Any], sections_config: List[Dict[str, Any]],
                           syllabus: Dict[str, Any]) -> Dict[str, Any]:
    """
    Faculty decide which questions get an OR alternative (`question_choices`) and enter the OR marks
    (`or_marks`). Sections without an explicit `question_choices` list keep the original behaviour.
    """
    units = _unit_lookup(syllabus)
    for si, sec in enumerate(blueprint.get("sections", [])):
        if si >= len(sections_config):
            break
        cfg = sections_config[si]
        choices = cfg.get("question_choices")
        or_marks = cfg.get("or_marks") if isinstance(cfg.get("or_marks"), list) else []
        if not isinstance(choices, list):
            continue
        for qi, slot in enumerate(sec.get("slots", [])):
            want = bool(choices[qi]) if qi < len(choices) else False
            if want:
                marks = None
                if qi < len(or_marks):
                    try:
                        marks = int(or_marks[qi])
                    except (TypeError, ValueError):
                        marks = None
                    if marks is not None and marks < 1:
                        marks = None
                slot["has_or_option"] = True
                slot["or_slot"] = _make_or_slot(slot, units.get(slot.get("unit_num")), marks)
            else:
                slot.pop("has_or_option", None)
                slot.pop("or_slot", None)
    return blueprint


# ---------------------------------------------------------------------------
# 3. numbering  Q.1 (a), (b), (c)
# ---------------------------------------------------------------------------
def _letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return s


def format_label(fmt: Optional[Dict[str, Any]], group: int, letter: Optional[str] = None) -> str:
    """Build a question label in the college's own style: Q.1 (a) / Q.1 a) / Q.1 a. / Q1 / 1 ..."""
    prefix = (fmt or {}).get("prefix", "Q.")
    sub = (fmt or {}).get("sub", "paren")
    base = f"{prefix}{group}"
    if letter is None:
        return base
    return {"paren": f"{base} ({letter})", "close": f"{base} {letter})", "dot": f"{base} {letter}."}.get(sub, f"{base} ({letter})")


def apply_numbering(blueprint: Dict[str, Any], style: Optional[str], fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    style 'sub'        -> each section is one numbered question Q.n with sub-questions (a), (b), (c) ...
    style 'sequential' -> legacy Q1, Q2, ... (re-labelled only when a college numbering format is supplied)
    `fmt` ({"prefix": "Q.", "sub": "paren|close|dot"}) copies the style of an uploaded college paper.
    """
    if style == "sub":
        for si, sec in enumerate(blueprint.get("sections", []), 1):
            slots = sec.get("slots", [])
            for qi, slot in enumerate(slots):
                letter = _letter(qi)
                slot["question_group"] = si
                slot["sub_label"] = letter
                slot["display_num"] = format_label(fmt, si, letter)
                if slot.get("or_slot"):
                    or_slot = slot["or_slot"]
                    or_slot["question_group"] = si
                    if len(slots) == 1:                       # single question with choice: Q.4 (a) OR Q.4 (b)
                        or_slot["sub_label"] = _letter(1)
                        or_slot["display_num"] = format_label(fmt, si, _letter(1))
                    else:
                        or_slot["sub_label"] = letter
                        or_slot["display_num"] = f"{slot['display_num']} (OR)"
        blueprint["numbering_style"] = "sub"
    elif fmt:
        n = 0
        for sec in blueprint.get("sections", []):
            for slot in sec.get("slots", []):
                n += 1
                slot["display_num"] = format_label(fmt, n)
                if slot.get("or_slot"):
                    slot["or_slot"]["display_num"] = f"{slot['display_num']} (OR)"
    return blueprint


# ---------------------------------------------------------------------------
# 4. reporting
# ---------------------------------------------------------------------------
def summarize_units(paper: Dict[str, Any], syllabus: Dict[str, Any], unit_plan: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Marks per unit in the final paper (OR alternatives are not double counted)."""
    primary = [q for q in paper.get("all_questions", []) if not q.get("is_choice")]
    total = sum(q.get("marks", 0) for q in primary) or 1
    targets: Dict[int, float] = {}
    plan_levels: Dict[int, List[str]] = {}
    if unit_plan:
        wsum = sum(float(e.get("marks") or 0) for e in unit_plan.get("units", [])) or 0
        for e in unit_plan.get("units", []):
            try:
                n = int(e.get("unit_num"))
            except (TypeError, ValueError):
                continue
            if wsum and unit_plan.get("use_weightage", True):
                targets[n] = float(e.get("marks") or 0) / wsum * total
            plan_levels[n] = _clean_levels(e.get("levels"))
    seen: Dict[int, Dict[str, Any]] = {}
    for u_no, u in _unit_lookup(syllabus).items():
        seen[u_no] = {"unit_num": u_no, "title": u.get("title", ""), "target_marks": round(targets.get(u_no, 0), 1),
                      "actual_marks": 0, "question_count": 0, "levels": plan_levels.get(u_no, []), "bloom_levels_used": []}
    for q in primary:
        n = q.get("unit_num")
        if n in seen:
            seen[n]["actual_marks"] += q.get("marks", 0)
            seen[n]["question_count"] += 1
            if q.get("bloom_level") not in seen[n]["bloom_levels_used"]:
                seen[n]["bloom_levels_used"].append(q.get("bloom_level"))
    out = list(seen.values())
    for u in out:
        u["bloom_levels_used"].sort()
        u["actual_pct"] = round(u["actual_marks"] / total * 100, 1)
    return out
