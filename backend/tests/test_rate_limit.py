import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.common.config import get_settings
from backend.common.db import get_db
from backend.common.queue import get_queue


class FakeQueue:
    def enqueue(self, *args, **kwargs):
        pass


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_queue] = lambda: FakeQueue()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_requests_within_limit_succeed(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 5)

    for _ in range(5):
        response = client.post("/api/v1/feedback", json={"user_id": "u1", "text": "hi"})
        assert response.status_code == 201


def test_requests_over_limit_are_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 2)

    for _ in range(2):
        response = client.post("/api/v1/feedback", json={"user_id": "u1", "text": "hi"})
        assert response.status_code == 201

    response = client.post("/api/v1/feedback", json={"user_id": "u1", "text": "hi"})
    assert response.status_code == 429
