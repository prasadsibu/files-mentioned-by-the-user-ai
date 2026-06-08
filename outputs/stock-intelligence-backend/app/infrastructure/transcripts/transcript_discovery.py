from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from io import BytesIO
import importlib.util
import logging
import re
import zlib
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredTranscript:
    source_url: str
    transcript_text: str
    transcript_date: date | None
    discovery_method: str


@dataclass(frozen=True)
class TranscriptCandidate:
    url: str
    discovery_method: str
    title: str = ""
    transcript_date: date | None = None


class TranscriptDiscoveryService:
    """Discover and retrieve the latest public earnings/concall transcript for an NSE symbol."""

    request_timeout = 20
    min_transcript_chars = 120

    transcript_keywords = (
        "transcript",
        "conference call",
        "earnings call",
        "concall",
        "analyst meet",
        "investor call",
        "quarterly presentation",
        "investor presentation",
    )

    def __init__(self, session=None) -> None:
        self.session = session or _DefaultHttpSession()
        if hasattr(self.session, "headers"):
            self.session.headers.update(
                {
                    "User-Agent": "stock-intelligence-transcript-discovery/1.0",
                    "Accept": "text/html,application/pdf,application/json;q=0.9,*/*;q=0.8",
                }
            )

    def discover(self, symbol: str, company_name: str | None = None) -> DiscoveredTranscript | None:
        normalized_symbol = symbol.strip().upper()
        logger.info("transcript_discovery_started symbol=%s", normalized_symbol)
        for method_name, candidate_loader in (
            ("company_ir", self._company_ir_candidates),
            ("nse_corporate_announcements", self._nse_candidates),
            ("earnings_call_pages", self._earnings_call_candidates),
            ("quarterly_presentation_pdf", self._quarterly_presentation_candidates),
        ):
            try:
                candidates = candidate_loader(normalized_symbol, company_name)
            except Exception as exc:
                logger.warning(
                    "transcript_discovery_source_failed symbol=%s method=%s error=%s",
                    normalized_symbol,
                    method_name,
                    exc,
                )
                candidates = []
            logger.info(
                "transcript_discovery_candidates symbol=%s method=%s count=%s",
                normalized_symbol,
                method_name,
                len(candidates),
            )
            for candidate in candidates:
                transcript = self.retrieve(candidate)
                if transcript is not None:
                    logger.info(
                        "transcript_discovered symbol=%s method=%s source=%s chars=%s",
                        normalized_symbol,
                        transcript.discovery_method,
                        transcript.source_url,
                        len(transcript.transcript_text),
                    )
                    return transcript
        logger.info("transcript_unavailable symbol=%s", normalized_symbol)
        return None

    def retrieve(self, candidate: TranscriptCandidate) -> DiscoveredTranscript | None:
        try:
            response = self.session.get(candidate.url, timeout=self.request_timeout, allow_redirects=True)
            response.raise_for_status()
        except Exception as exc:
            logger.warning(
                "transcript_retrieval_failed source=%s method=%s error=%s",
                candidate.url,
                candidate.discovery_method,
                exc,
            )
            return None

        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type or candidate.url.lower().split("?")[0].endswith(".pdf"):
            text = self.extract_pdf_text(response.content)
        else:
            text = self.extract_html_text(response.text)
        normalized = self.normalize_text(text)
        if not self._looks_like_transcript(normalized):
            logger.info(
                "transcript_retrieval_rejected source=%s method=%s chars=%s",
                candidate.url,
                candidate.discovery_method,
                len(normalized),
            )
            return None

        return DiscoveredTranscript(
            source_url=response.url or candidate.url,
            transcript_text=normalized,
            transcript_date=candidate.transcript_date,
            discovery_method=candidate.discovery_method,
        )

    def _company_ir_candidates(self, symbol: str, company_name: str | None) -> list[TranscriptCandidate]:
        query = f'{company_name or symbol} investor relations earnings call transcript pdf'
        return self._search_candidates(query, "company_ir", prefer_pdf=False)

    def _nse_candidates(self, symbol: str, company_name: str | None) -> list[TranscriptCandidate]:
        url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={quote_plus(symbol)}"
        try:
            self.session.get("https://www.nseindia.com", timeout=self.request_timeout)
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("nse_transcript_lookup_failed symbol=%s error=%s", symbol, exc)
            return []

        candidates: list[TranscriptCandidate] = []
        for item in payload if isinstance(payload, list) else []:
            title = " ".join(str(item.get(key, "")) for key in ("desc", "subject", "sm_name"))
            attachment = item.get("attchmntFile") or item.get("attachmentFile") or item.get("url")
            if not attachment or not self._contains_transcript_keyword(title + " " + attachment):
                continue
            transcript_date = self._parse_date(str(item.get("an_dt") or item.get("date") or ""))
            candidates.append(
                TranscriptCandidate(
                    url=str(attachment),
                    discovery_method="nse_corporate_announcements",
                    title=title,
                    transcript_date=transcript_date,
                )
            )
        return candidates

    def _earnings_call_candidates(self, symbol: str, company_name: str | None) -> list[TranscriptCandidate]:
        query = f'{company_name or symbol} earnings call transcript conference call transcript'
        return self._search_candidates(query, "earnings_call_pages", prefer_pdf=False)

    def _quarterly_presentation_candidates(self, symbol: str, company_name: str | None) -> list[TranscriptCandidate]:
        query = f'{company_name or symbol} quarterly results presentation pdf analyst meet transcript'
        return self._search_candidates(query, "quarterly_presentation_pdf", prefer_pdf=True)

    def _search_candidates(self, query: str, method: str, prefer_pdf: bool) -> list[TranscriptCandidate]:
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            response = self.session.get(search_url, timeout=self.request_timeout)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("transcript_search_failed method=%s query=%s error=%s", method, query, exc)
            return []
        links = _SearchResultParser().parse(response.text)
        candidates = [
            TranscriptCandidate(url=url, discovery_method=method, title=title, transcript_date=self._parse_date(title))
            for title, url in links
            if self._is_candidate_url(url, title, prefer_pdf=prefer_pdf)
        ]
        return self._dedupe_candidates(candidates)[:8]

    def _is_candidate_url(self, url: str, title: str, prefer_pdf: bool) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        normalized = f"{title} {url}".lower()
        if prefer_pdf and ".pdf" not in normalized:
            return False
        return self._contains_transcript_keyword(normalized)

    def _looks_like_transcript(self, text: str) -> bool:
        if len(text) < self.min_transcript_chars:
            return False
        normalized = text.lower()
        keyword_hits = sum(1 for keyword in self.transcript_keywords if keyword in normalized)
        management_hits = sum(
            1
            for keyword in ("management", "revenue", "margin", "guidance", "order book", "capex", "risk", "question")
            if keyword in normalized
        )
        return keyword_hits > 0 or management_hits >= 2

    def _contains_transcript_keyword(self, value: str) -> bool:
        normalized = value.lower()
        return any(keyword in normalized for keyword in self.transcript_keywords)

    @staticmethod
    def _dedupe_candidates(candidates: list[TranscriptCandidate]) -> list[TranscriptCandidate]:
        seen: set[str] = set()
        unique: list[TranscriptCandidate] = []
        for candidate in candidates:
            if candidate.url in seen:
                continue
            seen.add(candidate.url)
            unique.append(candidate)
        return unique

    @staticmethod
    def _parse_date(value: str) -> date | None:
        for pattern in ("%d-%b-%Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"):
            try:
                return datetime.strptime(value.strip()[:20], pattern).date()
            except ValueError:
                continue
        year_match = re.search(r"\b(20\d{2})\b", value)
        if year_match:
            return date(int(year_match.group(1)), 1, 1)
        return None

    @staticmethod
    def normalize_text(text: str) -> str:
        compact = re.sub(r"\s+", " ", text or "").strip()
        return compact[:120_000]

    @staticmethod
    def extract_html_text(html: str) -> str:
        parser = _VisibleTextParser()
        parser.feed(html or "")
        return parser.text

    @staticmethod
    def extract_pdf_text(payload: bytes) -> str:
        if importlib.util.find_spec("pypdf") is not None:
            from pypdf import PdfReader  # type: ignore

            try:
                reader = PdfReader(BytesIO(payload))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                pass

        chunks: list[str] = []
        for stream_match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", payload, flags=re.S):
            stream = stream_match.group(1).strip(b"\r\n")
            for candidate in (stream, _try_zlib(stream)):
                if not candidate:
                    continue
                chunks.extend(_pdf_text_literals(candidate))
                decoded = candidate.decode("latin-1", errors="ignore")
                chunks.append(decoded)
        if not chunks:
            chunks.append(payload.decode("latin-1", errors="ignore"))
        text = " ".join(chunks)
        text = re.sub(r"/[^\s]+|BT|ET|Tf|Td|Tj|TJ|Tm|\d+\s+\d+\s+obj|endobj", " ", text)
        return text


class _DefaultHttpResponse:
    def __init__(self, url: str, payload: bytes, headers) -> None:
        self.url = url
        self.content = payload
        self.headers = headers
        self.text = payload.decode("utf-8", errors="ignore")

    def raise_for_status(self) -> None:
        return None

    def json(self):
        import json

        return json.loads(self.text)


class _DefaultHttpSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: int = 20, allow_redirects: bool = True):
        request = Request(url, headers=self.headers)
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(4_000_000)
            final_url = response.geturl()
            headers = response.headers
        return _DefaultHttpResponse(final_url, payload, headers)


class _VisibleTextParser(HTMLParser):
    ignored_tags = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.ignored_tags:
            self._ignored_depth += 1
        if tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3"}:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in {"p", "div", "li", "tr"}:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(self._parts)


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self._results: list[tuple[str, str]] = []

    def parse(self, html: str) -> list[tuple[str, str]]:
        self.feed(html or "")
        return self._results

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        class_name = attrs_dict.get("class", "")
        if href and ("result__a" in class_name or "uddg=" in href or href.startswith("http")):
            self._current_href = self._clean_href(href)
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            title = " ".join(self._current_text).strip()
            self._results.append((title, self._current_href))
            self._current_href = None
            self._current_text = []

    @staticmethod
    def _clean_href(href: str) -> str:
        if "uddg=" not in href:
            return href
        from urllib.parse import parse_qs, unquote, urlparse

        query = parse_qs(urlparse(href).query)
        target = query.get("uddg", [href])[0]
        return unquote(target)


def _try_zlib(payload: bytes) -> bytes | None:
    try:
        return zlib.decompress(payload)
    except Exception:
        return None


def _pdf_text_literals(payload: bytes) -> list[str]:
    literals: list[str] = []
    for match in re.finditer(rb"\((.*?)\)\s*Tj", payload, flags=re.S):
        literals.append(_decode_pdf_literal(match.group(1)))
    for array_match in re.finditer(rb"\[(.*?)\]\s*TJ", payload, flags=re.S):
        literals.extend(_decode_pdf_literal(item) for item in re.findall(rb"\((.*?)\)", array_match.group(1), flags=re.S))
    return literals


def _decode_pdf_literal(value: bytes) -> str:
    text = value.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
    return text.decode("latin-1", errors="ignore")
