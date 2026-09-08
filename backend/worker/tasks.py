import logging
from datetime import datetime, timezone

from backend.common.config import get_settings
from backend.common.db import SessionLocal
from backend.common.logging import correlation_id_var
from backend.common.models import Feedback
from backend.worker.sentiment import analyze_sentiment
from backend.worker.slack import send_negative_feedback_alert

logger = logging.getLogger(__name__)


def process_feedback(feedback_id: str) -> None:
    token = correlation_id_var.set(feedback_id)
    db = SessionLocal()
    try:
        feedback = db.get(Feedback, feedback_id)
        if feedback is None:
            logger.warning("feedback not found", extra={"feedback_id": feedback_id})
            return

        label, score = analyze_sentiment(feedback.text)

        feedback.sentiment_label = label
        feedback.sentiment_score = score
        feedback.status = "processed"
        feedback.processed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "feedback processed",
            extra={"feedback_id": feedback_id, "sentiment_label": label, "sentiment_score": score},
        )

        threshold = get_settings().sentiment_negative_threshold
        if label == "NEGATIVE" and score >= threshold:
            send_negative_feedback_alert(feedback_id, feedback.user_id, feedback.text, score)
    finally:
        db.close()
        correlation_id_var.reset(token)


def handle_job_failure(job, connection, exc_type, exc_value, exc_traceback) -> None:
    """RQ failure callback: fires on every failed attempt.

    job.retries_left reflects the count *before* this attempt's retry is
    consumed, so 0 (or None, if no Retry was configured) means this was the
    last allowed attempt and the job is about to land in the queue's
    FailedJobRegistry - our dead-letter queue.
    """
    feedback_id = job.args[0]
    token = correlation_id_var.set(feedback_id)
    db = SessionLocal()
    try:
        feedback = db.get(Feedback, feedback_id)
        if feedback is None:
            return

        feedback.retry_count += 1
        permanently_failed = not job.retries_left
        if permanently_failed:
            feedback.status = "failed"
        db.commit()

        logger.error(
            "feedback job failed",
            extra={
                "feedback_id": feedback_id,
                "retries_left": job.retries_left,
                "permanently_failed": permanently_failed,
                "error": str(exc_value),
            },
        )
    finally:
        db.close()
        correlation_id_var.reset(token)
