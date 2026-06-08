from app.ai.finbert_sentiment import SentimentClassifier
from app.application.services.news_sentiment_service import NewsSentimentService
from app.domain.news_sentiment import NewsArticle, SentimentLabel
from app.infrastructure.news.news_collector import NewsCollector


class StubCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        return [
            NewsArticle(title="strong growth", url="local://1", source="test", published_at=None),
            NewsArticle(title="capacity expansion", url="local://2", source="test", published_at=None),
            NewsArticle(title="margin pressure", url="local://3", source="test", published_at=None),
            NewsArticle(title="steady quarter", url="local://4", source="test", published_at=None),
        ]


class StubClassifier(SentimentClassifier):
    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        if "strong" in text or "expansion" in text:
            return SentimentLabel.POSITIVE, 0.9
        if "pressure" in text:
            return SentimentLabel.NEGATIVE, 0.8
        return SentimentLabel.NEUTRAL, 0.7


def test_news_sentiment_service_returns_percentages_and_score() -> None:
    service = NewsSentimentService(collector=StubCollector(), classifier=StubClassifier())

    result = service.analyze("VOLTAMP")

    assert result.to_api_dict() == {
        "positive": 50,
        "neutral": 25,
        "negative": 25,
        "sentiment_score": 65,
    }
