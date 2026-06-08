from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConcallTranscriptRequest(BaseModel):
    transcript: str | None = Field(default=None, min_length=1)
    transcript_url: str | None = Field(default=None, min_length=1)

    @field_validator("transcript", "transcript_url")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_transcript_input(self):
        if not self.transcript and not self.transcript_url:
            raise ValueError("transcript or transcript_url is required")
        return self


class ConcallSectionResponse(BaseModel):
    summary: str
    evidence: list[str]
    sentiment: str


class ConcallTranscriptResponse(BaseModel):
    expansion_plans: ConcallSectionResponse
    order_book: ConcallSectionResponse
    margin_outlook: ConcallSectionResponse
    debt_discussion: ConcallSectionResponse
    risks: ConcallSectionResponse
    management_guidance: ConcallSectionResponse
    final_view: str
    confidence: int
    reasoning: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expansion_plans": {
                    "summary": "Capacity expansion planned over the next year.",
                    "evidence": ["Management said capacity expansion is underway."],
                    "sentiment": "Bullish",
                },
                "order_book": {
                    "summary": "Order book remains healthy.",
                    "evidence": ["Order inflow remains strong."],
                    "sentiment": "Bullish",
                },
                "margin_outlook": {
                    "summary": "Margins expected to remain stable.",
                    "evidence": ["Management guided for stable EBITDA margins."],
                    "sentiment": "Neutral",
                },
                "debt_discussion": {
                    "summary": "No material debt concern.",
                    "evidence": ["The company remains debt free."],
                    "sentiment": "Bullish",
                },
                "risks": {
                    "summary": "Input cost volatility remains a watch item.",
                    "evidence": ["Commodity costs can affect margins."],
                    "sentiment": "Neutral",
                },
                "management_guidance": {
                    "summary": "Management expects growth to continue.",
                    "evidence": ["Management guided for double-digit growth."],
                    "sentiment": "Bullish",
                },
                "final_view": "Bullish",
                "confidence": 82,
                "reasoning": "Demand, order book, and balance sheet commentary are constructive.",
            }
        }
    )
