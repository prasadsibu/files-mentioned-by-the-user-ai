from app.domain.entities import CategoryScore, FinancialMetrics


class GrowthAnalyzer:
    weight = 20

    def analyze(self, history: list[FinancialMetrics]) -> CategoryScore:
        ordered = sorted(history, key=lambda item: item.fiscal_year)
        first = ordered[0]
        latest = ordered[-1]
        years = max(len(ordered) - 1, 1)

        revenue_cagr = self._cagr(first.revenue, latest.revenue, years)
        profit_cagr = self._cagr(first.net_profit, latest.net_profit, years)
        eps_cagr = self._cagr(first.eps, latest.eps, years)

        points = 0
        reasons: list[str] = []

        if revenue_cagr > 15:
            points += 50
            reasons.append("Revenue CAGR is above 15%.")
        if profit_cagr > 20:
            points += 50
            reasons.append("Profit CAGR is above 20%.")

        return CategoryScore(
            category="growth",
            weight=self.weight,
            score=min(points, 100),
            reasoning=" ".join(reasons) or "Growth is below preferred compounding thresholds.",
            input_values={
                "revenue_cagr": round(revenue_cagr, 2),
                "profit_cagr": round(profit_cagr, 2),
            },
        )

    @staticmethod
    def _cagr(start: float, end: float, years: int) -> float:
        if start <= 0 or end <= 0:
            return 0
        return ((end / start) ** (1 / years) - 1) * 100
