from abc import ABC, abstractmethod

from app.domain.news_sentiment import SentimentLabel


class SentimentClassifier(ABC):
    @abstractmethod
    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        raise NotImplementedError


class FinBERTSentimentClassifier(SentimentClassifier):
    def __init__(self, model_name: str = "ProsusAI/finbert", local_files_only: bool = False) -> None:
        self.model_name = model_name
        self.local_files_only = local_files_only
        self._pipeline = None

    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        pipeline = self._get_pipeline()
        output = pipeline(text[:512], truncation=True)[0]
        label = self._normalize_label(str(output["label"]))
        confidence = float(output["score"])
        return label, confidence

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=self.local_files_only,
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                local_files_only=self.local_files_only,
            )
            self._pipeline = pipeline("text-classification", model=model, tokenizer=tokenizer)
            return self._pipeline
        except Exception as exc:
            raise RuntimeError(
                "FinBERT is unavailable. Install transformers/torch and ensure the model is cached locally."
            ) from exc

    @staticmethod
    def _normalize_label(label: str) -> SentimentLabel:
        normalized = label.strip().lower()
        if "positive" in normalized:
            return SentimentLabel.POSITIVE
        if "negative" in normalized:
            return SentimentLabel.NEGATIVE
        return SentimentLabel.NEUTRAL


class RuleBasedFinancialSentimentClassifier(SentimentClassifier):
    positive_terms = {
        "beat",
        "beats",
        "strong",
        "growth",
        "expands",
        "expansion",
        "profit",
        "improvement",
        "improves",
        "upgrade",
        "bullish",
        "order inflow",
        "margin improvement",
        "healthy demand",
    }
    negative_terms = {
        "loss",
        "weak",
        "decline",
        "falls",
        "downgrade",
        "bearish",
        "pressure",
        "resignation",
        "fraud",
        "debt concern",
        "pledge",
        "margin pressure",
    }

    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        normalized = text.lower()
        positive_hits = sum(1 for term in self.positive_terms if term in normalized)
        negative_hits = sum(1 for term in self.negative_terms if term in normalized)

        if positive_hits > negative_hits:
            return SentimentLabel.POSITIVE, min(0.99, 0.65 + positive_hits * 0.08)
        if negative_hits > positive_hits:
            return SentimentLabel.NEGATIVE, min(0.99, 0.65 + negative_hits * 0.08)
        return SentimentLabel.NEUTRAL, 0.60


class ResilientFinBERTClassifier(SentimentClassifier):
    def __init__(self, finbert: FinBERTSentimentClassifier | None = None) -> None:
        self.finbert = finbert or FinBERTSentimentClassifier(local_files_only=False)
        self.fallback = RuleBasedFinancialSentimentClassifier()
        self._finbert_failed = False

    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        if not self._finbert_failed:
            try:
                return self.finbert.classify(text)
            except RuntimeError:
                self._finbert_failed = True
        return self.fallback.classify(text)
