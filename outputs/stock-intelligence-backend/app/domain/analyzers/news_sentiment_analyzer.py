from app.domain.entities import CategoryScore, NewsSentiment


class NewsSentimentAnalyzer:
    weight = 10

    def analyze(self, sentiment: NewsSentiment | None) -> CategoryScore:
        if sentiment is None:
            return CategoryScore(
                category="news_sentiment",
                weight=self.weight,
                score=50,
                reasoning="News sentiment data is unavailable; assigning neutral score.",
                input_values={"status": "not_available"},
            )

        total = sentiment.positive_count + sentiment.neutral_count + sentiment.negative_count
        if total == 0:
            score = 50
        else:
            score = round(
                (
                    sentiment.positive_count * 100
                    + sentiment.neutral_count * 50
                    + sentiment.negative_count * 0
                )
                / total
            )

        if sentiment.average_sentiment_score:
            score = round((score + ((sentiment.average_sentiment_score + 1) / 2 * 100)) / 2)

        return CategoryScore(
            category="news_sentiment",
            weight=self.weight,
            score=max(0, min(score, 100)),
            reasoning="News score is based on positive, neutral, and negative news distribution.",
            input_values={
                "positive_count": sentiment.positive_count,
                "neutral_count": sentiment.neutral_count,
                "negative_count": sentiment.negative_count,
                "average_sentiment_score": sentiment.average_sentiment_score,
            },
        )
