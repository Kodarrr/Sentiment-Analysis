import logging

import requests

from backend.common.config import get_settings

logger = logging.getLogger(__name__)


def send_negative_feedback_alert(feedback_id: str, user_id: str, text: str, score: float) -> bool:
    """Best-effort: never raises, so a Slack outage can't fail the pipeline or trigger a retry."""
    settings = get_settings()
    if not settings.slack_webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set; skipping alert for feedback %s", feedback_id)
        return False

    payload = {
        "text": (
            f":rotating_light: Negative feedback detected (confidence {score:.2%})\n"
            f"*User:* {user_id}\n"
            f"*Feedback ID:* {feedback_id}\n"
            f"*Text:* {text}"
        )
    }

    try:
        response = requests.post(settings.slack_webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Failed to send Slack alert for feedback %s", feedback_id)
        return False
