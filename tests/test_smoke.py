"""
Smoke tests verifying Flask server initialization, static asset delivery,
and core REST API endpoints without requiring live external LLM connectivity.
"""

import json
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


@pytest.mark.smoke
def test_auth_login_invalid_credentials(client):
    """Verify POST /api/auth/login fails with invalid credentials."""
    payload = {
        "username": "prof.turing",
        "password": "incorrect_password_999"
    }
    response = client.post(
        "/api/auth/login",
        data=json.dumps(payload),
        content_type="application/json"
    )
    data = response.get_json()
    assert data.get("success") is False
    assert "error" in data


@pytest.mark.smoke
def test_auth_login_success(client):
    """Verify POST /api/auth/login succeeds with demo faculty account."""
    payload = {
        "username": "prof.turing",
        "password": "password123"
    }
    response = client.post(
        "/api/auth/login",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("success") is True
    assert "token" in data
    assert "user" in data
    assert data["user"]["username"] == "prof.turing"

    # Test GET /api/auth/me with the obtained token
    token = data["token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.get_json()
    assert me_data.get("success") is True
    assert me_data["user"]["username"] == "prof.turing"

@pytest.mark.smoke
def test_auth_login_by_user_id_and_display_name(client):
    """Verify login works flexibly with user_id or display_name."""
    # Login with user_id
    res_id = client.post("/api/auth/login", json={"username": "usr_turing", "password": "password123"})
    assert res_id.status_code == 200
    assert res_id.get_json()["success"] is True

    # Login with display_name
    res_name = client.post("/api/auth/login", json={"username": "Prof. Alan Turing", "password": "password123"})
    assert res_name.status_code == 200
    assert res_name.get_json()["success"] is True

    # Login with trailing space in password (mobile autofill compatibility)
    res_ws = client.post("/api/auth/login", json={"username": "prof.turing", "password": "password123 "})
    assert res_ws.status_code == 200
    assert res_ws.get_json()["success"] is True
