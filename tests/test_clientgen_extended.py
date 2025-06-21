import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
@patch('app.core.jobs.job_manager.process_jobs', new_callable=lambda: (lambda *args, **kwargs: None))
async def test_submit_job_with_local_openapi(mock_process_jobs):
    payload = {
        "service": "extended-test-service",
        "openapi_url": "https://client-generator.fountain.coach/openapi.json"
    }
    response = client.post("/jobs/clients/extended-test-service/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json().get("job_id")
    assert job_id is not None

    status_resp = client.get(f"/jobs/clients/extended-test-service/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data.get("status") in ("pending", "running", "completed", "failed")
