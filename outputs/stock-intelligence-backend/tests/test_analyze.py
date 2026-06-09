from dataclasses import replace
from datetime import date, datetime
import zlib

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
from app.infrastructure.transcripts.transcript_discovery import DiscoveredTranscript, TranscriptDiscoveryService
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
            valuation = replace(valuation, pe=None)
        if symbol == "JWL":
            financials = [replace(item, operating_cash_flow=0, free_cash_flow=0) for item in financials]
        if symbol == "PRAJIND":
            valuation = replace(valuation, pb=None, peg=None)
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
        if stock_name.startswith("POSNEWS"):
            headlines = [
                "strong revenue growth and market share gains",
                "bullish order inflow with margin improvement",
                "capacity expansion supports positive guidance",
                "debt free balance sheet and strong demand",
            ]
        elif stock_name.startswith("NEGNEWS"):
            headlines = [
                "weak demand creates margin pressure",
                "guidance cut after order slowdown",
                "high debt and cost pressure risks",
                "profit decline amid uncertainty",
            ]
        else:
            headlines = ["strong growth", "margin pressure"]
        return [
            NewsArticle(
                title=f"{stock_name} {headline}",
                url=f"local://{stock_name}/{index}",
                source="test",
                published_at=None,
            )
            for index, headline in enumerate(headlines, start=1)
        ]


class StubNewsClassifier:
    def classify(self, text: str) -> tuple[SentimentLabel, float]:
        normalized = text.lower()
        if any(term in normalized for term in ["strong", "bullish", "positive", "expansion", "debt free", "market share"]):
            return SentimentLabel.POSITIVE, 0.9
        if any(term in normalized for term in ["pressure", "weak", "cut", "high debt", "decline", "slowdown", "uncertainty"]):
            return SentimentLabel.NEGATIVE, 0.8
        return SentimentLabel.NEUTRAL, 0.7


class StubConcallClient:
    def analyze(self, transcript: str):
        from app.application.services.concall_transcript_service import RuleBasedConcallTranscriptAnalyzer

        return RuleBasedConcallTranscriptAnalyzer().analyze(transcript)


class StubTranscriptDiscoveryService:
    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def discover(self, symbol: str, company_name: str | None = None) -> DiscoveredTranscript | None:
        self.calls[symbol] = self.calls.get(symbol, 0) + 1
        bullish_transcript = (
            "Latest conference call transcript. Management tone is bullish and debt free with strong demand. "
            "Revenue growth guidance is positive and management expects market share gains. "
            "Margin improvement and operating leverage should continue. "
            "Order book and orders grew with a strong pipeline. "
            "Capacity expansion and capex plans support growth. "
        )
        if symbol in {"AUTOCONCALL", "CACHECONCALL"}:
            return DiscoveredTranscript(
                source_url=f"https://ir.example.com/{symbol.lower()}-transcript.pdf",
                transcript_text=bullish_transcript,
                transcript_date=date(2026, 1, 30),
                discovery_method="company_ir",
            )
        if symbol == "PDFCONCALL":
            pdf_payload = make_simple_pdf(
                "PDF conference call transcript. Management tone is bullish. Revenue growth guidance is positive. "
                "Margin improvement continues and order book is strong. Capacity expansion supports growth."
            )
            return DiscoveredTranscript(
                source_url="https://ir.example.com/pdfconcall.pdf",
                transcript_text=TranscriptDiscoveryService.extract_pdf_text(pdf_payload),
                transcript_date=date(2026, 2, 15),
                discovery_method="quarterly_presentation_pdf",
            )
        return None


transcript_discovery = StubTranscriptDiscoveryService()


def make_simple_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    compressed = zlib.compress(stream)
    return b"%PDF-1.4\n1 0 obj << /Length " + str(len(compressed)).encode() + b" /Filter /FlateDecode >> stream\n" + compressed + b"\nendstream endobj\n%%EOF"


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
        concall_transcript_service=ConcallTranscriptService(
            openai_client=StubConcallClient(),
            transcript_discovery_service=transcript_discovery,
        ),
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
    assert payload["news_score"] > 0
    assert payload["news_reasoning"]
    assert payload["concall_score"] == 50
    assert payload["concall_reasoning"]
    assert payload["transcript_found"] is False
    assert payload["transcript_source"] is None
    assert {item["category"] for item in payload["score_breakdown"]} >= {"news_sentiment", "concall_intelligence"}


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


def test_positive_news_increases_final_score() -> None:
    positive_response = client.post("/analyze", json={"stock": "POSNEWS"})
    negative_response = client.post("/analyze", json={"stock": "NEGNEWS"})

    assert positive_response.status_code == 200
    assert negative_response.status_code == 200
    positive_payload = positive_response.json()
    negative_payload = negative_response.json()
    assert positive_payload["news_score"] >= 80
    assert negative_payload["news_score"] <= 30
    assert positive_payload["news_score"] > negative_payload["news_score"]
    assert positive_payload["score"] > negative_payload["score"]
    assert "News recommendation" in positive_payload["news_reasoning"]


def test_negative_news_lowers_final_score() -> None:
    mixed_response = client.post("/analyze", json={"stock": "MIXNEWS"})
    negative_response = client.post("/analyze", json={"stock": "NEGNEWS2"})

    assert mixed_response.status_code == 200
    assert negative_response.status_code == 200
    mixed_payload = mixed_response.json()
    negative_payload = negative_response.json()
    assert negative_payload["news_score"] < mixed_payload["news_score"]
    assert negative_payload["score"] < mixed_payload["score"]


def test_bullish_concall_increases_final_score() -> None:
    bullish_transcript = (
        "Management tone is bullish and debt free with strong demand. "
        "Revenue growth guidance is positive and management expects market share gains. "
        "Margin improvement and operating leverage should continue. "
        "Order book and orders grew with a strong pipeline. "
        "Capacity expansion and capex plans support growth. "
    )
    bearish_transcript = (
        "Management tone reflects high debt and working capital risk. "
        "Revenue outlook faces weak demand and guidance cut. "
        "Margin pressure and cost pressure are severe. "
        "Order book declined after order slowdown and delays. "
        "Capex has uncertainty and risk warnings increased. "
    )
    bullish_response = client.post("/analyze", json={"stock": "BULLCONCALL", "concall_transcript": bullish_transcript})
    bearish_response = client.post("/analyze", json={"stock": "BEARCONCALL", "concall_transcript": bearish_transcript})

    assert bullish_response.status_code == 200
    assert bearish_response.status_code == 200
    bullish_payload = bullish_response.json()
    bearish_payload = bearish_response.json()
    assert bullish_payload["concall_score"] >= 80
    assert bearish_payload["concall_score"] <= 30
    assert bullish_payload["concall_score"] > bearish_payload["concall_score"]
    assert bullish_payload["score"] > bearish_payload["score"]
    assert "Concall recommendation" in bullish_payload["concall_reasoning"]


def test_bearish_concall_lowers_final_score() -> None:
    neutral_response = client.post("/analyze", json={"stock": "NEUTRALCONCALL"})
    bearish_response = client.post(
        "/analyze",
        json={
            "stock": "BEARCONCALL2",
            "concall_transcript": (
                "Management discussed high debt and risk. "
                "Revenue outlook has weak demand and guidance cut. "
                "Margin pressure and cost pressure persist. "
                "Order book decline and delays create uncertainty. "
            ),
        },
    )

    assert neutral_response.status_code == 200
    assert bearish_response.status_code == 200
    neutral_payload = neutral_response.json()
    bearish_payload = bearish_response.json()
    assert bearish_payload["concall_score"] < neutral_payload["concall_score"]
    assert bearish_payload["score"] < neutral_payload["score"]


def test_automatic_transcript_discovered_successfully() -> None:
    response = client.post("/analyze", json={"stock": "AUTOCONCALL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_found"] is True
    assert payload["transcript_source"] == "https://ir.example.com/autoconcall-transcript.pdf"
    assert payload["transcript_date"] == "2026-01-30"
    assert payload["concall_summary"]["signals"]
    assert payload["concall_score"] >= 80


def test_automatic_transcript_cache_reuse() -> None:
    transcript_discovery.calls.pop("CACHECONCALL", None)

    first_response = client.post("/analyze", json={"stock": "CACHECONCALL"})
    second_response = client.post("/analyze", json={"stock": "CACHECONCALL"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["transcript_found"] is True
    assert second_response.json()["transcript_found"] is True
    assert transcript_discovery.calls["CACHECONCALL"] == 1


def test_automatic_transcript_unavailable_fallback() -> None:
    response = client.post("/analyze", json={"stock": "NOCONCALL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_found"] is False
    assert payload["transcript_source"] is None
    assert payload["transcript_date"] is None
    assert payload["concall_summary"]["reasoning"] == "Latest earnings call transcript unavailable."
    assert payload["concall_score"] == 50


def test_manual_transcript_override_skips_auto_discovery() -> None:
    transcript_discovery.calls.pop("MANUALCONCALL", None)
    response = client.post(
        "/analyze",
        json={
            "stock": "MANUALCONCALL",
            "concall_transcript": (
                "Manual conference call transcript. Management discussed high debt and risk. "
                "Revenue outlook has weak demand and guidance cut. Margin pressure persists. "
                "Order book decline and delays create uncertainty."
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_found"] is True
    assert payload["transcript_source"] == "manual_upload"
    assert transcript_discovery.calls.get("MANUALCONCALL", 0) == 0
    assert payload["concall_score"] < 50


def test_pdf_transcript_extraction() -> None:
    pdf_payload = make_simple_pdf(
        "PDF conference call transcript with management tone bullish, revenue growth guidance, "
        "margin improvement, order book strength, capex plans, and risk commentary."
    )

    extracted = TranscriptDiscoveryService.extract_pdf_text(pdf_payload)

    assert "conference call transcript" in extracted
    assert "order book" in extracted


def test_pdf_transcript_discovered_and_analyzed() -> None:
    response = client.post("/analyze", json={"stock": "PDFCONCALL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_found"] is True
    assert payload["transcript_source"] == "https://ir.example.com/pdfconcall.pdf"
    assert payload["transcript_date"] == "2026-02-15"
    assert payload["concall_score"] >= 80
