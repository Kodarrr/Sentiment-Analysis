from functools import lru_cache

from backend.common.config import get_settings
from backend.worker.sentiment_engine import (
    SentimentResult,
    analyze_sentiment as analyze_sentiment_engine,
)


@lru_cache
def _default_pipeline():
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=get_settings().model_name)


# Kept for backward compatibility with existing unit tests that monkeypatch _get_pipeline
_get_pipeline = _default_pipeline


def analyze_sentiment_full(text: str, engine_override: str | None = None) -> SentimentResult:
    """Invokes the full unified sentiment engine returning complete metadata."""
    if _get_pipeline is not _default_pipeline:
        result = _get_pipeline()(text, truncation=True)[0]
        label = str(result["label"])
        score = float(result["score"])
        polarity = (
            "negative"
            if label.upper() in ["NEGATIVE", "SN", "WN"]
            else "positive"
            if label.upper() in ["POSITIVE", "SP", "WP"]
            else "neutral"
        )
        return SentimentResult(
            label=label,
            score=score,
            polarity=polarity,
            confidence=score,
            probabilities={label: score},
            model_id="distilbert-mock",
            model_revision=None,
            negative_polarity_score=score if polarity == "negative" else 0.0,
        )
    return analyze_sentiment_engine(text, engine_override=engine_override)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Backward-compatible interface returning (label, score)."""
    if _get_pipeline is not _default_pipeline:
        result = _get_pipeline()(text, truncation=True)[0]
        return result["label"], float(result["score"])

    res = analyze_sentiment_full(text)
    return res.label, res.score
