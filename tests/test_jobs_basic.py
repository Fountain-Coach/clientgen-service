import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_start_job_success():
    payload = {
        "service": "basic-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    response = client.post("/jobs/clients/basic-test-service/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"

def test_get_job_status():
    payload = {
        "service": "basic-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    response = client.post("/jobs/clients/basic-test-service/jobs", json=payload)
    job_id = response.json()["job_id"]
    status_response = client.get(f"/jobs/clients/basic-test-service/jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert status_data["status"] in ["pending", "running", "completed", "failed"]

def test_cancel_job():
    payload = {
        "service": "basic-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    response = client.post("/jobs/clients/basic-test-service/jobs", json=payload)
    job_id = response.json()["job_id"]
    cancel_response = client.delete(f"/jobs/clients/basic-test-service/jobs/{job_id}")
    # Cancellation may succeed or fail if job is running/completed
    assert cancel_response.status_code in [204, 409]
