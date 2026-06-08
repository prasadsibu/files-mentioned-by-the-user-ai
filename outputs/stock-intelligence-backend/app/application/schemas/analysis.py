from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    stock: str = Field(..., min_length=1, max_length=32, examples=["VOLTAMP"])

    @field_validator("stock")
    @classmethod
    def normalize_stock(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("stock is required")
        return normalized


class AnalyzeResponse(BaseModel):
    recommendation: str
    score: int

    model_config = ConfigDict(json_schema_extra={"example": {"recommendation": "BUY", "score": 87}})


class ScoreBreakdownItem(BaseModel):
    category: str
    weight: int
    score: int
    weighted_score: float
    reasoning: str
