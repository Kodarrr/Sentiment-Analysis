import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.common.db import get_db


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_submit_feedback_creates_pending_record(client):
    response = client.post(
        "/api/v1/feedback", json={"user_id": "user-1", "text": "This product is great!"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == "user-1"
    assert body["text"] == "This product is great!"
    assert body["status"] == "pending"
    assert body["sentiment_label"] is None
    assert body["retry_count"] == 0


def test_submit_feedback_rejects_empty_text(client):
    response = client.post("/api/v1/feedback", json={"user_id": "user-1", "text": ""})

    assert response.status_code == 422


def test_submit_feedback_rejects_missing_user_id(client):
    response = client.post("/api/v1/feedback", json={"text": "hello"})

    assert response.status_code == 422


def test_idempotency_key_replays_same_record(client):
    headers = {"Idempotency-Key": "key-123"}
    first = client.post(
        "/api/v1/feedback",
        json={"user_id": "user-1", "text": "first submission"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/feedback",
        json={"user_id": "user-1", "text": "a different body, same key"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["text"] == "first submission"


def test_different_idempotency_keys_create_separate_records(client):
    first = client.post(
        "/api/v1/feedback",
        json={"user_id": "user-1", "text": "one"},
        headers={"Idempotency-Key": "key-a"},
    )
    second = client.post(
        "/api/v1/feedback",
        json={"user_id": "user-1", "text": "two"},
        headers={"Idempotency-Key": "key-b"},
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
