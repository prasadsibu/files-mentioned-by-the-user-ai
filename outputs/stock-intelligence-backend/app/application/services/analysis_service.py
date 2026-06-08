from app.application.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.core.exceptions import AnalysisError
from app.domain.analyzers.concall_analyzer import ConcallAnalyzer
from app.domain.analyzers.financial_analyzer import FinancialAnalyzer
from app.domain.analyzers.growth_analyzer import GrowthAnalyzer
from app.domain.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from app.domain.analyzers.ownership_analyzer import OwnershipAnalyzer
from app.domain.analyzers.risk_analyzer import RiskAnalyzer
from app.domain.analyzers.valuation_analyzer import ValuationAnalyzer
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.market_data.stock_data_provider import StockDataProvider
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository


class AnalysisService:
    def __init__(
        self,
        stock_repository: StockRepository,
        analysis_repository: AnalysisRepository,
        financial_analyzer: FinancialAnalyzer,
        growth_analyzer: GrowthAnalyzer,
        valuation_analyzer: ValuationAnalyzer,
        ownership_analyzer: OwnershipAnalyzer,
        news_sentiment_analyzer: NewsSentimentAnalyzer,
        concall_analyzer: ConcallAnalyzer,
        risk_analyzer: RiskAnalyzer,
        recommendation_engine: RecommendationEngine,
        stock_data_provider: StockDataProvider | None = None,
    ) -> None:
        self.stock_repository = stock_repository
        self.analysis_repository = analysis_repository
        self.financial_analyzer = financial_analyzer
        self.growth_analyzer = growth_analyzer
        self.valuation_analyzer = valuation_analyzer
        self.ownership_analyzer = ownership_analyzer
        self.news_sentiment_analyzer = news_sentiment_analyzer
        self.concall_analyzer = concall_analyzer
        self.risk_analyzer = risk_analyzer
        self.recommendation_engine = recommendation_engine
        self.stock_data_provider = stock_data_provider or StockDataProvider()

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        stock = self.stock_repository.get_by_symbol(request.stock)
        if stock is None:
            stock = self.stock_repository.create_placeholder(request.stock)

        snapshots = self.stock_repository.get_stock_snapshot(stock.id)
        if (
            snapshots.financials is None
            or snapshots.valuation is None
            or snapshots.shareholding is None
            or not self.stock_repository.is_cache_fresh(stock.id)
        ):
            fetched_data = self.stock_data_provider.fetch(stock.symbol)
            if not fetched_data.is_analyzable:
                raise AnalysisError(f"Unable to fetch enough market data to analyze {stock.symbol}")
            stock = self.stock_repository.save_fetched_data(stock, fetched_data)
            snapshots = self.stock_repository.get_stock_snapshot(stock.id)

        if snapshots.financials is None or snapshots.valuation is None or snapshots.shareholding is None:
            raise AnalysisError(f"Unable to fetch enough market data to analyze {stock.symbol}")

        category_scores = [
            self.financial_analyzer.analyze(snapshots.financials),
            self.growth_analyzer.analyze(snapshots.financial_history),
            self.valuation_analyzer.analyze(snapshots.valuation, snapshots.financial_history),
            self.ownership_analyzer.analyze(snapshots.shareholding_history),
            self.news_sentiment_analyzer.analyze(sentiment=None),
            self.concall_analyzer.analyze(signals=None),
            self.risk_analyzer.analyze(
                financials=snapshots.financials,
                previous_financials=snapshots.financial_history[-2]
                if len(snapshots.financial_history) > 1
                else None,
                shareholding=snapshots.shareholding,
            ),
        ]

        result = self.recommendation_engine.recommend(category_scores)
        self.analysis_repository.save_result(stock_id=stock.id, result=result)

        return AnalyzeResponse(recommendation=result.recommendation, score=result.score)
