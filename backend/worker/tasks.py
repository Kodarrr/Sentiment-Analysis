import logging
from datetime import datetime, timezone

from backend.common.config import get_settings
from backend.common.db import SessionLocal
from backend.common.logging import correlation_id_var
from backend.common.models import Feedback
from backend.worker.sentiment import analyze_sentiment_full
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

        result = analyze_sentiment_full(feedback.text)

        feedback.sentiment_label = result.label
        feedback.sentiment_score = result.score
        feedback.sentiment_polarity = result.polarity
        feedback.confidence = result.confidence
        feedback.probabilities = result.probabilities
        feedback.model_id = result.model_id
        feedback.model_revision = result.model_revision
        feedback.status = "processed"
        feedback.processed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "feedback processed",
            extra={
                "feedback_id": feedback_id,
                "sentiment_label": result.label,
                "sentiment_polarity": result.polarity,
                "confidence": result.confidence,
                "model_id": result.model_id,
            },
        )

        settings = get_settings()
        # Support both top-class confidence and aggregated negative polarity probability
        effective_negative_score = max(result.confidence, result.negative_polarity_score)
        threshold = settings.confidence_threshold or settings.sentiment_negative_threshold

        if result.polarity == "negative" and effective_negative_score >= threshold:
            send_negative_feedback_alert(
                feedback_id=feedback_id,
                user_id=feedback.user_id,
                text=feedback.text,
                score=effective_negative_score,
                fine_label=result.label,
            )
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
