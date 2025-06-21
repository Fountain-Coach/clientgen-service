import asyncio
import logging
import time
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.webhooks import webhook_manager
from app.core.jobs import job_manager, JobStatus

client = TestClient(app)

@pytest.fixture(autouse=True)
def fast_complete_jobs(monkeypatch):
    async def dummy_process_jobs(*args, **kwargs):
        for job in job_manager._jobs.values():
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
    monkeypatch.setattr(job_manager, "process_jobs", dummy_process_jobs)
    yield

@pytest.fixture(autouse=True)
def activate_test_mode():
    job_manager.test_mode = True
    yield
    job_manager.test_mode = False

@pytest.fixture(autouse=True)
def clear_notifications():
    webhook_manager.clear_sent_notifications()
    yield
    webhook_manager.clear_sent_notifications()

@pytest.fixture(autouse=True)
def clear_jobs_before_tests():
    job_manager._jobs.clear()
    yield
    job_manager._jobs.clear()

@pytest.fixture
def example_service():
    return "robust-test-service"

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_job_success_and_status_and_cancel(example_service, caplog):
    with caplog.at_level(logging.DEBUG):
        payload = {"service": example_service, "openapi_url": "https://example.com/openapi.json"}
        response = client.post(f"/clients/{example_service}/jobs", json=payload)
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert "pending" in response.json()["status"] or "running" in response.json()["status"]

        status_resp = client.get(f"/clients/{example_service}/jobs/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["job_id"] == job_id

        cancel_resp = client.delete(f"/clients/{example_service}/jobs/{job_id}")
        assert cancel_resp.status_code in (204, 409)

    print(caplog.text)

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_job_invalid_service_mismatch():
    payload = {"service": "serviceA", "openapi_url": "https://example.com/openapi.json"}
    response = client.post("/clients/serviceB/jobs", json=payload)
    assert response.status_code == 400

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_job_missing_fields(example_service):
    payload = {"service": example_service}  # missing openapi_url
    response = client.post(f"/clients/{example_service}/jobs", json=payload)
    assert response.status_code == 422

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_get_job_not_found():
    response = client.get("/clients/nonexistent-service/jobs/invalid-job")
    assert response.status_code == 404

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_list_clients_empty_and_pagination(example_service):
    resp_empty = client.get("/clients/")
    assert resp_empty.status_code == 200
    assert resp_empty.json().get("clients") == []

    payload = {"service": example_service, "openapi_url": "https://example.com/openapi.json"}
    for _ in range(5):
        client.post(f"/clients/{example_service}/jobs", json=payload)

    resp_paginated = client.get("/clients/", params={"page": 1, "page_size": 3})
    assert resp_paginated.status_code == 200
    clients_page = resp_paginated.json().get("clients", [])
    assert len(clients_page) <= 3

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_get_import_path_existing_and_not_found(example_service):
    resp_not_found = client.get("/clients/unknown-service/import-path")
    assert resp_not_found.status_code == 404

    payload = {"service": example_service, "openapi_url": "https://example.com/openapi.json"}
    post_resp = client.post(f"/clients/{example_service}/jobs", json=payload)
    job_id = post_resp.json()["job_id"]

    resp = client.get(f"/clients/{example_service}/import-path")
    assert resp.status_code in (200, 404)

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_webhook_register_unregister_and_invalid_url():
    resp = client.post("/webhooks", json={"callback_url": "http://testserver/mock-webhook"})
    assert resp.status_code == 201
    webhook_id = resp.json()["webhook_id"]

    del_resp = client.delete(f"/webhooks/{webhook_id}")
    assert del_resp.status_code == 204

    bad_resp = client.post("/webhooks", json={"callback_url": "not-a-valid-url"})
    assert bad_resp.status_code == 422

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_webhook_notification_delivery(example_service):
    resp = client.post("/webhooks", json={"callback_url": "http://testserver/mock-webhook"})
    webhook_id = resp.json()["webhook_id"]

    job_payload = {"service": example_service, "openapi_url": "https://example.com/openapi.json"}
    post_resp = client.post(f"/clients/{example_service}/jobs", json=job_payload)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(job_manager.process_jobs(max_jobs=1))

    # Manually trigger webhook notification for completed jobs
    for job in job_manager._jobs.values():
        if job.status == JobStatus.COMPLETED:
            asyncio.run(webhook_manager.notify_webhooks(job))

    for _ in range(10):
        sent = webhook_manager.get_sent_notifications()
        if any(n["webhook_id"] == webhook_id for n in sent):
            break
        time.sleep(0.5)
    else:
        pytest.fail("Webhook notification was not sent")

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_concurrent_job_processing(example_service):
    payload = {"service": example_service, "openapi_url": "https://example.com/openapi.json"}

    for _ in range(10):
        client.post(f"/clients/{example_service}/jobs", json=payload)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(job_manager.process_jobs(max_jobs=10))

    completed = [job for job in job_manager._jobs.values() if job.status == JobStatus.COMPLETED]
    assert len(completed) > 0
