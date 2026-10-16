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


def analyze_sentiment_full(text: str) -> SentimentResult:
    """Invokes the full unified sentiment engine returning complete metadata."""
    return analyze_sentiment_engine(text)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Backward-compatible interface returning (label, score)."""
    if _get_pipeline is not _default_pipeline:
        result = _get_pipeline()(text, truncation=True)[0]
        return result["label"], float(result["score"])

    res = analyze_sentiment_full(text)
    return res.label, res.score
