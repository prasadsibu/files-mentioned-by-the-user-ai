from app.domain.entities import CategoryScore, NewsSentiment


class NewsSentimentAnalyzer:
    weight = 10

    def analyze(self, sentiment: NewsSentiment | None) -> CategoryScore:
        if sentiment is None:
            return CategoryScore(
                category="news_sentiment",
                weight=self.weight,
                score=50,
                reasoning="No news articles were collected for this run; assigning neutral news recommendation.",
                input_values={"status": "not_available", "news_recommendation": "WATCH"},
            )

        total = sentiment.positive_count + sentiment.neutral_count + sentiment.negative_count
        if total == 0:
            return CategoryScore(
                category="news_sentiment",
                weight=self.weight,
                score=50,
                reasoning="No news articles were classified; assigning neutral news recommendation.",
                input_values={"status": "no_articles", "news_recommendation": "WATCH"},
            )

        positive_pct = sentiment.positive_percent or (sentiment.positive_count / total * 100)
        neutral_pct = sentiment.neutral_percent or (sentiment.neutral_count / total * 100)
        negative_pct = sentiment.negative_percent or (sentiment.negative_count / total * 100)

        distribution_score = positive_pct + (neutral_pct * 0.55)
        normalized_sentiment_score = max(
            0,
            min(((sentiment.average_sentiment_score + 1) / 2) * 100, 100),
        )
        confidence_score = max(0, min(sentiment.average_confidence * 100, 100))

        score = round(
            (distribution_score * 0.55)
            + (normalized_sentiment_score * 0.35)
            + (confidence_score * 0.10)
        )

        if positive_pct >= 70 and negative_pct <= 15:
            score = max(score, 80)
        if negative_pct >= 60:
            score = min(score, 30)

        score = max(0, min(score, 100))
        recommendation = self._recommendation(score)
        reasoning = (
            f"News recommendation: {recommendation}. Classified {total} articles with "
            f"{positive_pct:.0f}% positive, {neutral_pct:.0f}% neutral, and {negative_pct:.0f}% negative flow; "
            f"aggregate sentiment score {round(normalized_sentiment_score)}/100 and average FinBERT confidence "
            f"{confidence_score:.0f}% were weighted into the news score."
        )

        return CategoryScore(
            category="news_sentiment",
            weight=self.weight,
            score=score,
            reasoning=reasoning,
            input_values={
                "positive_count": sentiment.positive_count,
                "neutral_count": sentiment.neutral_count,
                "negative_count": sentiment.negative_count,
                "positive_percent": round(positive_pct, 2),
                "neutral_percent": round(neutral_pct, 2),
                "negative_percent": round(negative_pct, 2),
                "average_sentiment_score": round(sentiment.average_sentiment_score, 4),
                "average_confidence": round(sentiment.average_confidence, 4),
                "news_recommendation": recommendation,
            },
        )

    @staticmethod
    def _recommendation(score: int) -> str:
        if score >= 80:
            return "BUY"
        if score >= 40:
            return "WATCH"
        return "IGNORE"
