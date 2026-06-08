from dataclasses import dataclass
from enum import StrEnum


class ConcallStance(StrEnum):
    BULLISH = "Bullish"
    NEUTRAL = "Neutral"
    BEARISH = "Bearish"


@dataclass(frozen=True)
class ExtractedConcallSection:
    summary: str
    evidence: list[str]
    sentiment: ConcallStance


@dataclass(frozen=True)
class ConcallTranscriptAnalysis:
    expansion_plans: ExtractedConcallSection
    order_book: ExtractedConcallSection
    margin_outlook: ExtractedConcallSection
    debt_discussion: ExtractedConcallSection
    risks: ExtractedConcallSection
    management_guidance: ExtractedConcallSection
    final_view: ConcallStance
    confidence: int
    reasoning: str

    def to_api_dict(self) -> dict:
        return {
            "expansion_plans": self._section_to_dict(self.expansion_plans),
            "order_book": self._section_to_dict(self.order_book),
            "margin_outlook": self._section_to_dict(self.margin_outlook),
            "debt_discussion": self._section_to_dict(self.debt_discussion),
            "risks": self._section_to_dict(self.risks),
            "management_guidance": self._section_to_dict(self.management_guidance),
            "final_view": self.final_view.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    @staticmethod
    def _section_to_dict(section: ExtractedConcallSection) -> dict[str, str | list[str]]:
        return {
            "summary": section.summary,
            "evidence": section.evidence,
            "sentiment": section.sentiment.value,
        }
