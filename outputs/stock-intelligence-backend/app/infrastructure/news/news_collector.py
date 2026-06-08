from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
