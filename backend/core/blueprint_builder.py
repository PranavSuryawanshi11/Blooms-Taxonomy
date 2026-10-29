"""
Exam Blueprint Builder
Constructs a balanced question slot matrix across syllabus units, marks, sections, and Bloom's cognitive tiers.
"""

import math
from typing import Dict, List, Any, Optional
from config import BLOOM_ORDER, BLOOM_LEVELS, EXAM_TEMPLATES, BLOOM_PRESETS


def get_preset_templates():
    """Return all standard examination templates."""
    return EXAM_TEMPLATES


def get_cognitive_presets():
    """Return standard Bloom's cognitive distribution presets."""
    return BLOOM_PRESETS


def build_blueprint(
    syllabus: Dict[str, Any],
    exam_config: Dict[str, Any],
    target_distribution: Dict[str, float],
    user_seed: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a detailed execution blueprint for question generation.
    Supports user_seed to ensure different users generating from the same syllabus receive distinct slot sets.
    """
    sections_config = exam_config.get("sections", [])
    if not sections_config:
        # Default to 50-mark midterm if not specified
        sections_config = EXAM_TEMPLATES["mid_sem_50"]["sections"]

    units = syllabus.get("units", [])
    if not units:
        raise ValueError("Syllabus must contain at least one unit.")

    total_target_marks = exam_config.get("total_marks", 50)
    
    # Calculate user-specific offset for multi-user divergence
    user_offset = 0
    if user_seed:
        import hashlib
        user_offset = int(hashlib.sha256(user_seed.encode()).hexdigest(), 16) % 997

    # Calculate desired mark quota per Bloom level
    desired_marks_by_bloom = {}
    for lvl in BLOOM_ORDER:
        pct = target_distribution.get(lvl, 0)
        desired_marks_by_bloom[lvl] = (pct / 100.0) * total_target_marks

    # Track allocated marks per Bloom level
    allocated_marks = {lvl: 0.0 for lvl in BLOOM_ORDER}
    
    sections = []
    question_counter = 1
    unit_cursor = user_offset
    total_slots = 0

    for sec_idx, sec_cfg in enumerate(sections_config, 1):
        sec_id = sec_cfg.get("id", f"sec_{sec_idx}")
        sec_name = sec_cfg.get("name", f"Section {chr(64 + sec_idx)}")
        instructions = sec_cfg.get("instructions", "Answer all questions.")
        q_count = int(sec_cfg.get("question_count", 5))
        marks_per_q = int(sec_cfg.get("marks_per_question", 2))
        allowed_levels = sec_cfg.get("allowed_levels", BLOOM_ORDER)
        has_internal_choice = sec_cfg.get("has_internal_choice", False)

        section_slots = []

        for q_idx in range(1, q_count + 1):
            # Select appropriate Bloom level for this question slot
            selected_lvl = _select_optimal_bloom_level(
                allowed_levels,
                desired_marks_by_bloom,
                allocated_marks,
                marks_per_q
            )
            allocated_marks[selected_lvl] += marks_per_q

            # Select unit and topic with user-specific divergence
            assigned_unit = units[unit_cursor % len(units)]
            unit_cursor += 1

            topics = assigned_unit.get("topics", ["Core Topic"])
            topic_idx = (q_idx - 1 + user_offset) % len(topics)
            assigned_topic = topics[topic_idx]

            # Resolve Course Outcome and description
            co_map = {co["id"]: co.get("description", "") for co in syllabus.get("course_outcomes", [])}
            co_id = assigned_unit.get("co", f"CO{min(assigned_unit.get('unit_num', 1), 5)}")
            co_desc = co_map.get(co_id, f"Understand and apply core principles in {assigned_unit.get('title', 'Module')}.")

            unit_n = assigned_unit.get("unit_num", 1)
            po_id = f"PO{min(unit_n, 12)}"
            pi_code = f"{unit_n}.{((q_idx - 1) % 3) + 1}"

            slot = {
                "slot_id": f"q_{question_counter}",
                "display_num": f"Q{question_counter}",
                "section_id": sec_id,
                "section_name": sec_name,
                "marks": marks_per_q,
                "bloom_level": selected_lvl,
                "bloom_name": BLOOM_LEVELS[selected_lvl]["name"],
                "unit_num": unit_n,
                "unit_title": assigned_unit.get("title", ""),
                "topic": assigned_topic,
                "co": co_id,
                "co_description": co_desc,
                "po": po_id,
                "pi_code": pi_code,
                "is_choice": False
            }

            # If section supports internal either/or choice
            if has_internal_choice and marks_per_q >= 5:
                slot["has_or_option"] = True
                # Select an alternative topic from the same unit or adjacent unit
                alt_topic_idx = (topic_idx + 1) % len(topics)
                alt_topic = topics[alt_topic_idx] if len(topics) > 1 else assigned_topic
                slot["or_slot"] = {
                    "slot_id": f"q_{question_counter}_or",
                    "display_num": f"Q{question_counter} (OR)",
                    "section_id": sec_id,
                    "marks": marks_per_q,
                    "bloom_level": selected_lvl,
                    "bloom_name": BLOOM_LEVELS[selected_lvl]["name"],
                    "unit_num": unit_n,
                    "unit_title": assigned_unit.get("title", ""),
                    "topic": alt_topic,
                    "co": co_id,
                    "co_description": co_desc,
                    "po": po_id,
                    "pi_code": pi_code,
                    "is_choice": True
                }

            section_slots.append(slot)
            question_counter += 1
            total_slots += 1

        sections.append({
            "section_id": sec_id,
            "section_name": sec_name,
            "instructions": instructions,
            "marks_per_question": marks_per_q,
            "question_count": q_count,
            "total_marks": q_count * marks_per_q,
            "slots": section_slots
        })

    # Prepare standard Course Outcomes list
    course_outcomes = syllabus.get("course_outcomes", [])
    if not course_outcomes and units:
        course_outcomes = [
            {"id": u.get("co", f"CO{i+1}"), "description": f"Mastery of {u.get('title', f'Unit {i+1}')}"}
            for i, u in enumerate(units)
        ]

    return {
        "institution_name": exam_config.get("institution_name", "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING"),
        "exam_title": exam_config.get("exam_title", "Semester Examination"),
        "college_profile": exam_config.get("college_profile"),
        "course_code": syllabus.get("code", "CS501"),
        "course_name": syllabus.get("name", "Subject"),
        "duration": exam_config.get("duration", "3 Hours"),
        "total_marks": total_target_marks,
        "instructions": exam_config.get("instructions", [
            "Answer all questions in accordance with section instructions.",
            "State clear assumptions where necessary.",
            "Illustrate your answers with neat diagrams wherever applicable."
        ]),
        "course_outcomes": course_outcomes,
        "sections": sections,
        "total_question_slots": total_slots
    }


def _select_optimal_bloom_level(
    allowed_levels: List[str],
    desired_marks: Dict[str, float],
    allocated_marks: Dict[str, float],
    question_marks: int
) -> str:
    """
    Greedily selects the allowed Bloom level that has the greatest unfilled mark deficit.
    """
    valid_levels = [lvl for lvl in allowed_levels if lvl in BLOOM_ORDER]
    if not valid_levels:
        valid_levels = ["L2"]

    # Calculate deficit = desired - allocated
    deficits = {
        lvl: desired_marks.get(lvl, 0) - allocated_marks.get(lvl, 0)
        for lvl in valid_levels
    }

    # Return level with highest unmet deficit
    best_level = max(valid_levels, key=lambda lvl: deficits[lvl])
    return best_level
