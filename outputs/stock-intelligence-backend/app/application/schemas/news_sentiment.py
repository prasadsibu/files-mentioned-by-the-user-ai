from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsSentimentRequest(BaseModel):
    stock: str = Field(..., min_length=1, max_length=128, examples=["VOLTAMP"])

    @field_validator("stock")
    @classmethod
    def normalize_stock(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("stock is required")
        return normalized


class NewsSentimentResponse(BaseModel):
    positive: int
    neutral: int
    negative: int
    sentiment_score: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "positive": 70,
                "neutral": 20,
                "negative": 10,
                "sentiment_score": 82,
            }
        }
    )
