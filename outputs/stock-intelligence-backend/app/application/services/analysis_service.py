from app.application.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConcallSignalResponse,
    ConcallSummaryResponse,
    FundamentalsResponse,
    NewsSentimentArticleResponse,
    NewsSentimentSummaryResponse,
    RiskFlagResponse,
    ScoreBreakdownItem,
    ShareholdingHistoryPoint,
    TrendHistoryPoint,
    ValuationResponse,
)
from app.core.exceptions import AnalysisError
from app.domain.analyzers.concall_analyzer import ConcallAnalyzer
from app.domain.analyzers.financial_analyzer import FinancialAnalyzer
from app.domain.analyzers.growth_analyzer import GrowthAnalyzer
from app.domain.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from app.domain.analyzers.ownership_analyzer import OwnershipAnalyzer
from app.domain.analyzers.risk_analyzer import RiskAnalyzer
from app.domain.analyzers.valuation_analyzer import ValuationAnalyzer
from app.domain.entities import FinancialMetrics, ShareholdingPattern, ValuationMetrics
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.market_data.stock_data_provider import StockDataProvider
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository, StockSnapshot


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

        return AnalyzeResponse(
            symbol=stock.symbol,
            recommendation=result.recommendation,
            score=result.score,
            fundamentals=self._fundamentals(snapshots.financials),
            valuation=self._valuation(snapshots.valuation),
            trend_history=self._trend_history(snapshots),
            shareholding_history=self._shareholding_history(snapshots.shareholding_history),
            risk_flags=self._risk_flags(
                financials=snapshots.financials,
                previous_financials=snapshots.financial_history[-2]
                if len(snapshots.financial_history) > 1
                else None,
                shareholding=snapshots.shareholding,
            ),
            news_sentiment=self._news_sentiment(stock.symbol),
            concall_summary=self._concall_summary(stock.symbol),
            score_breakdown=[
                ScoreBreakdownItem(
                    category=item.category,
                    weight=item.weight,
                    score=item.score,
                    weighted_score=item.weighted_score,
                    reasoning=item.reasoning,
                )
                for item in result.breakdown
            ],
        )

    @staticmethod
    def _fundamentals(financials: FinancialMetrics) -> FundamentalsResponse:
        return FundamentalsResponse(
            roe=financials.roe,
            roce=financials.roce,
            debt_equity=financials.debt_equity,
            operating_cash_flow=financials.operating_cash_flow,
            free_cash_flow=financials.free_cash_flow,
            eps=financials.eps,
        )

    @staticmethod
    def _valuation(valuation: ValuationMetrics) -> ValuationResponse:
        return ValuationResponse(
            pe=valuation.pe,
            pb=valuation.pb,
            peg=valuation.peg,
            industry_pe=valuation.industry_pe,
            price=valuation.price,
        )

    @staticmethod
    def _trend_history(snapshot: StockSnapshot) -> list[TrendHistoryPoint]:
        price_by_year = {item.fiscal_year: item.price for item in snapshot.price_history}
        points: list[TrendHistoryPoint] = []
        for item in sorted(snapshot.financial_history, key=lambda value: value.fiscal_year):
            price = price_by_year.get(item.fiscal_year, snapshot.valuation.price if snapshot.valuation else 0)
            pe = round(price / item.eps, 2) if item.eps else (snapshot.valuation.pe if snapshot.valuation else 0)
            points.append(
                TrendHistoryPoint(
                    period=f"FY{str(item.fiscal_year)[-2:]}",
                    revenue=item.revenue,
                    profit=item.net_profit,
                    eps=item.eps,
                    roe=item.roe,
                    roce=item.roce,
                    pe=pe,
                    price=price,
                )
            )
        return points

    @staticmethod
    def _shareholding_history(history: list[ShareholdingPattern]) -> list[ShareholdingHistoryPoint]:
        return [
            ShareholdingHistoryPoint(
                quarter=item.quarter,
                promoter=item.promoter_holding,
                fii=item.fii_holding,
                dii=item.dii_holding,
                retail=item.retail_holding,
                pledged_shares=item.pledged_shares,
            )
            for item in history
        ]

    @staticmethod
    def _risk_flags(
        financials: FinancialMetrics,
        previous_financials: FinancialMetrics | None,
        shareholding: ShareholdingPattern,
    ) -> list[RiskFlagResponse]:
        rising_debt = bool(previous_financials and financials.debt_equity > previous_financials.debt_equity)
        negative_cash_flow = financials.free_cash_flow < 0
        pledged_shares = shareholding.pledged_shares > 0
        return [
            RiskFlagResponse(
                label="Auditor resignation",
                severity="High",
                detected=False,
                detail="No auditor resignation signal is available in the fetched market data.",
            ),
            RiskFlagResponse(
                label="Rising debt",
                severity="Medium",
                detected=rising_debt,
                detail=(
                    f"Debt/equity moved from {previous_financials.debt_equity:.2f}x to {financials.debt_equity:.2f}x."
                    if previous_financials
                    else f"Latest debt/equity is {financials.debt_equity:.2f}x."
                ),
            ),
            RiskFlagResponse(
                label="Negative cash flow",
                severity="High",
                detected=negative_cash_flow,
                detail=f"Latest free cash flow is ₹{financials.free_cash_flow:,.0f} Cr.",
            ),
            RiskFlagResponse(
                label="Equity dilution",
                severity="Medium",
                detected=False,
                detail="No equity dilution signal is available in the fetched market data.",
            ),
            RiskFlagResponse(
                label="Pledged shares",
                severity="High",
                detected=pledged_shares,
                detail=f"Latest pledged promoter shares are {shareholding.pledged_shares:.2f}%.",
            ),
        ]

    @staticmethod
    def _news_sentiment(symbol: str) -> NewsSentimentSummaryResponse:
        return NewsSentimentSummaryResponse(
            positive=0,
            neutral=100,
            negative=0,
            sentiment_score=50,
            articles=[
                NewsSentimentArticleResponse(
                    title=f"No live news sentiment articles were analyzed for {symbol} in this run.",
                    source="Analysis API",
                    sentiment="Neutral",
                    score=0.5,
                )
            ],
        )

    @staticmethod
    def _concall_summary(symbol: str) -> ConcallSummaryResponse:
        return ConcallSummaryResponse(
            final_view="Neutral",
            confidence=50,
            reasoning=f"No concall transcript was submitted for {symbol}; transcript signals are neutral for this analysis.",
            signals=[
                ConcallSignalResponse(label="Expansion plans", detail="No transcript evidence available.", tone="neutral"),
                ConcallSignalResponse(label="Order book", detail="No transcript evidence available.", tone="neutral"),
                ConcallSignalResponse(label="Margins", detail="No transcript evidence available.", tone="neutral"),
                ConcallSignalResponse(label="Debt commentary", detail="No transcript evidence available.", tone="neutral"),
            ],
        )
