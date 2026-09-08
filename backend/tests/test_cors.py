from fastapi.testclient import TestClient

from backend.api.main import app


def test_allows_configured_frontend_origin():
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_omits_cors_header_for_unrecognized_origin():
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
