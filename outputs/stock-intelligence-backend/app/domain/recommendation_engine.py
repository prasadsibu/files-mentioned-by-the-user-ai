from app.domain.entities import CategoryScore, RecommendationResult


class RecommendationEngine:
    def recommend(self, scores: list[CategoryScore]) -> RecommendationResult:
        total = round(sum(item.weighted_score for item in scores))

        if total >= 80:
            recommendation = "BUY"
        elif total >= 60:
            recommendation = "WATCH"
        else:
            recommendation = "IGNORE"

        confidence = self._confidence(total, scores)

        return RecommendationResult(
            recommendation=recommendation,
            score=int(total),
            confidence=confidence,
            breakdown=scores,
        )

    @staticmethod
    def _confidence(total: int, scores: list[CategoryScore]) -> str:
        weak_categories = sum(1 for item in scores if item.score < 50)
        if weak_categories >= 2:
            return "LOW"
        if total >= 80 or total < 50:
            return "HIGH"
        return "MEDIUM"
