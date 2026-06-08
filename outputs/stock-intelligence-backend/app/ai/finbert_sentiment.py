import logging
import os
from abc import ABC, abstractmethod

# Set offline mode environment variables BEFORE importing transformers
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from app.domain.news_sentiment import SentimentLabel

logger = logging.getLogger(__name__)


class SentimentClassifier(ABC):
    @abstractmethod
    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        raise NotImplementedError


class FinBERTSentimentClassifier(SentimentClassifier):
    _instance = None
    _is_initialized = False

    def __new__(cls, model_name: str = "ProsusAI/finbert", local_files_only: bool = True):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "ProsusAI/finbert", local_files_only: bool = True) -> None:
        # Only initialize once
        if self._is_initialized:
            return

        self.model_name = model_name
        self.local_files_only = local_files_only
        self._pipeline = None
        FinBERTSentimentClassifier._is_initialized = True

    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        """Classify text sentiment. Requires pipeline to be pre-loaded at startup."""
        if self._pipeline is None:
            raise RuntimeError(
                "FinBERT pipeline not initialized. Call initialize_finbert() at application startup."
            )
        output = self._pipeline(text[:512], truncation=True)[0]
        label = self._normalize_label(str(output["label"]))
        confidence = float(output["score"])
        return label, confidence

    def initialize(self) -> bool:
        """
        Initialize the FinBERT pipeline at application startup.
        
        Returns:
            True if initialized successfully, False if initialization failed.
        """
        if self._pipeline is not None:
            logger.info("FinBERT already initialized")
            return True

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

            logger.info("Loading FinBERT model from local cache (offline mode enabled)")
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=self.local_files_only,
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                local_files_only=self.local_files_only,
            )
            self._pipeline = pipeline("text-classification", model=model, tokenizer=tokenizer)
            logger.info("FinBERT loaded successfully")
            return True
        except Exception as exc:
            logger.error(f"Failed to load FinBERT: {exc}")
            logger.warning("FinBERT will not be available for sentiment analysis")
            return False

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
    """
    Sentiment classifier that uses FinBERT if available, falls back to rule-based if not.
    
    FinBERT must be initialized at application startup via initialize_finbert_classifier().
    If initialization fails, automatically uses rule-based fallback.
    """

    def __init__(self, finbert: FinBERTSentimentClassifier | None = None) -> None:
        self.finbert = finbert or FinBERTSentimentClassifier(local_files_only=True)
        self.fallback = RuleBasedFinancialSentimentClassifier()
        self._using_fallback = False

    def initialize(self) -> None:
        """Initialize FinBERT at startup. Falls back to rule-based if FinBERT unavailable."""
        if self.finbert.initialize():
            logger.info("FinBERT offline mode enabled")
        else:
            logger.warning("Falling back to rule-based sentiment classifier")
            self._using_fallback = True

    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        """Classify sentiment using FinBERT or fallback rule-based classifier."""
        if self._using_fallback:
            return self.fallback.classify(text)

        try:
            return self.finbert.classify(text)
        except RuntimeError as e:
            logger.warning(f"FinBERT failed, using fallback: {e}")
            self._using_fallback = True
            return self.fallback.classify(text)


# Global singleton instance
_sentiment_classifier = None


def get_sentiment_classifier() -> ResilientFinBERTClassifier:
    """Get the global singleton sentiment classifier instance."""
    global _sentiment_classifier
    if _sentiment_classifier is None:
        _sentiment_classifier = ResilientFinBERTClassifier()
    return _sentiment_classifier


def initialize_finbert_classifier() -> None:
    """
    Initialize FinBERT classifier at application startup.
    
    This must be called before processing any requests.
    Sets up offline mode and loads the model from local cache only.
    """
    classifier = get_sentiment_classifier()
    classifier.initialize()
