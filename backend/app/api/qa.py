from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.qa import AnswerRequest, AnswerResponse
from ..services.llm_service import AnswerService
from .deps import get_answer_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/answer", response_model=AnswerResponse)
def answer_question(
    payload: AnswerRequest,
    service: AnswerService = Depends(get_answer_service),
) -> AnswerResponse:
    return service.answer(payload)
