from app.domain.entities import CategoryScore, FinancialMetrics, ShareholdingPattern


class RiskAnalyzer:
    weight = 10

    def analyze(
        self,
        financials: FinancialMetrics,
        previous_financials: FinancialMetrics | None,
        shareholding: ShareholdingPattern,
        auditor_resignation: bool = False,
        equity_dilution: bool = False,
    ) -> CategoryScore:
        score = 100
        reasons: list[str] = []

        if auditor_resignation:
            score -= 25
            reasons.append("Auditor resignation detected.")
        if previous_financials is not None and financials.debt_equity > previous_financials.debt_equity:
            score -= 20
            reasons.append("Debt/equity is rising.")
        if financials.free_cash_flow < 0:
            score -= 20
            reasons.append("Free cash flow is negative.")
        if equity_dilution:
            score -= 20
            reasons.append("Equity dilution detected.")
        if shareholding.pledged_shares > 0:
            score -= 15
            reasons.append("Promoter pledge is present.")

        if not reasons:
            reasons.append("No specified risk penalties detected.")

        return CategoryScore(
            category="risk",
            weight=self.weight,
            score=max(score, 0),
            reasoning=" ".join(reasons),
            input_values={
                "free_cash_flow": financials.free_cash_flow,
                "debt_equity": financials.debt_equity,
                "previous_debt_equity": previous_financials.debt_equity if previous_financials else "not_available",
                "pledged_shares": shareholding.pledged_shares,
                "auditor_resignation": str(auditor_resignation),
                "equity_dilution": str(equity_dilution),
            },
        )
