from app.ai.finbert_sentiment import ResilientFinBERTClassifier, SentimentClassifier
from app.domain.news_sentiment import ClassifiedNewsArticle, NewsSentimentResult, SentimentLabel
from app.infrastructure.news.news_collector import GoogleNewsRSSCollector, NewsCollector, StaticNewsCollector


class NewsSentimentService:
    def __init__(
        self,
        collector: NewsCollector | None = None,
        classifier: SentimentClassifier | None = None,
        fallback_collector: NewsCollector | None = None,
    ) -> None:
        self.collector = collector or GoogleNewsRSSCollector()
        self.classifier = classifier or ResilientFinBERTClassifier()
        self.fallback_collector = fallback_collector or StaticNewsCollector()

    def analyze(self, stock_name: str, limit: int = 20) -> NewsSentimentResult:
        normalized_stock = stock_name.strip()
        if not normalized_stock:
            raise ValueError("stock_name is required")

        try:
            articles = self.collector.collect(normalized_stock, limit=limit)
        except Exception:
            articles = self.fallback_collector.collect(normalized_stock, limit=limit)

        if not articles:
            articles = self.fallback_collector.collect(normalized_stock, limit=limit)

        classified_articles = [
            ClassifiedNewsArticle(
                article=article,
                label=label,
                confidence=confidence,
            )
            for article in articles
            for label, confidence in [self.classifier.classify(article.text_for_sentiment)]
        ]

        return self._summarize(normalized_stock, classified_articles)

    def _summarize(
        self,
        stock_name: str,
        classified_articles: list[ClassifiedNewsArticle],
    ) -> NewsSentimentResult:
        total = len(classified_articles)
        if total == 0:
            return NewsSentimentResult(
                stock_name=stock_name,
                positive=0,
                neutral=100,
                negative=0,
                sentiment_score=50,
                articles=[],
            )

        positive_count = sum(1 for item in classified_articles if item.label == SentimentLabel.POSITIVE)
        neutral_count = sum(1 for item in classified_articles if item.label == SentimentLabel.NEUTRAL)
        negative_count = sum(1 for item in classified_articles if item.label == SentimentLabel.NEGATIVE)

        positive = round(positive_count / total * 100)
        neutral = round(neutral_count / total * 100)
        negative = max(0, 100 - positive - neutral)
        sentiment_score = self._score(classified_articles)

        return NewsSentimentResult(
            stock_name=stock_name,
            positive=positive,
            neutral=neutral,
            negative=negative,
            sentiment_score=sentiment_score,
            articles=classified_articles,
        )

    @staticmethod
    def _score(classified_articles: list[ClassifiedNewsArticle]) -> int:
        if not classified_articles:
            return 50

        weighted_total = 0.0
        confidence_total = 0.0

        for item in classified_articles:
            label_score = {
                SentimentLabel.POSITIVE: 100,
                SentimentLabel.NEUTRAL: 50,
                SentimentLabel.NEGATIVE: 0,
            }[item.label]
            weight = max(item.confidence, 0.01)
            weighted_total += label_score * weight
            confidence_total += weight

        return round(weighted_total / confidence_total)
