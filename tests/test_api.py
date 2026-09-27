import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_create_and_get_session():
    payload = {
        "job_title": "Test Professor",
        "job_description": "Faculty position test",
        "required_degree": "PhD",
        "required_specialization": "Computer Science",
        "minimum_experience": 3.0,
        "minimum_publications": 5,
        "publication_window_years": 5,
        "top_n": 5,
        "scoring_weights": {
            "education": 0.35,
            "publication": 0.30,
            "academic_experience": 0.20,
            "industry_experience": 0.15
        }
    }

    create_res = client.post("/api/sessions", json=payload)
    assert create_res.status_code == 201
    session_data = create_res.json()
    assert "session_id" in session_data
    session_id = session_data["session_id"]

    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["job_title"] == "Test Professor"

def test_upload_and_status():
    payload = {
        "job_title": "Upload Test",
        "required_degree": "PhD",
        "required_specialization": "Computer Science",
        "minimum_experience": 2.0,
        "minimum_publications": 2,
        "publication_window_years": 5,
        "top_n": 5
    }
    create_res = client.post("/api/sessions", json=payload)
    session_id = create_res.json()["session_id"]

    zip_path = Path("data/test_resumes/resumes.zip")
    if zip_path.exists():
        with open(zip_path, "rb") as f:
            upload_res = client.post(f"/api/sessions/{session_id}/upload", files={"file": ("resumes.zip", f, "application/zip")})
        assert upload_res.status_code == 200

        status_res = client.get(f"/api/sessions/{session_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["session_id"] == session_id
