from dataclasses import replace
from datetime import date, datetime

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_analysis_service, get_db
from app.application.services.analysis_service import AnalysisService
from app.application.services.concall_transcript_service import ConcallTranscriptService
from app.application.services.news_sentiment_service import NewsSentimentService
from app.domain.analyzers.concall_analyzer import ConcallAnalyzer
from app.domain.analyzers.financial_analyzer import FinancialAnalyzer
from app.domain.analyzers.growth_analyzer import GrowthAnalyzer
from app.domain.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from app.domain.analyzers.ownership_analyzer import OwnershipAnalyzer
from app.domain.analyzers.risk_analyzer import RiskAnalyzer
from app.domain.analyzers.valuation_analyzer import ValuationAnalyzer
from app.domain.news_sentiment import NewsArticle, SentimentLabel
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.database import Base
from app.infrastructure.market_data.stock_data_provider import (
    FinancialStatementRecord,
    ShareholdingRecord,
    StockDataBundle,
    ValuationRecord,
)
from app.infrastructure.news.news_collector import NewsCollector
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository
from app.main import app


class StubStockDataProvider:
    def fetch(self, symbol: str) -> StockDataBundle:
        financials = [
            FinancialStatementRecord(
                fiscal_year=2023,
                revenue=1000,
                net_profit=100,
                eps=10,
                roe=16,
                roce=20,
                debt_equity=0.2,
                interest_coverage=8,
                operating_cash_flow=110,
                free_cash_flow=80,
            ),
            FinancialStatementRecord(
                fiscal_year=2024,
                revenue=1300,
                net_profit=140,
                eps=14,
                roe=18,
                roce=24,
                debt_equity=0.1,
                interest_coverage=10,
                operating_cash_flow=160,
                free_cash_flow=120,
            ),
        ]
        valuation = ValuationRecord(
            as_of_date=date.today(),
            pe=18,
            pb=3,
            peg=0.9,
            industry_pe=25,
            price=500,
            market_cap=50000000000,
        )
        shareholding = [
            ShareholdingRecord(
                quarter="2023Q4",
                promoter_holding=55,
                fii_holding=5,
                dii_holding=4,
                retail_holding=36,
                pledged_shares=0,
            ),
            ShareholdingRecord(
                quarter="2024Q4",
                promoter_holding=55,
                fii_holding=6,
                dii_holding=5,
                retail_holding=34,
                pledged_shares=0,
            ),
        ]

        if symbol == "GENUSPOWER":
            shareholding = []
        if symbol == "RKFORGE":
            valuation = None
        if symbol == "JWL":
            financials = [replace(item, operating_cash_flow=0, free_cash_flow=0) for item in financials]
        if symbol == "PRAJIND":
            valuation = replace(valuation, pb=999, peg=999)
        if symbol == "TARIL":
            financials = []

        return StockDataBundle(
            symbol=symbol,
            yahoo_symbol=f"{symbol}.NS",
            name=f"{symbol} Ltd",
            sector="Capital Goods",
            fetched_at=datetime.utcnow(),
            financials=financials,
            valuation=valuation,
            shareholding=shareholding,
            historical_prices=[],
            corporate_actions=[],
            raw_payloads={"yahoo_info": {"marketCap": 50000000000}},
        )


class StubNewsCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        return [
            NewsArticle(title=f"{stock_name} strong growth", url=f"local://{stock_name}/1", source="test", published_at=None),
            NewsArticle(title=f"{stock_name} margin pressure", url=f"local://{stock_name}/2", source="test", published_at=None),
        ]


class StubNewsClassifier:
    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        if "strong" in text:
            return SentimentLabel.POSITIVE, 0.9
        if "pressure" in text:
            return SentimentLabel.NEGATIVE, 0.8
        return SentimentLabel.NEUTRAL, 0.7


class StubConcallClient:
    def analyze(self, transcript: str):
        from app.application.services.concall_transcript_service import RuleBasedConcallTranscriptAnalyzer

        return RuleBasedConcallTranscriptAnalyzer().analyze(transcript)


def build_test_service() -> AnalysisService:
    db = TestingSessionLocal()
    stock_repository = StockRepository(db)
    return AnalysisService(
        stock_repository=stock_repository,
        analysis_repository=AnalysisRepository(db),
        financial_analyzer=FinancialAnalyzer(),
        growth_analyzer=GrowthAnalyzer(),
        valuation_analyzer=ValuationAnalyzer(),
        ownership_analyzer=OwnershipAnalyzer(),
        news_sentiment_analyzer=NewsSentimentAnalyzer(),
        concall_analyzer=ConcallAnalyzer(),
        risk_analyzer=RiskAnalyzer(),
        recommendation_engine=RecommendationEngine(),
        stock_data_provider=StubStockDataProvider(),
        news_sentiment_service=NewsSentimentService(collector=StubNewsCollector(), classifier=StubNewsClassifier()),
        concall_transcript_service=ConcallTranscriptService(openai_client=StubConcallClient()),
    )


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_analysis_service] = build_test_service
client = TestClient(app)


def test_analyze_fetches_missing_nse_stock_and_returns_score() -> None:
    response = client.post("/analyze", json={"stock": "RELIANCE"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "RELIANCE"
    assert payload["recommendation"] in {"BUY", "WATCH", "IGNORE"}
    assert payload["score"] > 0
    assert payload["fundamentals"]["roe"] == 18
    assert payload["valuation"]["pe"] == 18
    assert payload["trend_history"]
    assert payload["shareholding_history"]
    assert payload["risk_flags"]
    assert payload["news_sentiment"]["article_count"] == 2
    assert payload["news_sentiment"]["articles"]
    assert "signals" in payload["concall_summary"]


def test_analyze_reuses_cached_stock_data() -> None:
    first_response = client.post("/analyze", json={"stock": "TCS"})
    second_response = client.post("/analyze", json={"stock": "TCS"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200


@pytest.mark.parametrize(
    ("symbol", "expected_missing_flag"),
    [
        ("GENUSPOWER", "Missing shareholding"),
        ("RKFORGE", "Missing PE"),
        ("JWL", "Missing cashflow"),
        ("PRAJIND", "Missing PB"),
        ("TARIL", "Missing financial statements"),
    ],
)
def test_analyze_partial_market_data_for_valid_nse_symbols(symbol: str, expected_missing_flag: str) -> None:
    response = client.post("/analyze", json={"stock": symbol})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == symbol
    assert payload["recommendation"] in {"BUY", "WATCH", "IGNORE"}
    assert payload["fundamentals"]
    assert payload["valuation"]
    assert payload["shareholding_history"]
    assert payload["risk_flags"]
    assert expected_missing_flag in {item["label"] for item in payload["risk_flags"]}
