import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def poll_job_until_complete(service: str, job_id: str, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(f"/clients/{service}/jobs/{job_id}")
        if resp.status_code == 200:
            status = resp.json().get("status")
            if status in ["completed", "failed", "cancelled"]:
                return resp
        time.sleep(0.5)
    pytest.fail(f"Job {job_id} did not complete within {timeout} seconds")

def test_start_and_complete_job():
    payload = {
        "service": "smoke-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    # Start the job
    start_resp = client.post(f"/clients/{payload['service']}/jobs", json=payload)
    assert start_resp.status_code == 202
    job_id = start_resp.json().get("job_id")
    assert job_id is not None

    # Poll until job is complete
    final_resp = poll_job_until_complete(payload["service"], job_id)
    assert final_resp.status_code == 200
    assert final_resp.json().get("status") == "completed"
