from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_analysis_service, get_db
from app.application.services.analysis_service import AnalysisService
from app.domain.analyzers.concall_analyzer import ConcallAnalyzer
from app.domain.analyzers.financial_analyzer import FinancialAnalyzer
from app.domain.analyzers.growth_analyzer import GrowthAnalyzer
from app.domain.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from app.domain.analyzers.ownership_analyzer import OwnershipAnalyzer
from app.domain.analyzers.risk_analyzer import RiskAnalyzer
from app.domain.analyzers.valuation_analyzer import ValuationAnalyzer
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.database import Base
from app.infrastructure.market_data.stock_data_provider import (
    FinancialStatementRecord,
    ShareholdingRecord,
    StockDataBundle,
    ValuationRecord,
)
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository
from app.main import app


class StubStockDataProvider:
    def fetch(self, symbol: str) -> StockDataBundle:
        return StockDataBundle(
            symbol=symbol,
            yahoo_symbol=f"{symbol}.NS",
            name=f"{symbol} Ltd",
            sector="Capital Goods",
            fetched_at=datetime.utcnow(),
            financials=[
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
            ],
            valuation=ValuationRecord(
                as_of_date=date.today(),
                pe=18,
                pb=3,
                peg=0.9,
                industry_pe=25,
                price=500,
                market_cap=50000000000,
            ),
            shareholding=[
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
            ],
            historical_prices=[],
            corporate_actions=[],
            raw_payloads={"yahoo_info": {"marketCap": 50000000000}},
        )


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
    assert payload["news_sentiment"]["articles"]
    assert payload["concall_summary"]["signals"]


def test_analyze_reuses_cached_stock_data() -> None:
    first_response = client.post("/analyze", json={"stock": "TCS"})
    second_response = client.post("/analyze", json={"stock": "TCS"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
