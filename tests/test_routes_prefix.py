import pytest
from app.main import app

EXPECTED_PREFIXES = [
    "/clients",
    "/jobs",
    "/webhooks",
    "/mock-webhook",
    "/health",
    "/"
]

@pytest.mark.asyncio
async def test_route_prefixes_are_correct():
    routes = [route.path for route in app.routes if hasattr(route, "path")]

    # Check that no route path contains the same segment twice consecutively, e.g. /jobs/jobs or /clients/clients
    for path in routes:
        segments = [seg for seg in path.split("/") if seg]
        for i in range(len(segments) - 1):
            assert segments[i] != segments[i + 1], f"Repeated consecutive segment '{segments[i]}' found in path: {path}"

    # Ensure expected prefixes appear in at least one route path
    for prefix in EXPECTED_PREFIXES:
        matched = any(route.startswith(prefix) for route in routes)
        assert matched, f"Expected prefix '{prefix}' not found in any route paths"
