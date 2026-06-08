"""
Tests for FinBERT sentiment classifier implementation.

Verifies:
- Singleton pattern ensures model loads only once
- No network calls occur during sentiment analysis
- Fallback mechanism works when FinBERT is unavailable
- Offline mode is properly enforced
"""

import os
import unittest
from unittest.mock import MagicMock, Mock, patch

from app.ai.finbert_sentiment import (
    FinBERTSentimentClassifier,
    ResilientFinBERTClassifier,
    RuleBasedFinancialSentimentClassifier,
    get_sentiment_classifier,
    initialize_finbert_classifier,
)
from app.domain.news_sentiment import SentimentLabel


class TestFinBERTSingletonPattern(unittest.TestCase):
    """Test that FinBERT implements singleton pattern correctly."""

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_singleton_returns_same_instance(self) -> None:
        """Test that FinBERT returns the same instance on multiple calls."""
        instance1 = FinBERTSentimentClassifier()
        instance2 = FinBERTSentimentClassifier()

        self.assertIs(instance1, instance2)

    def test_singleton_with_different_params_returns_same_instance(self) -> None:
        """Test that singleton returns same instance even with different parameters."""
        instance1 = FinBERTSentimentClassifier(model_name="model1", local_files_only=True)
        instance2 = FinBERTSentimentClassifier(model_name="model2", local_files_only=False)

        self.assertIs(instance1, instance2)
        # Verify first initialization parameters are retained
        self.assertEqual(instance1.model_name, "model1")
        self.assertTrue(instance1.local_files_only)

    def test_singleton_initializes_only_once(self) -> None:
        """Test that __init__ runs only once for singleton."""
        with patch.object(FinBERTSentimentClassifier, "initialize") as mock_init:
            instance1 = FinBERTSentimentClassifier()
            instance2 = FinBERTSentimentClassifier()
            instance3 = FinBERTSentimentClassifier()

            # __init__ should only set state once due to _is_initialized flag
            self.assertEqual(instance1._is_initialized, True)


class TestFinBERTOfflineMode(unittest.TestCase):
    """Test that FinBERT operates in offline mode only."""

    def test_environment_variables_set_before_transformers_import(self) -> None:
        """Verify HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE are set."""
        self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")
        self.assertEqual(os.environ.get("TRANSFORMERS_OFFLINE"), "1")

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_initialize_uses_local_files_only(self) -> None:
        """Test that initialize() enforces local_files_only=True."""
        classifier = FinBERTSentimentClassifier(local_files_only=True)

        with patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer, patch(
            "transformers.AutoModelForSequenceClassification.from_pretrained"
        ) as mock_model, patch(
            "transformers.pipeline"
        ) as mock_pipeline:

            mock_tokenizer.return_value = Mock()
            mock_model.return_value = Mock()
            mock_pipeline.return_value = Mock()

            classifier.initialize()

            # Verify local_files_only=True was passed
            mock_tokenizer.assert_called_once()
            call_kwargs = mock_tokenizer.call_args[1]
            self.assertTrue(call_kwargs.get("local_files_only"))

            mock_model.assert_called_once()
            call_kwargs = mock_model.call_args[1]
            self.assertTrue(call_kwargs.get("local_files_only"))


class TestFinBERTInitialization(unittest.TestCase):
    """Test FinBERT initialization behavior."""

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_classify_fails_without_initialization(self) -> None:
        """Test that classify() raises RuntimeError if pipeline not initialized."""
        classifier = FinBERTSentimentClassifier()

        with self.assertRaises(RuntimeError) as context:
            classifier.classify("test text")

        self.assertIn("initialize_finbert", str(context.exception).lower())

    @patch("transformers.AutoTokenizer.from_pretrained")
    @patch("transformers.AutoModelForSequenceClassification.from_pretrained")
    @patch("transformers.pipeline")
    def test_initialize_returns_true_on_success(
        self, mock_pipeline, mock_model, mock_tokenizer
    ) -> None:
        """Test that initialize() returns True on successful initialization."""
        classifier = FinBERTSentimentClassifier()
        mock_tokenizer.return_value = Mock()
        mock_model.return_value = Mock()
        mock_pipeline.return_value = Mock()

        result = classifier.initialize()

        self.assertTrue(result)

    def test_initialize_returns_false_on_failure(self) -> None:
        """Test that initialize() returns False when model loading fails."""
        classifier = FinBERTSentimentClassifier()

        with patch("transformers.AutoTokenizer.from_pretrained", side_effect=FileNotFoundError):
            result = classifier.initialize()

        self.assertFalse(result)

    def test_initialize_idempotent(self) -> None:
        """Test that calling initialize() multiple times after success returns True."""
        classifier = FinBERTSentimentClassifier()

        # First, manually set the pipeline to simulate successful initialization
        classifier._pipeline = Mock()

        # Now call initialize multiple times - should return True and not change pipeline
        initial_pipeline = classifier._pipeline
        
        result2 = classifier.initialize()
        result3 = classifier.initialize()
        
        # Both calls should return True (since pipeline is already set)
        self.assertTrue(result2)
        self.assertTrue(result3)
        
        # Pipeline should not change
        self.assertIs(classifier._pipeline, initial_pipeline)


class TestResilientFinBERTClassifier(unittest.TestCase):
    """Test ResilientFinBERTClassifier fallback behavior."""

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_uses_finbert_when_available(self) -> None:
        """Test that classifier uses FinBERT when initialized successfully."""
        mock_finbert = Mock(spec=FinBERTSentimentClassifier)
        mock_finbert.initialize.return_value = True
        mock_finbert.classify.return_value = (SentimentLabel.POSITIVE, 0.95)

        classifier = ResilientFinBERTClassifier(finbert=mock_finbert)
        classifier.initialize()

        result = classifier.classify("strong growth")

        self.assertEqual(result, (SentimentLabel.POSITIVE, 0.95))
        mock_finbert.classify.assert_called_once_with("strong growth")

    def test_falls_back_to_rule_based_when_finbert_unavailable(self) -> None:
        """Test that classifier falls back to rule-based when FinBERT init fails."""
        mock_finbert = Mock(spec=FinBERTSentimentClassifier)
        mock_finbert.initialize.return_value = False

        classifier = ResilientFinBERTClassifier(finbert=mock_finbert)
        classifier.initialize()

        # Should use fallback for rule-based classification
        result = classifier.classify("strong growth")

        # Rule-based classifier should recognize "strong" and "growth"
        self.assertEqual(result[0], SentimentLabel.POSITIVE)

    def test_falls_back_when_finbert_raises_runtime_error(self) -> None:
        """Test that classifier falls back when FinBERT classify() raises RuntimeError."""
        mock_finbert = Mock(spec=FinBERTSentimentClassifier)
        mock_finbert.classify.side_effect = RuntimeError("Pipeline not initialized")

        classifier = ResilientFinBERTClassifier(finbert=mock_finbert)

        result = classifier.classify("strong growth")

        # Should fall back to rule-based classification
        self.assertEqual(result[0], SentimentLabel.POSITIVE)


class TestRuleBasedFallback(unittest.TestCase):
    """Test rule-based sentiment classifier works as fallback."""

    def test_classifies_positive_sentiment(self) -> None:
        """Test rule-based classifier recognizes positive terms."""
        classifier = RuleBasedFinancialSentimentClassifier()

        result = classifier.classify("company beat expectations with strong growth")

        self.assertEqual(result[0], SentimentLabel.POSITIVE)
        self.assertGreater(result[1], 0.65)

    def test_classifies_negative_sentiment(self) -> None:
        """Test rule-based classifier recognizes negative terms."""
        classifier = RuleBasedFinancialSentimentClassifier()

        result = classifier.classify("company faces margin pressure and downgrade")

        self.assertEqual(result[0], SentimentLabel.NEGATIVE)
        self.assertGreater(result[1], 0.65)

    def test_classifies_neutral_sentiment(self) -> None:
        """Test rule-based classifier returns neutral when no clear signals."""
        classifier = RuleBasedFinancialSentimentClassifier()

        result = classifier.classify("company reported on schedule")

        self.assertEqual(result[0], SentimentLabel.NEUTRAL)

    def test_no_network_calls(self) -> None:
        """Test that rule-based classifier never makes network calls."""
        classifier = RuleBasedFinancialSentimentClassifier()

        with patch("urllib.request.urlopen") as mock_urlopen:
            classifier.classify("test text with growth")
            mock_urlopen.assert_not_called()


class TestSentimentClassifierSingleton(unittest.TestCase):
    """Test the global singleton sentiment classifier."""

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        import app.ai.finbert_sentiment as fsm
        fsm._sentiment_classifier = None
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_get_sentiment_classifier_returns_singleton(self) -> None:
        """Test that get_sentiment_classifier() returns the same instance."""
        classifier1 = get_sentiment_classifier()
        classifier2 = get_sentiment_classifier()

        self.assertIs(classifier1, classifier2)

    def test_initialize_finbert_classifier_calls_initialize(self) -> None:
        """Test that initialize_finbert_classifier() initializes the classifier."""
        classifier = get_sentiment_classifier()

        with patch.object(classifier, "initialize") as mock_init:
            mock_init.return_value = None
            initialize_finbert_classifier()
            mock_init.assert_called_once()


class TestNoNetworkRequests(unittest.TestCase):
    """Test that analysis never makes network requests."""

    def tearDown(self) -> None:
        """Reset singleton state after each test."""
        FinBERTSentimentClassifier._instance = None
        FinBERTSentimentClassifier._is_initialized = False

    def test_rule_based_classifier_no_network(self) -> None:
        """Test rule-based classifier never attempts network calls."""
        classifier = RuleBasedFinancialSentimentClassifier()

        with patch("socket.socket") as mock_socket:
            classifier.classify("company beat expectations with strong growth")
            mock_socket.assert_not_called()

    def test_resilient_classifier_with_fallback_no_network(self) -> None:
        """Test resilient classifier with fallback doesn't make network calls."""
        mock_finbert = Mock(spec=FinBERTSentimentClassifier)
        mock_finbert.initialize.return_value = False
        classifier = ResilientFinBERTClassifier(finbert=mock_finbert)
        classifier.initialize()

        with patch("socket.socket") as mock_socket:
            classifier.classify("company beat expectations")
            mock_socket.assert_not_called()


if __name__ == "__main__":
    unittest.main()
