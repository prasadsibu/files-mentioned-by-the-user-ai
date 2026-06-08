from app.domain.entities import CategoryScore, FinancialMetrics


class FinancialAnalyzer:
    weight = 25

    def analyze(self, metrics: FinancialMetrics) -> CategoryScore:
        points = 0
        reasons: list[str] = []

        if metrics.roe > 15:
            points += 34
            reasons.append("ROE is above 15%.")
        if metrics.roce > 18:
            points += 33
            reasons.append("ROCE is above 18%.")
        if metrics.debt_equity < 0.5:
            points += 33
            reasons.append("Debt/equity is below 0.5.")

        return CategoryScore(
            category="fundamentals",
            weight=self.weight,
            score=min(points, 100),
            reasoning=" ".join(reasons) or "Fundamental metrics are below preferred thresholds.",
            input_values={
                "roe": metrics.roe,
                "roce": metrics.roce,
                "debt_equity": metrics.debt_equity,
                "interest_coverage": metrics.interest_coverage,
                "free_cash_flow": metrics.free_cash_flow,
            },
        )
