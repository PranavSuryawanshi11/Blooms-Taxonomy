"""
Unit and blueprint generation tests with mocked LLM providers.
Ensures generation pipeline executes deterministically without making network requests.
"""

from unittest.mock import patch

from config import EXAM_TEMPLATES
from core.bloom_engine import (
    validate_bloom_distribution,
    normalize_distribution,
    calculate_actual_distribution,
    calculate_cognitive_index
)
from core.syllabus_parser import parse_syllabus
from core.blueprint_builder import build_blueprint
from core.question_generator import generate_paper_from_blueprint


def test_bloom_distribution_math():
    """Verify cognitive distribution normalization and validation."""
    valid_dist = {"L1": 20, "L2": 25, "L3": 25, "L4": 15, "L5": 10, "L6": 5}
    valid, msg = validate_bloom_distribution(valid_dist)
    assert valid is True
    assert "valid" in msg.lower()

    # Unbalanced distribution normalization
    unbalanced = {"L1": 10, "L2": 10, "L3": 10, "L4": 10, "L5": 10, "L6": 10}
    normalized = normalize_distribution(unbalanced)
    assert sum(normalized.values()) == 100


def test_syllabus_parsing_in_memory():
    """Verify syllabus extraction and module segmentation."""
    sample_text = """
    UNIT 1: Relational Model Concepts
    Database architecture, Schema, ER diagrams, Relational Algebra, Selection, Projection, Joins.
    
    UNIT 2: SQL and Normalization
    DDL, DML, Subqueries, Functional Dependencies, 1NF, 2NF, 3NF, BCNF.

    UNIT 3: Transaction Processing
    ACID properties, Serializability, Concurrency Control, Two-phase locking, Deadlocks.
    """
    parsed = parse_syllabus(sample_text, course_code="CS501", course_name="Database Systems")
    assert parsed["total_units"] == 3
    assert len(parsed["units"]) == 3
    assert len(parsed["units"][0]["topics"]) > 0


@patch("core.llm_client.complete")
@patch("core.llm_client.is_available")
def test_mocked_paper_generation(mock_is_available, mock_complete):
    """
    Verify paper generation workflow with mocked LLM engine.
    Ensures zero external network calls occur during automated test execution.
    """
    mock_is_available.return_value = True
    mock_complete.return_value = (
        "Design a normalized 3NF database relational schema for a multi-campus university library management system."
    )

    sample_text = """
    UNIT 1: Relational Model Concepts
    Database architecture, Schema, ER diagrams, Relational Algebra, Selection, Projection, Joins.
    
    UNIT 2: SQL and Normalization
    DDL, DML, Subqueries, Functional Dependencies, 1NF, 2NF, 3NF, BCNF.
    """
    parsed = parse_syllabus(sample_text, course_code="CS501", course_name="Database Systems")

    exam_cfg = {
        "institution_name": "COLLEGE OF ENGINEERING",
        "exam_title": "Class Assessment Test",
        "duration": "2 Hours",
        "total_marks": 50,
        "sections": EXAM_TEMPLATES["mid_sem_50"]["sections"]
    }

    dist = {"L1": 20, "L2": 25, "L3": 25, "L4": 15, "L5": 10, "L6": 5}
    blueprint = build_blueprint(parsed, exam_cfg, dist)

    assert blueprint is not None
    assert len(blueprint["sections"]) == 2

    paper = generate_paper_from_blueprint(blueprint)
    assert paper is not None
    assert "sections" in paper
    assert len(paper["sections"]) == 2
    assert len(paper["all_questions"]) >= 10

    actual_stats = calculate_actual_distribution(paper["all_questions"])
    cog_index = calculate_cognitive_index(actual_stats)
    assert 1.0 <= cog_index <= 6.0
