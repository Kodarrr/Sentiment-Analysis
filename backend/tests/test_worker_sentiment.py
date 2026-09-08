import pytest

from backend.worker import sentiment as sentiment_module


def test_analyze_sentiment_extracts_label_and_score(monkeypatch):
    def fake_pipeline(text, truncation=True):
        assert text == "great product!"
        return [{"label": "POSITIVE", "score": 0.9987}]

    monkeypatch.setattr(sentiment_module, "_get_pipeline", lambda: fake_pipeline)

    label, score = sentiment_module.analyze_sentiment("great product!")

    assert label == "POSITIVE"
    assert score == pytest.approx(0.9987)


def test_analyze_sentiment_returns_plain_float(monkeypatch):
    monkeypatch.setattr(
        sentiment_module,
        "_get_pipeline",
        lambda: (lambda text, truncation=True: [{"label": "NEGATIVE", "score": 0.5}]),
    )

    _, score = sentiment_module.analyze_sentiment("meh")

    assert isinstance(score, float)
