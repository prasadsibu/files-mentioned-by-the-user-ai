from urllib.request import Request, urlopen

from app.domain.concall_transcript import ConcallStance, ConcallTranscriptAnalysis, ExtractedConcallSection
from app.infrastructure.transcripts.transcript_discovery import DiscoveredTranscript, TranscriptDiscoveryService


class ConcallTranscriptService:
    def __init__(self, openai_client=None, transcript_discovery_service: TranscriptDiscoveryService | None = None) -> None:
        self.openai_client = openai_client
        self.transcript_discovery_service = transcript_discovery_service or TranscriptDiscoveryService()

    def analyze(self, transcript: str) -> ConcallTranscriptAnalysis:
        cleaned = transcript.strip()
        if not cleaned:
            raise ValueError("concall transcript is required")

        try:
            return self._get_openai_client().analyze(cleaned)
        except Exception:
            return RuleBasedConcallTranscriptAnalyzer().analyze(cleaned)

    def analyze_input(self, transcript: str | None = None, transcript_url: str | None = None) -> ConcallTranscriptAnalysis:
        content = (transcript or "").strip()
        if not content and transcript_url:
            content = self.fetch_transcript_url(transcript_url)
        if not content:
            raise ValueError("concall transcript or transcript_url is required")
        return self.analyze(content)

    def discover_transcript(self, symbol: str, company_name: str | None = None) -> DiscoveredTranscript | None:
        return self.transcript_discovery_service.discover(symbol=symbol, company_name=company_name)

    @staticmethod
    def fetch_transcript_url(transcript_url: str) -> str:
        request = Request(transcript_url, headers={"User-Agent": "stock-intelligence-local/1.0"})
        with urlopen(request, timeout=20) as response:
            payload = response.read(4_000_000)
            content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type or transcript_url.lower().split("?")[0].endswith(".pdf"):
            return TranscriptDiscoveryService.extract_pdf_text(payload)
        return payload.decode("utf-8", errors="ignore")

    def _get_openai_client(self):
        if self.openai_client is not None:
            return self.openai_client

        from app.ai.openai_concall_client import OpenAIConcallClient

        self.openai_client = OpenAIConcallClient()
        return self.openai_client


class RuleBasedConcallTranscriptAnalyzer:
    bullish_terms = {
        "capacity expansion",
        "expansion",
        "strong demand",
        "order book",
        "orders grew",
        "margin improvement",
        "debt free",
        "guidance",
        "growth",
        "operating leverage",
        "bullish",
        "market share",
        "revenue growth",
        "price increase",
    }
    bearish_terms = {
        "slowdown",
        "weak demand",
        "margin pressure",
        "debt increased",
        "high debt",
        "risk",
        "delay",
        "cost pressure",
        "uncertainty",
        "decline",
        "guidance cut",
        "headwind",
    }

    def analyze(self, transcript: str) -> ConcallTranscriptAnalysis:
        sections = {
            "expansion_plans": self._extract_section(
                transcript,
                ["expansion", "capacity", "capex", "new plant"],
                "Capex Plans",
            ),
            "order_book": self._extract_section(
                transcript,
                ["order book", "orders", "inflow", "pipeline"],
                "Order Book Commentary",
            ),
            "margin_outlook": self._extract_section(
                transcript,
                ["margin", "ebitda", "gross margin", "operating leverage"],
                "Margin Outlook",
            ),
            "debt_discussion": self._extract_section(
                transcript,
                ["tone", "management", "debt", "borrowings", "cash", "working capital"],
                "Management Tone And Balance Sheet",
            ),
            "risks": self._extract_section(
                transcript,
                ["risk", "pressure", "delay", "slowdown", "uncertainty", "headwind"],
                "Risks Mentioned",
            ),
            "management_guidance": self._extract_section(
                transcript,
                ["guidance", "outlook", "expect", "target", "plan", "revenue"],
                "Revenue Outlook And Guidance Changes",
            ),
        }

        stance_values = [section.sentiment for section in sections.values()]
        bullish_count = stance_values.count(ConcallStance.BULLISH)
        bearish_count = stance_values.count(ConcallStance.BEARISH)

        if bullish_count > bearish_count + 1:
            final_view = ConcallStance.BULLISH
        elif bearish_count > bullish_count:
            final_view = ConcallStance.BEARISH
        else:
            final_view = ConcallStance.NEUTRAL

        evidence_count = sum(len(section.evidence) for section in sections.values())
        confidence = min(95, 45 + abs(bullish_count - bearish_count) * 12 + evidence_count * 2)

        return ConcallTranscriptAnalysis(
            expansion_plans=sections["expansion_plans"],
            order_book=sections["order_book"],
            margin_outlook=sections["margin_outlook"],
            debt_discussion=sections["debt_discussion"],
            risks=sections["risks"],
            management_guidance=sections["management_guidance"],
            final_view=final_view,
            confidence=confidence,
            reasoning=(
                f"Analysis found {bullish_count} bullish sections and "
                f"{bearish_count} bearish sections across management tone, revenue outlook, margins, order book, capex, risks, and guidance."
            ),
        )

    def _extract_section(self, transcript: str, keywords: list[str], label: str) -> ExtractedConcallSection:
        sentences = [
            sentence
            for sentence in self._sentences(transcript)
            if any(keyword in sentence.lower() for keyword in keywords)
        ][:5]

        section_text = " ".join(sentences)
        sentiment = self._classify(section_text)
        summary = (
            self._summarize(label, section_text)
            if section_text
            else f"{label}: no explicit transcript commentary was found."
        )

        return ExtractedConcallSection(
            summary=summary,
            evidence=sentences,
            sentiment=sentiment,
        )

    def _classify(self, text: str) -> ConcallStance:
        normalized = text.lower()
        bullish_hits = sum(1 for term in self.bullish_terms if term in normalized)
        bearish_hits = sum(1 for term in self.bearish_terms if term in normalized)

        if bullish_hits > bearish_hits:
            return ConcallStance.BULLISH
        if bearish_hits > bullish_hits:
            return ConcallStance.BEARISH
        return ConcallStance.NEUTRAL

    @staticmethod
    def _sentences(transcript: str) -> list[str]:
        normalized = transcript.replace("\n", " ")
        raw_sentences = normalized.split(".")
        return [sentence.strip() for sentence in raw_sentences if len(sentence.strip()) > 20]

    @staticmethod
    def _summarize(label: str, section_text: str) -> str:
        compact = section_text.strip()
        if len(compact) > 220:
            compact = compact[:217].rstrip() + "..."
        return f"{label}: {compact}"
