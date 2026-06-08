from app.domain.entities import CategoryScore, ShareholdingPattern


class OwnershipAnalyzer:
    weight = 10

    def analyze(self, history: list[ShareholdingPattern]) -> CategoryScore:
        ordered = history
        shareholding = ordered[-1]
        previous = ordered[-2] if len(ordered) > 1 else None
        points = 0
        reasons: list[str] = []

        if shareholding.promoter_holding > 50:
            points += 40
            reasons.append("Promoter holding is above 50%.")
        if previous is not None and shareholding.fii_holding > previous.fii_holding:
            points += 30
            reasons.append("FII holding is increasing.")
        if previous is not None and shareholding.dii_holding > previous.dii_holding:
            points += 30
            reasons.append("DII holding is increasing.")

        return CategoryScore(
            category="ownership",
            weight=self.weight,
            score=min(points, 100),
            reasoning=" ".join(reasons) or "Ownership quality is weak or insufficiently institutional.",
            input_values={
                "promoter_holding": shareholding.promoter_holding,
                "fii_holding": shareholding.fii_holding,
                "dii_holding": shareholding.dii_holding,
                "previous_fii_holding": previous.fii_holding if previous else "not_available",
                "previous_dii_holding": previous.dii_holding if previous else "not_available",
            },
        )
