"""
Bloom's Taxonomy Engine
Handles Bloom Level classification, verification, verb selection, and cognitive balance calculation.
"""

import re
from typing import Dict, List, Tuple
from config import BLOOM_LEVELS, BLOOM_ORDER


def get_bloom_level_info(level_code: str) -> dict:
    """Return dictionary with metadata for a given Bloom level code (L1..L6)."""
    return BLOOM_LEVELS.get(level_code, BLOOM_LEVELS["L2"])


def validate_bloom_distribution(distribution: Dict[str, float]) -> Tuple[bool, str]:
    """
    Validate that percentage distribution across L1-L6 sums to ~100%.
    Returns (is_valid, message).
    """
    total = sum(distribution.get(lvl, 0) for lvl in BLOOM_ORDER)
    if not (98 <= total <= 102):
        return False, f"Total percentage must equal 100% (currently {total:.1f}%)."
    return True, "Distribution is valid."


def normalize_distribution(distribution: Dict[str, float]) -> Dict[str, float]:
    """Normalize arbitrary weights or percentages so they sum exactly to 100%."""
    total = sum(distribution.get(lvl, 0) for lvl in BLOOM_ORDER)
    if total == 0:
        return {lvl: round(100 / len(BLOOM_ORDER), 1) for lvl in BLOOM_ORDER}
    
    normalized = {}
    running_sum = 0
    for i, lvl in enumerate(BLOOM_ORDER):
        if i == len(BLOOM_ORDER) - 1:
            # Last level absorbs rounding residual
            normalized[lvl] = round(100.0 - running_sum, 1)
        else:
            val = round((distribution.get(lvl, 0) / total) * 100.0, 1)
            normalized[lvl] = val
            running_sum += val
            
    return normalized


def classify_question_bloom_level(question_text: str) -> str:
    """
    Rule-based cognitive classifier.
    Examines the leading verb, keywords, and cognitive phrasing to estimate Bloom level.
    """
    cleaned = question_text.strip()
    # Extract leading word
    match = re.match(r"^(?:Q?\d+[\.\:\)]|\([a-zA-Z\d]+\)|\[\d+\])?\s*([a-zA-Z\-]+)", cleaned)
    leading_word = match.group(1).capitalize() if match else ""

    text_lower = cleaned.lower()

    # Check for strong level-specific indicator patterns
    for lvl in reversed(BLOOM_ORDER):  # Check higher-order first
        verbs = BLOOM_LEVELS[lvl]["verbs"]
        for v in verbs:
            # Match verb at beginning
            if leading_word.lower() == v.lower():
                return lvl
            # Or regex boundary match
            if re.search(rf"\b{re.escape(v.lower())}\b", text_lower[:40]):
                return lvl

    # Keyword based heuristics
    if any(k in text_lower for k in ["design", "architect", "propose a novel", "formulate a blueprint", "synthesize"]):
        return "L6"
    if any(k in text_lower for k in ["critique", "evaluate whether", "justify why", "assess the efficacy", "appraise"]):
        return "L5"
    if any(k in text_lower for k in ["differentiate between", "analyze the trade-off", "deconstruct", "investigate why"]):
        return "L4"
    if any(k in text_lower for k in ["calculate", "solve for", "demonstrate execution", "implement a", "compute the"]):
        return "L3"
    if any(k in text_lower for k in ["explain", "describe", "discuss", "summarize", "illustrate", "what are"]):
        return "L2"
    if any(k in text_lower for k in ["define", "list", "state", "name", "identify", "what is"]):
        return "L1"

    # Default fallback
    return "L2"


def calculate_actual_distribution(questions: List[dict]) -> Dict[str, dict]:
    """
    Computes both Question-count % and Marks-weighted % for each Bloom Level.
    Returns:
    {
       "L1": {"count": 2, "count_pct": 20.0, "marks": 4, "marks_pct": 10.0},
       ...
    }
    """
    total_questions = len(questions)
    total_marks = sum(q.get("marks", 0) for q in questions)

    stats = {
        lvl: {"count": 0, "count_pct": 0.0, "marks": 0, "marks_pct": 0.0}
        for lvl in BLOOM_ORDER
    }

    if total_questions == 0 or total_marks == 0:
        return stats

    for q in questions:
        lvl = q.get("bloom_level", "L2")
        if lvl not in stats:
            lvl = "L2"
        marks = q.get("marks", 0)
        stats[lvl]["count"] += 1
        stats[lvl]["marks"] += marks

    for lvl in BLOOM_ORDER:
        stats[lvl]["count_pct"] = round((stats[lvl]["count"] / total_questions) * 100.0, 1)
        stats[lvl]["marks_pct"] = round((stats[lvl]["marks"] / total_marks) * 100.0, 1)

    return stats


def calculate_cognitive_index(stats: Dict[str, dict]) -> float:
    """
    Calculate Cognitive Depth Index on a scale of 1.0 to 6.0 based on marks weight.
    Formula: Sum(level_rank * marks_pct) / 100
    Higher index means more rigorous higher-order cognitive challenge.
    """
    weights = {"L1": 1.0, "L2": 2.0, "L3": 3.0, "L4": 4.0, "L5": 5.0, "L6": 6.0}
    weighted_sum = sum(weights[lvl] * stats[lvl]["marks_pct"] for lvl in BLOOM_ORDER)
    return round(weighted_sum / 100.0, 2)
