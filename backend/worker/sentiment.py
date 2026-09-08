from functools import lru_cache

from backend.common.config import get_settings


@lru_cache
def _get_pipeline():
    # Imported lazily so anything that only needs analyze_sentiment's interface
    # (e.g. unit tests that monkeypatch this function) doesn't require
    # transformers/torch to be installed.
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=get_settings().model_name)


def analyze_sentiment(text: str) -> tuple[str, float]:
    result = _get_pipeline()(text, truncation=True)[0]
    return result["label"], float(result["score"])
