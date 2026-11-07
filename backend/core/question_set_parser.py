"""
Question Set Parser
Reads an uploaded question set (PDF / DOCX / TXT / MD / CSV / JSON), extracts every question with its
marks, then derives Unit names, Course Outcomes (CO) and Program Outcomes (PO) *from the questions
themselves* - no syllabus required and no network/LLM calls.
"""

import io
import re
import csv
import json
import math
from collections import Counter, OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from config import BLOOM_LEVELS

MAX_QUESTIONS = 300

# ---------------------------------------------------------------------------
# Bloom level detection from the leading action verb
# ---------------------------------------------------------------------------
_VERB_LEVEL = OrderedDict()
for _lvl, _verbs in {
    "L6": ["design", "create", "develop", "formulate", "propose", "devise", "invent", "compose",
           "synthesize", "synthesise", "plan", "build", "generate", "hypothesize", "architect"],
    "L5": ["evaluate", "justify", "assess", "critique", "judge", "recommend", "argue", "defend",
           "appraise", "rate", "validate", "prioritize", "prioritise", "criticize", "criticise"],
    "L4": ["analyze", "analyse", "compare", "contrast", "differentiate", "categorize", "categorise",
           "examine", "investigate", "deconstruct", "derive", "distinguish", "diagnose", "dissect",
           "break down"],
    "L3": ["apply", "solve", "compute", "calculate", "determine", "construct", "demonstrate", "use",
           "perform", "find", "draw", "sketch", "implement", "execute", "trace", "show", "illustrate",
           "modify", "prepare", "write a program", "write a query", "write an algorithm", "simulate"],
    "L2": ["explain", "describe", "discuss", "summarize", "summarise", "classify", "interpret",
           "outline", "elaborate", "paraphrase", "give example", "predict", "estimate", "express",
           "convert", "translate", "review", "infer"],
    "L1": ["define", "list", "state", "name", "identify", "label", "recall", "mention", "enumerate",
           "recognize", "recognise", "what", "who", "when", "which", "match", "select", "tabulate",
           "write", "repeat", "reproduce"],
}.items():
    for _v in _verbs:
        _VERB_LEVEL[_v] = _lvl

# ---------------------------------------------------------------------------
# Program outcomes (NBA / AICTE graduate attributes)
# ---------------------------------------------------------------------------
PO_TITLES = {
    "PO1": "Engineering knowledge",
    "PO2": "Problem analysis",
    "PO3": "Design / development of solutions",
    "PO4": "Conduct investigations of complex problems",
    "PO5": "Modern tool usage",
    "PO6": "The engineer and society",
    "PO7": "Environment and sustainability",
    "PO8": "Ethics",
    "PO9": "Individual and team work",
    "PO10": "Communication",
    "PO11": "Project management and finance",
    "PO12": "Life-long learning",
}

_PO_KEYWORDS = [
    ("PO3", r"\b(design|develop|architecture|build|implement|construct a|propose|formulate)\b"),
    ("PO4", r"\b(experiment|hypothes|investigat|test of|significance|confidence|evaluate (?:the )?performance|compare|validate|analy[sz]e (?:the )?data)\b"),
    ("PO5", r"\b(tool|software|simulat|python|sql|library|package|framework|matlab|compiler|query|program)\b"),
    ("PO6", r"\b(society|social|health|safety|fairness|public)\b"),
    ("PO7", r"\b(environment|sustainab|energy|green|carbon)\b"),
    ("PO8", r"\b(ethic|privacy|responsible|confidential)\b"),
    ("PO9", r"\b(team|collaborat|group)\b"),
    ("PO10", r"\b(report|present|document|communicat)\b"),
    ("PO11", r"\b(cost|budget|schedule|project management|economic)\b"),
    ("PO12", r"\b(latest|emerging|recent|trend|future|state[- ]of[- ]the[- ]art)\b"),
]
_PO_BY_LEVEL = {"L1": "PO1", "L2": "PO1", "L3": "PO2", "L4": "PO2", "L5": "PO4", "L6": "PO3"}

_CO_TEMPLATES = {
    "L1": "Recall the fundamental terms, definitions and concepts of {u}.",
    "L2": "Explain the principles, working and significance of {u}.",
    "L3": "Apply the methods and techniques of {u} to solve problems.",
    "L4": "Analyze and compare approaches in {u}.",
    "L5": "Evaluate and justify design choices in {u}.",
    "L6": "Design and develop solutions using {u}.",
}

# ---------------------------------------------------------------------------
# Text extraction from the uploaded file
# ---------------------------------------------------------------------------

def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        from core.syllabus_parser import extract_text_from_pdf
        return extract_text_from_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    return data.decode("utf-8", errors="replace")


def _extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    lines: List[str] = []
    body = doc.element.body
    # Walk the body in document order so tables stay where they appear
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            txt = "".join(t.text or "" for t in child.iter() if t.tag.rsplit("}", 1)[-1] == "t")
            lines.append(txt)
        elif tag == "tbl":
            from docx.table import Table
            table = Table(child, doc)
            for row in table.rows:
                cells = []
                for c in row.cells:
                    t = " ".join(c.text.split())
                    if t and (not cells or cells[-1] != t):   # merged cells repeat their text
                        cells.append(t)
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Line-level question extraction
# ---------------------------------------------------------------------------
_RE_Q_PREFIX = re.compile(r"^\s*(?:Q(?:uestion)?\s*\.?\s*)(\d{1,3})\s*[\.\):\-]?\s*(.*)$", re.I)
_RE_NUM = re.compile(r"^\s*\(?(\d{1,3})\s*[\.\)]\s+(.*)$")
_RE_SUB = re.compile(r"^\s*\(?([a-z])\)\s+(.*)$")
_RE_ROMAN = re.compile(r"^\s*\(?(i{1,3}|iv|vi{0,3}|ix|x)\)\s+(.*)$", re.I)
_RE_UNIT_HEAD = re.compile(r"^\s*(?:unit|module|chapter)\s*[-:]?\s*([0-9]+|[ivx]+)\s*[:\-–—.]?\s*(.*)$", re.I)
_RE_SECTION = re.compile(r"^\s*(?:section|part)\s+[a-z0-9]+\b.*$", re.I)
_RE_NOISE = re.compile(
    r"^\s*(?:page\s*\d+(?:\s*of\s*\d+)?|total marks.*|max(?:imum)?\.? marks.*|time\s*[:\-].*|duration.*|"
    r"instructions?\s*:?.*|note\s*:.*|answer (?:any|all|the following).*|all questions.*|figures? to the right.*|"
    r"\*+.*|[-_=~ ]{3,}|or|[-– ]*or[-– ]*|end of .*)\s*$", re.I)
_META_ONLY = re.compile(r"^(?:\s*(?:CO\s*\d+|BL?\s*\d|L\s*[1-6]|PO\s*\d+|\d{1,2}\s*(?:marks?|m|mks)?|marks?|[,/|:\-])\s*)+$", re.I)
_RE_BRACKET = re.compile(r"[\[\(]([^\]\)]{1,40})[\]\)]")
_RE_CO = re.compile(r"\bCO\s*[-:]?\s*(\d{1,2})\b", re.I)
_RE_LEVEL = re.compile(r"\b(?:BL|L)\s*[-:]?\s*([1-6])\b", re.I)
_RE_UNIT_TAG = re.compile(r"\b(?:unit|module|u)\s*[-:]?\s*(\d{1,2})\b", re.I)


def _find_marks(text: str) -> Tuple[Optional[int], str]:
    """Return (marks, text_without_marks_marker)."""
    patterns = [
        r"[\[\(]\s*(\d{1,2})\s*(?:marks?|mks|m|pts|points)?\s*[\]\)]\s*[.\u2013\u2014-]?\s*$",
        r"[\[\(]\s*(\d{1,2})\s*(?:marks?|mks|m|pts|points)\s*[\]\)]",
        r"\b(\d{1,2})\s*(?:marks?|mks)\b",
        r"\bmarks?\s*[:=]\s*(\d{1,2})\b",
        r"[\u2013\u2014-]\s*(\d{1,2})\s*(?:m|marks?)?\s*$",
        r"\b(\d{1,2})\s*M\s*$",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 30:
                return val, (text[:m.start()] + " " + text[m.end():]).strip(" \t-–—:,.")
    return None, text


def _strip_meta(text: str) -> Tuple[str, Dict[str, Any]]:
    """Pull CO / Bloom / Unit / PO tags out of bracketed groups; return clean text + tags."""
    tags: Dict[str, Any] = {}

    def _sub(m):
        inner = m.group(1)
        if _META_ONLY.match(inner) and re.search(r"CO\s*\d|\bBL?\s*\d|\bL\s*[1-6]|PO\s*\d|marks?", inner, re.I):
            co = _RE_CO.search(inner)
            lv = _RE_LEVEL.search(inner)
            po = re.search(r"\bPO\s*(\d{1,2})\b", inner, re.I)
            if co:
                tags["co"] = f"CO{int(co.group(1))}"
            if lv:
                tags["bloom_level"] = f"L{lv.group(1)}"
            if po:
                tags["po"] = f"PO{int(po.group(1))}"
            return " "
        return m.group(0)

    cleaned = _RE_BRACKET.sub(_sub, text)
    if "co" not in tags:
        m = re.search(r"\bCO\s*[-:]?\s*(\d{1,2})\b\s*$", cleaned, re.I)
        if m:
            tags["co"] = f"CO{int(m.group(1))}"
            cleaned = cleaned[:m.start()]
    return re.sub(r"\s{2,}", " ", cleaned).strip(" \t-–—:,"), tags


def _detect_bloom(text: str, marks: Optional[int]) -> str:
    low = text.lower()
    head = re.findall(r"[a-z]+", low)[:12]
    head_text = " ".join(head)
    # multi-word verbs first
    for verb, lvl in _VERB_LEVEL.items():
        if " " in verb and head_text.startswith(verb):
            return lvl
    for w in head[:4]:                         # leading verb is the strongest signal
        if w in _VERB_LEVEL:
            return _VERB_LEVEL[w]
    for w in head:                             # otherwise first verb that appears
        if w in _VERB_LEVEL and w not in ("use", "show", "find", "what", "which", "who", "when", "write", "name"):
            return _VERB_LEVEL[w]
    if marks is None:
        return "L2"
    return "L1" if marks <= 2 else "L2" if marks <= 5 else "L3" if marks <= 8 else "L4"


def _parse_table_row(line: str) -> Optional[Dict[str, Any]]:
    """Handle rows like '1 | Explain X | 5 | CO1 | L2' produced from DOCX tables."""
    if " | " not in line:
        return None
    cells = [c.strip() for c in line.split(" | ") if c.strip()]
    if len(cells) < 2:
        return None
    text_cell = max(cells, key=lambda c: len(c.split()))
    if len(text_cell.split()) < 3:
        return None
    marks = co = lvl = unit = None
    for c in cells:
        if c is text_cell:
            continue
        if re.fullmatch(r"\d{1,2}\s*(?:m|marks?)?", c, re.I) and marks is None:
            v = int(re.match(r"\d+", c).group(0))
            if 1 <= v <= 30:
                marks = v
        elif re.fullmatch(r"CO\s*\d+", c, re.I):
            co = "CO" + re.search(r"\d+", c).group(0)
        elif re.fullmatch(r"(?:BL|L)\s*[1-6]", c, re.I):
            lvl = "L" + re.search(r"[1-6]", c).group(0)
        elif re.fullmatch(r"(?:unit|module)\s*\d+", c, re.I):
            unit = int(re.search(r"\d+", c).group(0))
    return {"text": text_cell, "marks": marks, "co": co, "bloom_level": lvl, "unit_num": unit}


def _starts_like_question(line: str) -> bool:
    words = re.findall(r"[A-Za-z]+", line.lower())
    if not words:
        return False
    if words[0] in _VERB_LEVEL and words[0] not in ("use", "show", "find", "which", "when", "who", "name", "select", "match", "write", "list"):
        return True
    if words[0] == "write" and len(words) > 1 and words[1] in ("a", "an", "short", "the", "notes", "program", "query"):
        return True
    return line.rstrip().endswith("?") and len(words) >= 4


def _buffer_is_complete(buf: List[str]) -> bool:
    last = " ".join(buf).rstrip()
    return bool(last) and (last[-1] in ".?!])" or bool(re.search(r"\d\s*(?:m|marks?)?\s*[\]\)]?$", last, re.I)))


def _extract_questions(raw: str) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    """Return (questions, explicit_unit_titles)."""
    items: List[Dict[str, Any]] = []
    unit_titles: Dict[int, str] = {}
    cur_unit: Optional[int] = None
    current: Optional[Dict[str, Any]] = None
    group_no: Optional[int] = None
    group_stem: Optional[Dict[str, Any]] = None

    def flush():
        nonlocal current
        if current and current["buf"]:
            current["text"] = " ".join(current["buf"]).strip()
            items.append(current)
        current = None

    def start(text: str, group, sub, parent_marks=None):
        nonlocal current
        flush()
        current = {"buf": [text.strip()], "group": group, "sub": sub, "unit_num": cur_unit,
                   "parent_marks": parent_marks}

    lines = [ln.rstrip() for ln in raw.replace("\r", "\n").split("\n")]
    for line in lines:
        s = line.strip()
        if not s:
            continue
        mu = _RE_UNIT_HEAD.match(s)
        if mu and (len(s.split()) <= 14) and not _RE_NUM.match(s):
            flush()
            tok = mu.group(1)
            num = int(tok) if tok.isdigit() else _roman_to_int(tok)
            cur_unit = num
            if mu.group(2).strip():
                unit_titles[num] = mu.group(2).strip(" :-–—.")
            continue
        if _RE_SECTION.match(s) and len(s.split()) <= 14:
            flush()
            continue
        if _RE_NOISE.match(s):
            if re.fullmatch(r"[-– ]*or[-– ]*", s, re.I):
                flush()
            continue

        row = _parse_table_row(s)
        if row:
            flush()
            current = {"buf": [row["text"]], "group": None, "sub": None, "unit_num": row["unit_num"] or cur_unit,
                       "pre": {k: row[k] for k in ("marks", "co", "bloom_level") if row[k]}, "parent_marks": None}
            flush()
            continue

        mq = _RE_Q_PREFIX.match(s) or _RE_NUM.match(s)
        if mq:
            group_no = int(mq.group(1))
            group_stem = None
            inline_sub = _RE_SUB.match(mq.group(2))      # "Q.1 a) Define ..." - number and sub-part on one line
            if inline_sub:
                start(inline_sub.group(2), group_no, inline_sub.group(1).lower())
            else:
                start(mq.group(2), group_no, None)
            continue
        ms = _RE_SUB.match(s) or _RE_ROMAN.match(s)
        if ms and (group_no is not None or current is not None):
            # a sub-part: the preceding numbered item (if it was only a stem) is demoted to context
            if current is not None and current.get("sub") is None and current.get("group") is not None:
                group_stem = current
                current = None
                if group_stem["buf"]:
                    group_stem["text"] = " ".join(group_stem["buf"]).strip()
            start(ms.group(2), group_no, ms.group(1).lower(),
                  parent_marks=_find_marks(group_stem["text"])[0] if group_stem and group_stem.get("text") else None)
            continue
        if current is not None:
            # an un-numbered line that opens with an action verb, right after a finished question, is a new question
            if current.get("group") is None and current.get("sub") is None and _starts_like_question(s) and _buffer_is_complete(current["buf"]):
                start(s, None, None)
            elif current.get("group") is not None and _starts_like_question(s) and _buffer_is_complete(current["buf"]) \
                    and _find_marks(" ".join(current["buf"]))[0] is not None and current.get("sub") is None:
                start(s, None, None)
            else:
                current["buf"].append(s)
        elif _starts_like_question(s):
            start(s, None, None)
        # else: header / preamble text - ignored
    flush()
    return items, unit_titles


def _roman_to_int(tok: str) -> int:
    vals = {"i": 1, "v": 5, "x": 10}
    total, prev = 0, 0
    for ch in reversed(tok.lower()):
        v = vals.get(ch, 0)
        total += -v if v < prev else v
        prev = max(prev, v)
    return max(total, 1)


# ---------------------------------------------------------------------------
# Keyword analysis, clustering and naming
# ---------------------------------------------------------------------------
_STOP = set("""a an the of in on for to and or with by from at as is are be this that these those what which who whom how why
when where into using use given consider following below above each between among within also can may will shall would should
could their its it we you your whether conclude suppose assume obtain obtained required respective corresponding relevant observation observed resulting correct applicable our any all both either neither not no than then thus hence so such one two three four five six
seven eight nine ten example examples briefly detail detailed suitable appropriate etc eg ie if else about over under per via
write short note notes marks mark question questions answer answers neat diagram diagrams explain describe discuss define state
list name identify differentiate compare contrast analyze analyse evaluate justify design develop derive solve compute
calculate determine construct demonstrate apply perform find draw sketch implement trace show prepare illustrate classify
summarize summarise interpret outline elaborate give mention enumerate recall create formulate propose assess critique
important various different types type role significance concept concepts principle principles basic basics key main major
real world case study based way ways does do did has have had been being more most less least between during after before""".split())
_STOP |= set(_VERB_LEVEL.keys())


def _tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-\+']{1,}", text)


def _stem(w: str) -> str:
    w = w.lower().strip("-'")
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def _content_tokens(text: str) -> List[Tuple[str, str]]:
    """Return [(stem, original_form)] for content words, preserving sequence positions via None gaps."""
    out = []
    for tok in _tokens(text):
        low = tok.lower()
        if low in _STOP or len(low) < 3:
            out.append((None, tok))
        else:
            out.append((_stem(low), tok))
    return out


def _vectorize(docs: List[List[str]]) -> Tuple[List[Dict[str, float]], Dict[str, float]]:
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
    vecs = []
    for d in docs:
        tf = Counter(d)
        v = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs, idf


def _cos(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def _cluster(vecs: List[Dict[str, float]], k: int, min_size: int = 2) -> List[int]:
    """
    Average-link agglomerative clustering into k groups. Questions that sit next to each other in the
    document get a small similarity bonus (papers are usually ordered by unit), and clusters smaller than
    `min_size` are merged into their nearest neighbour so every unit has several questions.
    """
    n = len(vecs)
    if k <= 1 or n <= 1:
        return [0] * n
    if k >= n:
        return list(range(n))
    S = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = _cos(vecs[i], vecs[j]) if vecs[i] and vecs[j] else 0.0
            if j == i + 1:
                v += 0.12
            S[i][j] = S[j][i] = v
    members: Dict[int, List[int]] = {i: [i] for i in range(n)}

    def avg(a: int, b: int) -> float:
        return S[a][b] / (len(members[a]) * len(members[b]))

    def merge(a: int, b: int) -> None:
        for x in members:
            if x not in (a, b):
                S[a][x] += S[b][x]
                S[x][a] = S[a][x]
        members[a].extend(members.pop(b))

    while len(members) > k:
        keys = list(members)
        best, pair = -1.0, (keys[0], keys[1])
        for ai in range(len(keys)):
            for bi in range(ai + 1, len(keys)):
                v = avg(keys[ai], keys[bi])
                if v > best:
                    best, pair = v, (keys[ai], keys[bi])
        merge(*pair)
    while len(members) > 1:
        small = min(members, key=lambda c: len(members[c]))
        if len(members[small]) >= min_size:
            break
        other = max((c for c in members if c != small), key=lambda c: avg(small, c))
        merge(other, small)
    labels = [0] * n
    for lab, (_c, idx) in enumerate(members.items()):
        for i in idx:
            labels[i] = lab
    return labels


def _title_case(phrase_forms: List[str]) -> str:
    out = []
    for w in phrase_forms:
        if w.isupper() and len(w) <= 6:
            out.append(w)
        elif any(c.isupper() for c in w[1:]):
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def _name_cluster(member_idx: List[int], q_tokens: List[List[Tuple[str, str]]], idf: Dict[str, float],
                  forms: Dict[str, str], global_bigram_df: Counter) -> Tuple[str, List[str]]:
    bi_df: Counter = Counter()
    uni_w: Counter = Counter()
    for i in member_idx:
        seq = q_tokens[i]
        seen_bi = set()
        for a, b in zip(seq, seq[1:]):
            if a[0] and b[0]:
                seen_bi.add((a[0], b[0]))
        bi_df.update(seen_bi)
        for st in {st for st, _o in seq if st}:
            uni_w[st] += 1
    scored = sorted(
        ((c / (1 + 0.5 * (global_bigram_df[b] - c)), b) for b, c in bi_df.items() if c >= 2),
        reverse=True)
    big = len(member_idx) >= 3
    ranked_uni = sorted(((c * idf.get(st, 1.0), st) for st, c in uni_w.items() if (c >= 2 or not big)), reverse=True)
    if not ranked_uni:
        ranked_uni = sorted(((c * idf.get(st, 1.0), st) for st, c in uni_w.items()), reverse=True)
    name_parts: List[str] = []
    used: set = set()
    if scored:
        _s, (a, b) = scored[0]
        name_parts.append(_title_case([forms.get(a, a), forms.get(b, b)]))
        used |= {a, b}
    for _w, st in ranked_uni[:8]:
        if st in used:
            continue
        name_parts.append(_title_case([forms.get(st, st)]))
        used.add(st)
        if len(name_parts) >= 2:
            break
    title = " & ".join(name_parts[:2]) if name_parts else "General Topics"
    # topics: distinct strong phrases from the cluster
    topics: List[str] = []
    for _s, (a, b) in scored[:4]:
        topics.append(_title_case([forms.get(a, a), forms.get(b, b)]))
    for _w, st in ranked_uni[:10]:
        t = _title_case([forms.get(st, st)])
        if all(t.lower() not in x.lower() for x in topics):
            topics.append(t)
        if len(topics) >= 6:
            break
    return title, topics


def _question_topic(i: int, q_tokens, idf, forms, unit_title: str) -> str:
    seq = q_tokens[i]
    best, best_score = None, 0.0
    for a, b in zip(seq, seq[1:]):
        if a[0] and b[0]:
            sc = idf.get(a[0], 1) + idf.get(b[0], 1)
            if sc > best_score:
                best, best_score = _title_case([forms.get(a[0], a[1]), forms.get(b[0], b[1])]), sc
    if best:
        return best
    singles = [(idf.get(st, 1), st) for st, _o in seq if st]
    if singles:
        return _title_case([forms.get(max(singles)[1], max(singles)[1])])
    return unit_title


def _detect_po(text: str, level: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    low = text.lower()
    for po, pat in _PO_KEYWORDS:
        if re.search(pat, low):
            return po
    return _PO_BY_LEVEL.get(level, "PO1")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_question_set(filename: str, data: bytes, course_code: str = "CS501",
                       course_name: str = "") -> Dict[str, Any]:
    name = (filename or "questions").strip()
    low = name.lower()

    if low.endswith(".json"):
        raw_questions, unit_titles = _from_json(data)
    elif low.endswith(".csv"):
        raw_questions, unit_titles = _from_csv(data)
    else:
        text = extract_text(name, data)
        if len((text or "").strip()) < 10:
            raise ValueError("The file has no readable text. Scanned image PDFs are not supported.")
        items, unit_titles = _extract_questions(text)
        raw_questions = _items_to_raw(items)
        if not raw_questions:                      # plain unnumbered list of sentences
            for ln in text.splitlines():
                ln = ln.strip()
                if len(ln.split()) >= 5 and not _RE_NOISE.match(ln) and not _RE_UNIT_HEAD.match(ln):
                    marks, ln2 = _find_marks(ln)
                    ln2, tags = _strip_meta(ln2)
                    raw_questions.append({"text": ln2, "marks": marks, **tags, "unit_num": None})
    if not raw_questions:
        raise ValueError("No questions could be found. Number them like '1.', 'Q1.' or '(a)', or use the CSV template.")

    # filter, dedupe, cap
    seen, questions = set(), []
    for q in raw_questions:
        t = re.sub(r"\s{2,}", " ", (q.get("text") or "")).strip()
        if len(t.split()) < 3 or not re.search(r"[A-Za-z]{3}", t):
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        q["text"] = t
        questions.append(q)
    questions = questions[:MAX_QUESTIONS]
    if not questions:
        raise ValueError("No valid questions were found in the file.")

    # marks, bloom
    for q in questions:
        if q.get("marks") is None:
            q["marks"] = None
    known_marks = [q["marks"] for q in questions if q.get("marks")]
    default_marks = Counter(known_marks).most_common(1)[0][0] if known_marks else 5
    for q in questions:
        q["marks_assumed"] = not q.get("marks")
        q["marks"] = int(q["marks"] or default_marks)
        q["bloom_level"] = q.get("bloom_level") or _detect_bloom(q["text"], q["marks"])

    # tokens / vectors
    q_tokens = [_content_tokens(q["text"]) for q in questions]
    docs = [[st for st, _o in seq if st] for seq in q_tokens]
    vecs, idf = _vectorize(docs)
    forms: Dict[str, str] = {}
    form_count: Dict[str, Counter] = {}
    for seq in q_tokens:
        for st, orig in seq:
            if st:
                form_count.setdefault(st, Counter())[orig] += 1
    for st, c in form_count.items():
        forms[st] = c.most_common(1)[0][0]
    global_bi: Counter = Counter()
    for seq in q_tokens:
        global_bi.update({(a[0], b[0]) for a, b in zip(seq, seq[1:]) if a[0] and b[0]})

    # unit assignment: explicit labels win, otherwise cluster the questions by topic
    explicit = [q.get("unit_num") for q in questions]
    explicit_share = sum(1 for u in explicit if u) / len(questions)
    units: List[Dict[str, Any]] = []
    if explicit_share >= 0.6:
        nums = sorted({u for u in explicit if u})
        remap = {n: i + 1 for i, n in enumerate(nums)}
        last = nums[0]
        for q in questions:
            if not q.get("unit_num"):
                q["unit_num"] = last
            last = q["unit_num"]
        for n in nums:
            idx = [i for i, q in enumerate(questions) if q["unit_num"] == n]
            auto_title, topics = _name_cluster(idx, q_tokens, idf, forms, global_bi)
            units.append({"unit_num": remap[n], "title": unit_titles.get(n) or auto_title, "topics": topics, "_idx": idx})
        for q in questions:
            q["unit_num"] = remap[q["unit_num"]]
        unit_source = "labels"
    else:
        n = len(questions)
        k = 1 if n < 4 else min(6, max(2, round(n / 4)))
        assign = _cluster(vecs, k)
        groups: "OrderedDict[int, List[int]]" = OrderedDict()
        for i, a in enumerate(assign):
            groups.setdefault(a, []).append(i)
        for new_no, (_a, idx) in enumerate(groups.items(), 1):
            title, topics = _name_cluster(idx, q_tokens, idf, forms, global_bi)
            units.append({"unit_num": new_no, "title": title, "topics": topics, "_idx": idx})
            for i in idx:
                questions[i]["unit_num"] = new_no
        unit_source = "keywords"

    # make unit titles unique
    seen_titles: Counter = Counter()
    for u in units:
        seen_titles[u["title"]] += 1
        if seen_titles[u["title"]] > 1:
            u["title"] = f"{u['title']} ({u['unit_num']})"

    # COs per unit (explicit CO tags are kept on the questions)
    course_outcomes, unit_by_no = [], {}
    for u in units:
        lvl_counts = Counter(questions[i]["bloom_level"] for i in u["_idx"])
        dominant = lvl_counts.most_common(1)[0][0]
        u["co"] = f"CO{min(u['unit_num'], 12)}"
        course_outcomes.append({"id": u["co"], "description": _CO_TEMPLATES[dominant].format(u=u["title"])})
        u["question_count"] = len(u["_idx"])
        u["marks"] = sum(questions[i]["marks"] for i in u["_idx"])
        unit_by_no[u["unit_num"]] = u
    known_co_ids = {c["id"] for c in course_outcomes}

    out_questions, used_pos = [], set()
    for i, q in enumerate(questions):
        u = unit_by_no[q["unit_num"]]
        co = q.get("co") or u["co"]
        if co not in known_co_ids:
            course_outcomes.append({"id": co, "description": _CO_TEMPLATES[q["bloom_level"]].format(u=u["title"])})
            known_co_ids.add(co)
        topic = _question_topic(i, q_tokens, idf, forms, u["title"])
        po = _detect_po(q["text"], q["bloom_level"], q.get("po"))
        used_pos.add(po)
        verb_m = re.match(r"[A-Za-z]+", q["text"])
        out_questions.append({
            "question_text": q["text"],
            "marks": q["marks"],
            "marks_assumed": q["marks_assumed"],
            "bloom_level": q["bloom_level"],
            "aicte_verb": verb_m.group(0).capitalize() if verb_m else "Explain",
            "co": co,
            "co_description": next((c["description"] for c in course_outcomes if c["id"] == co), ""),
            "po": po,
            "unit_num": u["unit_num"],
            "unit_title": u["title"],
            "topic": topic,
        })

    course_outcomes.sort(key=lambda c: int(re.search(r"\d+", c["id"]).group(0)))
    for u in units:
        u.pop("_idx", None)

    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    set_name = f"Uploaded - {stem[:60]}"
    marks_profile = Counter(str(q["marks"]) for q in out_questions)
    derived_syllabus = {
        "code": course_code or "CS501",
        "name": course_name or stem[:60] or "Uploaded Question Set",
        "total_units": len(units),
        "total_topics": sum(len(u["topics"]) for u in units),
        "course_outcomes": course_outcomes,
        "units": [{"unit_num": u["unit_num"], "title": u["title"], "co": u["co"],
                   "topics": u["topics"] or [u["title"]]} for u in units],
        "extracted_text": "",
        "derived_from": "question_set",
    }
    return {
        "file_name": name,
        "unit_source": unit_source,
        "question_count": len(out_questions),
        "total_marks": sum(q["marks"] for q in out_questions),
        "assumed_marks_count": sum(1 for q in out_questions if q["marks_assumed"]),
        "marks_profile": dict(sorted(marks_profile.items(), key=lambda kv: int(kv[0]))),
        "units": units,
        "course_outcomes": course_outcomes,
        "program_outcomes": [{"id": p, "title": PO_TITLES[p]} for p in sorted(used_pos, key=lambda x: int(x[2:]))],
        "questions": out_questions,
        "syllabus": derived_syllabus,
        "set": {"set_id": "uploaded_set", "set_name": set_name,
                "questions": [{k: v for k, v in q.items() if k != "marks_assumed"} for q in out_questions]},
    }


def _items_to_raw(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn parsed line groups into question dicts (marks/meta extracted)."""
    # Parents that only act as a stem for sub-parts are dropped
    group_has_subs = {it["group"] for it in items if it.get("sub") and it.get("group") is not None}
    out = []
    for it in items:
        if it.get("group") in group_has_subs and not it.get("sub") and it.get("group") is not None:
            continue
        text = it.get("text") or " ".join(it["buf"])
        pre = it.get("pre") or {}
        marks, text = _find_marks(text)
        text, tags = _strip_meta(text)
        unit_m = _RE_UNIT_TAG.search(text) if re.search(r"\(\s*(?:unit|module)\s*\d", text, re.I) else None
        unit = it.get("unit_num") or (int(unit_m.group(1)) if unit_m else None)
        out.append({
            "text": text,
            "marks": pre.get("marks") or marks or (it.get("parent_marks") if it.get("sub") else None),
            "co": pre.get("co") or tags.get("co"),
            "bloom_level": pre.get("bloom_level") or tags.get("bloom_level"),
            "po": tags.get("po"),
            "unit_num": unit,
        })
    return out


def _from_json(data: bytes) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    obj = json.loads(data.decode("utf-8", errors="replace"))
    if isinstance(obj, dict):
        if isinstance(obj.get("sets"), list):
            obj = [q for s in obj["sets"] for q in s.get("questions", [])]
        else:
            obj = obj.get("questions", [])
    out = []
    for q in obj if isinstance(obj, list) else []:
        if isinstance(q, str):
            q = {"question_text": q}
        text = q.get("question_text") or q.get("question") or q.get("text") or ""
        out.append({"text": str(text), "marks": _int_or_none(q.get("marks")), "co": q.get("co"),
                    "bloom_level": q.get("bloom_level") or q.get("bloom"), "po": q.get("po"),
                    "unit_num": _int_or_none(q.get("unit_num") or q.get("unit"))})
    return out, {}


def _from_csv(data: bytes) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
    out = []
    for row in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        text = r.get("question") or r.get("question_text") or r.get("text") or ""
        bl = r.get("bloom") or r.get("bloom_level") or r.get("level") or ""
        m = re.search(r"[1-6]", bl)
        out.append({"text": text, "marks": _int_or_none(r.get("marks")), "co": (r.get("co") or None),
                    "bloom_level": f"L{m.group(0)}" if m else None, "po": r.get("po") or None,
                    "unit_num": _int_or_none(re.sub(r"\D", "", r.get("unit", "")) or None)})
    return out, {}


def _int_or_none(v) -> Optional[int]:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None
