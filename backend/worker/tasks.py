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
