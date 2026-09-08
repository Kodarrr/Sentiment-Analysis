from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.routers import health as health_module


def test_health_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_points_to_docs_and_health():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_ready_returns_200_when_dependencies_up(monkeypatch):
    monkeypatch.setattr(health_module, "_check_database", lambda: True)
    monkeypatch.setattr(health_module, "_check_redis", lambda: True)
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": True, "redis": True}}


def test_ready_returns_503_when_a_dependency_is_down(monkeypatch):
    monkeypatch.setattr(health_module, "_check_database", lambda: True)
    monkeypatch.setattr(health_module, "_check_redis", lambda: False)
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": True, "redis": False},
    }
