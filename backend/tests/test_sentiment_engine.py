import pytest
from unittest.mock import MagicMock, patch

from backend.worker.sentiment_engine import (
    BANGLA_POLARITY_MAP,
    DISTILBERT_POLARITY_MAP,
    BanglaBERTClassifier,
    DistilBERTClassifier,
    SentimentResult,
    analyze_sentiment,
    csebuetnlp_normalize,
    is_mostly_bangla,
)


def test_bangla_normalization():
    raw_text = "খুবই    সুন্দর     প্রোডাক্ট!!!!!   "
    normalized = csebuetnlp_normalize(raw_text)
    assert isinstance(normalized, str)
    assert len(normalized) > 0


def test_polarity_mapping_bangla():
    assert BANGLA_POLARITY_MAP["SN"] == "negative"
    assert BANGLA_POLARITY_MAP["WN"] == "negative"
    assert BANGLA_POLARITY_MAP["NU"] == "neutral"
    assert BANGLA_POLARITY_MAP["WP"] == "positive"
    assert BANGLA_POLARITY_MAP["SP"] == "positive"


def test_polarity_mapping_distilbert():
    assert DISTILBERT_POLARITY_MAP["NEGATIVE"] == "negative"
    assert DISTILBERT_POLARITY_MAP["POSITIVE"] == "positive"


def test_language_routing_bangla_script():
    # Pure Bangla
    assert is_mostly_bangla("আপনাদের সার্ভিসটা অসাধারণ!") is True
    assert is_mostly_bangla("খুব বাজে কোয়ালিটি") is True

    # Mixed Bangla + Numbers/English brand
    assert is_mostly_bangla("iPhone 15 খুব ভালো ফোন") is True

    # Pure English
    assert is_mostly_bangla("This was an awful delivery.") is False
    assert is_mostly_bangla("Loved the packaging, highly recommend!") is False

    # Edge cases: 0 letters / only punctuation / numbers (must not raise ZeroDivisionError)
    assert is_mostly_bangla("") is False
    assert is_mostly_bangla("1234567890") is False
    assert is_mostly_bangla("!@#$%^&*()_+") is False
    assert is_mostly_bangla(":-)") is False


def test_engine_mode_routing(monkeypatch):
    bangla_mock = MagicMock()
    bangla_mock.predict.return_value = SentimentResult(
        label="SP",
        score=0.95,
        polarity="positive",
        confidence=0.95,
        probabilities={"SP": 0.95, "WP": 0.05},
        model_id="bangla-test",
        model_revision="abc",
        negative_polarity_score=0.0,
    )

    distil_mock = MagicMock()
    distil_mock.predict.return_value = SentimentResult(
        label="POSITIVE",
        score=0.99,
        polarity="positive",
        confidence=0.99,
        probabilities={"POSITIVE": 0.99, "NEGATIVE": 0.01},
        model_id="distil-test",
        model_revision=None,
        negative_polarity_score=0.01,
    )

    monkeypatch.setattr(BanglaBERTClassifier, "get_instance", lambda: bangla_mock)
    monkeypatch.setattr(DistilBERTClassifier, "get_instance", lambda: distil_mock)

    # 1. Force bangla engine
    with patch("backend.worker.sentiment_engine.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_engine = "bangla"
        res = analyze_sentiment("Hello English text")
        assert res.model_id == "bangla-test"

    # 2. Force distilbert engine
    with patch("backend.worker.sentiment_engine.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_engine = "distilbert"
        res = analyze_sentiment("খুব ভালো সার্ভিস")
        assert res.model_id == "distil-test"

    # 3. Auto engine
    with patch("backend.worker.sentiment_engine.get_settings") as mock_settings:
        mock_settings.return_value.sentiment_engine = "auto"
        res_bn = analyze_sentiment("খুব ভালো সার্ভিস")
        assert res_bn.model_id == "bangla-test"

        res_en = analyze_sentiment("Great product")
        assert res_en.model_id == "distil-test"


def test_banglabert_inference_with_mocked_model(monkeypatch):
    import math
    import sys

    class MockArray(list):
        def argmax(self):
            return self.index(max(self))

    class MockTensor:
        def __init__(self, data):
            self.data = data

        def to(self, device):
            return self

        def squeeze(self, dim):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return MockArray(self.data)

    class MockTorch:
        def __init__(self):
            self.cuda = MagicMock()
            self.cuda.is_available.return_value = False

        def inference_mode(self):
            from contextlib import nullcontext

            return nullcontext()

        def tensor(self, data):
            return MockTensor(data)

        def softmax(self, logits, dim=-1):
            vals = logits.data[0]
            max_v = max(vals)
            exp_v = [math.exp(v - max_v) for v in vals]
            sum_exp = sum(exp_v)
            return MockTensor([v / sum_exp for v in exp_v])

    mock_torch = MockTorch()
    monkeypatch.setitem(sys.modules, "torch", mock_torch)

    mock_transformers = MagicMock()
    monkeypatch.setitem(sys.modules, "transformers", mock_transformers)

    # Mock tokenizer and model
    fake_tokenizer = MagicMock()
    fake_tokenizer.return_value = {
        "input_ids": mock_torch.tensor([[101, 102]]),
        "attention_mask": mock_torch.tensor([[1, 1]]),
    }

    # Logits correspond to: [NU, SN, WN, SP, WP]
    # Class 1 (SN) has highest logit (5.0)
    fake_logits = mock_torch.tensor([[1.0, 5.0, 2.0, 0.1, 0.2]])
    fake_output = MagicMock()
    fake_output.logits = fake_logits

    fake_model = MagicMock()
    fake_model.return_value = fake_output
    fake_model.config.id2label = {0: "NU", 1: "SN", 2: "WN", 3: "SP", 4: "WP"}
    fake_model.config._commit_hash = "commit_12345"

    mock_transformers.AutoTokenizer.from_pretrained.return_value = fake_tokenizer
    mock_transformers.AutoModelForSequenceClassification.from_pretrained.return_value = fake_model

    classifier = BanglaBERTClassifier(model_id="test-model", hf_token="")
    result = classifier.predict("খুব বাজে অভিজ্ঞতা")

    assert result.label == "SN"
    assert result.polarity == "negative"
    assert result.confidence > 0.80
    assert result.probabilities["SN"] > 0.80
    assert result.negative_polarity_score == pytest.approx(
        result.probabilities["SN"] + result.probabilities["WN"]
    )
    assert result.model_revision == "commit_12345"
    assert result.model_id == "test-model"


def test_worker_flow_with_mocked_model(db_session, monkeypatch):
    from backend.common.models import Feedback
    from backend.worker import tasks

    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)

    alert_calls = []

    def fake_alert(*args, **kwargs):
        alert_calls.append({"args": args, "kwargs": kwargs})
        return True

    monkeypatch.setattr(tasks, "send_negative_feedback_alert", fake_alert)

    mock_result = SentimentResult(
        label="SN",
        score=0.92,
        polarity="negative",
        confidence=0.92,
        probabilities={"SN": 0.92, "WN": 0.05, "NU": 0.02, "WP": 0.005, "SP": 0.005},
        model_id="sm-khalil/banglabert-sentigold",
        model_revision="rev_xyz",
        negative_polarity_score=0.97,
    )

    monkeypatch.setattr(tasks, "analyze_sentiment_full", lambda text: mock_result)

    fb = Feedback(user_id="user_bn", text="একদম বাজে কোয়ালিটি", status="pending")
    db_session.add(fb)
    db_session.commit()
    fb_id = str(fb.id)

    tasks.process_feedback(fb_id)

    saved = db_session.get(Feedback, fb_id)
    assert saved.status == "processed"
    assert saved.sentiment_label == "SN"
    assert saved.sentiment_score == pytest.approx(0.92)
    assert saved.sentiment_polarity == "negative"
    assert saved.confidence == pytest.approx(0.92)
    assert saved.probabilities["SN"] == pytest.approx(0.92)
    assert saved.model_id == "sm-khalil/banglabert-sentigold"
    assert saved.model_revision == "rev_xyz"

    # Verify Slack alert was triggered
    assert len(alert_calls) == 1
    call = alert_calls[0]
    fine_label = call["kwargs"].get("fine_label") or (
        call["args"][4] if len(call["args"]) > 4 else None
    )
    score = call["kwargs"].get("score", call["args"][3] if len(call["args"]) > 3 else None)
    assert fine_label == "SN"
    assert score == pytest.approx(0.97)


@pytest.mark.slow
def test_slow_integration_model_loading_skipped_unless_configured():
    import os
    if not os.getenv("RUN_SLOW_INTEGRATION"):
        pytest.skip("Skipping slow real model download test. Set RUN_SLOW_INTEGRATION=1 to run.")
