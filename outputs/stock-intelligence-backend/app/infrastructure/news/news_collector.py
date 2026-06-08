from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from app.domain.news_sentiment import NewsArticle


class NewsCollectionError(Exception):
    pass


class NewsCollector(ABC):
    @abstractmethod
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        raise NotImplementedError


class CompositeNewsCollector(NewsCollector):
    def __init__(self, collectors: list[NewsCollector] | None = None) -> None:
        self.collectors = collectors or [
            GoogleNewsRSSCollector(),
            YahooFinanceNewsCollector(),
            NSECorporateAnnouncementsCollector(),
        ]

    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for collector in self.collectors:
            try:
                articles.extend(collector.collect(stock_name, limit=limit))
            except Exception:
                continue

        deduped: dict[str, NewsArticle] = {}
        for article in articles:
            key = (article.url or article.title).strip().lower()
            if key and key not in deduped:
                deduped[key] = article

        return sorted(
            deduped.values(),
            key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:limit]


class GoogleNewsRSSCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        query = quote_plus(f"{stock_name} stock India")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        request = Request(url, headers={"User-Agent": "stock-intelligence-local/1.0"})

        try:
            with urlopen(request, timeout=10) as response:
                payload = response.read()
        except URLError as exc:
            raise NewsCollectionError(f"Unable to collect recent news for {stock_name}") from exc

        root = ElementTree.fromstring(payload)
        articles: list[NewsArticle] = []

        for item in root.findall("./channel/item")[:limit]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            source = item.findtext("source") or "Google News"
            published_at = self._parse_date(item.findtext("pubDate"))
            summary = item.findtext("description") or ""

            if title:
                articles.append(
                    NewsArticle(
                        title=title,
                        url=link,
                        source=source,
                        published_at=published_at,
                        summary=summary,
                    )
                )

        return articles

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None


class YahooFinanceNewsCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        import yfinance as yf

        ticker = yf.Ticker(self._to_yahoo_symbol(stock_name))
        try:
            rows = ticker.news or []
        except Exception as exc:
            raise NewsCollectionError(f"Unable to collect Yahoo Finance news for {stock_name}") from exc

        articles: list[NewsArticle] = []
        for row in rows[:limit]:
            content = row.get("content", row) if isinstance(row, dict) else {}
            title = str(content.get("title") or row.get("title") or "").strip()
            url = str(
                content.get("canonicalUrl", {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict)
                else content.get("clickThroughUrl", {}).get("url")
                if isinstance(content.get("clickThroughUrl"), dict)
                else row.get("link") or row.get("url") or ""
            )
            provider = content.get("provider", {}) if isinstance(content, dict) else {}
            source = str(provider.get("displayName") if isinstance(provider, dict) else row.get("publisher") or "Yahoo Finance")
            published_at = self._published_at(content.get("pubDate") or row.get("providerPublishTime"))
            summary = str(content.get("summary") or row.get("summary") or "")
            if title:
                articles.append(NewsArticle(title=title, url=url, source=source, published_at=published_at, summary=summary))
        return articles

    @staticmethod
    def _to_yahoo_symbol(symbol: str) -> str:
        normalized = symbol.upper().strip()
        return normalized if normalized.endswith((".NS", ".BO")) else f"{normalized}.NS"

    @staticmethod
    def _published_at(value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


class NSECorporateAnnouncementsCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        symbol = stock_name.upper().strip().split(".")[0]
        url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={quote_plus(symbol)}"
        request = Request(
            "https://www.nseindia.com/",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
        )
        opener_request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.nseindia.com/"},
        )
        try:
            with urlopen(request, timeout=10):
                pass
            with urlopen(opener_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise NewsCollectionError(f"Unable to collect NSE announcements for {stock_name}") from exc

        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []

        articles: list[NewsArticle] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("desc") or row.get("subject") or row.get("attchmntText") or "").strip()
            url = str(row.get("attchmntFile") or row.get("smIndustry") or "")
            published_at = self._parse_date(row.get("an_dt") or row.get("date") or row.get("sort_date"))
            if title:
                articles.append(
                    NewsArticle(
                        title=title,
                        url=url,
                        source="NSE Corporate Announcements",
                        published_at=published_at,
                        summary=str(row.get("sm_name") or row.get("symbol") or symbol),
                    )
                )
        return articles

    @staticmethod
    def _parse_date(value) -> datetime | None:
        if not value:
            return None
        text = str(value)
        for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None


class StaticNewsCollector(NewsCollector):
    def collect(self, stock_name: str, limit: int = 20) -> list[NewsArticle]:
        samples = [
            NewsArticle(
                title=f"{stock_name} reports strong order inflow and margin improvement",
                url="local://news/strong-order-inflow",
                source="Local Sample",
                published_at=datetime.now(timezone.utc),
                summary="Management commentary points to healthy demand and improved execution.",
            ),
            NewsArticle(
                title=f"{stock_name} expands capacity to capture industrial capex cycle",
                url="local://news/capacity-expansion",
                source="Local Sample",
                published_at=datetime.now(timezone.utc),
                summary="The company is investing in expansion after robust customer enquiries.",
            ),
            NewsArticle(
                title=f"Analysts watch input cost pressure for {stock_name}",
                url="local://news/input-cost-pressure",
                source="Local Sample",
                published_at=datetime.now(timezone.utc),
                summary="Raw material volatility could keep margins under watch in coming quarters.",
            ),
            NewsArticle(
                title=f"{stock_name} stock trades steady after quarterly update",
                url="local://news/quarterly-update",
                source="Local Sample",
                published_at=datetime.now(timezone.utc),
                summary="Investors await more details on revenue growth and working capital.",
            ),
        ]
        return samples[:limit]
