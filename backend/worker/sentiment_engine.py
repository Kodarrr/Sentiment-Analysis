"""Unified Sentiment Engine supporting fine-tuned BanglaBERT (SentiGOLD 5-class) and DistilBERT (SST-2 English).

Features:
- Lazy process-level singletons (models and tokenizers loaded ONCE per worker process).
- Bangla text normalization via csebuetnlp normalizer.
- Dynamic id2label extraction from model config.
- Coarse polarity mapping (negative, neutral, positive).
- Robust language routing (Bangla script vs English/Latin, handling empty/punct edge cases).
- torch.inference_mode() with max_length=128 and automatic device selection (CUDA if available, else CPU).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.common.config import get_settings

logger = logging.getLogger(__name__)

# Safe import of csebuetnlp normalizer (graceful fallback if not installed)
try:
    from normalizer import normalize as csebuetnlp_normalize
except ImportError:
    try:
        from csebuetnlp_normalizer import normalize as csebuetnlp_normalize  # type: ignore[no-redef]
    except ImportError:

        def csebuetnlp_normalize(text: str) -> str:
            return text


# Expected SentiGOLD labels:
# NU = Neutral, SN = Strongly Negative, WN = Weakly Negative, SP = Strongly Positive, WP = Weakly Positive
BANGLA_POLARITY_MAP: dict[str, str] = {
    "SN": "negative",
    "WN": "negative",
    "NU": "neutral",
    "WP": "positive",
    "SP": "positive",
}

DISTILBERT_POLARITY_MAP: dict[str, str] = {
    "NEGATIVE": "negative",
    "POSITIVE": "positive",
}


@dataclass
class SentimentResult:
    label: str  # Fine-grained label: SN, WN, NU, WP, SP (or NEGATIVE/POSITIVE)
    score: float  # Top confidence score (matches legacy sentiment_score)
    polarity: str  # Coarse polarity: "negative", "neutral", "positive"
    confidence: float  # Confidence of top prediction
    probabilities: dict[str, float]  # Full softmax distribution across all classes
    model_id: str
    model_revision: str | None
    negative_polarity_score: float  # Sum of negative probabilities (e.g. P(SN) + P(WN))


def is_mostly_bangla(text: str) -> bool:
    """Detects whether text is primarily written in the Bengali Unicode script (U+0980 - U+09FF).

    Safely handles numbers, emojis, and punctuation without division-by-zero.
    """
    if not text:
        return False

    bangla_count = sum(1 for char in text if "\u0980" <= char <= "\u09ff")
    if bangla_count == 0:
        return False

    # Count all letters (alphabetic characters across all scripts)
    letter_count = sum(1 for char in text if char.isalpha())
    if letter_count == 0:
        # String has Bangla characters and no Latin/other alphabets (e.g. Bangla with digits/puncts)
        return True

    # If Bangla script accounts for at least 30% of alphabetic characters, classify as Bangla
    return (bangla_count / letter_count) >= 0.3


class BanglaBERTClassifier:
    """Lazy singleton wrapper for the fine-tuned BanglaBERT 5-class sequence classifier."""

    _instance: BanglaBERTClassifier | None = None

    def __init__(self, model_id: str, hf_token: str = "") -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = model_id
        logger.info("Initializing BanglaBERT from %s on device=%s", model_id, self.device)

        token_arg = hf_token if hf_token else None

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            token=token_arg,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id,
            token=token_arg,
        )
        self.model.to(self.device)
        self.model.eval()

        self.id2label: dict[int, str] = {
            int(k): str(v) for k, v in self.model.config.id2label.items()
        }
        self.commit_hash: str | None = getattr(self.model.config, "_commit_hash", None)

        logger.info(
            "BanglaBERT initialized. id2label=%s, commit_hash=%s",
            self.id2label,
            self.commit_hash,
        )

        # Sanity check against expected SentiGOLD classes
        expected = {"NU", "SN", "WN", "SP", "WP"}
        loaded_classes = set(self.id2label.values())
        if not expected.issubset(loaded_classes):
            logger.warning(
                "Model id2label %s does not match expected SentiGOLD classes %s",
                loaded_classes,
                expected,
            )

    @classmethod
    def get_instance(cls) -> BanglaBERTClassifier:
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(
                model_id=settings.bangla_model_id,
                hf_token=settings.hf_token,
            )
        return cls._instance

    def predict(self, text: str) -> SentimentResult:
        import torch

        # Step 1: Preprocessing with csebuetnlp normalizer
        cleaned_text = csebuetnlp_normalize(text)

        # Step 2: Tokenization with truncation max_length=128
        inputs = self.tokenizer(
            cleaned_text,
            truncation=True,
            max_length=128,
            padding=False,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Step 3: Inference mode
        with torch.inference_mode():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        # Step 4: Map probabilities using model.config.id2label
        probabilities: dict[str, float] = {}
        for idx, prob in enumerate(probs):
            label_name = self.id2label.get(idx, f"CLASS_{idx}")
            probabilities[label_name] = float(prob)

        # Find top prediction
        top_idx = int(probs.argmax())
        top_label = self.id2label.get(top_idx, f"CLASS_{top_idx}")
        top_confidence = float(probs[top_idx])

        # Step 5: Derive coarse polarity
        polarity = BANGLA_POLARITY_MAP.get(top_label, "neutral")

        # Calculate aggregated negative probability: P(SN) + P(WN)
        negative_score = probabilities.get("SN", 0.0) + probabilities.get("WN", 0.0)

        return SentimentResult(
            label=top_label,
            score=top_confidence,
            polarity=polarity,
            confidence=top_confidence,
            probabilities=probabilities,
            model_id=self.model_id,
            model_revision=self.commit_hash,
            negative_polarity_score=negative_score,
        )


class DistilBERTClassifier:
    """Lazy singleton wrapper for the baseline English DistilBERT SST-2 model."""

    _instance: DistilBERTClassifier | None = None

    def __init__(self, model_name: str) -> None:
        from transformers import pipeline

        self.model_name = model_name
        logger.info("Initializing DistilBERT pipeline for model=%s", model_name)
        self.pipe = pipeline("sentiment-analysis", model=model_name, top_k=None)

    @classmethod
    def get_instance(cls) -> DistilBERTClassifier:
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(model_name=settings.model_name)
        return cls._instance

    def predict(self, text: str) -> SentimentResult:
        # returns list of dicts: [{'label': 'POSITIVE', 'score': 0.99}, {'label': 'NEGATIVE', 'score': 0.01}]
        results: list[dict[str, Any]] = self.pipe(text, truncation=True)
        if results and isinstance(results[0], list):
            results = results[0]

        probabilities: dict[str, float] = {}
        for r in results:
            probabilities[r["label"]] = float(r["score"])

        # Determine top label
        if results:
            # Sort descending by score
            sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
            top_label = sorted_results[0]["label"]
            top_confidence = float(sorted_results[0]["score"])
        else:
            top_label = "NEGATIVE"
            top_confidence = 0.5

        polarity = DISTILBERT_POLARITY_MAP.get(top_label.upper(), "neutral")
        negative_score = probabilities.get("NEGATIVE", 0.0)

        return SentimentResult(
            label=top_label,
            score=top_confidence,
            polarity=polarity,
            confidence=top_confidence,
            probabilities=probabilities,
            model_id=self.model_name,
            model_revision=None,
            negative_polarity_score=negative_score,
        )


def analyze_sentiment(text: str) -> SentimentResult:
    """Main routing entrypoint.

    Selects between BanglaBERT and DistilBERT based on:
    1. SENTIMENT_ENGINE config ('auto', 'bangla', 'distilbert').
    2. Language detection (predominant Bangla script).
    """
    settings = get_settings()
    engine_mode = (settings.sentiment_engine or "auto").lower()

    if engine_mode == "bangla":
        use_bangla = True
    elif engine_mode == "distilbert":
        use_bangla = False
    else:  # auto
        use_bangla = is_mostly_bangla(text)

    if use_bangla:
        return BanglaBERTClassifier.get_instance().predict(text)
    return DistilBERTClassifier.get_instance().predict(text)

