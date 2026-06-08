from fastapi import APIRouter, Depends

from app.api.dependencies import get_news_sentiment_service
from app.application.schemas.news_sentiment import NewsSentimentRequest, NewsSentimentResponse
from app.application.services.news_sentiment_service import NewsSentimentService

router = APIRouter(tags=["news-sentiment"])


@router.post("/news-sentiment", response_model=NewsSentimentResponse)
def analyze_news_sentiment(
    request: NewsSentimentRequest,
    service: NewsSentimentService = Depends(get_news_sentiment_service),
) -> NewsSentimentResponse:
    result = service.analyze(request.stock)
    return NewsSentimentResponse(**result.to_api_dict())
