from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities import FinancialMetrics, ShareholdingPattern, ValuationMetrics
from app.infrastructure.market_data.stock_data_provider import StockDataBundle
from app.infrastructure.models import (
    CorporateActionModel,
    FinancialMetricModel,
    HistoricalPriceModel,
    ShareholdingPatternModel,
    StockDataCacheModel,
    StockModel,
    ValuationMetricModel,
)


@dataclass(frozen=True)
class HistoricalPricePoint:
    fiscal_year: int
    price: float


@dataclass(frozen=True)
class StockSnapshot:
    financials: FinancialMetrics | None
    financial_history: list[FinancialMetrics]
    valuation: ValuationMetrics | None
    shareholding: ShareholdingPattern | None
    shareholding_history: list[ShareholdingPattern]
    price_history: list[HistoricalPricePoint]


class StockRepository:
    cache_ttl = timedelta(hours=24)

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_symbol(self, symbol: str) -> StockModel | None:
        statement = select(StockModel).where(StockModel.symbol == symbol.upper().strip())
        return self.db.scalar(statement)

    def create_placeholder(self, symbol: str) -> StockModel:
        stock = StockModel(symbol=symbol.upper().strip(), name=symbol.upper().strip(), sector="Unknown")
        self.db.add(stock)
        self.db.commit()
        self.db.refresh(stock)
        return stock

    def is_cache_fresh(self, stock_id: int) -> bool:
        cache_row = self.db.scalar(
            select(StockDataCacheModel)
            .where(StockDataCacheModel.stock_id == stock_id, StockDataCacheModel.source == "yahoo_info")
            .order_by(StockDataCacheModel.fetched_at.desc())
            .limit(1)
        )
        return bool(cache_row and cache_row.fetched_at >= datetime.utcnow() - self.cache_ttl)

    def save_fetched_data(self, stock: StockModel, bundle: StockDataBundle) -> StockModel:
        stock.name = bundle.name
        stock.sector = bundle.sector
        self.db.add(stock)
        self.db.flush()

        self.db.execute(delete(FinancialMetricModel).where(FinancialMetricModel.stock_id == stock.id))
        self.db.execute(delete(ValuationMetricModel).where(ValuationMetricModel.stock_id == stock.id))
        self.db.execute(delete(ShareholdingPatternModel).where(ShareholdingPatternModel.stock_id == stock.id))
        self.db.execute(delete(HistoricalPriceModel).where(HistoricalPriceModel.stock_id == stock.id))
        self.db.execute(delete(CorporateActionModel).where(CorporateActionModel.stock_id == stock.id))

        financial_items = bundle.financials or []
        if not financial_items:
            self.db.add(
                FinancialMetricModel(
                    stock_id=stock.id,
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
            )
        for item in financial_items:
            self.db.add(
                FinancialMetricModel(
                    stock_id=stock.id,
                    fiscal_year=item.fiscal_year,
                    revenue=item.revenue,
                    net_profit=item.net_profit,
                    eps=item.eps,
                    roe=item.roe,
                    roce=item.roce,
                    debt_equity=item.debt_equity,
                    interest_coverage=item.interest_coverage,
                    operating_cash_flow=item.operating_cash_flow,
                    free_cash_flow=item.free_cash_flow,
                )
            )

        if bundle.valuation is not None:
            self.db.add(
                ValuationMetricModel(
                    stock_id=stock.id,
                    as_of_date=bundle.valuation.as_of_date,
                    pe=bundle.valuation.pe,
                    pb=bundle.valuation.pb,
                    peg=bundle.valuation.peg,
                    industry_pe=bundle.valuation.industry_pe,
                    price=bundle.valuation.price,
                )
            )
        else:
            self.db.add(
                ValuationMetricModel(
                    stock_id=stock.id,
                    as_of_date=date.today(),
                    pe=999,
                    pb=999,
                    peg=999,
                    industry_pe=999,
                    price=0,
                )
            )

        shareholding_items = bundle.shareholding or []
        if not shareholding_items:
            self.db.add(
                ShareholdingPatternModel(
                    stock_id=stock.id,
                    quarter="not_available",
                    promoter_holding=0,
                    fii_holding=0,
                    dii_holding=0,
                    retail_holding=100,
                    pledged_shares=0,
                )
            )
        for item in shareholding_items:
            self.db.add(
                ShareholdingPatternModel(
                    stock_id=stock.id,
                    quarter=item.quarter[:16],
                    promoter_holding=item.promoter_holding,
                    fii_holding=item.fii_holding,
                    dii_holding=item.dii_holding,
                    retail_holding=item.retail_holding,
                    pledged_shares=item.pledged_shares,
                )
            )

        for item in bundle.historical_prices:
            self.db.add(
                HistoricalPriceModel(
                    stock_id=stock.id,
                    trade_date=item.trade_date,
                    open=item.open,
                    high=item.high,
                    low=item.low,
                    close=item.close,
                    volume=item.volume,
                )
            )

        for item in bundle.corporate_actions:
            self.db.add(
                CorporateActionModel(
                    stock_id=stock.id,
                    action_date=item.action_date,
                    action_type=item.action_type[:64],
                    description=item.description,
                )
            )

        for source, payload in bundle.raw_payloads.items():
            existing = self.db.scalar(
                select(StockDataCacheModel).where(
                    StockDataCacheModel.stock_id == stock.id,
                    StockDataCacheModel.source == source,
                )
            )
            if existing is None:
                existing = StockDataCacheModel(stock_id=stock.id, source=source, payload_json="{}")
            existing.payload_json = json.dumps(payload, default=str)
            existing.fetched_at = bundle.fetched_at
            self.db.add(existing)

        if bundle.valuation and bundle.valuation.market_cap is not None:
            existing = self.db.scalar(
                select(StockDataCacheModel).where(
                    StockDataCacheModel.stock_id == stock.id,
                    StockDataCacheModel.source == "yahoo_market_cap",
                )
            )
            if existing is None:
                existing = StockDataCacheModel(stock_id=stock.id, source="yahoo_market_cap", payload_json="{}")
            existing.payload_json = json.dumps({"market_cap": bundle.valuation.market_cap})
            existing.fetched_at = bundle.fetched_at
            self.db.add(existing)

        self.db.commit()
        self.db.refresh(stock)
        return stock

    def get_stock_snapshot(self, stock_id: int) -> StockSnapshot:
        financial_rows = list(
            self.db.scalars(
                select(FinancialMetricModel)
                .where(FinancialMetricModel.stock_id == stock_id)
                .order_by(FinancialMetricModel.fiscal_year.asc())
            )
        )
        valuation_row = self.db.scalar(
            select(ValuationMetricModel)
            .where(ValuationMetricModel.stock_id == stock_id)
            .order_by(ValuationMetricModel.as_of_date.desc())
            .limit(1)
        )
        shareholding_row = self.db.scalar(
            select(ShareholdingPatternModel)
            .where(ShareholdingPatternModel.stock_id == stock_id)
            .order_by(ShareholdingPatternModel.id.desc())
            .limit(1)
        )
        shareholding_rows = list(
            self.db.scalars(
                select(ShareholdingPatternModel)
                .where(ShareholdingPatternModel.stock_id == stock_id)
                .order_by(ShareholdingPatternModel.id.asc())
            )
        )
        price_rows = list(
            self.db.scalars(
                select(HistoricalPriceModel)
                .where(HistoricalPriceModel.stock_id == stock_id)
                .order_by(HistoricalPriceModel.trade_date.asc())
            )
        )

        financial_history = [self._to_financial_entity(row) for row in financial_rows]
        shareholding_history = [self._to_shareholding_entity(row) for row in shareholding_rows]

        return StockSnapshot(
            financials=financial_history[-1] if financial_history else None,
            financial_history=financial_history,
            valuation=self._to_valuation_entity(valuation_row) if valuation_row else None,
            shareholding=self._to_shareholding_entity(shareholding_row) if shareholding_row else None,
            shareholding_history=shareholding_history,
            price_history=self._to_year_end_prices(price_rows),
        )

    @staticmethod
    def _to_financial_entity(row: FinancialMetricModel) -> FinancialMetrics:
        return FinancialMetrics(
            fiscal_year=row.fiscal_year,
            revenue=row.revenue,
            net_profit=row.net_profit,
            eps=row.eps,
            roe=row.roe,
            roce=row.roce,
            debt_equity=row.debt_equity,
            interest_coverage=row.interest_coverage,
            operating_cash_flow=row.operating_cash_flow,
            free_cash_flow=row.free_cash_flow,
        )

    @staticmethod
    def _to_valuation_entity(row: ValuationMetricModel) -> ValuationMetrics:
        return ValuationMetrics(
            as_of_date=row.as_of_date,
            pe=row.pe,
            pb=row.pb,
            peg=row.peg,
            industry_pe=row.industry_pe,
            price=row.price,
        )

    @staticmethod
    def _to_shareholding_entity(row: ShareholdingPatternModel) -> ShareholdingPattern:
        return ShareholdingPattern(
            quarter=row.quarter,
            promoter_holding=row.promoter_holding,
            fii_holding=row.fii_holding,
            dii_holding=row.dii_holding,
            retail_holding=row.retail_holding,
            pledged_shares=row.pledged_shares,
        )

    @staticmethod
    def _to_year_end_prices(rows: list[HistoricalPriceModel]) -> list[HistoricalPricePoint]:
        latest_by_year: dict[int, HistoricalPriceModel] = {}
        for row in rows:
            latest_by_year[row.trade_date.year] = row
        return [
            HistoricalPricePoint(fiscal_year=year, price=row.close)
            for year, row in sorted(latest_by_year.items())
        ]
