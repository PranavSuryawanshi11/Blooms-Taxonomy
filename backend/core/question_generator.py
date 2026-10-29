"""
Question Generation Engine
Synthesizes academically rigorous examination questions tailored to specific Bloom's cognitive tiers,
marks weight, syllabus topics, and course outcomes.
Supports Pedagogical Algorithmic generation out of the box with optional LLM augmentation.
"""

import os
import json
import random
import re
from typing import Dict, List, Any, Optional
from config import BLOOM_LEVELS, BLOOM_ORDER

# Load curated cognitive stems
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
STEMS_FILE = os.path.join(DATA_DIR, "bloom_stems.json")

try:
    with open(STEMS_FILE, "r", encoding="utf-8") as f:
        STEMS_DATA = json.load(f)
except Exception:
    STEMS_DATA = {}


from core.figure_generator import generate_technical_diagram
from core import llm_client
from core.figure_planner import attach_figures


def generate_paper_from_blueprint(
    blueprint: Dict[str, Any],
    api_config: Optional[Dict[str, str]] = None,
    user_seed: Optional[str] = None,
    user_sets: Optional[List[Dict[str, Any]]] = None,
    diagram_mode: str = "auto"
) -> Dict[str, Any]:
    """
    Generates all questions for an entire examination paper from its blueprint.
    Figures are planned afterwards (see figure_planner): only questions that need one get a diagram.
    Supports user_seed to ensure different users receive distinct papers.
    Supports user_sets where user provides custom sets of questions (e.g. Set 1, Set 2, Set 3, Set 4)
    from which questions are sampled and assembled matching the blueprint.
    """
    generated_sections = []
    flat_questions = []

    # Flatten user question sets pool if provided
    user_question_pool = []
    if user_sets and isinstance(user_sets, list):
        for s_idx, q_set in enumerate(user_sets, 1):
            s_name = q_set.get("set_name", f"Set {s_idx}")
            questions_in_set = q_set.get("questions", [])
            for q_item in questions_in_set:
                if isinstance(q_item, dict) and q_item.get("question_text"):
                    user_question_pool.append({
                        "set_name": s_name,
                        "question_text": q_item.get("question_text", "").strip(),
                        "marks": int(q_item.get("marks", 5)),
                        "bloom_level": q_item.get("bloom_level", "L2"),
                        "aicte_verb": q_item.get("aicte_verb"),
                        "co": q_item.get("co", "CO1"),
                        "topic": q_item.get("topic", "Subject Core"),
                        "figure": q_item.get("figure"),
                        "is_used": False
                    })

    # Helper to pick from user sets pool
    def _pick_from_user_pool(slot_marks: int, slot_lvl: str, slot_co: str) -> Optional[Dict[str, Any]]:
        if not user_question_pool:
            return None
        # Priority 1: exact marks and bloom level match
        for item in user_question_pool:
            if not item["is_used"] and item["marks"] == slot_marks and item["bloom_level"] == slot_lvl:
                item["is_used"] = True
                return item
        # Priority 2: exact marks match
        for item in user_question_pool:
            if not item["is_used"] and item["marks"] == slot_marks:
                item["is_used"] = True
                return item
        # Priority 3: any unused question
        for item in user_question_pool:
            if not item["is_used"]:
                item["is_used"] = True
                return item
        return None

    for sec in blueprint.get("sections", []):
        sec_questions = []
        for slot in sec.get("slots", []):
            user_q_candidate = _pick_from_user_pool(
                slot.get("marks", 5), slot.get("bloom_level", "L2"), slot.get("co", "CO1")
            )
            if user_q_candidate:
                q = _adapt_user_question_to_slot(user_q_candidate, slot, api_config=api_config)
            else:
                q = generate_single_question(slot, api_config=api_config, user_seed=user_seed, with_figure=False)

            sec_questions.append(q)
            flat_questions.append(q)

            # If slot has an internal OR option
            if slot.get("has_or_option") and "or_slot" in slot:
                or_slot = slot["or_slot"]
                user_or_candidate = _pick_from_user_pool(
                    or_slot.get("marks", slot.get("marks", 5)),
                    or_slot.get("bloom_level", slot.get("bloom_level", "L2")),
                    or_slot.get("co", slot.get("co", "CO1"))
                )
                if user_or_candidate:
                    or_q = _adapt_user_question_to_slot(user_or_candidate, or_slot, api_config=api_config)
                else:
                    or_q = generate_single_question(or_slot, api_config=api_config, user_seed=user_seed, with_figure=False)
                q["or_question"] = or_q
                flat_questions.append(or_q)

        generated_sections.append({
            "section_id": sec.get("section_id"),
            "section_name": sec.get("section_name"),
            "instructions": sec.get("instructions"),
            "marks_per_question": sec.get("marks_per_question"),
            "total_marks": sec.get("total_marks"),
            "questions": sec_questions
        })

    # Decide which questions really need a figure, then generate only those
    try:
        attach_figures(flat_questions, api_config, diagram_mode)
    except Exception:
        import logging
        logging.getLogger("bloomcraft").exception("Figure planning failed; paper generated without figures")

    # Build Course Outcomes (CO) Fulfillment Matrix
    co_matrix = []
    course_outcomes = blueprint.get("course_outcomes", [])
    co_summary = {}

    for co_item in course_outcomes:
        c_id = co_item.get("id", "CO1")
        co_summary[c_id] = {
            "id": c_id,
            "description": co_item.get("description", ""),
            "total_marks": 0,
            "question_count": 0,
            "questions": []
        }

    for q in flat_questions:
        co_id = q.get("co", "CO1")
        if co_id not in co_summary:
            co_summary[co_id] = {
                "id": co_id,
                "description": q.get("co_description", f"Course Outcome {co_id}"),
                "total_marks": 0,
                "question_count": 0,
                "questions": []
            }
        co_summary[co_id]["total_marks"] += q.get("marks", 0)
        co_summary[co_id]["question_count"] += 1
        co_summary[co_id]["questions"].append(q.get("display_num", "Q"))

        co_matrix.append({
            "slot_id": q.get("slot_id"),
            "display_num": q.get("display_num"),
            "question_text": q.get("question_text"),
            "marks": q.get("marks"),
            "bloom_level": q.get("bloom_level"),
            "bloom_name": q.get("bloom_name"),
            "aicte_verb": q.get("aicte_verb", q.get("bloom_verb", "Explain")),
            "co": co_id,
            "co_description": q.get("co_description", co_summary[co_id]["description"]),
            "po": q.get("po", "PO1")
        })

    return {
        "institution_name": blueprint.get("institution_name"),
        "exam_title": blueprint.get("exam_title"),
        "college_profile": blueprint.get("college_profile"),
        "course_code": blueprint.get("course_code"),
        "course_name": blueprint.get("course_name"),
        "duration": blueprint.get("duration"),
        "total_marks": blueprint.get("total_marks"),
        "instructions": blueprint.get("instructions"),
        "course_outcomes": course_outcomes,
        "co_fulfillment_matrix": co_matrix,
        "co_summary": co_summary,
        "sections": generated_sections,
        "all_questions": flat_questions,
        "source_mode": "User-Question-Sets" if user_sets else "AICTE-Pedagogical-Engine"
    }


def _adapt_user_question_to_slot(user_q: Dict[str, Any], slot: Dict[str, Any],
                                 api_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Wraps a user-provided question from their custom set into a standard paper question object."""
    disp_num = slot.get("display_num", "Q")
    bloom_lvl = user_q.get("bloom_level") or slot.get("bloom_level", "L2")
    marks = user_q.get("marks") or slot.get("marks", 5)
    topic = user_q.get("topic") or slot.get("topic", "Core Concepts")

    # Extract or classify leading verb
    text = user_q.get("question_text", "").strip()
    match = re.match(r"^[A-Za-z]+", text)
    verb = match.group(0).capitalize() if match else "Explain"

    # Keep the figure the user supplied; otherwise the figure planner decides later
    figure = user_q.get("figure")

    marking_guide = _generate_marking_scheme(bloom_lvl, marks, topic)

    return {
        "slot_id": slot.get("slot_id"),
        "display_num": disp_num,
        "question_text": text,
        "bloom_level": bloom_lvl,
        "bloom_name": BLOOM_LEVELS.get(bloom_lvl, {}).get("name", "Understanding"),
        "bloom_verb": verb,
        "aicte_verb": verb,
        "marks": marks,
        "unit_num": slot.get("unit_num", 1),
        "unit_title": slot.get("unit_title", ""),
        "topic": topic,
        "co": user_q.get("co") or slot.get("co", "CO1"),
        "co_description": slot.get("co_description", ""),
        "po": slot.get("po", "PO1"),
        "pi_code": slot.get("pi_code", "1.1"),
        "is_choice": slot.get("is_choice", False),
        "marking_scheme": marking_guide,
        "generator_mode": f"Custom-Set ({user_q.get('set_name', 'Bank')})",
        "figure": figure
    }


def generate_single_question(
    slot: Dict[str, Any],
    api_config: Optional[Dict[str, str]] = None,
    exclude_texts: Optional[List[str]] = None,
    user_seed: Optional[str] = None,
    with_figure: bool = True,
    diagram_mode: str = "auto"
) -> Dict[str, Any]:
    """
    Generates a single question strictly conforming to AICTE verbs standards and slot parameters.
    Integrates user_seed for divergence and attaches vector diagrams / figures when applicable.
    """
    exclude_texts = exclude_texts or []
    bloom_lvl = slot.get("bloom_level", "L2")
    topic = slot.get("topic", "Core Principles")
    marks = slot.get("marks", 5)
    disp_num = slot.get("display_num", "Q")

    # Step 1: Generate question text (LLM or Pedagogical Engine)
    llm_generated = False
    question_text = ""
    verb = "Explain"

    # Optional cloud LLM generation if any free-tier provider key is configured
    if llm_client.is_available(api_config):
        try:
            llm_text, llm_verb = _generate_with_llm(slot, api_config)
            if llm_text and len(llm_text) > 15:
                question_text = llm_text
                verb = llm_verb
                llm_generated = True
        except Exception:
            pass  # Fall through to Pedagogical Engine

    if not question_text:
        # Pedagogical Algorithmic Generation strictly enforcing AICTE action verbs
        question_text, verb = _generate_algorithmic_question(
            bloom_lvl, topic, marks, exclude_texts, user_seed=user_seed, slot_id=slot.get("slot_id")
        )

    marking_guide = _generate_marking_scheme(bloom_lvl, marks, topic)

    res = {
        "slot_id": slot.get("slot_id"),
        "display_num": disp_num,
        "question_text": question_text,
        "bloom_level": bloom_lvl,
        "bloom_name": BLOOM_LEVELS[bloom_lvl]["name"],
        "bloom_verb": verb,
        "aicte_verb": verb,
        "marks": marks,
        "unit_num": slot.get("unit_num", 1),
        "unit_title": slot.get("unit_title", ""),
        "topic": topic,
        "co": slot.get("co", "CO1"),
        "co_description": slot.get("co_description", ""),
        "po": slot.get("po", "PO1"),
        "pi_code": slot.get("pi_code", "1.1"),
        "is_choice": slot.get("is_choice", False),
        "marking_scheme": marking_guide,
        "generator_mode": "AICTE-Cloud-Enhanced" if llm_generated else "AICTE-Standard-Engine"
    }
    if with_figure:
        attach_figures([res], api_config, diagram_mode)   # planner: only if this question really needs one
    return res


def _generate_algorithmic_question(
    level: str,
    topic: str,
    marks: int,
    exclude_texts: List[str],
    user_seed: Optional[str] = None,
    slot_id: Optional[str] = None
) -> (str, str):
    """
    Crafts an examination question strictly beginning with an AICTE approved action verb.
    """
    level_info = BLOOM_LEVELS.get(level, BLOOM_LEVELS["L2"])
    level_data = STEMS_DATA.get(level, {})

    # Approved AICTE verbs from Revised Exam Reform Policy
    aicte_verbs = level_info.get("verbs", ["Explain"])
    scenarios = STEMS_DATA.get("scenarios", ["a high-frequency algorithmic system"])
    parameters = STEMS_DATA.get("parameter_samples", ["workload scale N = 100,000 requests/sec with latency < 50ms"])

    if user_seed:
        import hashlib
        seed_key = f"{user_seed}_{topic}_{slot_id}_{marks}_{level}"
        seed_int = int(hashlib.sha256(seed_key.encode()).hexdigest(), 16)
        rng = random.Random(seed_int)
    else:
        rng = random

    verb = rng.choice(aicte_verbs)
    scenario = rng.choice(scenarios)
    param = rng.choice(parameters)

    # Select templates based on marks
    if marks <= 4:
        templates = level_data.get("templates_short", level_data.get("templates_medium", []))
    elif marks <= 9:
        templates = level_data.get("templates_medium", level_data.get("templates_short", []))
    else:
        templates = level_data.get("templates_long", level_data.get("templates_medium", []))

    if not templates:
        templates = ["{verb} the fundamental concepts, principles, and implementation of {topic}."]

    formatted = ""
    for _ in range(10):
        raw_tmpl = rng.choice(templates)
        try:
            formatted = raw_tmpl.format(
                verb=verb,
                topic=topic,
                scenario=scenario,
                parameters=param
            )
        except Exception:
            formatted = f"{verb} the operational architecture and characteristics of {topic}."

        # Ensure question strictly begins with or features an AICTE action verb
        if not re.match(rf"^(?:Q\d+[\.\:\)]\s*)?{re.escape(verb)}", formatted, re.IGNORECASE):
            if not any(formatted.lower().startswith(v.lower()) for v in aicte_verbs):
                formatted = f"{verb} {formatted[0].lower() + formatted[1:]}"

        if formatted not in exclude_texts:
            return formatted, verb

    return formatted or f"{verb} the key principles and characteristics of {topic}.", verb


def _generate_marking_scheme(level: str, marks: int, topic: str) -> List[Dict[str, Any]]:
    """
    Generates step-wise marks distribution rubric for examiners.
    """
    if marks <= 2:
        return [
            {"criterion": f"Accurate definition / statement regarding {topic}", "marks": 1},
            {"criterion": "Key characteristics or formula", "marks": 1}
        ]
    elif marks <= 5:
        if level in ["L1", "L2"]:
            return [
                {"criterion": f"Conceptual explanation of {topic}", "marks": 2},
                {"criterion": "Neat diagram / illustrative example", "marks": 2},
                {"criterion": "Key advantages and limitations", "marks": 1}
            ]
        else:
            return [
                {"criterion": "Formulation and approach identification", "marks": 2},
                {"criterion": f"Step-by-step problem solving / execution for {topic}", "marks": 2},
                {"criterion": "Final result and interpretation", "marks": 1}
            ]
    elif marks <= 10:
        if level in ["L1", "L2"]:
            return [
                {"criterion": f"Detailed theoretical foundation of {topic}", "marks": 3},
                {"criterion": "Architectural block schematic / workflow", "marks": 3},
                {"criterion": "Comparative analysis and use-case discussion", "marks": 4}
            ]
        elif level in ["L3", "L4"]:
            return [
                {"criterion": "Mathematical or algorithmic model formulation", "marks": 3},
                {"criterion": f"Analytical decomposition / trace of {topic}", "marks": 4},
                {"criterion": "Complexity trade-offs and performance analysis", "marks": 3}
            ]
        else:  # L5, L6
            return [
                {"criterion": f"Architectural specification / critique of {topic}", "marks": 4},
                {"criterion": "Design schematic, protocol interfaces & failure handling", "marks": 4},
                {"criterion": "Evaluation matrix, SLA guarantees & recommendations", "marks": 2}
            ]
    else:  # 15+ marks
        return [
            {"criterion": f"System architecture & problem breakdown for {topic}", "marks": 5},
            {"criterion": "Complete procedural or algorithmic design with constraints", "marks": 6},
            {"criterion": "Verification, edge case analysis, and performance bounds", "marks": 4}
        ]


def _generate_with_llm(slot: Dict[str, Any], api_config: Dict[str, str]) -> (Optional[str], str):
    """
    Cloud LLM generation (free-tier providers via llm_client) strictly enforcing AICTE Exam Reform Policy action verbs.
    """
    bloom_lvl = slot.get("bloom_level", "L2")
    level_info = BLOOM_LEVELS.get(bloom_lvl, BLOOM_LEVELS["L2"])
    aicte_verbs = level_info.get("verbs", ["Explain"])

    system = (
        "You are a university examiner setting a formal examination question according to the AICTE Revised "
        "Exam Reform Policy (Criterion 3 NBA). Output ONLY the question text, no preamble, no numbering."
    )
    prompt = (
        f"Topic: '{slot['topic']}'. "
        f"Bloom Cognitive Level: {bloom_lvl} ({level_info['name']}) - {level_info.get('aicte_descriptor', '')}. "
        f"Marks allotted: {slot['marks']}. "
        f"Course: {slot.get('course_name', 'Computer Science & Engineering')}. "
        f"MANDATORY RULE: The question MUST start with an approved AICTE action verb for this level from: "
        f"{', '.join(aicte_verbs[:8])}."
    )
    res = llm_client.complete(system, prompt, json_mode=False, temperature=0.7, max_tokens=400,
                              api_config=api_config, models_per_provider=2, timeout=25.0, total_budget=40.0)
    if not res:
        return None, aicte_verbs[0]
    text = res[0].strip().strip('"').strip()
    match = re.match(r"^[A-Za-z]+", text)
    verb = match.group(0).capitalize() if match else aicte_verbs[0]
    return text, verb
