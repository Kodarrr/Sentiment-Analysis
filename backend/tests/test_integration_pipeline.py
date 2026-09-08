"""End-to-end test of the full feedback pipeline: POST /api/v1/feedback -> real
Redis/RQ queue -> a real worker processing the job -> Postgres updated -> Slack
alert dispatched for negative feedback.

Unlike the other test modules, this one deliberately does NOT override get_db
with the transactional test-session fixture: the worker's process_feedback()
opens its own SessionLocal(), a separate connection that would never see rows
sitting in another connection's uncommitted transaction. So this test lets the
API commit for real (as it does in production) and cleans up the rows it
creates afterward.

Only the ML model call itself is mocked (no torch/transformers in this dev
environment) - everything else (HTTP request, queue dispatch, RQ job
execution, database writes, Slack call) is the real code path.
"""

from fastapi.testclient import TestClient
from rq import Queue, SimpleWorker

from backend.api.main import app
from backend.common.db import SessionLocal
from backend.common.models import Feedback
from backend.common.queue import QUEUE_NAME, get_queue
from backend.worker import sentiment as sentiment_module
from backend.worker import slack as slack_module


class FakeSlackResponse:
    status_code = 200

    def raise_for_status(self):
        pass


def run_worker_until_idle():
    connection = get_queue().connection
    worker = SimpleWorker([Queue(QUEUE_NAME, connection=connection)], connection=connection)
    worker.work(burst=True)


def cleanup_feedback(feedback_id: str) -> None:
    db = SessionLocal()
    try:
        db.query(Feedback).filter(Feedback.id == feedback_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_negative_feedback_flows_through_queue_worker_and_triggers_slack_alert(monkeypatch):
    monkeypatch.setattr(
        sentiment_module,
        "_get_pipeline",
        lambda: (lambda text, truncation=True: [{"label": "NEGATIVE", "score": 0.97}]),
    )
    slack_calls = []
    monkeypatch.setattr(
        slack_module.requests,
        "post",
        lambda url, json, timeout: slack_calls.append((url, json)) or FakeSlackResponse(),
    )
    monkeypatch.setattr(
        slack_module.get_settings(), "slack_webhook_url", "https://hooks.slack.test/abc"
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/feedback", json={"user_id": "integration-user", "text": "This is terrible"}
    )
    assert response.status_code == 201
    feedback_id = response.json()["id"]
    assert response.json()["status"] == "pending"

    try:
        run_worker_until_idle()

        db = SessionLocal()
        try:
            processed = db.get(Feedback, feedback_id)
            assert processed.status == "processed"
            assert processed.sentiment_label == "NEGATIVE"
            assert processed.sentiment_score == 0.97
            assert processed.processed_at is not None
        finally:
            db.close()

        assert len(slack_calls) == 1
        _, payload = slack_calls[0]
        assert "integration-user" in payload["text"]
        assert feedback_id in payload["text"]
    finally:
        cleanup_feedback(feedback_id)


def test_positive_feedback_flows_through_queue_worker_without_slack_alert(monkeypatch):
    monkeypatch.setattr(
        sentiment_module,
        "_get_pipeline",
        lambda: (lambda text, truncation=True: [{"label": "POSITIVE", "score": 0.99}]),
    )
    slack_calls = []
    monkeypatch.setattr(
        slack_module.requests,
        "post",
        lambda url, json, timeout: slack_calls.append((url, json)) or FakeSlackResponse(),
    )
    monkeypatch.setattr(
        slack_module.get_settings(), "slack_webhook_url", "https://hooks.slack.test/abc"
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/feedback", json={"user_id": "integration-user", "text": "This is wonderful"}
    )
    assert response.status_code == 201
    feedback_id = response.json()["id"]

    try:
        run_worker_until_idle()

        db = SessionLocal()
        try:
            processed = db.get(Feedback, feedback_id)
            assert processed.status == "processed"
            assert processed.sentiment_label == "POSITIVE"
        finally:
            db.close()

        assert slack_calls == []
    finally:
        cleanup_feedback(feedback_id)
