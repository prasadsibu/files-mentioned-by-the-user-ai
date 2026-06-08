from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

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
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.database import SessionLocal
from app.infrastructure.market_data.stock_data_provider import StockDataProvider
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    stock_repository = StockRepository(db)
    analysis_repository = AnalysisRepository(db)

    return AnalysisService(
        stock_repository=stock_repository,
        analysis_repository=analysis_repository,
        financial_analyzer=FinancialAnalyzer(),
        growth_analyzer=GrowthAnalyzer(),
        valuation_analyzer=ValuationAnalyzer(),
        ownership_analyzer=OwnershipAnalyzer(),
        news_sentiment_analyzer=NewsSentimentAnalyzer(),
        concall_analyzer=ConcallAnalyzer(),
        risk_analyzer=RiskAnalyzer(),
        recommendation_engine=RecommendationEngine(),
        stock_data_provider=StockDataProvider(),
        news_sentiment_service=NewsSentimentService(),
        concall_transcript_service=ConcallTranscriptService(),
    )


def get_news_sentiment_service() -> NewsSentimentService:
    return NewsSentimentService()


def get_concall_transcript_service() -> ConcallTranscriptService:
    return ConcallTranscriptService()
