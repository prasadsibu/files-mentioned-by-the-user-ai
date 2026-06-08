import json

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.domain.concall_transcript import ConcallStance, ConcallTranscriptAnalysis, ExtractedConcallSection


class ConcallSectionPayload(BaseModel):
    summary: str = Field(..., min_length=1)
    evidence: list[str] = Field(default_factory=list, max_length=5)
    sentiment: ConcallStance


class ConcallAnalysisPayload(BaseModel):
    expansion_plans: ConcallSectionPayload
    order_book: ConcallSectionPayload
    margin_outlook: ConcallSectionPayload
    debt_discussion: ConcallSectionPayload
    risks: ConcallSectionPayload
    management_guidance: ConcallSectionPayload
    final_view: ConcallStance
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., min_length=1)


class OpenAIConcallClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.openai_model
        self.client = self._build_client(settings.openai_api_key) if settings.openai_api_key else None

    def analyze(self, transcript: str) -> ConcallTranscriptAnalysis:
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an equity research analyst. Extract structured concall insights. "
                        "Return strict JSON only. Classify all sentiment values exactly as Bullish, Neutral, or Bearish."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(transcript),
                },
            ],
        )

        content = response.choices[0].message.content or "{}"
        try:
            payload = ConcallAnalysisPayload.model_validate_json(content)
        except ValidationError:
            payload = ConcallAnalysisPayload.model_validate(json.loads(content))

        return self._to_domain(payload)

    @staticmethod
    def _build_client(api_key: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the openai package to use OpenAI concall analysis.") from exc
        return OpenAI(api_key=api_key)

    @staticmethod
    def _build_prompt(transcript: str) -> str:
        return f"""
Analyze this concall transcript and extract:
- management tone and balance-sheet/debt commentary as debt_discussion
- revenue outlook and guidance changes as management_guidance
- margin outlook
- order book commentary
- capex plans as expansion_plans
- risks mentioned

For each section return:
- summary: concise analyst summary
- evidence: 1 to 5 short transcript-backed evidence points
- sentiment: Bullish, Neutral, or Bearish

Also return:
- final_view: Bullish, Neutral, or Bearish
- confidence: integer 0-100
- reasoning: concise explanation covering management tone, revenue outlook, margin outlook, order book commentary, capex plans, risks mentioned, and guidance changes

JSON shape:
{{
  "expansion_plans": {{"summary": "...", "evidence": ["..."], "sentiment": "Bullish"}},
  "order_book": {{"summary": "...", "evidence": ["..."], "sentiment": "Bullish"}},
  "margin_outlook": {{"summary": "...", "evidence": ["..."], "sentiment": "Neutral"}},
  "debt_discussion": {{"summary": "...", "evidence": ["..."], "sentiment": "Neutral"}},
  "risks": {{"summary": "...", "evidence": ["..."], "sentiment": "Bearish"}},
  "management_guidance": {{"summary": "...", "evidence": ["..."], "sentiment": "Bullish"}},
  "final_view": "Bullish",
  "confidence": 82,
  "reasoning": "..."
}}

Transcript:
{transcript[:24000]}
""".strip()

    @staticmethod
    def _to_domain(payload: ConcallAnalysisPayload) -> ConcallTranscriptAnalysis:
        return ConcallTranscriptAnalysis(
            expansion_plans=OpenAIConcallClient._section(payload.expansion_plans),
            order_book=OpenAIConcallClient._section(payload.order_book),
            margin_outlook=OpenAIConcallClient._section(payload.margin_outlook),
            debt_discussion=OpenAIConcallClient._section(payload.debt_discussion),
            risks=OpenAIConcallClient._section(payload.risks),
            management_guidance=OpenAIConcallClient._section(payload.management_guidance),
            final_view=payload.final_view,
            confidence=payload.confidence,
            reasoning=payload.reasoning,
        )

    @staticmethod
    def _section(payload: ConcallSectionPayload) -> ExtractedConcallSection:
        return ExtractedConcallSection(
            summary=payload.summary,
            evidence=payload.evidence,
            sentiment=payload.sentiment,
        )
