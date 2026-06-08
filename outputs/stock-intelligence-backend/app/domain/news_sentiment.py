from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SentimentLabel(StrEnum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


@dataclass(frozen=True)
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: datetime | None
    summary: str = ""

    @property
    def text_for_sentiment(self) -> str:
        return f"{self.title}. {self.summary}".strip()


@dataclass(frozen=True)
class ClassifiedNewsArticle:
    article: NewsArticle
    label: SentimentLabel
    confidence: float


@dataclass(frozen=True)
class NewsSentimentResult:
    stock_name: str
    positive: int
    neutral: int
    negative: int
    sentiment_score: int
    articles: list[ClassifiedNewsArticle]

    def to_api_dict(self) -> dict:
        return {
            "positive": self.positive,
            "neutral": self.neutral,
            "negative": self.negative,
            "sentiment_score": self.sentiment_score,
            "article_count": len(self.articles),
            "articles": [
                {
                    "title": item.article.title,
                    "source": item.article.source,
                    "published_at": item.article.published_at.isoformat() if item.article.published_at else None,
                    "url": item.article.url,
                    "sentiment": item.label.value,
                    "confidence": item.confidence,
                    "score": item.confidence,
                }
                for item in self.articles
            ],
        }
