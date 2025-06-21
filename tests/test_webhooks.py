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
def test_webhook_notification_delivery(caplog):
    with caplog.at_level(logging.DEBUG):
        response = client.post("/webhooks", json={"callback_url": "http://testserver/mock-webhook"})
        assert response.status_code == 201
        webhook_id = response.json()["webhook_id"]

        service = "notify-test-service"
        job_payload = {
            "service": service,
            "openapi_url": "https://example.com/openapi.json"
        }
        post_resp = client.post(f"/clients/{service}/jobs", json=job_payload)
        assert post_resp.status_code == 202

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(job_manager.process_jobs(max_jobs=1))

        # Retry checking notifications up to 5 seconds
        for _ in range(10):
            sent = webhook_manager.get_sent_notifications()
            if any(n["webhook_id"] == webhook_id for n in sent):
                break
            time.sleep(0.5)
        else:
            pytest.fail("Webhook notification was not sent")

        print(caplog.text)
