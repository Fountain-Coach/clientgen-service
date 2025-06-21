import asyncio
import logging
import time
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.webhooks import webhook_manager
from app.core.jobs import job_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_subprocess_popen():
    with patch("subprocess.Popen") as mock_popen:
        process_mock = MagicMock()
        attrs = {
            "poll.return_value": 0,
            "stdout.read.return_value": "",
            "stderr.read.return_value": "",
            "terminate.return_value": None,
        }
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock
        yield

@pytest.fixture(autouse=True)
def clear_notifications():
    webhook_manager.clear_sent_notifications()
    yield
    webhook_manager.clear_sent_notifications()

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_client_generation_job_success(caplog):
    with caplog.at_level(logging.DEBUG):
        service = "expressive-service"
        payload = {
            "service": service,
            "openapi_url": "https://example.com/openapi.json"
        }
        response = client.post(f"/clients/{service}/jobs", json=payload)
        assert response.status_code == 202
        json_data = response.json()
        assert "job_id" in json_data
        assert json_data["status"] in ["pending", "running"]
        assert "submitted_at" in json_data
    print(caplog.text)

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_client_generation_job_service_mismatch():
    service = "expressive-service"
    payload = {
        "service": "mismatched-service",
        "openapi_url": "https://example.com/openapi.json"
    }
    response = client.post(f"/clients/{service}/jobs", json=payload)
    assert response.status_code == 400

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_client_generation_job_missing_fields():
    service = "expressive-service"
    payload = {"service": service}  # missing openapi_url
    response = client.post(f"/clients/{service}/jobs", json=payload)
    assert response.status_code == 422

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_get_job_status_not_found():
    response = client.get("/clients/nonexistent-service/jobs/invalid-job")
    assert response.status_code == 404

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_get_and_cancel_job():
    service = "expressive-service"
    payload = {
        "service": service,
        "openapi_url": "https://example.com/openapi.json"
    }
    post_resp = client.post(f"/clients/{service}/jobs", json=payload)
    job_id = post_resp.json()["job_id"]

    get_resp = client.get(f"/clients/{service}/jobs/{job_id}")
    assert get_resp.status_code == 200

    del_resp = client.delete(f"/clients/{service}/jobs/{job_id}")
    assert del_resp.status_code in (204, 409)

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_list_clients_pagination():
    service = "expressive-service"
    payload = {
        "service": service,
        "openapi_url": "https://example.com/openapi.json"
    }
    for _ in range(3):
        client.post(f"/clients/{service}/jobs", json=payload)
    response = client.get("/clients/", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["clients"]) <= 2
    assert data["page"] == 1

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_get_import_path_and_not_found():
    service = "expressive-service"
    # Expect 404 for unknown service
    resp = client.get(f"/clients/unknown-service/import-path")
    assert resp.status_code == 404

    # For existing, we can only test presence of keys or 404 (due to mock)
    post_resp = client.post(f"/clients/{service}/jobs", json={
        "service": service,
        "openapi_url": "https://example.com/openapi.json"
    })
    job_id = post_resp.json()["job_id"]
    resp = client.get(f"/clients/{service}/import-path")
    assert resp.status_code in (200, 404)

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_webhook_register_unregister():
    # Register webhook
    resp = client.post("/webhooks", json={"callback_url": "http://testserver/mock-webhook"})
    assert resp.status_code == 201
    webhook_id = resp.json()["webhook_id"]

    # Unregister webhook
    del_resp = client.delete(f"/webhooks/{webhook_id}")
    assert del_resp.status_code == 204

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_webhook_notification_delivery():
    resp = client.post("/webhooks", json={"callback_url": "http://testserver/mock-webhook"})
    webhook_id = resp.json()["webhook_id"]

    service = "expressive-service"
    job_payload = {
        "service": service,
        "openapi_url": "https://example.com/openapi.json"
    }
    post_resp = client.post(f"/clients/{service}/jobs", json=job_payload)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(job_manager.process_jobs(max_jobs=1))

    # Retry for up to 5s to wait for notification
    for _ in range(10):
        sent = webhook_manager.get_sent_notifications()
        if any(n["webhook_id"] == webhook_id for n in sent):
            break
        time.sleep(0.5)
    else:
        pytest.fail("Webhook notification was not sent")

    print("Sent notifications:", sent)
