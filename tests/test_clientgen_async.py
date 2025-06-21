import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_async_start_and_get_job_lifecycle():
    payload = {
        "service": "smoke-test-service",
        "openapi_url": "https://example.com/openapi.json"
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/clients/smoke-test-service/jobs", json=payload)
        assert response.status_code == 202

        job_id = response.json().get("job_id")
        assert job_id is not None

        # Poll the job status until terminal or timeout
        for _ in range(30):  # up to 30 attempts
            status_resp = await client.get(f"/clients/smoke-test-service/jobs/{job_id}")
            assert status_resp.status_code == 200

            status_data = status_resp.json()
            if status_data["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.2)
        else:
            pytest.fail("Job did not complete in time")

        assert status_data["job_id"] == job_id
        assert status_data["service"] == "smoke-test-service"
        assert status_data["status"] in ["completed", "failed"]
