from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialMetrics:
    fiscal_year: int
    revenue: float
    net_profit: float
    eps: float
    roe: float
    roce: float
    debt_equity: float
    interest_coverage: float
    operating_cash_flow: float
    free_cash_flow: float


@dataclass(frozen=True)
class ValuationMetrics:
    as_of_date: date
    pe: float
    pb: float
    peg: float
    industry_pe: float
    price: float


@dataclass(frozen=True)
class ShareholdingPattern:
    quarter: str
    promoter_holding: float
    fii_holding: float
    dii_holding: float
    retail_holding: float
    pledged_shares: float


@dataclass(frozen=True)
class NewsSentiment:
    positive_count: int
    neutral_count: int
    negative_count: int
    average_sentiment_score: float
    positive_percent: float = 0
    neutral_percent: float = 0
    negative_percent: float = 0
    average_confidence: float = 0


@dataclass(frozen=True)
class ConcallSignals:
    bullish_signals: int
    neutral_signals: int
    bearish_signals: int
    has_expansion_plan: bool
    has_order_book_growth: bool
    has_margin_guidance: bool
    has_debt_concern: bool
    management_tone: str = "Neutral"
    revenue_outlook: str = "Neutral"
    margin_outlook: str = "Neutral"
    order_book_commentary: str = "Neutral"
    capex_plans: str = "Neutral"
    risks_mentioned: str = "Neutral"
    guidance_changes: str = "Neutral"
    confidence: int = 0


@dataclass(frozen=True)
class CategoryScore:
    category: str
    weight: int
    score: int
    reasoning: str
    input_values: dict[str, float | int | str]

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight / 100


@dataclass(frozen=True)
class RecommendationResult:
    recommendation: str
    score: int
    confidence: str
    breakdown: list[CategoryScore]
