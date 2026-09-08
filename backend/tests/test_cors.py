from fastapi.testclient import TestClient

from backend.api.main import app
from backend.common.config import get_settings


def test_allows_configured_frontend_origin():
    # CORSMiddleware is configured once at app import time from whatever
    # CORS_ALLOWED_ORIGINS was set to then, so assert against the actual
    # configured origin rather than hardcoding the default - a real .env
    # with a customized value would otherwise make this test fragile.
    allowed_origin = get_settings().cors_allowed_origins_list[0]
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": allowed_origin})

    assert response.headers.get("access-control-allow-origin") == allowed_origin


def test_omits_cors_header_for_unrecognized_origin():
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
