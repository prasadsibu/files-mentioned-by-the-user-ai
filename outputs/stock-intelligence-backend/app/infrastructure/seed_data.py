from datetime import date

from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.infrastructure.models import (
    FinancialMetricModel,
    ShareholdingPatternModel,
    StockModel,
    ValuationMetricModel,
)


def seed_database() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(StockModel).where(StockModel.symbol == "VOLTAMP"))
        if existing is not None:
            return

        stock = StockModel(symbol="VOLTAMP", name="Voltamp Transformers Ltd", sector="Capital Goods")
        db.add(stock)
        db.flush()

        financials = [
            FinancialMetricModel(
                stock_id=stock.id,
                fiscal_year=2021,
                revenue=900,
                net_profit=115,
                eps=112,
                roe=18,
                roce=22,
                debt_equity=0.05,
                interest_coverage=30,
                operating_cash_flow=130,
                free_cash_flow=105,
            ),
            FinancialMetricModel(
                stock_id=stock.id,
                fiscal_year=2022,
                revenue=1120,
                net_profit=150,
                eps=146,
                roe=20,
                roce=24,
                debt_equity=0.04,
                interest_coverage=35,
                operating_cash_flow=165,
                free_cash_flow=130,
            ),
            FinancialMetricModel(
                stock_id=stock.id,
                fiscal_year=2023,
                revenue=1430,
                net_profit=205,
                eps=201,
                roe=23,
                roce=28,
                debt_equity=0.03,
                interest_coverage=45,
                operating_cash_flow=230,
                free_cash_flow=190,
            ),
            FinancialMetricModel(
                stock_id=stock.id,
                fiscal_year=2024,
                revenue=1780,
                net_profit=280,
                eps=275,
                roe=24,
                roce=31,
                debt_equity=0.02,
                interest_coverage=55,
                operating_cash_flow=315,
                free_cash_flow=260,
            ),
        ]

        db.add_all(financials)
        db.add(
            ValuationMetricModel(
                stock_id=stock.id,
                as_of_date=date.today(),
                pe=21,
                pb=3.7,
                peg=0.8,
                industry_pe=32,
                price=9800,
            )
        )
        db.add_all(
            [
                ShareholdingPatternModel(
                    stock_id=stock.id,
                    quarter="2024Q3",
                    promoter_holding=50.1,
                    fii_holding=7.5,
                    dii_holding=10.9,
                    retail_holding=31.5,
                    pledged_shares=0,
                ),
                ShareholdingPatternModel(
                    stock_id=stock.id,
                    quarter="2024Q4",
                    promoter_holding=50.1,
                    fii_holding=8.2,
                    dii_holding=11.7,
                    retail_holding=30.0,
                    pledged_shares=0,
                ),
            ]
        )

        db.commit()
    finally:
        db.close()
