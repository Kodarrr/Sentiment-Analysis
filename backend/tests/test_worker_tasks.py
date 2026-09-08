import uuid

import pytest

from backend.common.logging import correlation_id_var
from backend.common.models import Feedback
from backend.worker import tasks


@pytest.fixture(autouse=True)
def patch_session_local(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


@pytest.fixture
def fake_slack_alert(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tasks, "send_negative_feedback_alert", lambda *args: calls.append(args) or True
    )
    return calls


def test_process_feedback_updates_sentiment(db_session, monkeypatch, fake_slack_alert):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("NEGATIVE", 0.987654))
    feedback = Feedback(user_id="u1", text="This is terrible", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    updated = db_session.get(Feedback, feedback_id)
    assert updated.status == "processed"
    assert updated.sentiment_label == "NEGATIVE"
    assert updated.sentiment_score == pytest.approx(0.987654)
    assert updated.processed_at is not None


def test_process_feedback_positive_case(db_session, monkeypatch, fake_slack_alert):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("POSITIVE", 0.99))
    feedback = Feedback(user_id="u1", text="Loved it", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    updated = db_session.get(Feedback, feedback_id)
    assert updated.status == "processed"
    assert updated.sentiment_label == "POSITIVE"


def test_process_feedback_sets_correlation_id_to_feedback_id_during_processing(
    db_session, monkeypatch, fake_slack_alert
):
    seen = {}

    def fake_analyze_sentiment(text):
        seen["cid"] = correlation_id_var.get()
        return "POSITIVE", 0.9

    monkeypatch.setattr(tasks, "analyze_sentiment", fake_analyze_sentiment)
    feedback = Feedback(user_id="u1", text="ok", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    assert correlation_id_var.get() is None
    tasks.process_feedback(feedback_id)

    assert seen["cid"] == feedback_id
    assert correlation_id_var.get() is None


def test_process_feedback_sends_slack_alert_for_negative_above_threshold(
    db_session, monkeypatch, fake_slack_alert
):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("NEGATIVE", 0.95))
    feedback = Feedback(user_id="u1", text="This is terrible", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    assert len(fake_slack_alert) == 1
    assert fake_slack_alert[0] == (feedback_id, "u1", "This is terrible", 0.95)


def test_process_feedback_skips_slack_alert_below_threshold(
    db_session, monkeypatch, fake_slack_alert
):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("NEGATIVE", 0.5))
    feedback = Feedback(user_id="u1", text="meh", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    assert fake_slack_alert == []


def test_process_feedback_skips_slack_alert_for_positive(
    db_session, monkeypatch, fake_slack_alert
):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("POSITIVE", 0.99))
    feedback = Feedback(user_id="u1", text="great", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    assert fake_slack_alert == []


def test_process_feedback_missing_record_is_noop(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: calls.append(text))

    tasks.process_feedback(str(uuid.uuid4()))

    assert calls == []


class FakeJob:
    def __init__(self, feedback_id, retries_left):
        self.args = (feedback_id,)
        self.retries_left = retries_left


def test_handle_job_failure_with_retries_remaining_keeps_pending(db_session):
    feedback = Feedback(user_id="u1", text="boom", status="pending", retry_count=0)
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    job = FakeJob(feedback_id, retries_left=2)
    tasks.handle_job_failure(job, None, RuntimeError, RuntimeError("boom"), None)

    updated = db_session.get(Feedback, feedback_id)
    assert updated.retry_count == 1
    assert updated.status == "pending"


def test_handle_job_failure_exhausted_marks_failed(db_session):
    feedback = Feedback(user_id="u1", text="boom", status="pending", retry_count=2)
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    job = FakeJob(feedback_id, retries_left=0)
    tasks.handle_job_failure(job, None, RuntimeError, RuntimeError("boom"), None)

    updated = db_session.get(Feedback, feedback_id)
    assert updated.retry_count == 3
    assert updated.status == "failed"


def test_handle_job_failure_missing_record_is_noop(db_session):
    job = FakeJob(str(uuid.uuid4()), retries_left=0)

    tasks.handle_job_failure(job, None, RuntimeError, RuntimeError("boom"), None)
