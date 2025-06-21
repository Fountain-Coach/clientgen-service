import asyncio
import logging
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
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
    from app.core.webhooks import webhook_manager
    webhook_manager.clear_sent_notifications()
    yield
    webhook_manager.clear_sent_notifications()

@pytest.mark.timeout(30)
@pytest.mark.flaky(reruns=2)
def test_post_client_generation_job_success(caplog):
    with caplog.at_level(logging.DEBUG):
        service = "test-service"
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

# ... You can similarly update other tests to use caplog if needed ...

