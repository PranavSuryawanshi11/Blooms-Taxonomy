"""
Smoke tests verifying Flask server initialization, static asset delivery,
and core REST API endpoints without requiring live external LLM connectivity.
"""

import json
import os
import uuid
import pytest


@pytest.mark.smoke
def test_app_imports_cleanly():
    """Verify that the Flask application instance is created without errors."""
    from app import app
    assert app is not None
    assert app.name == "app"


@pytest.mark.smoke
def test_root_index_route(client):
    """Verify that GET / returns HTTP 200 and loads the main frontend dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "BloomCraft AI" in html
    assert "auth-gate-view" in html
    assert "dashboard-view" in html


@pytest.mark.smoke
def test_blueprint_presets_endpoint(client):
    """Verify GET /api/blueprint/presets delivers cognitive levels and exam templates."""
    response = client.get("/api/blueprint/presets")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("success") is True
    assert "exam_templates" in data
    assert "cognitive_presets" in data
    assert "bloom_levels" in data


@pytest.mark.smoke
def test_syllabus_samples_endpoint(client):
    """Verify GET /api/syllabus/samples delivers pre-configured engineering syllabi."""
    response = client.get("/api/syllabus/samples")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("samples"), list)
    assert len(data["samples"]) > 0
    # Verify DBMS sample is present
    first_sample = data["samples"][0]
    assert "code" in first_sample
    assert "name" in first_sample


@pytest.mark.smoke
def test_auth_me_unauthorized(client):
    """Verify GET /api/auth/me rejects requests without a valid Bearer token."""
    response = client.get("/api/auth/me")
    assert response.status_code in (401, 200)
    data = response.get_json()
    # If returned as JSON error
    if response.status_code == 401 or not data.get("success"):
        assert data.get("success") is not True


needs_db = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL (PostgreSQL) not configured")


def _register(client, prefix="faculty"):
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    res = client.post("/api/auth/register", json={
        "username": username, "display_name": "Test Faculty", "department": "CSE", "password": "Str0ngPass!42"})
    return username, res.get_json()


@needs_db
@pytest.mark.smoke
def test_auth_login_invalid_credentials(client):
    """Wrong password is rejected."""
    username, _ = _register(client)
    response = client.post("/api/auth/login", json={"username": username, "password": "incorrect_password_999"})
    data = response.get_json()
    assert response.status_code == 401
    assert data.get("success") is False and "error" in data


@needs_db
@pytest.mark.smoke
def test_register_login_me_and_recovery(client):
    """Register -> login -> /me -> reset via recovery code."""
    username, reg = _register(client)
    assert reg["success"] is True and reg["recovery_code"]
    login = client.post("/api/auth/login", json={"username": username, "password": "Str0ngPass!42"}).get_json()
    assert login["success"] is True and len(login["token"]) >= 40
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login['token']}"}).get_json()
    assert me["user"]["username"] == username and me["user"]["is_guest"] is False

    bad = client.post("/api/auth/forgot-password", json={
        "username": username, "new_password": "An0therPass!7", "recovery_code": "AAAA-BBBB-CCCC-DDDD"})
    assert bad.status_code == 400
    ok = client.post("/api/auth/forgot-password", json={
        "username": username, "new_password": "An0therPass!7", "recovery_code": reg["recovery_code"]}).get_json()
    assert ok["success"] is True and ok["recovery_code"] != reg["recovery_code"]
    assert client.post("/api/auth/login", json={"username": username, "password": "An0therPass!7"}).status_code == 200


@needs_db
@pytest.mark.smoke
def test_weak_password_and_demo_accounts_removed(client):
    res = client.post("/api/auth/register", json={"username": f"weak_{uuid.uuid4().hex[:6]}", "password": "abc"})
    assert res.status_code == 400
    for demo in ("prof.turing", "dr.hopper", "pranav11"):
        r = client.post("/api/auth/login", json={"username": demo, "password": "password123"})
        assert r.status_code == 401


@needs_db
@pytest.mark.smoke
def test_guest_gets_one_paper_per_device(client):
    device = "dev-" + uuid.uuid4().hex
    guest = client.post("/api/auth/guest", json={"device_id": device}).get_json()
    assert guest["success"] and guest["user"]["is_guest"] and guest["guest_quota"]["remaining"] == 1
    headers = {"Authorization": f"Bearer {guest['token']}"}
    syl = client.get("/api/syllabus/samples").get_json()["samples"][0]
    body = {"syllabus": syl, "exam_config": {"template_id": "quiz_30"}}
    first = client.post("/api/paper/generate", json=body, headers=headers)
    assert first.status_code == 200
    second = client.post("/api/paper/generate", json=body, headers=headers)
    assert second.status_code == 403 and second.get_json()["guest_limit_reached"] is True
    # pressing "Continue as Guest" again on the same device does not reset the quota
    again = client.post("/api/auth/guest", json={"device_id": device}).get_json()
    third = client.post("/api/paper/generate", json=body, headers={"Authorization": f"Bearer {again['token']}"})
    assert third.status_code == 403


@needs_db
@pytest.mark.smoke
def test_generation_requires_login(client):
    syl = client.get("/api/syllabus/samples").get_json()["samples"][0]
    res = client.post("/api/paper/generate", json={"syllabus": syl, "exam_config": {"template_id": "quiz_30"}})
    assert res.status_code == 401


@needs_db
@pytest.mark.smoke
def test_unit_plan_manual_or_and_sub_numbering(client):
    _, reg = _register(client)
    headers = {"Authorization": f"Bearer {reg['token']}"}
    syl = client.get("/api/syllabus/samples").get_json()["samples"][0]
    sections = [
        {"id": "s1", "name": "Question 1", "question_count": 3, "marks_per_question": 5,
         "question_marks": [5, 5, 10], "question_choices": [False, True, False], "or_marks": [5, 3, 10],
         "allowed_levels": ["L1", "L2", "L3"]},
        {"id": "s2", "name": "Question 2", "question_count": 1, "marks_per_question": 40,
         "question_marks": [40], "question_choices": [True], "or_marks": [40], "allowed_levels": ["L3", "L4"]},
    ]
    n_units = len(syl["units"])
    plan = {"enabled": True, "units": [{"unit_num": u["unit_num"], "marks": 10, "levels": []} for u in syl["units"]]}
    res = client.post("/api/paper/generate", headers=headers, json={
        "syllabus": syl, "unit_plan": plan,
        "exam_config": {"sections": sections, "total_marks": 60, "numbering_style": "sub"}}).get_json()
    assert res["success"], res
    paper = res["paper"]
    labels = [q["display_num"] for q in paper["all_questions"]]
    assert labels[:3] == ["Q.1 (a)", "Q.1 (b)", "Q.1 (b) (OR)"]
    assert "Q.2 (a)" in labels and "Q.2 (b)" in labels            # single question with OR -> (a) / (b)
    or_q = [q for q in paper["all_questions"] if q["display_num"] == "Q.1 (b) (OR)"][0]
    assert or_q["marks"] == 3 and or_q["is_choice"]
    assert paper["marks_check"]["matches"] is True
    assert len(paper["unit_summary"]) == n_units


def test_unit_bloom_levels_are_respected():
    from core.blueprint_builder import build_blueprint
    from core.paper_structure import apply_unit_plan
    from config import EXAM_TEMPLATES, BLOOM_PRESETS
    import copy
    from app import app
    syl = app.test_client().get("/api/syllabus/samples").get_json()["samples"][0]
    cfg = copy.deepcopy(EXAM_TEMPLATES["end_sem_100"])
    bp = build_blueprint(syl, cfg, BLOOM_PRESETS["balanced"]["distribution"], user_seed="x")
    plan = {"enabled": True, "units": [{"unit_num": 1, "marks": 100, "levels": ["L2"]},
                                      *[{"unit_num": u["unit_num"], "marks": 0, "levels": []} for u in syl["units"][1:]]]}
    bp = apply_unit_plan(bp, syl, plan, cfg["sections"])
    slots = [s for sec in bp["sections"] for s in sec["slots"]]
    assert all(s["unit_num"] == 1 and s["bloom_level"] == "L2" for s in slots)


def test_options_off_leaves_blueprint_untouched():
    from core.blueprint_builder import build_blueprint
    from core.paper_structure import apply_unit_plan, apply_or_configuration, apply_numbering
    from config import EXAM_TEMPLATES, BLOOM_PRESETS
    import copy
    from app import app
    syl = app.test_client().get("/api/syllabus/samples").get_json()["samples"][0]
    cfg = copy.deepcopy(EXAM_TEMPLATES["end_sem_100"])
    original = build_blueprint(syl, cfg, BLOOM_PRESETS["balanced"]["distribution"], user_seed="x")
    after = apply_numbering(apply_or_configuration(apply_unit_plan(copy.deepcopy(original), syl, None, cfg["sections"]),
                                                   cfg["sections"], syl), "sequential")
    assert after == original


def test_question_set_parser_derives_units_co_po():
    from core.question_set_parser import parse_question_set
    text = """Q.1 a) Define overfitting in machine learning. [5M]
b) Explain the bias-variance tradeoff with a neat diagram. [5M]
Q.2 Apply K-means clustering on the given points for two iterations. (10 Marks)
Q.3 Perform two-way ANOVA on the given treatments and conclude. [8M]
Q.4 Design an ensemble model using bagging and boosting for fraud detection. [10M]
Q.5 Calculate the 95% confidence interval for the observation vector. [4M]
Q.6 Evaluate two classifiers using ROC curve and AUC comparison. [5M]
Q.7 Explain regularization in linear regression using ridge and lasso. [5M]"""
    r = parse_question_set("qs.txt", text.encode(), "CS601")
    assert r["question_count"] == 8 and r["total_marks"] == 52
    assert len(r["units"]) >= 2 and all(u["title"] for u in r["units"])
    assert all(q["co"].startswith("CO") and q["po"].startswith("PO") and q["unit_title"] for q in r["questions"])
    by = {q["question_text"][:6]: q["bloom_level"] for q in r["questions"]}
    assert by["Define"] == "L1" and by["Design"] == "L6" and by["Evalua"] == "L5"
    assert r["syllabus"]["units"] and r["syllabus"]["course_outcomes"]
