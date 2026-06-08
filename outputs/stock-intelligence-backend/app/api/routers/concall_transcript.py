from fastapi import APIRouter, Depends

from app.api.dependencies import get_concall_transcript_service
from app.application.schemas.concall_transcript import ConcallTranscriptRequest, ConcallTranscriptResponse
from app.application.services.concall_transcript_service import ConcallTranscriptService

router = APIRouter(tags=["concall-transcript"])


@router.post("/concall/analyze", response_model=ConcallTranscriptResponse)
def analyze_concall_transcript(
    request: ConcallTranscriptRequest,
    service: ConcallTranscriptService = Depends(get_concall_transcript_service),
) -> ConcallTranscriptResponse:
    result = service.analyze_input(request.transcript, request.transcript_url)
    return ConcallTranscriptResponse(**result.to_api_dict())
