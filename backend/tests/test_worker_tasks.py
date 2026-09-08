import uuid

import pytest

from backend.common.models import Feedback
from backend.worker import tasks


@pytest.fixture(autouse=True)
def patch_session_local(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


def test_process_feedback_updates_sentiment(db_session, monkeypatch):
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


def test_process_feedback_positive_case(db_session, monkeypatch):
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: ("POSITIVE", 0.99))
    feedback = Feedback(user_id="u1", text="Loved it", status="pending")
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    tasks.process_feedback(feedback_id)

    updated = db_session.get(Feedback, feedback_id)
    assert updated.status == "processed"
    assert updated.sentiment_label == "POSITIVE"


def test_process_feedback_missing_record_is_noop(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, "analyze_sentiment", lambda text: calls.append(text))

    tasks.process_feedback(str(uuid.uuid4()))

    assert calls == []
