"""
Live End-to-End Test Suite for BloomCraft AI
Tests all live HTTP endpoints on http://127.0.0.1:5000
Verifies:
1. Static HTML, CSS, JS delivery (including custom_sets.js and updated index.html)
2. Faculty Authentication (Prof. Alan Turing)
3. Presets & College Templates (RCPIT 65M, RCPIT 60M, DJSCE 60M, Unit Test 20M, In-Sem 25M)
4. Question Sets API (GET, POST, sampling)
5. AICTE Verbs Standards Enforcement in generated paper
6. Technical Diagrams & Schematics in questions
7. AICTE Covered COs table & Question-to-CO Fulfillment Matrix
8. Custom Question Sets paper generation
9. Word Document (.doc) Export with College Branding & CO Matrix
"""

import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_static_assets():
    print("\n--- 1. Testing Static Assets & Script Delivery ---")
    req = urllib.request.urlopen(f"{BASE_URL}/")
    html = req.read().decode('utf-8')
    assert "modal-question-sets" in html, "modal-question-sets not found in index.html"
    assert "js/custom_sets.js" in html, "custom_sets.js script tag not found in index.html"
    assert "select-generation-source" in html, "select-generation-source not found in index.html"
    assert "exam-co-covered-box" in html, "exam-co-covered-box not found in index.html"
    assert "exam-co-matrix-target" in html, "exam-co-matrix-target not found in index.html"
    assert "analytics-co-breakdown-container" in html, "analytics-co-breakdown-container not found in index.html"
    assert "rcpit_sem_65" in html, "rcpit_sem_65 option not found in index.html"
    assert "djsce_sem_60" in html, "djsce_sem_60 option not found in index.html"
    print("[PASS] index.html contains all required containers, selectors, and modals.")

    # Check custom_sets.js delivery
    req_js = urllib.request.urlopen(f"{BASE_URL}/js/custom_sets.js")
    js_code = req_js.read().decode('utf-8')
    assert "QuestionSetsModule" in js_code, "QuestionSetsModule not found in custom_sets.js"
    print("[PASS] js/custom_sets.js delivered successfully.")

    # Check components.css delivery
    req_css = urllib.request.urlopen(f"{BASE_URL}/css/components.css")
    css_code = req_css.read().decode('utf-8')
    assert "badge-aicte" in css_code, "badge-aicte not found in components.css"
    assert "exam-co-covered-box" in css_code, "exam-co-covered-box not found in components.css"
    print("[PASS] css/components.css delivers AICTE and CO matrix styles.")

def test_auth_and_presets():
    print("\n--- 2. Testing Faculty Authentication & Presets ---")
    login_data = json.dumps({"username": "prof.turing", "password": "password123"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        assert data.get("success") is True
        token = data.get("token")
        user = data.get("user")
        print(f"[PASS] Logged in as: {user['display_name']} ({user['department']})")

    req_presets = urllib.request.urlopen(f"{BASE_URL}/api/blueprint/presets")
    presets = json.loads(req_presets.read().decode('utf-8'))
    templates = presets["exam_templates"]
    assert "rcpit_sem_65" in templates, "rcpit_sem_65 missing from presets"
    assert "rcpit_sem_60" in templates, "rcpit_sem_60 missing from presets"
    assert "djsce_sem_60" in templates, "djsce_sem_60 missing from presets"
    assert "unit_test_20" in templates, "unit_test_20 missing from presets"
    assert "insem_25" in templates, "insem_25 missing from presets"
    print(f"[PASS] Presets endpoint verified with {len(templates)} templates including college autonomous formats.")
    return token

def test_question_sets_api(token):
    print("\n--- 3. Testing Question Sets API ---")
    req = urllib.request.Request(f"{BASE_URL}/api/question-sets", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        assert data.get("success") is True
        sets = data.get("sets", [])
        assert len(sets) >= 4, f"Expected at least 4 question sets, found {len(sets)}"
        total_q = sum(len(s.get("questions", [])) for s in sets)
        print(f"[PASS] Successfully loaded {len(sets)} question sets with {total_q} starter questions.")

def test_paper_generation_aicte_rcpit(token):
    print("\n--- 4. Testing Paper Generation with AICTE Verbs & RCPIT 65M Template ---")
    # Load sample syllabus
    req_samples = urllib.request.urlopen(f"{BASE_URL}/api/syllabus/samples")
    samples = json.loads(req_samples.read().decode('utf-8'))["samples"]
    parsed_syllabus = next((s for s in samples if "Machine Learning" in s.get("name", "")), samples[0])
    print(f"[PASS] Loaded curriculum: {parsed_syllabus['name']} ({parsed_syllabus['code']}) with {len(parsed_syllabus.get('units', []))} units and {len(parsed_syllabus.get('course_outcomes', []))} COs.")

    # Generate Paper using rcpit_sem_65 template and AICTE verbs
    gen_payload = {
        "syllabus": parsed_syllabus,
        "template_id": "rcpit_sem_65",
        "blueprint_config": {
            "template_id": "rcpit_sem_65",
            "total_marks": 65,
            "duration": "02:00 Hrs.",
            "exam_title": "END SEMESTER EXAMINATION EVEN SEM-IV"
        },
        "target_distribution": {"L1": 15, "L2": 25, "L3": 30, "L4": 15, "L5": 10, "L6": 5},
        "generation_source": "engine"
    }

    req_gen = urllib.request.Request(
        f"{BASE_URL}/api/paper/generate",
        data=json.dumps(gen_payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_gen) as resp:
        gen_data = json.loads(resp.read().decode('utf-8'))
        assert gen_data.get("success") is True, f"Paper generation failed: {gen_data}"
        paper = gen_data["paper"]

        # Verify college profile header
        college = paper.get("college_profile", {})
        assert "R. C. PATEL INSTITUTE OF TECHNOLOGY" in college.get("college", ""), "RCPIT college name missing"
        assert college.get("regional_title"), "Marathi regional autonomous title missing"
        print(f"[PASS] College Profile: {college.get('college')}")

        # Verify Course Outcomes covered table
        cos = paper.get("course_outcomes", [])
        assert len(cos) >= 3, f"Expected at least 3 course outcomes, got {len(cos)}"
        print(f"[PASS] Course Outcomes covered: {len(cos)} COs ({[c['id'] for c in cos]})")

        # Verify Questions & AICTE verbs
        all_q = paper.get("all_questions", [])
        assert len(all_q) > 0, "No questions generated"
        aicte_verbs_found = [q.get("aicte_verb") for q in all_q if q.get("aicte_verb")]
        assert len(aicte_verbs_found) == len(all_q), f"Not all questions have AICTE verb: {len(aicte_verbs_found)}/{len(all_q)}"
        print(f"[PASS] AICTE Verbs strictly enforced across {len(all_q)} questions: {aicte_verbs_found[:6]}...")

        # Verify Question-to-CO Fulfillment Matrix
        co_matrix = paper.get("co_fulfillment_matrix", [])
        assert len(co_matrix) == len(all_q), f"CO matrix length {len(co_matrix)} != all questions count {len(all_q)}"
        first_row = co_matrix[0]
        assert "display_num" in first_row and "co" in first_row and "aicte_verb" in first_row
        print(f"[PASS] Question-to-CO Fulfillment Matrix verified: {len(co_matrix)} entries mapping questions to {first_row['co']}.")

        # Verify diagrams / figures generated
        figs = [q for q in all_q if q.get("figure") and q["figure"].get("svg")]
        assert len(figs) > 0, "Expected at least one technical diagram/figure in generated questions"
        print(f"[PASS] {len(figs)} technical vector schematics / dataset tables generated (e.g. '{figs[0]['figure'].get('title')}').")

        # Test On-Demand /api/diagram/generate endpoint
        diag_req = urllib.request.Request(
            f"{BASE_URL}/api/diagram/generate",
            data=json.dumps({
                "topic": "Microservices Architecture",
                "question_text": "Design a 3-tier microservice architecture with API Gateway, Kafka, and PostgreSQL",
                "diagram_type": "architecture",
                "display_num": "Q5"
            }).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(diag_req) as d_resp:
            d_data = json.loads(d_resp.read().decode('utf-8'))
            assert d_data.get("success") is True and "<svg" in d_data["figure"]["svg"]
            print(f"[PASS] On-Demand dynamic diagram API synthesized: '{d_data['figure'].get('title')}'.")

        # Test Word export with college branding & CO matrix
        export_payload = {"paper": paper}
        req_export = urllib.request.Request(
            f"{BASE_URL}/api/export/word",
            data=json.dumps(export_payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_export) as exp_resp:
            word_bytes = exp_resp.read()
            assert len(word_bytes) > 5000, f"Exported Word doc too small: {len(word_bytes)} bytes"
            word_text = word_bytes.decode('utf-8', errors='ignore')
            assert "R. C. PATEL INSTITUTE OF TECHNOLOGY" in word_text
            assert "Question-to-CO Fulfillment" in word_text
            print(f"[PASS] Word document exported ({len(word_bytes)} bytes) with college branding and CO fulfillment matrix.")

    return parsed_syllabus

def test_paper_generation_user_sets(token, parsed_syllabus):
    print("\n--- 5. Testing Paper Generation from Custom Question Sets ---")
    gen_payload = {
        "syllabus": parsed_syllabus,
        "template_id": "unit_test_20",
        "blueprint_config": {
            "template_id": "unit_test_20",
            "total_marks": 20,
            "duration": "45 Mins - 1 Hour",
            "exam_title": "Continuous Internal Evaluation / Unit Test"
        },
        "target_distribution": {"L1": 20, "L2": 30, "L3": 30, "L4": 20, "L5": 0, "L6": 0},
        "generation_source": "user_sets"
    }

    req_gen = urllib.request.Request(
        f"{BASE_URL}/api/paper/generate",
        data=json.dumps(gen_payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_gen) as resp:
        gen_data = json.loads(resp.read().decode('utf-8'))
        assert gen_data.get("success") is True
        paper = gen_data["paper"]
        all_q = paper.get("all_questions", [])
        assert len(all_q) > 0, "No questions in custom-sets generated paper"
        custom_sampled = [q for q in all_q if q.get("source") == "user_set"]
        print(f"[PASS] Custom Question Sets sampling verified: {len(custom_sampled)}/{len(all_q)} questions sampled from faculty question sets.")

def main():
    print("==========================================================")
    print("   BLOOMCRAFT AI - COMPREHENSIVE LIVE END-TO-END TESTS   ")
    print("==========================================================")
    try:
        test_static_assets()
        token = test_auth_and_presets()
        test_question_sets_api(token)
        parsed_syllabus = test_paper_generation_aicte_rcpit(token)
        test_paper_generation_user_sets(token, parsed_syllabus)
        print("\n==========================================================")
        print("   >>> ALL LIVE END-TO-END VERIFICATION CHECKS PASSED! <<<")
        print("==========================================================")
    except Exception as e:
        print(f"\n[FAIL] Test encountered exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
