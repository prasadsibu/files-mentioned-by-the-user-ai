from app.application.services.concall_transcript_service import RuleBasedConcallTranscriptAnalyzer


def test_rule_based_concall_analyzer_extracts_bullish_view() -> None:
    transcript = """
    Management said capacity expansion is underway and the new line should support growth.
    The order book remains strong with healthy demand from industrial customers.
    EBITDA margin improvement is expected as operating leverage improves.
    The company remains debt free with strong cash generation.
    Key risks include raw material cost pressure and execution delays.
    Management guidance indicates double digit revenue growth next year.
    """

    result = RuleBasedConcallTranscriptAnalyzer().analyze(transcript)

    assert result.final_view.value == "Bullish"
    assert result.confidence >= 50
    assert result.expansion_plans.evidence
    assert result.order_book.sentiment.value == "Bullish"
    assert result.debt_discussion.sentiment.value == "Bullish"


def test_concall_output_contains_required_sections() -> None:
    transcript = "Management guidance is stable. Margin outlook is neutral. Risks remain manageable."

    payload = RuleBasedConcallTranscriptAnalyzer().analyze(transcript).to_api_dict()

    assert set(payload) == {
        "expansion_plans",
        "order_book",
        "margin_outlook",
        "debt_discussion",
        "risks",
        "management_guidance",
        "final_view",
        "confidence",
        "reasoning",
    }
