from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import FinancialMetrics, ShareholdingPattern, ValuationMetrics
from app.infrastructure.models import (
    FinancialMetricModel,
    ShareholdingPatternModel,
    StockModel,
    ValuationMetricModel,
)


@dataclass(frozen=True)
class StockSnapshot:
    financials: FinancialMetrics | None
    financial_history: list[FinancialMetrics]
    valuation: ValuationMetrics | None
    shareholding: ShareholdingPattern | None
    shareholding_history: list[ShareholdingPattern]


class StockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_symbol(self, symbol: str) -> StockModel | None:
        statement = select(StockModel).where(StockModel.symbol == symbol.upper())
        return self.db.scalar(statement)

    def create_placeholder(self, symbol: str) -> StockModel:
        stock = StockModel(symbol=symbol.upper(), name=symbol.upper(), sector="Unknown")
        self.db.add(stock)
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

        financial_history = [self._to_financial_entity(row) for row in financial_rows]
        shareholding_history = [self._to_shareholding_entity(row) for row in shareholding_rows]

        return StockSnapshot(
            financials=financial_history[-1] if financial_history else None,
            financial_history=financial_history,
            valuation=self._to_valuation_entity(valuation_row) if valuation_row else None,
            shareholding=self._to_shareholding_entity(shareholding_row) if shareholding_row else None,
            shareholding_history=shareholding_history,
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
