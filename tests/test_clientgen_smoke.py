import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@pytest.mark.asyncio
def test_landing_page_returns_json():
    resp = client.get("/")
    assert resp.status_code == 200
    # Accept JSON response, since main.py returns JSON
    assert "application/json" in resp.headers.get("content-type", "")

def wait_for_job_completion(service: str, job_id: str, timeout=10):
    start = time.time()
    while True:
        resp = client.get(f"/clients/{service}/jobs/{job_id}")
        if resp.status_code != 200:
            pytest.fail(f"Failed to get job status: {resp.status_code} {resp.text}")
        status = resp.json().get("status")
        if status in ("completed", "failed"):
            return resp.json()
        if time.time() - start > timeout:
            pytest.fail(f"Timeout waiting for job {job_id} to complete")
        time.sleep(0.5)

@pytest.mark.asyncio
def test_start_and_get_job_lifecycle():
    payload = {
        "service": "smoke-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    start_resp = client.post("/clients/smoke-test-service/jobs", json=payload)
    assert start_resp.status_code == 202
    job_id = start_resp.json().get("job_id")
    assert job_id is not None

    job_info = wait_for_job_completion("smoke-test-service", job_id)
    assert job_info["status"] == "completed"
    assert "result" in job_info

@pytest.mark.asyncio
def test_list_clients_behavior():
    resp = client.get("/clients/")
    assert resp.status_code == 200
    clients_list = resp.json().get("clients")
    assert isinstance(clients_list, list)
    # At least one client service should exist if previous jobs completed
    assert any(client["service"] == "smoke-test-service" for client in clients_list)

@pytest.mark.asyncio
def test_get_import_path_behavior():
    resp = client.get("/clients/smoke-test-service/import-path")
    # May 404 if no client generated yet, so accept 200 or 404
    assert resp.status_code in (200, 404)

@pytest.mark.asyncio
def test_webhook_registration_and_deletion():
    # Register webhook
    reg_resp = client.post("/webhooks", json={"callback_url": "http://example.com/webhook"})
    assert reg_resp.status_code == 201
    webhook_id = reg_resp.json().get("webhook_id")
    assert webhook_id is not None

    # Unregister webhook
    del_resp = client.delete(f"/webhooks/{webhook_id}")
    assert del_resp.status_code == 204

@pytest.mark.asyncio
def test_concurrent_job_creation():
    payload = {
        "service": "concurrent-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    job_ids = set()
    for _ in range(3):
        resp = client.post("/clients/concurrent-test-service/jobs", json=payload)
        assert resp.status_code == 202
        job_id = resp.json().get("job_id")
        assert job_id not in job_ids
        job_ids.add(job_id)

    # Poll all jobs for completion
    for job_id in job_ids:
        job_info = wait_for_job_completion("concurrent-test-service", job_id)
        assert job_info["status"] == "completed"
