from fastapi import APIRouter, Depends, status
import traceback

from app.api.dependencies import get_analysis_service
from app.application.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.application.services.analysis_service import AnalysisService

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_stock(
    request: AnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalyzeResponse:
    try:
        return service.analyze(request)
    except Exception:
        traceback.print_exc()
        raise
