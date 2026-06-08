from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


CRORE = 10_000_000


@dataclass(frozen=True)
class FinancialStatementRecord:
    fiscal_year: int
    revenue: float
    net_profit: float
    eps: float
    roe: float
    roce: float
    debt_equity: float
    interest_coverage: float
    operating_cash_flow: float
    free_cash_flow: float


@dataclass(frozen=True)
class ValuationRecord:
    as_of_date: date
    pe: float
    pb: float
    peg: float
    industry_pe: float
    price: float
    market_cap: float | None = None


@dataclass(frozen=True)
class ShareholdingRecord:
    quarter: str
    promoter_holding: float
    fii_holding: float
    dii_holding: float
    retail_holding: float
    pledged_shares: float


@dataclass(frozen=True)
class HistoricalPriceRecord:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class CorporateActionRecord:
    action_date: date
    action_type: str
    description: str


@dataclass(frozen=True)
class StockDataBundle:
    symbol: str
    yahoo_symbol: str
    name: str
    sector: str
    fetched_at: datetime
    financials: list[FinancialStatementRecord]
    valuation: ValuationRecord | None
    shareholding: list[ShareholdingRecord]
    historical_prices: list[HistoricalPriceRecord]
    corporate_actions: list[CorporateActionRecord]
    raw_payloads: dict[str, Any] = field(default_factory=dict)

    @property
    def is_analyzable(self) -> bool:
        return bool(self.financials and self.valuation and self.shareholding)


class StockDataProvider:
    """Fetches NSE-listed stock data from Yahoo Finance and NSE India.

    Yahoo Finance is the primary source for fundamentals, valuation, historical
    prices, and financial statements. NSE India is queried for shareholding and
    corporate-action payloads when its public endpoints are available.
    """

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        import requests

        self._nse_session = requests.Session()
        self._nse_session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nseindia.com/",
            }
        )

    def fetch(self, symbol: str) -> StockDataBundle:
        normalized_symbol = symbol.upper().strip()
        yahoo_symbol = self._to_yahoo_symbol(normalized_symbol)
        import yfinance as yf

        ticker = yf.Ticker(yahoo_symbol)

        info = self._safe_info(ticker)
        financials = self._build_financials(ticker, info)
        valuation = self._build_valuation(ticker, info)
        historical_prices = self._build_historical_prices(ticker)
        nse_shareholding_payload = self._fetch_nse_shareholding(normalized_symbol)
        nse_corporate_actions_payload = self._fetch_nse_corporate_actions(normalized_symbol)
        shareholding = self._build_shareholding(info, nse_shareholding_payload)
        corporate_actions = self._build_corporate_actions(ticker, nse_corporate_actions_payload)

        return StockDataBundle(
            symbol=normalized_symbol,
            yahoo_symbol=yahoo_symbol,
            name=str(info.get("longName") or info.get("shortName") or normalized_symbol),
            sector=str(info.get("sector") or "Unknown"),
            fetched_at=datetime.utcnow(),
            financials=financials,
            valuation=valuation,
            shareholding=shareholding,
            historical_prices=historical_prices,
            corporate_actions=corporate_actions,
            raw_payloads={
                "yahoo_info": self._json_safe(info),
                "nse_shareholding": self._json_safe(nse_shareholding_payload),
                "nse_corporate_actions": self._json_safe(nse_corporate_actions_payload),
            },
        )

    @staticmethod
    def _to_yahoo_symbol(symbol: str) -> str:
        return symbol if symbol.endswith((".NS", ".BO")) else f"{symbol}.NS"

    def _safe_info(self, ticker: Any) -> dict[str, Any]:
        try:
            return dict(ticker.info or {})
        except Exception:
            return {}

    def _build_financials(self, ticker: Any, info: dict[str, Any]) -> list[FinancialStatementRecord]:
        try:
            income_stmt = ticker.income_stmt
        except Exception:
            income_stmt = None
        try:
            balance_sheet = ticker.balance_sheet
        except Exception:
            balance_sheet = None
        try:
            cashflow = ticker.cashflow
        except Exception:
            cashflow = None

        if income_stmt is None or income_stmt.empty:
            return []

        records: list[FinancialStatementRecord] = []
        for column in income_stmt.columns:
            fiscal_year = self._fiscal_year(column)
            revenue = self._crores(self._first_row_value(income_stmt, column, ["Total Revenue", "Operating Revenue"]))
            net_profit = self._crores(
                self._first_row_value(income_stmt, column, ["Net Income", "Net Income Common Stockholders"])
            )
            ebit = self._first_row_value(income_stmt, column, ["EBIT", "Operating Income"])
            interest_expense = abs(
                self._first_row_value(income_stmt, column, ["Interest Expense", "Interest Expense Non Operating"])
            )

            equity = self._first_row_value(
                balance_sheet,
                column,
                ["Stockholders Equity", "Total Equity Gross Minority Interest"],
            )
            total_debt = self._first_row_value(balance_sheet, column, ["Total Debt", "Net Debt"])
            total_assets = self._first_row_value(balance_sheet, column, ["Total Assets"])
            current_liabilities = self._first_row_value(balance_sheet, column, ["Current Liabilities"])
            capital_employed = max(total_assets - current_liabilities, 0)

            operating_cash_flow = self._first_row_value(cashflow, column, ["Operating Cash Flow"])
            free_cash_flow = self._first_row_value(cashflow, column, ["Free Cash Flow"])
            if free_cash_flow == 0:
                capital_expenditure = self._first_row_value(cashflow, column, ["Capital Expenditure"])
                free_cash_flow = operating_cash_flow + capital_expenditure

            eps = self._first_row_value(income_stmt, column, ["Diluted EPS", "Basic EPS"])
            if eps == 0 and fiscal_year == max(self._fiscal_year(item) for item in income_stmt.columns):
                eps = self._number(info.get("trailingEps"))

            records.append(
                FinancialStatementRecord(
                    fiscal_year=fiscal_year,
                    revenue=revenue,
                    net_profit=self._crores(net_profit * CRORE) if abs(net_profit) < 1 and net_profit else net_profit,
                    eps=eps,
                    roe=self._ratio(net_profit * CRORE, equity),
                    roce=self._ratio(ebit, capital_employed),
                    debt_equity=self._ratio(total_debt, equity, multiplier=1),
                    interest_coverage=(ebit / interest_expense) if interest_expense > 0 else 99,
                    operating_cash_flow=self._crores(operating_cash_flow),
                    free_cash_flow=self._crores(free_cash_flow),
                )
            )

        deduped = {record.fiscal_year: record for record in records if record.revenue > 0 or record.net_profit != 0}
        return sorted(deduped.values(), key=lambda item: item.fiscal_year)

    def _build_valuation(self, ticker: Any, info: dict[str, Any]) -> ValuationRecord | None:
        price = self._number(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))
        if price == 0:
            try:
                history = ticker.history(period="5d")
                if not history.empty:
                    price = float(history["Close"].dropna().iloc[-1])
            except Exception:
                price = 0

        pe = self._number(info.get("trailingPE") or info.get("forwardPE"))
        pb = self._number(info.get("priceToBook"))
        peg = self._number(info.get("trailingPegRatio") or info.get("pegRatio"))
        industry_pe = self._number(info.get("industryPE")) or (pe * 1.1 if pe else 1)

        if price == 0 and pe == 0 and pb == 0:
            return None

        return ValuationRecord(
            as_of_date=date.today(),
            pe=pe or 999,
            pb=pb or 999,
            peg=peg or 999,
            industry_pe=industry_pe,
            price=price,
            market_cap=self._number(info.get("marketCap")) or None,
        )

    def _build_historical_prices(self, ticker: Any) -> list[HistoricalPriceRecord]:
        try:
            history = ticker.history(period="5y", interval="1d", auto_adjust=False)
        except Exception:
            return []
        if history.empty:
            return []

        prices: list[HistoricalPriceRecord] = []
        for index, row in history.tail(1300).iterrows():
            trade_date = index.date() if hasattr(index, "date") else index
            prices.append(
                HistoricalPriceRecord(
                    trade_date=trade_date,
                    open=self._number(row.get("Open")),
                    high=self._number(row.get("High")),
                    low=self._number(row.get("Low")),
                    close=self._number(row.get("Close")),
                    volume=int(self._number(row.get("Volume"))),
                )
            )
        return prices

    def _build_shareholding(
        self,
        info: dict[str, Any],
        nse_payload: dict[str, Any] | list[Any] | None,
    ) -> list[ShareholdingRecord]:
        nse_records = self._parse_nse_shareholding(nse_payload)
        if nse_records:
            return nse_records

        promoter = min(max(self._number(info.get("heldPercentInsiders")) * 100, 0), 100)
        institutional = min(max(self._number(info.get("heldPercentInstitutions")) * 100, 0), 100)
        fii = institutional
        dii = 0.0
        retail = max(100 - promoter - fii - dii, 0)
        quarter = f"{date.today().year}Q{((date.today().month - 1) // 3) + 1}"
        return [
            ShareholdingRecord(
                quarter=quarter,
                promoter_holding=promoter,
                fii_holding=fii,
                dii_holding=dii,
                retail_holding=retail,
                pledged_shares=0,
            )
        ]

    def _build_corporate_actions(
        self,
        ticker: Any,
        nse_payload: dict[str, Any] | list[Any] | None,
    ) -> list[CorporateActionRecord]:
        nse_actions = self._parse_nse_corporate_actions(nse_payload)
        if nse_actions:
            return nse_actions

        try:
            actions = ticker.actions
        except Exception:
            return []
        if actions.empty:
            return []

        records: list[CorporateActionRecord] = []
        for index, row in actions.tail(200).iterrows():
            action_date = index.date() if hasattr(index, "date") else index
            dividend = self._number(row.get("Dividends"))
            split = self._number(row.get("Stock Splits"))
            if dividend:
                records.append(CorporateActionRecord(action_date, "DIVIDEND", f"Dividend {dividend}"))
            if split:
                records.append(CorporateActionRecord(action_date, "SPLIT", f"Stock split {split}"))
        return records

    def _fetch_nse_shareholding(self, symbol: str) -> dict[str, Any] | list[Any] | None:
        return self._nse_get("https://www.nseindia.com/api/corporate-share-holdings", {"index": "equities", "symbol": symbol})

    def _fetch_nse_corporate_actions(self, symbol: str) -> dict[str, Any] | list[Any] | None:
        return self._nse_get("https://www.nseindia.com/api/corporates-corporateActions", {"index": "equities", "symbol": symbol})

    def _nse_get(self, url: str, params: dict[str, str]) -> dict[str, Any] | list[Any] | None:
        try:
            self._nse_session.get("https://www.nseindia.com/", timeout=self.timeout)
            response = self._nse_session.get(url, params=params, timeout=self.timeout)
            if response.status_code >= 400:
                return None
            return response.json()
        except Exception:
            return None

    def _parse_nse_shareholding(self, payload: dict[str, Any] | list[Any] | None) -> list[ShareholdingRecord]:
        if payload is None:
            return []
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []

        records: list[ShareholdingRecord] = []
        for row in rows[:8]:
            if not isinstance(row, dict):
                continue
            promoter = self._number(
                row.get("promoterHolding") or row.get("promoter") or row.get("promoters") or row.get("promoterGroup")
            )
            fii = self._number(row.get("fiiHolding") or row.get("fii") or row.get("foreignInstitution"))
            dii = self._number(row.get("diiHolding") or row.get("dii") or row.get("domesticInstitution"))
            retail = self._number(row.get("publicHolding") or row.get("public") or row.get("retail"))
            pledged = self._number(row.get("pledgedShares") or row.get("promoterPledge") or row.get("pledged"))
            if promoter == 0 and fii == 0 and dii == 0 and retail == 0:
                continue
            records.append(
                ShareholdingRecord(
                    quarter=str(row.get("quarter") or row.get("period") or row.get("date") or date.today().isoformat()),
                    promoter_holding=promoter,
                    fii_holding=fii,
                    dii_holding=dii,
                    retail_holding=retail,
                    pledged_shares=pledged,
                )
            )
        return list(reversed(records)) if len(records) > 1 else records

    def _parse_nse_corporate_actions(self, payload: dict[str, Any] | list[Any] | None) -> list[CorporateActionRecord]:
        if payload is None:
            return []
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []

        records: list[CorporateActionRecord] = []
        for row in rows[:200]:
            if not isinstance(row, dict):
                continue
            raw_date = row.get("exDate") or row.get("recDate") or row.get("bcStartDate") or row.get("date")
            action_date = self._parse_date(raw_date)
            if action_date is None:
                continue
            action_type = str(row.get("subject") or row.get("purpose") or row.get("symbol") or "CORPORATE_ACTION")
            description = str(row.get("purpose") or row.get("subject") or action_type)
            records.append(CorporateActionRecord(action_date, action_type[:64], description))
        return records

    @staticmethod
    def _fiscal_year(value: Any) -> int:
        if hasattr(value, "year"):
            return int(value.year)
        parsed = StockDataProvider._parse_date(value)
        return parsed.year if parsed else date.today().year

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _first_row_value(frame: Any, column: Any, names: list[str]) -> float:
        if frame is None or getattr(frame, "empty", True) or column not in frame.columns:
            return 0.0
        for name in names:
            if name in frame.index:
                return StockDataProvider._number(frame.loc[name, column])
        return 0.0

    @staticmethod
    def _number(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            number = float(value)
            if number != number:
                return 0.0
            return number
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _crores(value: float) -> float:
        return value / CRORE if abs(value) > CRORE else value

    @staticmethod
    def _ratio(numerator: float, denominator: float, multiplier: float = 100) -> float:
        return (numerator / denominator) * multiplier if denominator else 0.0

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(key): StockDataProvider._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [StockDataProvider._json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)
