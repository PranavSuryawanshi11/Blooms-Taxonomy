"""
Syllabus Parser Module
Extracts text from PDF/Text sources and parses course curricula into structured Units, Topics, and Course Outcomes.
"""

import re
import io
from typing import Dict, List, Optional, Any

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from PDF file byte stream using pdfplumber."""
    if not PDF_SUPPORT:
        raise RuntimeError("PDF extraction library (pdfplumber) is not available.")

    extracted_pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                extracted_pages.append(text)

    return "\n\n".join(extracted_pages)


def clean_syllabus_text(text: str) -> str:
    """Normalize text line breaks, tabs, and excess whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_syllabus(raw_text: str, course_code: str = "CS500", course_name: str = "Course Curriculum") -> Dict[str, Any]:
    """
    Intelligently parses syllabus text into structured Units, Topics, and Course Outcomes.
    """
    cleaned = clean_syllabus_text(raw_text)
    
    # Try to detect course title from top lines if default
    lines = cleaned.split("\n")
    detected_title = course_name
    for line in lines[:5]:
        stripped = line.strip()
        if len(stripped) > 4 and not stripped.lower().startswith(("unit", "module", "chapter", "syllabus", "course")):
            # If line looks like a subject name
            if re.match(r"^[A-Z0-9\s\-\&\,]{5,60}$", stripped):
                detected_title = stripped.title()
                break

    # Regex patterns for unit demarcations
    unit_patterns = [
        r"(?i)(?:^|\n)(?:UNIT|MODULE|CHAPTER|SECTION)\s*[-:–—\s]*([0-9IVXLCDM]+)[\.\:\-–—\s]*(.*?)(?=(?:\n(?:UNIT|MODULE|CHAPTER|SECTION)\s*[-:–—\s]*[0-9IVXLCDM]+)|\Z)",
        r"(?i)(?:^|\n)Unit\s*([0-9]+)[\.\:\-–—\s]*(.*?)(?=(?:\nUnit\s*[0-9]+)|\Z)"
    ]

    matched_units = []

    for pattern in unit_patterns:
        matches = list(re.finditer(pattern, cleaned, re.DOTALL))
        if len(matches) >= 2:
            for idx, m in enumerate(matches, 1):
                unit_num_str = m.group(1).strip()
                unit_content = m.group(2).strip()
                
                # Split content into Title (first line) and Topics (rest)
                parts = unit_content.split("\n", 1)
                title = parts[0].strip(" :-–—.")
                body = parts[1].strip() if len(parts) > 1 else title
                
                # Clean up title if it contains hours or marks like "(8 Hours)"
                title = re.sub(r"\(\s*\d+\s*(?:hours|hrs|periods|lectures)?\s*\)", "", title, flags=re.IGNORECASE).strip()
                if not title:
                    title = f"Unit {unit_num_str}"

                topics = _extract_topics_from_text(body)
                matched_units.append({
                    "unit_num": idx,
                    "title": title,
                    "co": f"CO{min(idx, 5)}",
                    "topics": topics
                })
            break

    # Fallback: If no explicit Unit headers found, chunk by paragraphs
    if not matched_units:
        matched_units = _fallback_chunking(cleaned)

    # Generate Course Outcomes based on Units
    course_outcomes = []
    for u in matched_units:
        co_id = u["co"]
        if not any(co["id"] == co_id for co in course_outcomes):
            course_outcomes.append({
                "id": co_id,
                "description": f"Demonstrate mastery and application of core principles in {u['title']}."
            })

    return {
        "code": course_code,
        "name": detected_title,
        "raw_length": len(cleaned),
        "total_units": len(matched_units),
        "total_topics": sum(len(u["topics"]) for u in matched_units),
        "course_outcomes": course_outcomes,
        "units": matched_units,
        "extracted_text": cleaned
    }


def _extract_topics_from_text(text: str) -> List[str]:
    """Extract granular topic list from a unit description."""
    # Remove metadata like "(10 hours)", "Reference Books", etc.
    text = re.sub(r"(?i)\b(?:hours?|hrs|lectures?|periods?)\s*[:=]?\s*\d+", "", text)
    text = re.sub(r"(?i)\btext\s*books?.*", "", text)
    text = re.sub(r"(?i)\breferences?.*", "", text)

    topics = []
    # Split by semicolons, bullet points, or newlines
    delimiters = r"[\n;•\*\-\–]|(?<=[a-zA-Z0-9\)])\s*,\s*(?=[A-Z])"
    chunks = re.split(delimiters, text)

    for chunk in chunks:
        c = chunk.strip(" \t\n\r:.,-")
        if len(c) >= 4 and not c.isdigit():
            # Exclude trivial non-topic phrases
            if not re.match(r"(?i)^(total|hours|lecture|unit|module|self-study)", c):
                topics.append(c)

    # If splitting yielded too few or one big chunk, split by commas
    if len(topics) <= 1 and "," in text:
        topics = [t.strip(" \t\n\r:.,-") for t in text.split(",") if len(t.strip()) >= 4]

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for t in topics:
        clean_t = t.strip()
        if clean_t.lower() not in seen:
            seen.add(clean_t.lower())
            deduped.append(clean_t)

    return deduped if deduped else ["Foundational Concepts and Core Architecture", "Operational Principles and Methodology"]


def _fallback_chunking(text: str) -> List[Dict[str, Any]]:
    """Segment unformatted syllabus into 4-5 balanced units."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 20]

    num_units = min(max(len(paragraphs), 3), 5)
    chunk_size = max(1, len(paragraphs) // num_units)

    units = []
    for i in range(num_units):
        start = i * chunk_size
        end = start + chunk_size if i < num_units - 1 else len(paragraphs)
        unit_text = " ".join(paragraphs[start:end])
        
        topics = _extract_topics_from_text(unit_text)
        first_topic = topics[0] if topics else f"Core Module {i+1}"
        
        units.append({
            "unit_num": i + 1,
            "title": first_topic[:50],
            "co": f"CO{min(i+1, 5)}",
            "topics": topics
        })

    return units
