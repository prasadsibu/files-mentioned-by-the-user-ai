from app.application.services.news_sentiment_service import NewsSentimentService


def analyze_news_sentiment(stock_name: str) -> dict[str, int]:
    service = NewsSentimentService()
    return service.analyze(stock_name).to_api_dict()


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Analyze recent stock news sentiment with FinBERT.")
    parser.add_argument("stock", help="Stock name or symbol, for example TCS")
    args = parser.parse_args()

    print(json.dumps(analyze_news_sentiment(args.stock), indent=2))
