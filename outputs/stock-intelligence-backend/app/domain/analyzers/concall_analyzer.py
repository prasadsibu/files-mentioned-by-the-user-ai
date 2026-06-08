from app.domain.entities import CategoryScore, ConcallSignals


class ConcallAnalyzer:
    weight = 10

    def analyze(self, signals: ConcallSignals | None) -> CategoryScore:
        if signals is None:
            return CategoryScore(
                category="concall_intelligence",
                weight=self.weight,
                score=50,
                reasoning="No concall transcript was submitted; assigning neutral concall recommendation.",
                input_values={"status": "not_available", "concall_recommendation": "WATCH"},
            )

        section_scores = {
            "management_tone": self._stance_score(signals.management_tone),
            "revenue_outlook": self._stance_score(signals.revenue_outlook),
            "margin_outlook": self._stance_score(signals.margin_outlook),
            "order_book_commentary": self._stance_score(signals.order_book_commentary),
            "capex_plans": self._stance_score(signals.capex_plans),
            "risks_mentioned": self._risk_score(signals.risks_mentioned),
            "guidance_changes": self._stance_score(signals.guidance_changes),
        }
        weights = {
            "management_tone": 15,
            "revenue_outlook": 20,
            "margin_outlook": 15,
            "order_book_commentary": 15,
            "capex_plans": 10,
            "risks_mentioned": 15,
            "guidance_changes": 10,
        }
        weighted_section_score = sum(section_scores[key] * weights[key] for key in weights) / sum(weights.values())
        confidence = max(0, min(signals.confidence or 50, 100))
        score = round((weighted_section_score * 0.90) + (confidence * 0.10))

        if signals.has_expansion_plan:
            score += 3
        if signals.has_order_book_growth:
            score += 4
        if signals.has_margin_guidance:
            score += 2
        if signals.has_debt_concern:
            score -= 8

        if signals.bullish_signals >= 4 and signals.bearish_signals == 0:
            score = max(score, 80)
        if signals.bearish_signals >= 3:
            score = min(score, 30)

        score = max(0, min(score, 100))
        recommendation = self._recommendation(score)
        reasoning = (
            f"Concall recommendation: {recommendation}. Management tone {signals.management_tone.lower()}, "
            f"revenue outlook {signals.revenue_outlook.lower()}, margin outlook {signals.margin_outlook.lower()}, "
            f"order book commentary {signals.order_book_commentary.lower()}, capex plans {signals.capex_plans.lower()}, "
            f"risks mentioned {signals.risks_mentioned.lower()}, and guidance changes {signals.guidance_changes.lower()} "
            f"were weighted with {confidence}% transcript-analysis confidence."
        )

        return CategoryScore(
            category="concall_intelligence",
            weight=self.weight,
            score=score,
            reasoning=reasoning,
            input_values={
                "bullish_signals": signals.bullish_signals,
                "neutral_signals": signals.neutral_signals,
                "bearish_signals": signals.bearish_signals,
                "has_expansion_plan": str(signals.has_expansion_plan),
                "has_order_book_growth": str(signals.has_order_book_growth),
                "has_margin_guidance": str(signals.has_margin_guidance),
                "has_debt_concern": str(signals.has_debt_concern),
                "management_tone": signals.management_tone,
                "revenue_outlook": signals.revenue_outlook,
                "margin_outlook": signals.margin_outlook,
                "order_book_commentary": signals.order_book_commentary,
                "capex_plans": signals.capex_plans,
                "risks_mentioned": signals.risks_mentioned,
                "guidance_changes": signals.guidance_changes,
                "confidence": confidence,
                "concall_recommendation": recommendation,
            },
        )

    @staticmethod
    def _stance_score(stance: str) -> int:
        normalized = stance.lower()
        if normalized == "bullish":
            return 100
        if normalized == "bearish":
            return 15
        return 55

    @staticmethod
    def _risk_score(stance: str) -> int:
        normalized = stance.lower()
        if normalized == "bearish":
            return 10
        if normalized == "bullish":
            return 75
        return 55

    @staticmethod
    def _recommendation(score: int) -> str:
        if score >= 80:
            return "BUY"
        if score >= 40:
            return "WATCH"
        return "IGNORE"
