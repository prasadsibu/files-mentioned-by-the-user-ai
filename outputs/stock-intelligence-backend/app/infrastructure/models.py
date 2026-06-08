from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class StockModel(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(128), default="Unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    financials: Mapped[list["FinancialMetricModel"]] = relationship(back_populates="stock")
    valuations: Mapped[list["ValuationMetricModel"]] = relationship(back_populates="stock")
    shareholding: Mapped[list["ShareholdingPatternModel"]] = relationship(back_populates="stock")


class FinancialMetricModel(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    revenue: Mapped[float] = mapped_column(Float)
    net_profit: Mapped[float] = mapped_column(Float)
    eps: Mapped[float] = mapped_column(Float)
    roe: Mapped[float] = mapped_column(Float)
    roce: Mapped[float] = mapped_column(Float)
    debt_equity: Mapped[float] = mapped_column(Float)
    interest_coverage: Mapped[float] = mapped_column(Float)
    operating_cash_flow: Mapped[float] = mapped_column(Float)
    free_cash_flow: Mapped[float] = mapped_column(Float)

    stock: Mapped[StockModel] = relationship(back_populates="financials")


class ValuationMetricModel(Base):
    __tablename__ = "valuation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    pe: Mapped[float] = mapped_column(Float)
    pb: Mapped[float] = mapped_column(Float)
    peg: Mapped[float] = mapped_column(Float)
    industry_pe: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)

    stock: Mapped[StockModel] = relationship(back_populates="valuations")


class ShareholdingPatternModel(Base):
    __tablename__ = "shareholding_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    quarter: Mapped[str] = mapped_column(String(16))
    promoter_holding: Mapped[float] = mapped_column(Float)
    fii_holding: Mapped[float] = mapped_column(Float)
    dii_holding: Mapped[float] = mapped_column(Float)
    retail_holding: Mapped[float] = mapped_column(Float)
    pledged_shares: Mapped[float] = mapped_column(Float)

    stock: Mapped[StockModel] = relationship(back_populates="shareholding")


class AnalysisRunModel(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    recommendation: Mapped[str] = mapped_column(String(16))
    score: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    breakdown: Mapped[list["ScoreBreakdownModel"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )


class ScoreBreakdownModel(Base):
    __tablename__ = "score_breakdowns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))
    weight: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    weighted_score: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    input_values_json: Mapped[str] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRunModel] = relationship(back_populates="breakdown")
