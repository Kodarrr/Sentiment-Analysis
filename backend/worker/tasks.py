from datetime import datetime, timezone

from backend.common.db import SessionLocal
from backend.common.models import Feedback
from backend.worker.sentiment import analyze_sentiment


def process_feedback(feedback_id: str) -> None:
    db = SessionLocal()
    try:
        feedback = db.get(Feedback, feedback_id)
        if feedback is None:
            return

        label, score = analyze_sentiment(feedback.text)

        feedback.sentiment_label = label
        feedback.sentiment_score = score
        feedback.status = "processed"
        feedback.processed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def handle_job_failure(job, connection, exc_type, exc_value, exc_traceback) -> None:
    """RQ failure callback: fires on every failed attempt.

    job.retries_left reflects the count *before* this attempt's retry is
    consumed, so 0 (or None, if no Retry was configured) means this was the
    last allowed attempt and the job is about to land in the queue's
    FailedJobRegistry - our dead-letter queue.
    """
    feedback_id = job.args[0]
    db = SessionLocal()
    try:
        feedback = db.get(Feedback, feedback_id)
        if feedback is None:
            return

        feedback.retry_count += 1
        if not job.retries_left:
            feedback.status = "failed"
        db.commit()
    finally:
        db.close()
