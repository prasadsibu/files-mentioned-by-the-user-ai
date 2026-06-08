from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    stock: str = Field(..., min_length=1, max_length=32, examples=["TCS"])

    @field_validator("stock")
    @classmethod
    def normalize_stock(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("stock is required")
        return normalized


class FundamentalsResponse(BaseModel):
    roe: float
    roce: float
    debt_equity: float
    operating_cash_flow: float
    free_cash_flow: float
    eps: float


class ValuationResponse(BaseModel):
    pe: float
    pb: float
    peg: float
    industry_pe: float
    price: float


class TrendHistoryPoint(BaseModel):
    period: str
    revenue: float
    profit: float
    eps: float
    roe: float
    roce: float
    pe: float
    price: float


class ShareholdingHistoryPoint(BaseModel):
    quarter: str
    promoter: float
    fii: float
    dii: float
    retail: float
    pledged_shares: float


class RiskFlagResponse(BaseModel):
    label: str
    severity: str
    detected: bool
    detail: str


class NewsSentimentArticleResponse(BaseModel):
    title: str
    source: str
    sentiment: str
    score: float


class NewsSentimentSummaryResponse(BaseModel):
    positive: int
    neutral: int
    negative: int
    sentiment_score: int
    articles: list[NewsSentimentArticleResponse]


class ConcallSignalResponse(BaseModel):
    label: str
    detail: str
    tone: str


class ConcallSummaryResponse(BaseModel):
    final_view: str
    confidence: int
    reasoning: str
    signals: list[ConcallSignalResponse]


class ScoreBreakdownItem(BaseModel):
    category: str
    weight: int
    score: int
    weighted_score: float
    reasoning: str


class AnalyzeResponse(BaseModel):
    symbol: str
    recommendation: str
    score: int
    fundamentals: FundamentalsResponse
    valuation: ValuationResponse
    trend_history: list[TrendHistoryPoint]
    shareholding_history: list[ShareholdingHistoryPoint]
    risk_flags: list[RiskFlagResponse]
    news_sentiment: NewsSentimentSummaryResponse
    concall_summary: ConcallSummaryResponse
    score_breakdown: list[ScoreBreakdownItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "TCS",
                "recommendation": "BUY",
                "score": 87,
                "fundamentals": {
                    "roe": 42.5,
                    "roce": 55.2,
                    "debt_equity": 0.08,
                    "operating_cash_flow": 45200,
                    "free_cash_flow": 39800,
                    "eps": 120.4,
                },
                "valuation": {"pe": 28.1, "pb": 12.2, "peg": 1.4, "industry_pe": 31.0, "price": 4200},
                "trend_history": [],
                "shareholding_history": [],
                "risk_flags": [],
                "news_sentiment": {"positive": 0, "neutral": 100, "negative": 0, "sentiment_score": 50, "articles": []},
                "concall_summary": {"final_view": "Neutral", "confidence": 50, "reasoning": "No transcript analyzed.", "signals": []},
                "score_breakdown": [],
            }
        }
    )
