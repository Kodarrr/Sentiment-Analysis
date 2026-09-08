from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.common.db import get_db
from backend.common.models import Feedback
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


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "hunter22"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_feedback(db_session, *, user_id="u1", text="hi", label=None, score=None, days_ago=0):
    fb = Feedback(
        user_id=user_id,
        text=text,
        status="processed" if label else "pending",
        sentiment_label=label,
        sentiment_score=score,
    )
    db_session.add(fb)
    db_session.commit()
    db_session.refresh(fb)
    if days_ago:
        fb.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        db_session.commit()
    return fb


def test_list_feedback_requires_auth(client):
    response = client.get("/api/v1/feedback")

    assert response.status_code == 403


def test_list_feedback_returns_items(client, db_session, auth_headers):
    make_feedback(db_session, text="one")
    make_feedback(db_session, text="two")

    response = client.get("/api/v1/feedback", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_list_feedback_paginates(client, db_session, auth_headers):
    for i in range(5):
        make_feedback(db_session, text=f"item-{i}")

    response = client.get("/api/v1/feedback?page=2&page_size=2", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 2
    assert body["page_size"] == 2


def test_list_feedback_filters_by_sentiment(client, db_session, auth_headers):
    make_feedback(db_session, text="good", label="POSITIVE", score=0.9)
    make_feedback(db_session, text="bad", label="NEGATIVE", score=0.9)

    response = client.get("/api/v1/feedback?sentiment=negative", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["text"] == "bad"


def test_list_feedback_filters_by_date_range(client, db_session, auth_headers):
    make_feedback(db_session, text="today")
    make_feedback(db_session, text="old", days_ago=10)

    today = date.today().isoformat()
    response = client.get(f"/api/v1/feedback?start_date={today}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["text"] == "today"


def test_sentiment_trend_requires_auth(client):
    response = client.get("/api/v1/feedback/stats/trend")

    assert response.status_code == 403


def test_sentiment_trend_aggregates_by_day(client, db_session, auth_headers):
    make_feedback(db_session, text="a", label="POSITIVE", score=0.9)
    make_feedback(db_session, text="b", label="POSITIVE", score=0.9)
    make_feedback(db_session, text="c", label="NEGATIVE", score=0.9)

    response = client.get("/api/v1/feedback/stats/trend", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["positive_count"] == 2
    assert body[0]["negative_count"] == 1
