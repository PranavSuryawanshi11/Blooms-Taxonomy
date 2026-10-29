"""
BloomCraft AI - figure planner
==============================

Not every exam question needs a diagram ("Define ...", "List ...", "Differentiate ..." do not).
After all questions of a paper exist, ONE cheap LLM call looks at the whole paper and picks the
few questions where a figure genuinely helps. Only those questions get a (more expensive) diagram
generation call - so papers are faster, use fewer free-tier tokens and are not cluttered.

diagram_mode:
    "auto" (default) - planner decides (LLM, or a light keyword heuristic when no AI is available)
    "all"            - every question gets a figure
    "none"           - no figures
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set

from core import llm_client
from core.figure_generator import generate_technical_diagram

log = logging.getLogger("bloomcraft.planner")

MAX_FIGURE_RATIO = 0.25          # never more than ~25% of the questions of a paper get a figure

PLANNER_SYSTEM = """You decide which questions of a university exam paper need an accompanying figure.
A figure is justified ONLY when the question gives or refers to something students must look at: a graph, tree, automaton, network, architecture, dataset/table, schedule, circuit, curve/plot, protocol exchange, or a design baseline to extend.
NO figure for: explaining/describing/discussing a process, framework, workflow, lifecycle, architecture or "how it works" in words; optimisation or design-strategy questions; definitions, listing/naming/stating, theory or conceptual short answers, "differentiate / compare / justify / discuss" in words, formula-only or purely numeric questions with no structure to draw.
Prefer fewer figures. Return ONLY JSON: {"figures": [<question numbers that need a figure>]}"""

_VISUAL_CUE = re.compile(
    r"diagram|graph|tree|network|automat|dfa|nfa|state machine|table|dataset|data set|curve|plot|"
    r"circuit|topology|matrix|schedul|gantt|sequence|weights|nodes|vertices|"
    r"adjacency|given (the )?(data|set|points|samples)|samples?\b.*\(|decision boundary|clustering|perceptron|"
    r"neural network|packet|handshake|memory map|cache", re.I)
_THEORY_LEAD = re.compile(
    r"^\s*(define|list|state|name|enumerate|mention|what is|what are|write (a )?short|differentiate|distinguish|"
    r"outline|recall|identify|give (the )?(definition|meaning))", re.I)


def _priority(q: Dict[str, Any]) -> float:
    try:
        lvl = int(str(q.get("bloom_level", "L2"))[1:])
    except ValueError:
        lvl = 2
    return float(q.get("marks", 5) or 5) + lvl


def _heuristic(q: Dict[str, Any]) -> bool:
    text = q.get("question_text", "") or ""
    if _VISUAL_CUE.search(text):
        return True
    if _THEORY_LEAD.match(text):
        return False
    return False


def _llm_plan(questions: List[Dict[str, Any]], api_config: Optional[Dict[str, str]], cap: int) -> Optional[Set[int]]:
    lines = []
    for i, q in enumerate(questions, 1):
        text = re.sub(r"\s+", " ", q.get("question_text", ""))[:230]
        lines.append(f"{i}. [{q.get('bloom_level', '')}, {q.get('marks', '')}M] {text}")
    user = f"Pick at most {cap} questions that need a figure.\n" + "\n".join(lines)

    def ok(t: str) -> bool:
        return _parse(t) is not None

    res = llm_client.complete(PLANNER_SYSTEM, user, json_mode=True, temperature=0.1, max_tokens=300,
                              api_config=api_config, models_per_provider=3, timeout=30.0, total_budget=40.0,
                              validate=ok)
    if not res:
        return None
    ids = _parse(res[0])
    return {i for i in ids if 1 <= i <= len(questions)} if ids is not None else None


def _parse(text: str) -> Optional[List[int]]:
    try:
        m = re.search(r"\{[\s\S]*\}", text)
        data = json.loads(m.group(0)) if m else None
        figs = data.get("figures") if isinstance(data, dict) else None
        if not isinstance(figs, list):
            return None
        out = []
        for f in figs:
            try:
                out.append(int(re.sub(r"\D", "", str(f))))
            except ValueError:
                continue
        return out
    except Exception:
        return None


def plan_figures(questions: List[Dict[str, Any]], api_config: Optional[Dict[str, str]] = None,
                 mode: str = "auto") -> Set[int]:
    """Returns 1-based indexes (into `questions`) that should get a figure."""
    n = len(questions)
    if n == 0 or mode == "none":
        return set()
    candidates = [i for i, q in enumerate(questions, 1) if not q.get("figure")]
    if mode == "all":
        return set(candidates)

    cap = max(1, math.ceil(MAX_FIGURE_RATIO * n))
    chosen: Optional[Set[int]] = None
    if llm_client.is_available(api_config):
        chosen = _llm_plan(questions, api_config, cap)
    if chosen is None:                                   # no AI or planner failed: light heuristic
        chosen = {i for i in candidates if _heuristic(questions[i - 1])}
    chosen &= set(candidates)
    if len(chosen) > cap:                                # keep the most valuable ones
        chosen = set(sorted(chosen, key=lambda i: _priority(questions[i - 1]), reverse=True)[:cap])
    return chosen


def attach_figures(questions: List[Dict[str, Any]], api_config: Optional[Dict[str, str]] = None,
                   mode: str = "auto") -> None:
    """Plans, then generates and attaches figures in place."""
    chosen = plan_figures(questions, api_config, mode)
    log.info("Figure plan (%s): %d of %d questions", mode, len(chosen), len(questions))
    for i in sorted(chosen):
        q = questions[i - 1]
        figure = generate_technical_diagram(
            topic=q.get("topic", ""),
            bloom_level=q.get("bloom_level", "L2"),
            question_num=q.get("display_num", str(i)),
            question_text=q.get("question_text", ""),
            api_config=api_config,
            marks=q.get("marks"),
            force=(mode == "all"),
        )
        if figure:
            q["figure"] = figure
            if "Figure" not in q.get("question_text", ""):
                q["question_text"] = (
                    f"{q['question_text']} (Refer to {figure.get('title', 'technical schematic')} "
                    f"in Figure {q.get('display_num', i)} below)."
                )
