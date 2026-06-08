from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsSentimentRequest(BaseModel):
    stock: str = Field(..., min_length=1, max_length=128, examples=["TCS"])

    @field_validator("stock")
    @classmethod
    def normalize_stock(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("stock is required")
        return normalized


class NewsSentimentArticleResponse(BaseModel):
    title: str
    source: str
    published_at: str | None = None
    url: str
    sentiment: str
    confidence: float
    score: float


class NewsSentimentResponse(BaseModel):
    positive: int
    neutral: int
    negative: int
    sentiment_score: int
    article_count: int
    articles: list[NewsSentimentArticleResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "positive": 70,
                "neutral": 20,
                "negative": 10,
                "sentiment_score": 82,
                "article_count": 1,
                "articles": [
                    {
                        "title": "TCS wins large deal",
                        "source": "Google News",
                        "published_at": "2026-06-08T10:00:00+00:00",
                        "url": "https://example.com/tcs-news",
                        "sentiment": "Positive",
                        "confidence": 0.91,
                        "score": 0.91,
                    }
                ],
            }
        }
    )
