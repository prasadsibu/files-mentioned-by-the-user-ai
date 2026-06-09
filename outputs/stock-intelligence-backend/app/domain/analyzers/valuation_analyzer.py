from app.domain.entities import CategoryScore, FinancialMetrics, ValuationMetrics


class ValuationAnalyzer:
    weight = 15

    def analyze(self, valuation: ValuationMetrics, history: list[FinancialMetrics]) -> CategoryScore:
        latest = sorted(history, key=lambda item: item.fiscal_year)[-1]
        points = 0
        reasons: list[str] = []

        if (
            valuation.pe is not None
            and valuation.industry_pe is not None
            and valuation.pe < valuation.industry_pe
        ):
            points += 35
            reasons.append("Current PE is below industry PE.")

        if valuation.pb is not None and valuation.pb <= 4:
            points += 20
            reasons.append("PB ratio is reasonable.")

        if valuation.peg is not None and valuation.peg <= 1:
            points += 30
            reasons.append("PEG is at or below 1.")
        if (
            latest.roe >= 15
            and valuation.pe is not None
            and valuation.industry_pe is not None
            and valuation.pe < valuation.industry_pe
        ):
            points += 15
            reasons.append("Quality is strong while valuation is below industry.")

        return CategoryScore(
            category="valuation",
            weight=self.weight,
            score=min(points, 100),
            reasoning=" ".join(reasons) or "Valuation does not offer enough margin versus industry metrics.",
            input_values={
                "pe": valuation.pe,
                "industry_pe": valuation.industry_pe,
                "pb": valuation.pb,
                "peg": valuation.peg,
                "roe": latest.roe,
            },
        )
