from app.domain.entities import CategoryScore, ConcallSignals


class ConcallAnalyzer:
    weight = 10

    def analyze(self, signals: ConcallSignals | None) -> CategoryScore:
        if signals is None:
            return CategoryScore(
                category="concall",
                weight=self.weight,
                score=50,
                reasoning="No concall transcript was submitted for this run; assigning neutral score.",
                input_values={"status": "not_available"},
            )

        signal_total = signals.bullish_signals + signals.neutral_signals + signals.bearish_signals
        base_score = 50 if signal_total == 0 else round(
            (
                signals.bullish_signals * 100
                + signals.neutral_signals * 50
                + signals.bearish_signals * 0
            )
            / signal_total
        )

        bonus = 0
        reasons: list[str] = ["Concall score is based on extracted management signals."]
        if signals.has_expansion_plan:
            bonus += 10
            reasons.append("Expansion plan detected.")
        if signals.has_order_book_growth:
            bonus += 10
            reasons.append("Order book growth detected.")
        if signals.has_margin_guidance:
            bonus += 5
            reasons.append("Margin guidance detected.")
        if signals.has_debt_concern:
            bonus -= 15
            reasons.append("Debt concern detected.")

        return CategoryScore(
            category="concall",
            weight=self.weight,
            score=max(0, min(base_score + bonus, 100)),
            reasoning=" ".join(reasons),
            input_values={
                "bullish_signals": signals.bullish_signals,
                "neutral_signals": signals.neutral_signals,
                "bearish_signals": signals.bearish_signals,
                "has_expansion_plan": str(signals.has_expansion_plan),
                "has_order_book_growth": str(signals.has_order_book_growth),
                "has_margin_guidance": str(signals.has_margin_guidance),
                "has_debt_concern": str(signals.has_debt_concern),
            },
        )
