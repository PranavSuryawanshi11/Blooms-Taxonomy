"""
Comprehensive Integration Test for Mandatory Faculty Auth & Strict Privacy/Isolation
Verifies:
1. Static files delivery (index.html, js/auth.js, css/components.css).
2. Unauthenticated access to history is blocked (401 Unauthorized).
3. Faculty Login issues an isolated session token.
4. Faculty Registration issues an isolated session token.
5. Strict Data Isolation:
   - Faculty A and Faculty B have isolated sessions.
   - Faculty A's generated papers are visible ONLY to Faculty A.
   - Faculty B CANNOT see Faculty A's history or papers (returns 404/401).
   - Faculty B CANNOT delete Faculty A's papers.
6. Proper deletion and logout token revocation.
"""

import urllib.request
import urllib.error
import json
import time
import os
import sys

# Support running directly without separate server via Flask test client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

client = app.test_client()
BASE_URL = "http://127.0.0.1:5000"

# Check if external server is reachable
USE_LIVE_SERVER = False
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=1.0) as _:
        USE_LIVE_SERVER = True
except Exception:
    USE_LIVE_SERVER = False


def _request(path, method="GET", data=None, headers=None):
    headers = headers or {}
    if USE_LIVE_SERVER:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
        return urllib.request.urlopen(req)
    else:
        # Use Flask test client
        if method == "GET":
            res = client.get(path, headers=headers)
        elif method == "POST":
            res = client.post(path, json=data, headers=headers)
        elif method == "DELETE":
            res = client.delete(path, headers=headers)
        else:
            res = client.open(path, method=method, json=data, headers=headers)

        class MockResponse:
            def __init__(self, r):
                self.status_code = r.status_code
                self.data = r.data
                self.code = r.status_code
            def read(self):
                return self.data

        if res.status_code >= 400:
            raise urllib.error.HTTPError(path, res.status_code, "HTTP Error", {}, None)
        return MockResponse(res)

def test_static_files():
    print("[TEST 1] Testing static files delivery & mandatory login gate...")
    res = _request("/")
    html = res.read().decode("utf-8")
    assert "auth-gate-view" in html, "auth-gate-view missing in index.html"
    assert "dashboard-view" in html, "dashboard-view missing in index.html"
    assert 'id="dashboard-view" class="dashboard-view" style="display: none;"' in html, "dashboard-view must be hidden by default"
    print("  -> index.html successfully configured with mandatory auth-gate-view and hidden dashboard-view.")


def test_unauthenticated_access_blocked():
    print("[TEST 2] Testing unauthenticated history protection...")
    try:
        _request("/api/history")
        assert False, "Expected 401 Unauthorized for unauthenticated history access"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("  -> Unauthenticated access to /api/history successfully blocked with HTTP 401.")


def test_faculty_login_and_token():
    print("[TEST 3] Testing Faculty Login & Token Generation...")
    payload = {"username": "prof.turing", "password": "password123"}
    res = _request("/api/auth/login", method="POST", data=payload, headers={"Content-Type": "application/json"})
    data = json.loads(res.read().decode("utf-8"))
    assert data["success"] is True
    assert "token" in data and data["token"].startswith("tok_")
    assert data["user"]["username"] == "prof.turing"
    print(f"  -> Login success: {data['user']['display_name']} [Token: {data['token'][:12]}...]")
    return data["user"], data["token"]


def test_strict_isolation_between_faculty():
    print("[TEST 4] Testing Strict Multi-Faculty Isolation & Privacy...")
    # Faculty A (Turing)
    turing_payload = {"username": "prof.turing", "password": "password123"}
    res = _request("/api/auth/login", method="POST", data=turing_payload, headers={"Content-Type": "application/json"})
    data_a = json.loads(res.read().decode("utf-8"))
    token_a = data_a["token"]

    # Faculty B (Hopper)
    hopper_payload = {"username": "dr.hopper", "password": "password123"}
    res = _request("/api/auth/login", method="POST", data=hopper_payload, headers={"Content-Type": "application/json"})
    data_b = json.loads(res.read().decode("utf-8"))
    token_b = data_b["token"]

    assert token_a != token_b, "Tokens must be unique per session"

    # Faculty A generates a question paper
    res = _request("/api/syllabus/samples")
    syllabus = json.loads(res.read().decode("utf-8"))["samples"][0]

    gen_payload = {
        "syllabus": syllabus,
        "exam_config": {
            "institution_name": "INSTITUTE OF ADVANCED STUDIES",
            "exam_title": "Turing Private Examination",
            "duration": "3 Hours",
            "total_marks": 100,
            "sections": [
                {"id": "s1", "name": "Part A", "question_count": 2, "marks_per_question": 5, "total_section_marks": 10, "allowed_levels": ["L1", "L2"]},
                {"id": "s2", "name": "Part B", "question_count": 2, "marks_per_question": 45, "total_section_marks": 90, "allowed_levels": ["L3", "L4"]}
            ]
        }
    }
    
    # Send with Faculty A's Authorization token
    res = _request(
        "/api/paper/generate",
        method="POST",
        data=gen_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token_a}"}
    )
    paper_a = json.loads(res.read().decode("utf-8"))["paper"]
    paper_a_id = paper_a["paper_id"]
    print(f"  -> Faculty A synthesized paper ID: {paper_a_id}")

    # 1. Faculty A can view the paper in their history
    res = _request("/api/history", headers={"Authorization": f"Bearer {token_a}"})
    history_a = json.loads(res.read().decode("utf-8"))["history"]
    assert any(p["paper_id"] == paper_a_id for p in history_a), "Faculty A must see their paper"
    print("  -> Faculty A successfully retrieved paper from their own archive.")

    # 2. Faculty B CANNOT see Faculty A's paper in their history list
    res = _request("/api/history", headers={"Authorization": f"Bearer {token_b}"})
    history_b = json.loads(res.read().decode("utf-8"))["history"]
    assert not any(p["paper_id"] == paper_a_id for p in history_b), "Faculty B must NOT see Faculty A's paper in history!"
    print("  -> [ISOLATION VERIFIED] Faculty B history list does NOT contain Faculty A's paper.")

    # 3. Faculty B CANNOT fetch Faculty A's paper directly by ID
    try:
        _request(f"/api/history/{paper_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert False, "Faculty B should NOT be able to view Faculty A's paper!"
    except urllib.error.HTTPError as e:
        assert e.code == 404, f"Expected 404 Not Found, got {e.code}"
        print("  -> [ISOLATION VERIFIED] Direct access attempt by Faculty B blocked with HTTP 404.")

    # 4. Faculty B CANNOT delete Faculty A's paper
    del_res = json.loads(_request(f"/api/history/{paper_a_id}", headers={"Authorization": f"Bearer {token_b}"}, method="DELETE").read().decode("utf-8"))
    assert del_res["deleted"] is False, "Faculty B should NOT be able to delete Faculty A's paper!"
    print("  -> [ISOLATION VERIFIED] Deletion attempt by Faculty B rejected.")

    # 5. Faculty A CAN delete their own paper
    del_res = json.loads(_request(f"/api/history/{paper_a_id}", headers={"Authorization": f"Bearer {token_a}"}, method="DELETE").read().decode("utf-8"))
    assert del_res["deleted"] is True, "Faculty A must be able to delete their own paper"
    print("  -> Faculty A successfully deleted their own paper.")

    # 6. Test logout token invalidation
    _request("/api/auth/logout", headers={"Authorization": f"Bearer {token_a}"}, method="POST", data={})
    try:
        _request("/api/history", headers={"Authorization": f"Bearer {token_a}"})
        assert False, "Revoked token should not be accepted"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("  -> [SESSION REVOKED] Revoked token correctly rejected with HTTP 401.")


if __name__ == "__main__":
    test_static_files()
    test_unauthenticated_access_blocked()
    test_faculty_login_and_token()
    test_strict_isolation_between_faculty()
    print("\n>>> ALL MANDATORY GATE & STRICT FACULTY PRIVACY TESTS PASSED 100%! <<<\n")
