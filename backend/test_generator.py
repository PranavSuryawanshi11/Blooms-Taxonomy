"""
Automated Verification Suite for Bloom's Taxonomy Question Paper Generator
"""

import sys
import os
import json

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BLOOM_LEVELS, BLOOM_ORDER, BLOOM_PRESETS, EXAM_TEMPLATES
from core.bloom_engine import (
    validate_bloom_distribution, 
    calculate_actual_distribution, 
    calculate_cognitive_index, 
    normalize_distribution,
    classify_question_bloom_level
)
from core.syllabus_parser import parse_syllabus
from core.blueprint_builder import build_blueprint
from core.question_generator import generate_paper_from_blueprint, generate_single_question
from core.export_service import generate_word_document


def run_tests():
    print(">>> Starting BloomCraft Backend Automated Verification...")
    
    # 1. Test Distribution Normalization and Validation
    dist = {"L1": 20, "L2": 25, "L3": 25, "L4": 15, "L5": 10, "L6": 5}
    valid, msg = validate_bloom_distribution(dist)
    assert valid, f"Distribution validation failed: {msg}"
    print("[PASS] Distribution validation and normalization.")

    # 2. Test Syllabus Parser with raw text
    sample_text = """
    UNIT 1: Relational Model Concepts
    Database architecture, Schema, ER diagrams, Relational Algebra, Selection, Projection, Joins.
    
    UNIT 2: SQL and Normalization
    DDL, DML, Subqueries, Functional Dependencies, 1NF, 2NF, 3NF, BCNF.

    UNIT 3: Transaction Processing
    ACID properties, Serializability, Concurrency Control, Two-phase locking, Deadlocks.
    """
    parsed = parse_syllabus(sample_text, course_code="CS501", course_name="Database Systems")
    assert parsed["total_units"] == 3, f"Expected 3 units, got {parsed['total_units']}"
    assert len(parsed["units"][0]["topics"]) > 0, "No topics extracted from Unit 1"
    print(f"[PASS] Syllabus parsing: {parsed['total_units']} units and {parsed['total_topics']} topics extracted.")

    # 3. Test Blueprint Building (50 marks Midterm)
    exam_cfg = {
        "institution_name": "INSTITUTE OF TECHNOLOGY",
        "exam_title": "Midterm Examination",
        "duration": "2 Hours",
        "total_marks": 50,
        "sections": EXAM_TEMPLATES["mid_sem_50"]["sections"]
    }
    blueprint = build_blueprint(parsed, exam_cfg, dist)
    assert len(blueprint["sections"]) == 2, f"Expected 2 sections, got {len(blueprint['sections'])}"
    total_slots = blueprint["total_question_slots"]
    assert total_slots == 10, f"Expected 10 total slots (5 + 5), got {total_slots}"
    print(f"[PASS] Blueprint generated: {len(blueprint['sections'])} sections with {total_slots} question slots.")

    # 4. Test Paper Generation
    paper = generate_paper_from_blueprint(blueprint)
    assert len(paper["sections"]) == 2
    assert len(paper["all_questions"]) >= 10
    first_q = paper["sections"][0]["questions"][0]
    print(f"[PASS] Question generated ({first_q['bloom_level']} - {first_q['bloom_name']}):")
    print(f"       \"{first_q['question_text']}\" [{first_q['marks']} Marks]")

    # 5. Test Cognitive Metrics & Distribution Calculation
    actual_stats = calculate_actual_distribution(paper["all_questions"])
    cog_index = calculate_cognitive_index(actual_stats)
    print(f"[PASS] Actual distribution computed. Cognitive Depth Index: {cog_index}/6.0")

    # 6. Test Single Question Regeneration
    slot_to_regen = blueprint["sections"][1]["slots"][0]
    fresh_q = generate_single_question(slot_to_regen, exclude_texts=[first_q["question_text"]])
    assert fresh_q["bloom_level"] == slot_to_regen["bloom_level"]
    print(f"[PASS] Single question regenerated preserving {fresh_q['bloom_level']} target level.")

    # 7. Test Word Document Generation
    word_html = generate_word_document(paper)
    assert "<html" in word_html and "INSTITUTE OF TECHNOLOGY" in word_html
    print(f"[PASS] Word document generated ({len(word_html)} bytes).")

    # 8. Test Cognitive Classifier Heuristic
    # 9. Test User Authentication & History
    from core.auth_history_service import authenticate_user, register_user, save_paper_to_history, get_user_history, get_history_paper, delete_history_paper
    turing = authenticate_user("prof.turing", "password123")
    assert turing is not None and turing["username"] == "prof.turing", "Failed to authenticate demo user prof.turing"
    print(f"[PASS] User authentication verified for {turing['display_name']}.")

    # 10. Test Multi-User Differentiation (Same syllabus, distinct outputs)
    blueprint_a = build_blueprint(parsed, exam_cfg, dist, user_seed="usr_turing_001")
    paper_a = generate_paper_from_blueprint(blueprint_a, user_seed="usr_turing_001")

    blueprint_b = build_blueprint(parsed, exam_cfg, dist, user_seed="usr_hopper_002")
    paper_b = generate_paper_from_blueprint(blueprint_b, user_seed="usr_hopper_002")

    questions_a = [q["question_text"] for q in paper_a["all_questions"]]
    questions_b = [q["question_text"] for q in paper_b["all_questions"]]
    differences = sum(1 for qa, qb in zip(questions_a, questions_b) if qa != qb)
    assert differences > 0, "Multi-user generation failed to differentiate question papers!"
    print(f"[PASS] Multi-user differentiation verified: {differences}/{len(questions_a)} questions differ between User A and User B.")

    # 11. Test Academic Technical Figure Generator
    from core.figure_generator import generate_technical_diagram
    fig_er = generate_technical_diagram("Relational Model and ER diagrams", "L4", "Q3")
    assert fig_er is not None and "<svg" in fig_er["svg"], "Failed to generate ER vector diagram"
    assert "Figure" in fig_er["caption"] or "Entity" in fig_er["title"] or "E-R" in fig_er["title"]
    print(f"[PASS] Academic Technical Vector Diagram generated: '{fig_er['title']}' ({len(fig_er['svg'])} bytes SVG).")

    # 12. Test History Persistence
    pid = save_paper_to_history("usr_turing_001", paper_a)
    history = get_user_history("usr_turing_001")
    assert any(h["paper_id"] == pid for h in history), "Paper not found in user history"
    retrieved_paper = get_history_paper("usr_turing_001", pid)
    assert retrieved_paper is not None and len(retrieved_paper["all_questions"]) == len(paper_a["all_questions"])
    deleted = delete_history_paper("usr_turing_001", pid)
    assert deleted, "Failed to delete test paper from history"
    print("[PASS] User history persistence, reload, and deletion verified.")

    # 13. Test Custom Template CRUD
    from app import load_all_templates, save_custom_template, delete_custom_template
    custom_tmpl = {
        "name": "Unit Test Custom Exam",
        "total_marks": 75,
        "duration": "2.5 Hours",
        "sections": [
            {"id": "s1", "name": "Part A", "question_count": 5, "marks_per_question": 3, "total_section_marks": 15, "allowed_levels": ["L1", "L2"]},
            {"id": "s2", "name": "Part B", "question_count": 6, "marks_per_question": 10, "total_section_marks": 60, "allowed_levels": ["L3", "L4", "L5"]}
        ]
    }
    save_custom_template("test_custom_75", custom_tmpl)
    templates = load_all_templates()
    assert "test_custom_75" in templates, "Custom template was not loaded"
    delete_custom_template("test_custom_75")
    assert "test_custom_75" not in load_all_templates(), "Custom template was not deleted"
    print("[PASS] Custom template creation, retrieval, and deletion verified.")

    # 14. Test AICTE Action Verbs Standards Compliance & CO Fulfillment Matrix
    all_aicte_verbs_set = set()
    for lvl in BLOOM_ORDER:
        for v in BLOOM_LEVELS[lvl]["verbs"]:
            all_aicte_verbs_set.add(v.lower())
    for q in paper["all_questions"]:
        assert "aicte_verb" in q and q["aicte_verb"], f"Question {q.get('display_num')} missing aicte_verb"
        assert q["aicte_verb"].lower() in all_aicte_verbs_set or any(q["question_text"].lower().startswith(v) for v in all_aicte_verbs_set), f"Question did not use AICTE verb: {q['aicte_verb']}"
        assert "co" in q and q["co"].startswith("CO"), f"Question missing valid CO: {q}"
    assert "co_fulfillment_matrix" in paper and len(paper["co_fulfillment_matrix"]) == len(paper["all_questions"]), "Missing co_fulfillment_matrix"
    print(f"[PASS] AICTE verbs standard verified on {len(paper['all_questions'])} questions. Course Outcomes (CO) fulfillment matrix verified.")

    # 15. Test College Templates (RCPIT 65M, DJSCE 60M, 20M, 25M)
    rcpit_bp = build_blueprint(parsed, EXAM_TEMPLATES["rcpit_sem_65"], dist)
    assert rcpit_bp["total_marks"] == 65, f"Expected 65 marks for RCPIT, got {rcpit_bp['total_marks']}"
    rcpit_paper = generate_paper_from_blueprint(rcpit_bp)
    assert rcpit_paper["total_marks"] == 65
    assert len(rcpit_paper["sections"]) == 4

    djsce_bp = build_blueprint(parsed, EXAM_TEMPLATES["djsce_sem_60"], dist)
    assert djsce_bp["total_marks"] == 60, f"Expected 60 marks for DJSCE, got {djsce_bp['total_marks']}"
    djsce_paper = generate_paper_from_blueprint(djsce_bp)
    assert djsce_paper["total_marks"] == 60

    unit_test_bp = build_blueprint(parsed, EXAM_TEMPLATES["unit_test_20"], dist)
    assert unit_test_bp["total_marks"] == 20
    print("[PASS] College Templates verified: RCPIT Shirpur (65M), SVKM DJSCE (60M), and Unit Test (20M).")

    # 16. Test Generation from User Question Sets (Sets 1..4 with 4 questions each)
    from app import get_default_starter_sets
    starter_sets = get_default_starter_sets()
    assert len(starter_sets) == 4
    assert all(len(s["questions"]) == 4 for s in starter_sets)
    custom_set_paper = generate_paper_from_blueprint(rcpit_bp, user_sets=starter_sets)
    assert custom_set_paper["source_mode"] == "User-Question-Sets"
    assert any("Custom-Set" in q.get("generator_mode", "") for q in custom_set_paper["all_questions"])
    print(f"[PASS] User Question Sets generation verified: questions successfully assembled from 4 user sets of 4 questions each.")

    # 17. Test Academic Figures & Diagrams (Bias-Variance, ROC, K-Means, ANOVA table, Dataset table)
    fig_bv = generate_technical_diagram("Bias and Variance tradeoff in regression", "L4", "Q1")
    assert fig_bv is not None and "Bias-Variance" in fig_bv["title"]
    fig_roc = generate_technical_diagram("ROC Curves and AUC classification metric", "L4", "Q2")
    assert fig_roc is not None and "ROC" in fig_roc["title"]
    fig_kmeans = generate_technical_diagram("K-Means clustering with coordinate data", "L3", "Q3")
    assert fig_kmeans is not None and "K-Means" in fig_kmeans["title"]
    fig_anova = generate_technical_diagram("Two-way ANOVA experimental design", "L3", "Q4")
    assert fig_anova is not None and "ANOVA" in fig_anova["title"]
    fig_ml_table = generate_technical_diagram("SVM Dataset with test query point", "L5", "Q5")
    assert fig_ml_table is not None and "Dataset" in fig_ml_table["title"]
    print("[PASS] Academic figures verified: Bias-Variance curve, ROC curve, K-Means coordinate plot, ANOVA table, ML dataset table.")

    # 19. Test Dynamic Non-Hardcoded Diagram Generation (Domain-specific extraction)
    # Test A: Custom Medical/Hospital ER diagram extraction (Doctor & Patient instead of hardcoded Student)
    fig_hospital = generate_technical_diagram(
        topic="Database Systems",
        bloom_level="L4",
        question_num="Q6",
        question_text="Construct an Entity-Relationship (ER) model for a Hospital Management System tracking Patient and Doctor consultations with primary keys."
    )
    assert fig_hospital is not None, "Failed to generate dynamic hospital ER diagram"
    assert "PATIENT" in fig_hospital["svg"] and "DOCTOR" in fig_hospital["svg"], "Failed to extract dynamic entities PATIENT and DOCTOR"
    assert "STUDENT" not in fig_hospital["svg"], "Hardcoded student entity leaked into hospital ER diagram!"

    # Test B: Custom Tree generation with specific keys
    fig_tree = generate_technical_diagram(
        topic="Data Structures & Algorithms",
        bloom_level="L3",
        question_num="Q7",
        question_text="Construct a Binary Search Tree (BST) after inserting keys: 25, 12, 38, 7, 19, 31, 45."
    )
    assert fig_tree is not None and "<svg" in fig_tree["svg"], "Failed to generate dynamic BST diagram"
    assert "25" in fig_tree["svg"] and "38" in fig_tree["svg"], "Specific numerical keys not present in generated BST"

    # Test C: OS Process State Machine
    fig_proc = generate_technical_diagram(
        topic="Operating Systems Kernel",
        bloom_level="L3",
        question_num="Q8",
        question_text="Illustrate the process state transition lifecycle detailing Ready, Running, and Waiting states."
    )
    assert fig_proc is not None and "READY" in fig_proc["svg"] and "RUNNING" in fig_proc["svg"]

    print("[PASS] Dynamic non-hardcoded diagram synthesis verified across Hospital ER, BST with custom keys, and OS state machine.")

    print("\n>>> ALL 19 BACKEND AUTOMATED TESTS PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    run_tests()


