import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.common.db import get_db
from backend.common.queue import get_queue


class FakeQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, func, *args, **kwargs):
        self.enqueued.append((func, args, kwargs))


@pytest.fixture
def fake_queue():
    return FakeQueue()


@pytest.fixture
def client(db_session, fake_queue):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_queue] = lambda: fake_queue
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_submit_feedback_creates_pending_record(client, fake_queue):
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

    assert len(fake_queue.enqueued) == 1
    func, args, _ = fake_queue.enqueued[0]
    assert func == "backend.worker.tasks.process_feedback"
    assert args == (body["id"],)


def test_submit_feedback_rejects_empty_text(client):
    response = client.post("/api/v1/feedback", json={"user_id": "user-1", "text": ""})

    assert response.status_code == 422


def test_submit_feedback_rejects_missing_user_id(client):
    response = client.post("/api/v1/feedback", json={"text": "hello"})

    assert response.status_code == 422


def test_idempotency_key_replays_same_record(client, fake_queue):
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
    assert len(fake_queue.enqueued) == 1


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
