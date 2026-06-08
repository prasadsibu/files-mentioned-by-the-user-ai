from datetime import date
import logging

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
from app.domain.analyzers.concall_analyzer import ConcallAnalyzer
from app.domain.analyzers.financial_analyzer import FinancialAnalyzer
from app.domain.analyzers.growth_analyzer import GrowthAnalyzer
from app.domain.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from app.domain.analyzers.ownership_analyzer import OwnershipAnalyzer
from app.domain.analyzers.risk_analyzer import RiskAnalyzer
from app.domain.analyzers.valuation_analyzer import ValuationAnalyzer
from app.application.services.concall_transcript_service import ConcallTranscriptService
from app.application.services.news_sentiment_service import NewsSentimentService
from app.domain.concall_transcript import ConcallStance, ConcallTranscriptAnalysis
from app.domain.entities import CategoryScore, ConcallSignals, FinancialMetrics, NewsSentiment, ShareholdingPattern, ValuationMetrics
from app.domain.news_sentiment import NewsSentimentResult
from app.domain.recommendation_engine import RecommendationEngine
from app.infrastructure.market_data.stock_data_provider import StockDataProvider
from app.infrastructure.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.repositories.stock_repository import StockRepository, StockSnapshot


logger = logging.getLogger(__name__)


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
        news_sentiment_service: NewsSentimentService | None = None,
        concall_transcript_service: ConcallTranscriptService | None = None,
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
        self.news_sentiment_service = news_sentiment_service or NewsSentimentService()
        self.concall_transcript_service = concall_transcript_service or ConcallTranscriptService()

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        stock = self.stock_repository.get_by_symbol(request.stock)
        if stock is None:
            stock = self.stock_repository.create_placeholder(request.stock)

        snapshots = self.stock_repository.get_stock_snapshot(stock.id)
        logger.info("analysis_requested symbol=%s", stock.symbol)
        if (
            snapshots.financials is None
            or snapshots.valuation is None
            or snapshots.shareholding is None
            or not self.stock_repository.is_cache_fresh(stock.id)
        ):
            try:
                fetched_data = self.stock_data_provider.fetch(stock.symbol)
                stock = self.stock_repository.save_fetched_data(stock, fetched_data)
                snapshots = self.stock_repository.get_stock_snapshot(stock.id)
            except Exception as exc:
                logger.warning(
                    "stock_ingestion_failed_partial_analysis_continues symbol=%s error=%s",
                    stock.symbol,
                    exc,
                )

        financials = snapshots.financials or self._default_financials()
        financial_history = snapshots.financial_history or [financials]
        valuation = snapshots.valuation or self._default_valuation()
        shareholding = snapshots.shareholding or self._default_shareholding()
        shareholding_history = snapshots.shareholding_history or [shareholding]

        news_result = self._analyze_news_sentiment(stock.symbol)
        concall_result = self._analyze_concall(request)

        category_scores = [
            self.financial_analyzer.analyze(financials),
            self.growth_analyzer.analyze(financial_history),
            self.valuation_analyzer.analyze(valuation, financial_history),
            self.ownership_analyzer.analyze(shareholding_history),
            self.risk_analyzer.analyze(
                financials=financials,
                previous_financials=financial_history[-2]
                if len(financial_history) > 1
                else None,
                shareholding=shareholding,
            ),
            self.news_sentiment_analyzer.analyze(sentiment=self._news_domain(news_result)),
            self.concall_analyzer.analyze(signals=self._concall_signals(concall_result)),
        ]

        result = self.recommendation_engine.recommend(category_scores)
        self.analysis_repository.save_result(stock_id=stock.id, result=result)
        news_category = self._category_score(result.breakdown, "news_sentiment")
        concall_category = self._category_score(result.breakdown, "concall_intelligence")

        return AnalyzeResponse(
            symbol=stock.symbol,
            recommendation=result.recommendation,
            score=result.score,
            fundamentals=self._fundamentals(financials),
            valuation=self._valuation(valuation),
            trend_history=self._trend_history(snapshots, financial_history, valuation),
            shareholding_history=self._shareholding_history(shareholding_history),
            risk_flags=self._risk_flags(
                financials=financials,
                previous_financials=financial_history[-2]
                if len(financial_history) > 1
                else None,
                shareholding=shareholding,
                valuation=valuation,
                financial_history=financial_history,
                shareholding_history=shareholding_history,
            ),
            news_sentiment=self._news_sentiment(news_result),
            news_score=news_category.score,
            news_reasoning=news_category.reasoning,
            concall_summary=self._concall_summary(concall_result),
            concall_score=concall_category.score,
            concall_reasoning=concall_category.reasoning,
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
    def _category_score(scores: list[CategoryScore], category: str) -> CategoryScore:
        for item in scores:
            if item.category == category:
                return item
        raise ValueError(f"Missing score category: {category}")

    @staticmethod
    def _default_financials() -> FinancialMetrics:
        return FinancialMetrics(
            fiscal_year=date.today().year,
            revenue=0,
            net_profit=0,
            eps=0,
            roe=0,
            roce=0,
            debt_equity=0,
            interest_coverage=0,
            operating_cash_flow=0,
            free_cash_flow=0,
        )

    @staticmethod
    def _default_valuation() -> ValuationMetrics:
        return ValuationMetrics(as_of_date=date.today(), pe=999, pb=999, peg=999, industry_pe=999, price=0)

    @staticmethod
    def _default_shareholding() -> ShareholdingPattern:
        return ShareholdingPattern(
            quarter="not_available",
            promoter_holding=0,
            fii_holding=0,
            dii_holding=0,
            retail_holding=100,
            pledged_shares=0,
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
    def _trend_history(
        snapshot: StockSnapshot,
        financial_history: list[FinancialMetrics],
        valuation: ValuationMetrics,
    ) -> list[TrendHistoryPoint]:
        price_by_year = {item.fiscal_year: item.price for item in snapshot.price_history}
        points: list[TrendHistoryPoint] = []
        for item in sorted(financial_history, key=lambda value: value.fiscal_year):
            price = price_by_year.get(item.fiscal_year, valuation.price)
            pe = round(price / item.eps, 2) if item.eps else valuation.pe
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
        valuation: ValuationMetrics,
        financial_history: list[FinancialMetrics],
        shareholding_history: list[ShareholdingPattern],
    ) -> list[RiskFlagResponse]:
        rising_debt = bool(previous_financials and financials.debt_equity > previous_financials.debt_equity)
        negative_cash_flow = financials.free_cash_flow < 0
        pledged_shares = shareholding.pledged_shares > 0
        flags = [
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
        flags.extend(AnalysisService._missing_data_flags(financials, valuation, shareholding, financial_history, shareholding_history))
        return flags

    @staticmethod
    def _missing_data_flags(
        financials: FinancialMetrics,
        valuation: ValuationMetrics,
        shareholding: ShareholdingPattern,
        financial_history: list[FinancialMetrics],
        shareholding_history: list[ShareholdingPattern],
    ) -> list[RiskFlagResponse]:
        missing: list[RiskFlagResponse] = []
        if not financial_history or all(item.revenue == 0 and item.net_profit == 0 and item.eps == 0 for item in financial_history):
            missing.append(RiskFlagResponse(label="Missing financial statements", severity="Medium", detected=True, detail="Yahoo/NSE did not return complete financial statements; available fallback metrics were used."))
        if valuation.pe >= 999:
            missing.append(RiskFlagResponse(label="Missing PE", severity="Low", detected=True, detail="PE was not returned; valuation scoring used a conservative neutral value."))
        if valuation.pb >= 999:
            missing.append(RiskFlagResponse(label="Missing PB", severity="Low", detected=True, detail="PB was not returned; valuation scoring used a conservative neutral value."))
        if financials.operating_cash_flow == 0 and financials.free_cash_flow == 0:
            missing.append(RiskFlagResponse(label="Missing cashflow", severity="Low", detected=True, detail="Cash-flow values were not returned; zero values were used for cash-flow display and risk checks."))
        if not shareholding_history or (shareholding.promoter_holding == 0 and shareholding.fii_holding == 0 and shareholding.dii_holding == 0):
            missing.append(RiskFlagResponse(label="Missing shareholding", severity="Low", detected=True, detail="Shareholding data was not returned; ownership scoring used neutral fallback holdings."))
        return missing

    def _analyze_news_sentiment(self, symbol: str) -> NewsSentimentResult:
        try:
            return self.news_sentiment_service.analyze(symbol, limit=12)
        except Exception as exc:
            logger.warning("news_sentiment_failed symbol=%s error=%s", symbol, exc)
            return NewsSentimentResult(
                stock_name=symbol,
                positive=0,
                neutral=0,
                negative=0,
                sentiment_score=50,
                articles=[],
            )

    def _analyze_concall(self, request: AnalyzeRequest) -> ConcallTranscriptAnalysis | None:
        if not request.concall_transcript and not request.concall_transcript_url:
            return None
        try:
            return self.concall_transcript_service.analyze_input(
                transcript=request.concall_transcript,
                transcript_url=request.concall_transcript_url,
            )
        except Exception as exc:
            logger.warning("concall_analysis_failed symbol=%s error=%s", request.stock, exc)
            return None

    @staticmethod
    def _news_domain(result: NewsSentimentResult) -> NewsSentiment:
        article_count = len(result.articles)
        average_confidence = (
            sum(item.confidence for item in result.articles) / article_count
            if article_count
            else 0
        )
        return NewsSentiment(
            positive_count=sum(1 for item in result.articles if item.label.value == "Positive"),
            neutral_count=sum(1 for item in result.articles if item.label.value == "Neutral"),
            negative_count=sum(1 for item in result.articles if item.label.value == "Negative"),
            average_sentiment_score=(result.sentiment_score / 50) - 1,
            positive_percent=result.positive,
            neutral_percent=result.neutral,
            negative_percent=result.negative,
            average_confidence=average_confidence,
        )

    @staticmethod
    def _concall_signals(result: ConcallTranscriptAnalysis | None) -> ConcallSignals | None:
        if result is None:
            return None
        sections = [
            result.debt_discussion,
            result.management_guidance,
            result.margin_outlook,
            result.order_book,
            result.expansion_plans,
            result.risks,
            result.management_guidance,
        ]
        return ConcallSignals(
            bullish_signals=sum(1 for section in sections if section.sentiment == ConcallStance.BULLISH),
            neutral_signals=sum(1 for section in sections if section.sentiment == ConcallStance.NEUTRAL),
            bearish_signals=sum(1 for section in sections if section.sentiment == ConcallStance.BEARISH),
            has_expansion_plan=bool(result.expansion_plans.evidence),
            has_order_book_growth=result.order_book.sentiment == ConcallStance.BULLISH,
            has_margin_guidance=bool(result.margin_outlook.evidence),
            has_debt_concern=result.debt_discussion.sentiment == ConcallStance.BEARISH,
            management_tone=result.debt_discussion.sentiment.value,
            revenue_outlook=result.management_guidance.sentiment.value,
            margin_outlook=result.margin_outlook.sentiment.value,
            order_book_commentary=result.order_book.sentiment.value,
            capex_plans=result.expansion_plans.sentiment.value,
            risks_mentioned=result.risks.sentiment.value,
            guidance_changes=result.management_guidance.sentiment.value,
            confidence=result.confidence,
        )

    @staticmethod
    def _news_sentiment(result: NewsSentimentResult) -> NewsSentimentSummaryResponse:
        return NewsSentimentSummaryResponse(
            positive=result.positive,
            neutral=result.neutral,
            negative=result.negative,
            sentiment_score=result.sentiment_score,
            article_count=len(result.articles),
            articles=[
                NewsSentimentArticleResponse(
                    title=item.article.title,
                    source=item.article.source,
                    published_at=item.article.published_at.isoformat() if item.article.published_at else None,
                    url=item.article.url,
                    sentiment=item.label.value,
                    confidence=item.confidence,
                    score=item.confidence,
                )
                for item in result.articles
            ],
        )

    @staticmethod
    def _concall_summary(result: ConcallTranscriptAnalysis | None) -> ConcallSummaryResponse:
        if result is None:
            return ConcallSummaryResponse(
                final_view="Not Submitted",
                confidence=0,
                reasoning="Upload transcript text or provide a transcript URL to generate concall intelligence.",
                signals=[],
            )
        sections = [
            ("Management tone", result.debt_discussion),
            ("Revenue outlook", result.management_guidance),
            ("Margin outlook", result.margin_outlook),
            ("Order book commentary", result.order_book),
            ("Capex plans", result.expansion_plans),
            ("Risks mentioned", result.risks),
            ("Guidance changes", result.management_guidance),
        ]
        return ConcallSummaryResponse(
            final_view=result.final_view.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            signals=[
                ConcallSignalResponse(
                    label=label,
                    detail=section.summary,
                    tone=section.sentiment.value.lower(),
                )
                for label, section in sections
            ],
        )
