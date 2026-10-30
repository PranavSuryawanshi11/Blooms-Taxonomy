"""
BloomCraft AI - Question-driven AI diagram engine
=================================================

Nothing here is tied to a topic. For every question the pipeline is:

    question text + topic + Bloom level + marks
        -> auto-built prompt (nothing static except the output contract)
        -> a free-tier LLM (Groq -> OpenRouter -> Cerebras/Mistral, discovered at runtime,
           see llm_client.py) returns a JSON *diagram spec*
        -> spec is validated (and repaired by the model once if it is broken)
        -> deterministic renderer draws SVG with automatic layout
           (text wrapping, node sizing, layering, tree layout, graph layout ...)

The model decides WHAT the diagram contains (nodes, edges, rows, curves ...);
the renderer decides HOW it looks, so labels never get cut off, nothing overlaps
and the output is always valid, print-safe SVG.

Public API
----------
generate_ai_diagram(...) -> (figure_dict | None, status)
render_spec(spec, uid)   -> svg string      (usable on its own, e.g. for edited specs)
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import math
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from core import llm_client

log = logging.getLogger("bloomcraft.diagram_ai")

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

DIAGRAM_TYPES = [
    "flowchart", "tree", "graph", "state_machine", "layered",
    "sequence", "table", "gantt", "plot",
]
NODE_KINDS = [
    "process", "decision", "terminal", "io", "state", "initial_state",
    "accepting_state", "vertex", "component", "neuron", "leaf",
]
CIRCLE_KINDS = {"state", "initial_state", "accepting_state", "vertex", "neuron"}

MAX_FIGURE_NODES = 8
LIMITS = {"nodes": 9, "edges": 14, "rows": 8, "cols": 5, "series": 3, "points": 40, "segments": 8}   # compact figures only

# --------------------------------------------------------------------------
# Output contract shown to the model (shape only - the placeholders carry no content)
# --------------------------------------------------------------------------

# Plain-text description of the same contract (used for OpenAI json mode and as documentation to the model)
SCHEMA_HINT = """OUTPUT: exactly one JSON object, no prose, no markdown. Shape (<...> = placeholders to replace with real content):
{"needs_diagram": true, "diagram_type": "<flowchart|tree|graph|state_machine|layered|sequence|table|gantt|plot>",
 "title": "<short>", "caption": "Figure <num>: <sentence>", "direction": "<TB|LR>",
 "nodes": [{"id": "<id>", "label": "<text>", "sublabel": "<opt>", "kind": "<process|decision|terminal|io|state|initial_state|accepting_state|vertex|component|neuron|leaf>", "layer": <int, layered only>}],
 "edges": [{"from": "<id>", "to": "<id>", "label": "<opt>", "directed": <true|false>, "style": "<solid|dashed>"}],
 "layer_names": ["<layered only>"], "table": {"headers": ["<c>"], "rows": [["<c>"]]},
 "segments": [{"label": "<n>", "start": <num>, "end": <num>}],
 "plot": {"x_label": "<t>", "y_label": "<t>", "series": [{"name": "<t>", "style": "<line|curve|scatter>", "points": [[<x>, <y>]]}], "annotations": [{"x": <n>, "y": <n>, "text": "<t>"}]}}
Include only the keys the chosen diagram_type needs. If needs_diagram is false, give only title and caption."""

# --------------------------------------------------------------------------
# Prompt construction (fully derived from the question; nothing per-topic)
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You design the figure for ONE university exam question. Output one JSON object only; a renderer draws it with automatic layout, so only content and structure matter.
RULES
1. Be specific to THIS question: use its exact entities, symbols, values and names (or the standard textbook version of the problem). No generic placeholders ("Input", "Processor", "Result Synthesis", "Block A").
2. Show the GIVEN setup (data, structure, partial design), never the solution, answer or trace the student must produce.
3. Pick the type experts use:
 flowchart = algorithms, pipelines, workflows (kinds: terminal, process, decision, io; label decision edges Yes/No).
 tree = search / state-space / decision / game / parse / hierarchy (edges parent->child, branch labels, kind leaf for end nodes).
 graph = vertices + edges, networks (weights in edge labels; directed=false when undirected).
 state_machine = DFA / NFA / FSM (kinds initial_state, state, accepting_state; edge label = symbol/event; self-loop = from equals to).
 layered = architectures, protocol stacks, neural networks (every node gets a layer index 0,1,..; fill layer_names; neural nets: direction LR, kind neuron, edges between adjacent layers).
 sequence = nodes are parties, edges are messages in time order (dashed = reply).
 table = given data as headers + rows.  gantt = segments with numeric start/end.  plot = curves/points with real coordinates in plot.series.
4. COMPACT: the figure must be small and simple enough to sit beside the question on a printed page (about 8 cm wide). Use the node band given and NEVER more than 8 nodes. No long flowcharts: at most one decision node, no loops back more than once, no more than 3 nodes side by side; prefer direction TB with a short chain, or a small tree/graph/table. Show only what the question needs. Every node must be connected (except layered/table/gantt/plot).
5. Labels max 3 words / 20 chars; extra detail goes in sublabel or edge labels. PLAIN TEXT ONLY: no LaTeX, no $ signs - use Unicode symbols (θ, Σ, ŷ, ≤, →). Ids short and unique; edges only reference existing ids.
6. Set needs_diagram=false (give only title and caption) whenever the question asks to explain, discuss, describe, justify, compare, analyse, evaluate or design something in words, or is about a framework, process, procedure, lifecycle, workflow or "how X works". NEVER draw the step-by-step process/workflow that the student is supposed to describe, and never a flowchart with feedback loops, "challenges", "risks" or decision diamonds. Draw a figure ONLY when the question hands the student something concrete to look at: a given graph, tree, automaton, table of data, plot, circuit, network topology or a small block diagram of a named system.
   "flowchart" is allowed only if the question itself asks for a flowchart.
7. caption: one sentence starting "Figure <num>: " saying what is shown, without revealing the answer."""

BLOOM_GUIDE = {
    "L1": "Remember: clean labelled standard structure/process, textbook names.",
    "L2": "Understand: how the parts relate; short edge labels for what passes between them.",
    "L3": "Apply: carry the concrete GIVEN INPUT of the problem (graph, array, table, automaton, dataset). Do NOT draw the solution.",
    "L4": "Analyze: components and relationships needed to decompose/compare the system.",
    "L5": "Evaluate: the system or alternatives plus the decision points/criteria to judge.",
    "L6": "Create: only the baseline/context/constraints the student extends into an original design, not a finished design.",
}


def _size_band(marks: Any) -> Tuple[int, int]:
    """Small, exam-paper-sized figures: never more than 8 nodes."""
    try:
        m = int(marks)
    except (TypeError, ValueError):
        m = 5
    if m <= 3:
        return 3, 5
    if m <= 6:
        return 4, 6
    return 5, 8


def build_user_prompt(
    question_text: str, topic: str, bloom_level: str, marks: Any,
    question_num: str, custom_prompt: Optional[str] = None,
    diagram_hint: Optional[str] = None, variation: int = 0,
) -> str:
    lo, hi = _size_band(marks)
    parts = [
        f"Figure number: {question_num}",
        f"Examination question: \"{(question_text or topic or '').strip()}\"",
        f"Syllabus topic: \"{(topic or '').strip()}\"",
        f"Bloom level: {bloom_level} - {BLOOM_GUIDE.get(bloom_level, BLOOM_GUIDE['L2'])}",
        f"Marks: {marks if marks is not None else 'unspecified'}. Size band: roughly {lo}-{hi} nodes "
        f"(or an equivalent number of rows/points/segments).",
    ]
    if diagram_hint and diagram_hint != "auto":
        parts.append(f"The teacher suggests this kind of figure (soft hint, you may still choose better): {diagram_hint}")
    if custom_prompt:
        parts.append(f"Teacher's additional requirement for this figure (follow it): \"{custom_prompt}\"")
    if variation:
        parts.append(
            f"This is regeneration attempt #{variation}: choose a different valid way to visualise this question "
            f"than the most obvious one (different representation, concrete values or layout direction)."
        )
    parts.append("Design the figure now and return only the JSON object.")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# LLM access (free-tier providers, models discovered at runtime - see llm_client.py)
# --------------------------------------------------------------------------

def _loads_lenient(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        val = json.loads(cleaned)
        return val if isinstance(val, dict) else None
    except Exception:
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if m:
            try:
                val = json.loads(m.group(0))
                return val if isinstance(val, dict) else None
            except Exception:
                return None
    return None


def _call_llm(system: str, user: str, api_config: Optional[Dict[str, str]],
              temperature: float) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    res = llm_client.complete(
        f"{system}\n\n{SCHEMA_HINT}", user, json_mode=True, temperature=temperature,
        max_tokens=1400, api_config=api_config, models_per_provider=4, total_budget=90.0,
        validate=lambda t: _loads_lenient(t) is not None,
    )
    if not res:
        return None, None
    return _loads_lenient(res[0]), res[1]


# --------------------------------------------------------------------------
# Spec validation / normalisation
# --------------------------------------------------------------------------

_LATEX = {
    r"\\sum": "Σ", r"\\Sigma": "Σ", r"\\prod": "Π", r"\\theta": "θ", r"\\Theta": "Θ", r"\\alpha": "α", r"\\beta": "β",
    r"\\gamma": "γ", r"\\delta": "δ", r"\\Delta": "Δ", r"\\epsilon": "ε", r"\\varepsilon": "ε", r"\\eta": "η",
    r"\\lambda": "λ", r"\\mu": "μ", r"\\sigma": "σ", r"\\pi": "π", r"\\phi": "φ", r"\\omega": "ω", r"\\rho": "ρ",
    r"\\tau": "τ", r"\\infty": "∞", r"\\rightarrow": "→", r"\\to": "→", r"\\leftarrow": "←", r"\\Rightarrow": "⇒",
    r"\\leq": "≤", r"\\le": "≤", r"\\geq": "≥", r"\\ge": "≥", r"\\neq": "≠", r"\\times": "×", r"\\cdot": "·",
    r"\\approx": "≈", r"\\partial": "∂", r"\\nabla": "∇", r"\\in": "∈", r"\\log": "log", r"\\max": "max", r"\\min": "min",
    r"\\ldots": "…", r"\\dots": "…", r"\\%": "%", r"\\_": "_",
}
_SUB = dict(zip("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ"))
_SUP = dict(zip("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ"))


def _clean_math(t: str) -> str:
    """Models sometimes answer in LaTeX; the renderer draws plain text, so convert to Unicode."""
    if "$" not in t and "\\" not in t and "_" not in t and "^" not in t and "{" not in t:
        return t
    t = re.sub(r"\\(?:hat|widehat)\{(\w)\}", lambda m: m.group(1) + "\u0302", t)
    t = re.sub(r"\\(?:bar|overline)\{(\w)\}", lambda m: m.group(1) + "\u0304", t)
    t = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", t)
    t = re.sub(r"\\sqrt\{([^}]*)\}", r"√(\1)", t)
    for cmd in sorted(_LATEX, key=len, reverse=True):
        t = re.sub(cmd + r"(?![A-Za-z])", _LATEX[cmd], t)

    def sub(m: "re.Match[str]") -> str:
        body = m.group(1) if m.group(1) is not None else m.group(2)
        return "".join(_SUB.get(c, c) for c in body) if all(c in _SUB for c in body) else body

    def sup(m: "re.Match[str]") -> str:
        body = m.group(1) if m.group(1) is not None else m.group(2)
        return "".join(_SUP.get(c, c) for c in body) if all(c in _SUP for c in body) else "^" + body

    t = re.sub(r"_\{([^}]*)\}|_(\w)", sub, t)
    t = re.sub(r"\^\{([^}]*)\}|\^(\w)", sup, t)
    t = t.replace("$", "").replace("\\", "")
    t = re.sub(r"[{}]", "", t)
    return t


def _s(v: Any, n: int = 80) -> str:
    if v is None:
        return ""
    return _clean_math(re.sub(r"\s+", " ", str(v))).strip()[:n]


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def normalize_spec(raw: Any, q_num: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Returns (clean_spec, errors). A non-empty errors list means the spec is unusable."""
    errors: List[str] = []
    warnings: List[str] = []           # soft problems: worth one repair attempt, but still drawable
    if not isinstance(raw, dict):
        return None, ["The response was not a JSON object."]

    dtype = raw.get("diagram_type")
    if dtype not in DIAGRAM_TYPES:
        errors.append(f"diagram_type must be one of {DIAGRAM_TYPES}.")
        dtype = "flowchart"

    title = _s(raw.get("title"), 80) or "Technical Schematic"
    caption = _s(raw.get("caption"), 240)
    if not re.match(r"^figure\b", caption, re.I):
        caption = f"Figure {q_num}: {caption or title}"
    if not caption.endswith("."):
        caption += "."

    spec: Dict[str, Any] = {
        "needs_diagram": raw.get("needs_diagram") is not False,
        "diagram_type": dtype, "title": title, "caption": caption,
    }
    if not spec["needs_diagram"]:
        return spec, []

    if dtype == "table":
        t = raw.get("table") or {}
        headers = [_s(h, 40) for h in (t.get("headers") or [])][: LIMITS["cols"]]
        rows_raw = t.get("rows") or []
        if not headers or not rows_raw:
            errors.append("table needs 'headers' and at least one row in 'rows'.")
        else:
            rows = []
            for r in rows_raw[: LIMITS["rows"]]:
                if not isinstance(r, list):
                    continue
                cells = [_s(c, 40) for c in r][: len(headers)]
                cells += [""] * (len(headers) - len(cells))
                rows.append(cells)
            spec["table"] = {"headers": headers, "rows": rows}
        return spec, errors

    if dtype == "gantt":
        segs = []
        for s in (raw.get("segments") or [])[: LIMITS["segments"]]:
            if not isinstance(s, dict):
                continue
            a, b = _num(s.get("start")), _num(s.get("end"))
            if a is None or b is None or b <= a:
                continue
            segs.append({"label": _s(s.get("label"), 24), "start": a, "end": b})
        if not segs:
            errors.append("gantt needs 'segments' with numeric start < end.")
        spec["segments"] = sorted(segs, key=lambda x: x["start"])
        return spec, errors

    if dtype == "plot":
        p = raw.get("plot") or {}
        series = []
        for s in (p.get("series") or [])[: LIMITS["series"]]:
            if not isinstance(s, dict):
                continue
            pts = []
            for pt in (s.get("points") or [])[: LIMITS["points"]]:
                if isinstance(pt, list) and len(pt) >= 2 and _num(pt[0]) is not None and _num(pt[1]) is not None:
                    pts.append([_num(pt[0]), _num(pt[1])])
            style = s.get("style") if s.get("style") in ("line", "curve", "scatter") else "line"
            if (style == "scatter" and pts) or len(pts) >= 2:
                series.append({"name": _s(s.get("name"), 28), "style": style, "points": pts})
        if not series:
            errors.append("plot needs at least one series with numeric [x, y] points (2+ for line/curve).")
        anns = []
        for a in (p.get("annotations") or [])[:6]:
            if isinstance(a, dict) and _num(a.get("x")) is not None and _num(a.get("y")) is not None:
                anns.append({"x": _num(a["x"]), "y": _num(a["y"]), "text": _s(a.get("text"), 28)})
        spec["plot"] = {"x_label": _s(p.get("x_label"), 40), "y_label": _s(p.get("y_label"), 40),
                        "series": series, "annotations": anns}
        return spec, errors

    # ---- node/edge based types -------------------------------------------------
    raw_nodes = raw.get("nodes") or []
    if len(raw_nodes) > MAX_FIGURE_NODES:
        errors.append(f"Too many nodes ({len(raw_nodes)}). Redraw it with at most {MAX_FIGURE_NODES} nodes: keep only what the question needs.")
        raw_nodes = raw_nodes[: LIMITS["nodes"]]
    nodes: List[Dict[str, Any]] = []
    idmap: Dict[str, str] = {}
    labelmap: Dict[str, str] = {}
    default_kind = {"flowchart": "process", "state_machine": "state", "graph": "vertex",
                    "tree": "process", "layered": "component", "sequence": "component"}[dtype]
    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict):
            continue
        orig = _s(n.get("id"), 30) or f"n{i + 1}"
        nid = orig if orig not in {x["id"] for x in nodes} else f"{orig}_{i}"
        label = _s(n.get("label"), 60) or orig
        kind = n.get("kind") if n.get("kind") in NODE_KINDS else default_kind
        if dtype == "tree" and not n.get("kind") and len(label) <= 6:
            kind = "vertex"
        layer = n.get("layer")
        layer = int(layer) if isinstance(layer, (int, float)) and not isinstance(layer, bool) else None
        nodes.append({"id": nid, "label": label, "sublabel": _s(n.get("sublabel"), 60), "kind": kind, "layer": layer})
        idmap.setdefault(orig, nid)
        labelmap.setdefault(label.lower(), nid)

    min_nodes = 2
    if len(nodes) < min_nodes:
        errors.append(f"{dtype} needs at least {min_nodes} nodes.")
        return spec, errors

    edges: List[Dict[str, Any]] = []
    bad = 0
    default_directed = dtype != "graph"
    raw_edges = raw.get("edges") or []
    for e in raw_edges[: LIMITS["edges"]]:
        if not isinstance(e, dict):
            bad += 1
            continue
        a = idmap.get(_s(e.get("from"), 30)) or labelmap.get(_s(e.get("from"), 60).lower())
        b = idmap.get(_s(e.get("to"), 30)) or labelmap.get(_s(e.get("to"), 60).lower())
        if not a or not b:
            bad += 1
            continue
        directed = e.get("directed") if isinstance(e.get("directed"), bool) else default_directed
        edges.append({"src": a, "tgt": b, "label": _s(e.get("label"), 40), "directed": directed,
                      "dashed": e.get("style") == "dashed"})
    if bad and bad > max(2, 0.3 * len(raw_edges)):
        errors.append(f"{bad} edges reference node ids that do not exist; every 'from'/'to' must be a node id.")

    if dtype == "sequence":
        if not edges:
            errors.append("sequence needs 'edges' listing the messages in chronological order.")
    elif dtype not in ("layered",):
        if not edges:
            errors.append(f"{dtype} needs edges connecting the nodes.")
        else:
            comps = _components([n["id"] for n in nodes], edges)
            if comps > 1 and dtype in ("flowchart", "tree", "state_machine"):
                warnings.append(f"The diagram is disconnected ({comps} separate parts); connect every node into one diagram.")

    explicit = dtype == "layered" and all(n["layer"] is not None for n in nodes)
    spec.update({
        "nodes": nodes, "edges": edges, "explicit_layers": explicit, "warnings": warnings,
        "layer_names": [_s(x, 30) for x in (raw.get("layer_names") or [])][:10],
        "direction": raw.get("direction") if raw.get("direction") in ("TB", "LR")
        else ("LR" if dtype == "state_machine" else "TB"),
    })
    return spec, errors


def _components(ids: List[str], edges: List[Dict[str, Any]]) -> int:
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        ra, rb = find(e["src"]), find(e["tgt"])
        if ra != rb:
            parent[ra] = rb
    return len({find(i) for i in ids})


def _is_forest(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
    parent: Dict[str, str] = {}
    for e in edges:
        if e["src"] == e["tgt"] or e["tgt"] in parent:
            return False
        parent[e["tgt"]] = e["src"]
    # cycle check
    for n in nodes:
        seen, cur = set(), n["id"]
        while cur in parent:
            if cur in seen:
                return False
            seen.add(cur)
            cur = parent[cur]
    return any(n["id"] not in parent for n in nodes)


# --------------------------------------------------------------------------
# Text measurement and wrapping (no font files needed)
# --------------------------------------------------------------------------

FS, FS_SUB, LH, LH_SUB = 12.0, 10.0, 15.0, 12.5
INK, MUTED, GRID, BLUE = "#0F172A", "#475569", "#CBD5E1", "#1D4ED8"
_NARROW = set("iljtfIr.,;:'|!()[]{} ")
_WIDE = set("mwMW@%")


def _cw(c: str) -> float:
    if c in _NARROW:
        return 0.30
    if c in _WIDE:
        return 0.85
    if c.isupper():
        return 0.68
    if c.isdigit():
        return 0.50
    return 0.47


def _tw(text: str, size: float, bold: bool = False) -> float:
    w = sum(_cw(c) for c in text) * size * 1.06
    return w * (1.07 if bold else 1.0)


def _wrap(text: str, size: float, max_w: float, bold: bool = False, max_lines: int = 4) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and _tw(trial, size, bold) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return lines


def _esc(t: str) -> str:
    return html.escape(t, quote=True)


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------

class _Bounds:
    def __init__(self) -> None:
        self.x0 = self.y0 = float("inf")
        self.x1 = self.y1 = float("-inf")

    def add(self, x: float, y: float) -> None:
        self.x0, self.x1 = min(self.x0, x), max(self.x1, x)
        self.y0, self.y1 = min(self.y0, y), max(self.y1, y)

    def box(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.add(x0, y0)
        self.add(x1, y1)


def _svg_doc(inner: str, b: _Bounds, uid: str, pad: float = 12.0, min_w: float = 0) -> str:
    w = max(b.x1 - b.x0 + 2 * pad, min_w)
    extra = max(0.0, (w - (b.x1 - b.x0 + 2 * pad)) / 2)
    h = b.y1 - b.y0 + 2 * pad
    tx, ty = pad - b.x0 + extra, pad - b.y0
    max_w = int(min(w, 420))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
        f'style="width:{max_w}px;max-width:100%;height:auto;display:block;margin:8px auto;background:#FFFFFF;'
        f'border:1px solid {GRID};border-radius:6px;font-family:\'Times New Roman\',Times,serif;">'
        f'<defs><marker id="arr-{uid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M 0 1 L 10 5 L 0 9 z" fill="{INK}"/></marker></defs>'
        f'<g transform="translate({tx:.1f},{ty:.1f})">{inner}</g></svg>'
    )


def _text(x: float, y: float, s: str, size: float = FS, bold: bool = False, fill: str = INK,
          anchor: str = "middle", italic: bool = False, halo: bool = False, extra: str = "") -> str:
    style = ""
    if halo:
        style = ' stroke="#FFFFFF" stroke-width="4" stroke-linejoin="round" paint-order="stroke"'
    weight_attr = ' font-weight="bold"' if bold else ''
    italic_attr = ' font-style="italic"' if italic else ''
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"'
        f'{weight_attr}{italic_attr}{style}{extra}>{_esc(s)}</text>'
    )


# --------------------------------------------------------------------------
# Node model and drawing
# --------------------------------------------------------------------------

class _N:
    def __init__(self, nid: str, label: str, sub: str, kind: str, layer: Optional[int], dummy: bool = False) -> None:
        self.id, self.label, self.sub, self.kind, self.layer, self.dummy = nid, label, sub, kind, layer, dummy
        self.lines: List[str] = []
        self.sublines: List[str] = []
        self.w = self.h = 0.0
        self.x = self.y = 0.0
        self.c = self.m = 0.0


def _measure(n: _N, wrap_w: float) -> None:
    n.lines = _wrap(n.label, FS, wrap_w, bold=True, max_lines=4)
    n.sublines = _wrap(n.sub, FS_SUB, wrap_w, max_lines=2) if n.sub else []
    tw = max([_tw(l, FS, True) for l in n.lines] + [_tw(l, FS_SUB) for l in n.sublines] + [0.0])
    th = len(n.lines) * LH + len(n.sublines) * LH_SUB
    if n.kind in CIRCLE_KINDS:
        r = max(19.0, tw / 2 + 9, th / 2 + 8)
        if len(n.lines) > 1 or n.sublines:
            r = max(r, math.hypot(tw / 2, th / 2) + 3)
        n.w = n.h = 2 * r
    elif n.kind == "decision":
        n.w, n.h = max(92.0, tw * 1.55 + 24), max(54.0, th * 1.7 + 18)
    elif n.kind == "terminal":
        n.w, n.h = max(84.0, tw + 36), max(34.0, th + 16)
    elif n.kind == "io":
        n.w, n.h = max(84.0, tw + 40), max(36.0, th + 18)
    else:
        n.w, n.h = max(66.0, tw + 26), max(36.0, th + 18)


def _wrap_width_for(kind: str, tb: bool = True) -> float:
    if kind in CIRCLE_KINDS:
        return 66.0
    if kind == "decision":
        return 100.0
    return 130.0 if tb else 120.0


_FILL = {"decision": "#FFF7ED", "terminal": "#E2E8F0", "io": "#EFF6FF", "leaf": "#ECFDF5"}


def _node_svg(n: _N) -> str:
    kind, cx, cy, w, h = n.kind, n.x, n.y, n.w, n.h
    fill = _FILL.get(kind, "#F8FAFC")
    sw = 1.6
    out: List[str] = []
    if kind in CIRCLE_KINDS:
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{w / 2:.1f}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>')
        if kind == "accepting_state":
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{w / 2 - 4:.1f}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
    elif kind == "decision":
        pts = f"{cx:.1f},{cy - h / 2:.1f} {cx + w / 2:.1f},{cy:.1f} {cx:.1f},{cy + h / 2:.1f} {cx - w / 2:.1f},{cy:.1f}"
        out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>')
    elif kind == "io":
        sk = 11
        pts = (f"{cx - w / 2 + sk:.1f},{cy - h / 2:.1f} {cx + w / 2:.1f},{cy - h / 2:.1f} "
               f"{cx + w / 2 - sk:.1f},{cy + h / 2:.1f} {cx - w / 2:.1f},{cy + h / 2:.1f}")
        out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>')
    else:
        rx = h / 2 if kind == "terminal" else (8 if kind == "leaf" else 3)
        out.append(f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" '
                   f'fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>')
    # text block
    th = len(n.lines) * LH + len(n.sublines) * LH_SUB
    y = cy - th / 2
    for line in n.lines:
        out.append(_text(cx, y + LH * 0.5 + FS * 0.35, line, FS, bold=True, fill=BLUE if kind == "component" else INK))
        y += LH
    for line in n.sublines:
        out.append(_text(cx, y + LH_SUB * 0.5 + FS_SUB * 0.35, line, FS_SUB, fill=MUTED, italic=True))
        y += LH_SUB
    return "".join(out)


def _clip(n: _N, tx: float, ty: float) -> Tuple[float, float]:
    cx, cy = n.x, n.y
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy
    if n.dummy:
        return cx, cy
    if n.kind in CIRCLE_KINDS:
        d = math.hypot(dx, dy)
        r = n.w / 2
        return cx + dx / d * r, cy + dy / d * r
    if n.kind == "decision":
        s = 1.0 / (abs(dx) / (n.w / 2) + abs(dy) / (n.h / 2))
        return cx + dx * s, cy + dy * s
    sx = (n.w / 2) / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = (n.h / 2) / abs(dy) if abs(dy) > 1e-9 else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


# --------------------------------------------------------------------------
# Edge drawing
# --------------------------------------------------------------------------

Pt = Tuple[float, float]


def _path_from_points(pts: List[Pt]) -> str:
    if len(pts) == 2:
        return f"M {pts[0][0]:.1f} {pts[0][1]:.1f} L {pts[1][0]:.1f} {pts[1][1]:.1f}"
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C {c1[0]:.1f} {c1[1]:.1f}, {c2[0]:.1f} {c2[1]:.1f}, {p2[0]:.1f} {p2[1]:.1f}"
    return d


def _mid_of_polyline(pts: List[Pt]) -> Pt:
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    half = sum(seg) / 2
    acc = 0.0
    for i, s in enumerate(seg):
        if acc + s >= half and s > 0:
            t = (half - acc) / s
            return pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
        acc += s
    return pts[-1]


class _Edge:
    def __init__(self, e: Dict[str, Any], a: _N, b: _N) -> None:
        self.e, self.a, self.b = e, a, b
        self.d = ""
        self.label_xy: Pt = (0.0, 0.0)
        self.pts: List[Pt] = []


def _poly_edge(ed: _Edge, pts: List[Pt]) -> None:
    ed.pts = pts
    ed.d = _path_from_points(pts)
    ed.label_xy = _mid_of_polyline(pts)


def _curve_edge(ed: _Edge, bulge: float, prefer_up: bool = False) -> None:
    a, b = ed.a, ed.b
    mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / d, dx / d
    if prefer_up and (ny > 0 or (abs(ny) < 1e-9 and nx > 0)):
        nx, ny = -nx, -ny
    cx, cy = mx + 2 * bulge * nx, my + 2 * bulge * ny
    s = _clip(a, cx, cy)
    e = _clip(b, cx, cy)
    ed.d = f"M {s[0]:.1f} {s[1]:.1f} Q {cx:.1f} {cy:.1f} {e[0]:.1f} {e[1]:.1f}"
    ed.label_xy = (0.25 * s[0] + 0.5 * cx + 0.25 * e[0], 0.25 * s[1] + 0.5 * cy + 0.25 * e[1])
    ed.pts = [s, (cx, cy), e]


def _self_loop(ed: _Edge) -> None:
    n = ed.a
    cx, cy = n.x, n.y
    if n.kind in CIRCLE_KINDS:
        r = n.w / 2
        x1, x2, y1 = cx - r * 0.5, cx + r * 0.5, cy - r * 0.866
        top = cy - r
    else:
        x1, x2, y1 = cx - n.w * 0.18, cx + n.w * 0.18, cy - n.h / 2
        top = cy - n.h / 2
    hgt = 34.0
    ed.d = (f"M {x1:.1f} {y1:.1f} C {x1 - hgt * 0.6:.1f} {top - hgt:.1f}, "
            f"{x2 + hgt * 0.6:.1f} {top - hgt:.1f}, {x2:.1f} {y1:.1f}")
    ed.label_xy = (cx, top - hgt * 0.75 - 6)
    ed.pts = [(x1, y1), (cx, top - hgt), (x2, y1)]


def _edges_svg(edges: List[_Edge], uid: str, b: _Bounds, dense: bool = False) -> str:
    out: List[str] = []
    labels: List[str] = []
    sw = 1.0 if dense else 1.5
    for ed in edges:
        e = ed.e
        attrs = f'fill="none" stroke="{INK}" stroke-width="{sw}"'
        if e.get("dashed"):
            attrs += ' stroke-dasharray="6 4"'
        if e.get("directed"):
            attrs += f' marker-end="url(#arr-{uid})"'
        out.append(f'<path d="{ed.d}" {attrs}/>')
        for p in ed.pts:
            b.add(*p)
        if e.get("label"):
            lx, ly = ed.label_xy
            labels.append(_text(lx, ly + 4, e["label"], 11, fill=INK, halo=True, italic=True))
            tw = _tw(e["label"], 11)
            b.box(lx - tw / 2, ly - 9, lx + tw / 2, ly + 9)
    return "".join(out) + "".join(labels)


def _pair_offsets(edges: List[_Edge], prefer_up: bool = False) -> None:
    """Edges A->B and B->A are drawn as two opposite curves instead of overlapping lines."""
    groups: Dict[frozenset, List[_Edge]] = {}
    for ed in edges:
        if ed.a is not ed.b:
            groups.setdefault(frozenset((id(ed.a), id(ed.b))), []).append(ed)
    for g in groups.values():
        if len(g) == 2 and g[0].a is g[1].b:
            for ed in g:
                _curve_edge(ed, 22.0)
        elif len(g) > 2:
            for i, ed in enumerate(g):
                _curve_edge(ed, (i - (len(g) - 1) / 2) * 24.0)


# --------------------------------------------------------------------------
# Layered / tree layout engine (flowchart, tree, state machine, layered/neural nets)
# --------------------------------------------------------------------------

def _assign_layers(nodes: List[_N], edges: List[Dict[str, Any]]) -> None:
    adj: Dict[str, List[str]] = {n.id: [] for n in nodes}
    for e in edges:
        if e["src"] != e["tgt"]:
            adj[e["src"]].append(e["tgt"])
    color: Dict[str, int] = {}
    back = set()
    for root in [n.id for n in nodes]:
        if color.get(root):
            continue
        color[root] = 1
        stack = [(root, iter(adj[root]))]
        while stack:
            u, it = stack[-1]
            for v in it:
                c = color.get(v, 0)
                if c == 0:
                    color[v] = 1
                    stack.append((v, iter(adj[v])))
                    break
                if c == 1:
                    back.add((u, v))
            else:
                color[u] = 2
                stack.pop()
    fwd: Dict[str, List[str]] = {n.id: [] for n in nodes}
    indeg = {n.id: 0 for n in nodes}
    for e in edges:
        s, t = e["src"], e["tgt"]
        if s == t or (s, t) in back:
            continue
        fwd[s].append(t)
        indeg[t] += 1
    layer = {n.id: 0 for n in nodes}
    queue = [i for i, d in indeg.items() if d == 0]
    while queue:
        u = queue.pop(0)
        for v in fwd[u]:
            layer[v] = max(layer[v], layer[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    for n in nodes:
        n.layer = layer[n.id]


def _spread(ns: List[_N], desired: List[float], size, gap: float) -> None:
    k = len(ns)
    if k == 0:
        return
    sep = [(size(ns[i]) + size(ns[i + 1])) / 2 + gap for i in range(k - 1)]
    f = [0.0] * k
    f[0] = desired[0]
    for i in range(1, k):
        f[i] = max(desired[i], f[i - 1] + sep[i - 1])
    g = [0.0] * k
    g[-1] = desired[-1]
    for i in range(k - 2, -1, -1):
        g[i] = min(desired[i], g[i + 1] - sep[i])
    for i in range(k):
        ns[i].c = (f[i] + g[i]) / 2


def _layout_flow(spec: Dict[str, Any], uid: str, tree_mode: bool = False) -> str:
    tb = spec["direction"] == "TB"
    nodes = [_N(n["id"], n["label"], n["sublabel"], n["kind"], n["layer"]) for n in spec["nodes"]]
    for n in nodes:
        _measure(n, _wrap_width_for(n.kind, tb))
    byid = {n.id: n for n in nodes}
    edges = spec["edges"]

    if spec.get("explicit_layers"):
        pass
    else:
        _assign_layers(nodes, edges)
    uniq = sorted({n.layer for n in nodes})
    remap = {l: i for i, l in enumerate(uniq)}
    for n in nodes:
        n.layer = remap[n.layer]
    nl = len(uniq)

    layers: Dict[int, List[_N]] = {i: [] for i in range(nl)}
    for n in nodes:
        layers[n.layer].append(n)

    routes: List[Dict[str, Any]] = []
    up: Dict[_N, List[_N]] = {}
    down: Dict[_N, List[_N]] = {}

    def link(a: _N, b: _N) -> None:
        down.setdefault(a, []).append(b)
        up.setdefault(b, []).append(a)

    for e in edges:
        s, t = byid[e["src"]], byid[e["tgt"]]
        if s is t:
            routes.append({"e": e, "kind": "self", "chain": [s]})
        elif s.layer == t.layer:
            routes.append({"e": e, "kind": "same", "chain": [s, t]})
        else:
            flip = s.layer > t.layer
            lo, hi = (t, s) if flip else (s, t)
            chain = [lo]
            for L in range(lo.layer + 1, hi.layer):
                d = _N(f"_d{len(routes)}_{L}", "", "", "process", L, dummy=True)
                d.w, d.h = 6, 6
                layers[L].append(d)
                chain.append(d)
            chain.append(hi)
            for a, b in zip(chain, chain[1:]):
                link(a, b)
            routes.append({"e": e, "kind": "normal", "chain": chain, "flip": flip})

    order = {L: list(layers[L]) for L in layers}
    # crossing reduction (barycentre)
    for it in range(8):
        downpass = it % 2 == 0
        rng = range(1, nl) if downpass else range(nl - 2, -1, -1)
        for L in rng:
            ref = order[L - 1] if downpass else order[L + 1]
            idx = {n: i for i, n in enumerate(ref)}
            nb = up if downpass else down

            def key(pair: Tuple[int, _N]) -> Tuple[float, int]:
                i, n = pair
                ns = [idx[m] for m in nb.get(n, []) if m in idx]
                return (sum(ns) / len(ns) if ns else float(i), i)

            order[L] = [n for _, n in sorted(enumerate(order[L]), key=key)]

    def csize(n: _N) -> float:
        return (n.w if tb else n.h) if not n.dummy else 8.0

    def msize(n: _N) -> float:
        return n.h if tb else n.w

    gap_c = 24.0 if tb else 20.0
    gap_m = 34.0 if tb else 56.0           # tight spacing keeps figures short
    for L in range(nl):
        x = 0.0
        for n in order[L]:
            n.c = x + csize(n) / 2
            x += csize(n) + gap_c
        total = x - gap_c
        for n in order[L]:
            n.c -= total / 2

    if tree_mode:
        children: Dict[_N, List[_N]] = {n: [] for n in nodes}
        has_parent = set()
        for r in routes:
            if r["kind"] == "normal" and not r["flip"] and len(r["chain"]) == 2:
                children[r["chain"][0]].append(r["chain"][1])
                has_parent.add(r["chain"][1])
        cursor = [0.0]

        def place(n: _N) -> None:
            ch = children[n]
            if not ch:
                n.c = cursor[0] + csize(n) / 2
                cursor[0] += csize(n) + gap_c
                return
            for c in ch:
                place(c)
            n.c = (ch[0].c + ch[-1].c) / 2

        for r in [n for n in nodes if n not in has_parent]:
            place(r)
        for L in range(nl):
            order[L].sort(key=lambda n: n.c)
            _spread(order[L], [n.c for n in order[L]], csize, gap_c)
    else:
        for it in range(10):
            downpass = it % 2 == 0
            rng = range(1, nl) if downpass else range(nl - 2, -1, -1)
            for L in rng:
                desired = []
                for n in order[L]:
                    nbrs = (up if downpass else down).get(n, [])
                    desired.append(sum(m.c for m in nbrs) / len(nbrs) if nbrs else n.c)
                _spread(order[L], desired, csize, gap_c)

    # main-axis positions
    main_pos: Dict[int, float] = {}
    band: Dict[int, Tuple[float, float]] = {}
    pos = 0.0
    for L in range(nl):
        real = [n for n in order[L] if not n.dummy]
        mh = max([msize(n) for n in real] + [20.0])
        main_pos[L] = pos + mh / 2
        band[L] = (pos - gap_m * 0.38, pos + mh + gap_m * 0.38)
        pos += mh + gap_m
    for L in range(nl):
        for n in order[L]:
            n.m = main_pos[L]
            n.x, n.y = (n.c, n.m) if tb else (n.m, n.c)

    # edges
    drawn: List[_Edge] = []
    for r in routes:
        e = r["e"]
        a, b = byid[e["src"]], byid[e["tgt"]]
        ed = _Edge(e, a, b)
        if r["kind"] == "self":
            _self_loop(ed)
        elif r["kind"] == "same":
            _curve_edge(ed, 30.0, prefer_up=True)
        else:
            chain = r["chain"]
            pts = [(n.x, n.y) for n in chain]
            pts[0] = _clip(chain[0], *pts[1])
            pts[-1] = _clip(chain[-1], *pts[-2])
            if r["flip"]:
                pts.reverse()
            _poly_edge(ed, pts)
        drawn.append(ed)
    _pair_offsets([d for d in drawn if d.a is not d.b])

    bnds = _Bounds()
    parts: List[str] = []
    names = spec.get("layer_names") or []
    if spec["diagram_type"] == "layered" and names:
        # light bands + layer captions
        xs = [n.x - n.w / 2 for n in nodes] + [n.x + n.w / 2 for n in nodes]
        ys = [n.y - n.h / 2 for n in nodes] + [n.y + n.h / 2 for n in nodes]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        for L in range(min(nl, len(names))):
            lo, hi = band[L]
            if tb:
                x0, x1 = minx - 120, maxx + 20
                parts.append(f'<rect x="{x0:.1f}" y="{lo:.1f}" width="{x1 - x0:.1f}" height="{hi - lo:.1f}" fill="#F8FAFC" '
                             f'stroke="{GRID}" stroke-dasharray="4 3"/>')
                parts.append(_text(x0 + 8, (lo + hi) / 2 + 4, names[L], 11, fill=MUTED, anchor="start", italic=True))
                bnds.box(x0, lo, x1, hi)
            else:
                parts.append(_text(main_pos[L], miny - 26, names[L], 11, fill=MUTED, italic=True))
                bnds.box(main_pos[L] - _tw(names[L], 11) / 2, miny - 40, main_pos[L] + _tw(names[L], 11) / 2, miny - 20)
    dense = len(drawn) > 14
    parts.append(_edges_svg(drawn, uid, bnds, dense=dense))
    for n in nodes:
        parts.append(_node_svg(n))
        bnds.box(n.x - n.w / 2, n.y - n.h / 2, n.x + n.w / 2, n.y + n.h / 2)
        if n.kind == "initial_state":
            parts.append(f'<path d="M {n.x - n.w / 2 - 26:.1f} {n.y:.1f} L {n.x - n.w / 2:.1f} {n.y:.1f}" stroke="{INK}" '
                         f'stroke-width="1.5" fill="none" marker-end="url(#arr-{uid})"/>')
            bnds.add(n.x - n.w / 2 - 26, n.y)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Graph layout (weighted/undirected graphs): crossing-minimising force layout
# --------------------------------------------------------------------------

def _seg_cross(p1: Pt, p2: Pt, p3: Pt, p4: Pt) -> bool:
    def o(a: Pt, b: Pt, c: Pt) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (o(p1, p2, p3) * o(p1, p2, p4) < 0) and (o(p3, p4, p1) * o(p3, p4, p2) < 0)


def _dist_pt_seg(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _score_layout(pos: List[Pt], idx_edges: List[Tuple[int, int]], radii: List[float]) -> float:
    score = 0.0
    n = len(pos)
    for i in range(n):
        for j in range(i + 1, n):
            if math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]) < radii[i] + radii[j] + 26:
                score += 800
    for a in range(len(idx_edges)):
        i, j = idx_edges[a]
        score += math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]) / 100.0
        for k in range(n):
            if k not in (i, j) and _dist_pt_seg(pos[k], pos[i], pos[j]) < radii[k] + 5:
                score += 600
        for b in range(a + 1, len(idx_edges)):
            k, l = idx_edges[b]
            if len({i, j, k, l}) == 4 and _seg_cross(pos[i], pos[j], pos[k], pos[l]):
                score += 1000
    return score


def _layout_graph(spec: Dict[str, Any], uid: str) -> str:
    nodes = [_N(n["id"], n["label"], n["sublabel"], n["kind"], None) for n in spec["nodes"]]
    for n in nodes:
        _measure(n, _wrap_width_for(n.kind))
    byid = {n.id: n for n in nodes}
    index = {n.id: i for i, n in enumerate(nodes)}
    n = len(nodes)
    radii = [x.w / 2 for x in nodes]
    idx_edges = [(index[e["src"]], index[e["tgt"]]) for e in spec["edges"] if e["src"] != e["tgt"]]
    W = max(430.0, math.sqrt(n * 120 * 100 * 1.6))
    H = W / 1.55
    margin = max(radii) + 14

    def circular() -> List[Pt]:
        return [(W / 2 + (W / 2 - margin) * math.sin(2 * math.pi * i / n),
                 H / 2 - (H / 2 - margin) * math.cos(2 * math.pi * i / n)) for i in range(n)]

    def force(seed: int) -> List[Pt]:
        rnd = random.Random(seed * 7919 + n)
        pos = [[rnd.uniform(margin, W - margin), rnd.uniform(margin, H - margin)] for _ in range(n)]
        k = math.sqrt(W * H / n) * 0.9
        iters = 260
        for it in range(iters):
            t = (W / 9.0) * (1 - it / iters) + 0.5
            disp = [[0.0, 0.0] for _ in range(n)]
            for i in range(n):
                for j in range(i + 1, n):
                    dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
                    d = math.hypot(dx, dy) or 0.01
                    f = (k * k) / d
                    if d < radii[i] + radii[j] + 28:
                        f *= 3
                    disp[i][0] += dx / d * f
                    disp[i][1] += dy / d * f
                    disp[j][0] -= dx / d * f
                    disp[j][1] -= dy / d * f
            for i, j in idx_edges:
                dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
                d = math.hypot(dx, dy) or 0.01
                f = (d * d) / k
                disp[i][0] -= dx / d * f
                disp[i][1] -= dy / d * f
                disp[j][0] += dx / d * f
                disp[j][1] += dy / d * f
            for i in range(n):
                d = math.hypot(*disp[i]) or 0.01
                step = min(d, t)
                pos[i][0] = min(W - margin, max(margin, pos[i][0] + disp[i][0] / d * step))
                pos[i][1] = min(H - margin, max(margin, pos[i][1] + disp[i][1] / d * step))
        return [(p[0], p[1]) for p in pos]

    candidates = [circular()] + [force(s) for s in range(1, 8)]
    best = min(candidates, key=lambda p: _score_layout(p, idx_edges, radii))
    for nd, (x, y) in zip(nodes, best):
        nd.x, nd.y = x, y

    drawn: List[_Edge] = []
    for e in spec["edges"]:
        a, b = byid[e["src"]], byid[e["tgt"]]
        ed = _Edge(e, a, b)
        if a is b:
            _self_loop(ed)
        else:
            _poly_edge(ed, [_clip(a, b.x, b.y), _clip(b, a.x, a.y)])
        drawn.append(ed)
    _pair_offsets([d for d in drawn if d.a is not d.b])
    bnds = _Bounds()
    parts = [_edges_svg(drawn, uid, bnds)]
    for nd in nodes:
        parts.append(_node_svg(nd))
        bnds.box(nd.x - nd.w / 2, nd.y - nd.h / 2, nd.x + nd.w / 2, nd.y + nd.h / 2)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Sequence diagram
# --------------------------------------------------------------------------

def _render_sequence(spec: Dict[str, Any], uid: str) -> str:
    actors = [_N(n["id"], n["label"], n["sublabel"], "component", None) for n in spec["nodes"]]
    for a in actors:
        _measure(a, 120)
    byid = {a.id: a for a in actors}
    col = max(130.0, max(a.w for a in actors) + 34)
    for i, a in enumerate(actors):
        a.x = col * i + col / 2
    head_h = max(a.h for a in actors)
    for a in actors:
        a.h = head_h
        a.y = head_h / 2
    y = head_h + 38
    rows: List[str] = []
    bnds = _Bounds()
    for e in spec["edges"]:
        s, t = byid[e["src"]], byid[e["tgt"]]
        label = e.get("label", "")
        dash = ' stroke-dasharray="6 4"' if e.get("dashed") else ""
        if s is t:
            rows.append(f'<path d="M {s.x:.1f} {y:.1f} h 34 v 18 h -34" fill="none" stroke="{INK}" stroke-width="1.5"{dash} '
                        f'marker-end="url(#arr-{uid})"/>')
            if label:
                rows.append(_text(s.x + 40, y + 8, label, 11, anchor="start", italic=True))
                bnds.add(s.x + 40 + _tw(label, 11), y)
            y += 46
        else:
            span = abs(t.x - s.x) - 12
            lines = _wrap(label, 11, max(span, 60), max_lines=2) if label else []
            x1, x2 = s.x, t.x
            rows.append(f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{INK}" stroke-width="1.5"{dash} '
                        f'marker-end="url(#arr-{uid})"/>')
            for li, ln in enumerate(lines):
                ly = y - 6 - (len(lines) - 1 - li) * 13
                rows.append(_text((x1 + x2) / 2, ly, ln, 11, italic=True, halo=True))
            y += 40 + 13 * max(0, len(lines) - 1)
    end_y = y
    parts: List[str] = []
    for a in actors:
        parts.append(f'<line x1="{a.x:.1f}" y1="{head_h:.1f}" x2="{a.x:.1f}" y2="{end_y:.1f}" stroke="#94A3B8" '
                     f'stroke-width="1.2" stroke-dasharray="5 4"/>')
    parts.extend(rows)
    for a in actors:
        parts.append(_node_svg(a))
        bnds.box(a.x - a.w / 2, 0, a.x + a.w / 2, head_h)
    bnds.add(actors[0].x - col / 2, end_y)
    bnds.add(actors[-1].x + col / 2, end_y)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Table
# --------------------------------------------------------------------------

def _render_table(spec: Dict[str, Any], uid: str) -> str:
    headers, rows = spec["table"]["headers"], spec["table"]["rows"]
    cols = len(headers)
    colw = []
    for c in range(cols):
        cells = [headers[c]] + [r[c] for r in rows]
        wmax = max(_tw(x, FS, bold=(i == 0)) for i, x in enumerate(cells))
        colw.append(min(180.0, max(54.0, wmax + 22)))
    hdr = [_wrap(h, FS, colw[c] - 14, True, 3) for c, h in enumerate(headers)]
    body = [[_wrap(cell, FS, colw[c] - 14, False, 3) for c, cell in enumerate(r)] for r in rows]
    heights = [max(len(l) for l in hdr) * LH + 12] + [max(len(l) for l in rl) * LH + 12 for rl in body]
    width, height = sum(colw), sum(heights)
    parts: List[str] = []
    y = 0.0
    for ri, rh in enumerate(heights):
        x = 0.0
        for c in range(cols):
            fill = "#E2E8F0" if ri == 0 else ("#FFFFFF" if ri % 2 else "#F8FAFC")
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{colw[c]:.1f}" height="{rh:.1f}" fill="{fill}" stroke="#94A3B8" stroke-width="0.9"/>')
            lines = hdr[c] if ri == 0 else body[ri - 1][c]
            ty = y + rh / 2 - len(lines) * LH / 2
            for ln in lines:
                parts.append(_text(x + colw[c] / 2, ty + LH * 0.5 + FS * 0.35, ln, FS, bold=(ri == 0)))
                ty += LH
            x += colw[c]
        y += rh
    parts.append(f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    bnds = _Bounds()
    bnds.box(0, 0, width, height)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Gantt
# --------------------------------------------------------------------------

def _fmt(v: float) -> str:
    return f"{v:g}"


def _render_gantt(spec: Dict[str, Any], uid: str) -> str:
    segs = spec["segments"]
    t0, t1 = min(s["start"] for s in segs), max(s["end"] for s in segs)
    W, left = 580.0, 4.0
    sc = (W - 2 * left) / (t1 - t0)
    bar_y, bar_h = 6.0, 46.0
    parts: List[str] = []
    for i, s in enumerate(segs):
        x, w = left + (s["start"] - t0) * sc, (s["end"] - s["start"]) * sc
        parts.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" fill="{"#E2E8F0" if i % 2 else "#F1F5F9"}" '
                     f'stroke="{INK}" stroke-width="1.5"/>')
        size = 12.0
        label = s["label"]
        while size > 8.5 and _tw(label, size, True) > w - 6:
            size -= 0.5
        if _tw(label, size, True) > w - 6:
            while len(label) > 1 and _tw(label + "…", size, True) > w - 6:
                label = label[:-1]
            label += "…"
        parts.append(_text(x + w / 2, bar_y + bar_h / 2 + size * 0.35, label, size, bold=True))
    ticks = sorted({s["start"] for s in segs} | {s["end"] for s in segs})
    last_x = -100.0
    for v in ticks:
        x = left + (v - t0) * sc
        parts.append(f'<line x1="{x:.1f}" y1="{bar_y + bar_h}" x2="{x:.1f}" y2="{bar_y + bar_h + 6}" stroke="{INK}" stroke-width="1.2"/>')
        if x - last_x >= 20:
            parts.append(_text(x, bar_y + bar_h + 20, _fmt(v), 11, fill=MUTED))
            last_x = x
    bnds = _Bounds()
    bnds.box(0, 0, W, bar_y + bar_h + 28)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Plot
# --------------------------------------------------------------------------

def _nice_ticks(lo: float, hi: float, n: int = 5) -> List[float]:
    if hi - lo < 1e-12:
        lo, hi = lo - 1, hi + 1
    raw = (hi - lo) / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = mag
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    start, end = math.floor(lo / step) * step, math.ceil(hi / step) * step
    ticks, v = [], start
    while v <= end + step * 1e-6:
        ticks.append(round(v, 10))
        v += step
    return ticks


_DASH = ["", "7 4", "2 3", "10 3 2 3"]
_COLORS = [INK, "#2563EB", "#DC2626", "#16A34A"]


def _render_plot(spec: Dict[str, Any], uid: str) -> str:
    p = spec["plot"]
    series = p["series"]
    xs = [pt[0] for s in series for pt in s["points"]] + [a["x"] for a in p["annotations"]]
    ys = [pt[1] for s in series for pt in s["points"]] + [a["y"] for a in p["annotations"]]
    xt, yt = _nice_ticks(min(xs), max(xs)), _nice_ticks(min(ys), max(ys))
    xmin, xmax, ymin, ymax = xt[0], xt[-1], yt[0], yt[-1]
    W, H, L, R, T, B = 600.0, 340.0, 62.0, 22.0, 20.0, 56.0
    pw, ph = W - L - R, H - T - B

    def X(v: float) -> float:
        return L + (v - xmin) / (xmax - xmin) * pw

    def Y(v: float) -> float:
        return T + ph - (v - ymin) / (ymax - ymin) * ph

    parts: List[str] = []
    for v in xt:
        parts.append(f'<line x1="{X(v):.1f}" y1="{T}" x2="{X(v):.1f}" y2="{T + ph}" stroke="#E2E8F0" stroke-width="1"/>')
        parts.append(f'<line x1="{X(v):.1f}" y1="{T + ph}" x2="{X(v):.1f}" y2="{T + ph + 5}" stroke="{INK}"/>')
        parts.append(_text(X(v), T + ph + 19, _fmt(v), 11, fill=MUTED))
    for v in yt:
        parts.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{L + pw}" y2="{Y(v):.1f}" stroke="#E2E8F0" stroke-width="1"/>')
        parts.append(f'<line x1="{L - 5}" y1="{Y(v):.1f}" x2="{L}" y2="{Y(v):.1f}" stroke="{INK}"/>')
        parts.append(_text(L - 9, Y(v) + 4, _fmt(v), 11, fill=MUTED, anchor="end"))
    parts.append(f'<path d="M {L} {T} L {L} {T + ph} L {L + pw} {T + ph}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    if p["x_label"]:
        parts.append(_text(L + pw / 2, H - 12, p["x_label"], 12, bold=True))
    if p["y_label"]:
        parts.append(_text(16, T + ph / 2, p["y_label"], 12, bold=True, extra=f' transform="rotate(-90 16 {T + ph / 2:.1f})"'))
    for si, s in enumerate(series):
        col, dash = _COLORS[si % 4], _DASH[si % 4]
        pts = [(X(a), Y(b)) for a, b in s["points"]]
        if s["style"] == "scatter":
            for (px, py) in pts:
                if si % 3 == 0:
                    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{col}"/>')
                elif si % 3 == 1:
                    parts.append(f'<rect x="{px - 3.5:.1f}" y="{py - 3.5:.1f}" width="7" height="7" fill="{col}"/>')
                else:
                    parts.append(f'<polygon points="{px:.1f},{py - 4.5:.1f} {px + 4.2:.1f},{py + 3.2:.1f} {px - 4.2:.1f},{py + 3.2:.1f}" fill="{col}"/>')
        else:
            d = _path_from_points(pts) if s["style"] == "curve" and len(pts) > 2 else \
                "M " + " L ".join(f"{a:.1f} {b:.1f}" for a, b in pts)
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
            parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2"{dash_attr}/>')
    for a in p["annotations"]:
        parts.append(f'<circle cx="{X(a["x"]):.1f}" cy="{Y(a["y"]):.1f}" r="4" fill="#FFFFFF" stroke="{INK}" stroke-width="1.6"/>')
        parts.append(_text(X(a["x"]) + 8, Y(a["y"]) - 8, a["text"], 11, anchor="start", italic=True, halo=True))
    named = [(i, s) for i, s in enumerate(series) if s["name"]]
    if named:
        lw = max(_tw(s["name"], 11) for _, s in named) + 44
        lx, ly = L + pw - lw - 6, T + 6
        parts.append(f'<rect x="{lx:.1f}" y="{ly}" width="{lw:.1f}" height="{len(named) * 17 + 8}" fill="#FFFFFF" stroke="{GRID}"/>')
        for k, (i, s) in enumerate(named):
            yy = ly + 16 + k * 17
            col, dash = _COLORS[i % 4], _DASH[i % 4]
            if s["style"] == "scatter":
                parts.append(f'<circle cx="{lx + 16:.1f}" cy="{yy - 4:.1f}" r="4" fill="{col}"/>')
            else:
                dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
                parts.append(f'<line x1="{lx + 6:.1f}" y1="{yy - 4:.1f}" x2="{lx + 26:.1f}" y2="{yy - 4:.1f}" stroke="{col}" stroke-width="2"{dash_attr}/>')
            parts.append(_text(lx + 32, yy, s["name"], 11, anchor="start"))
    bnds = _Bounds()
    bnds.box(0, 0, W, H)
    return _svg_doc("".join(parts), bnds, uid)


# --------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------

def render_spec(spec: Dict[str, Any], uid: str = "fig") -> str:
    """Render a *normalised* spec to SVG."""
    t = spec["diagram_type"]
    if t == "table":
        return _render_table(spec, uid)
    if t == "gantt":
        return _render_gantt(spec, uid)
    if t == "plot":
        return _render_plot(spec, uid)
    if t == "sequence":
        return _render_sequence(spec, uid)
    if t == "graph":
        return _layout_graph(spec, uid)
    if t == "tree":
        return _layout_flow(spec, uid, tree_mode=_is_forest(spec["nodes"], spec["edges"]))
    return _layout_flow(spec, uid)          # flowchart, state_machine, layered


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def _q_num(question_num: Any) -> str:
    q = str(question_num).replace("Question ", "Q").replace("Q.", "Q")
    return f"Q{q}" if q.isdigit() else q


def generate_ai_diagram(
    topic: str,
    question_text: str,
    bloom_level: str = "L2",
    question_num: Any = "1",
    marks: Any = None,
    custom_prompt: Optional[str] = None,
    api_config: Optional[Dict[str, str]] = None,
    diagram_type: Optional[str] = None,
    force: bool = False,
    variation: int = 0,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Returns (figure, status).
    status: "ok" | "not_needed" (model judged the question needs no figure) |
            "unavailable" (no API key) | "failed" (LLM/validation/render failed)
    """
    if not llm_client.is_available(api_config):
        return None, "unavailable"

    q_num = _q_num(question_num)
    user_prompt = build_user_prompt(question_text, topic, bloom_level, marks, q_num, custom_prompt, diagram_type, variation)
    temperature = 0.3 if not variation else min(0.9, 0.5 + 0.1 * variation)

    raw, model_used = _call_llm(SYSTEM_PROMPT, user_prompt, api_config, temperature)
    spec, errors = normalize_spec(raw, q_num) if raw is not None else (None, ["no response"])

    soft = (spec or {}).get("warnings") or []
    if raw is not None and (errors or soft):
        repair_prompt = (
            f"{user_prompt}\n\nYour previous JSON had these problems:\n- " + "\n- ".join(list(errors) + list(soft)) +
            f"\n\nPrevious JSON:\n{json.dumps(raw)[:6000]}\n\nReturn a corrected JSON object only."
        )
        raw2, model2 = _call_llm(SYSTEM_PROMPT, repair_prompt, api_config, 0.2)
        if raw2 is not None:
            spec2, errors2 = normalize_spec(raw2, q_num)
            if not errors2 or errors:          # never trade a drawable diagram for a broken one
                spec, errors = spec2, errors2
                model_used = model2 or model_used

    if spec is None or errors:
        reason = errors or llm_client.last_errors[-3:] or ["no response from any provider"]
        log.warning("AI diagram failed for %s: %s", q_num, "; ".join(map(str, reason)))
        return None, "failed"

    if spec["needs_diagram"] and spec["diagram_type"] == "flowchart":
        asked = re.search(r"flow\s*-?chart|flow\s*diagram", f"{question_text} {custom_prompt or ''}", re.I) \
            or (diagram_type or "").lower() == "flowchart"
        if not asked and not force:      # a teacher pressing "add diagram" always gets one
            log.info("Dropping process flowchart for %s: question does not ask for one", q_num)
            return None, "not_needed"
    if not spec["needs_diagram"] and not force:
        return None, "not_needed"
    if not spec["needs_diagram"]:
        return None, "failed"        # forced but the model had nothing to draw -> let the caller fall back

    uid = re.sub(r"[^A-Za-z0-9]", "", q_num) + hashlib.md5(
        f"{question_text}{random.random()}".encode()).hexdigest()[:6]
    try:
        svg = render_spec(spec, uid)
    except Exception:
        log.exception("Rendering AI diagram spec failed")
        return None, "failed"

    return {
        "figure_id": f"fig_{q_num}",
        "title": spec["title"],
        "caption": spec["caption"],
        "svg": svg,
        "diagram_type": "ai_synthesized",
        "ai_diagram_type": spec["diagram_type"],
        "ai_model": model_used,
        "spec": spec,
    }, "ok"
