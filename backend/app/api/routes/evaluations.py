from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_evaluation_service
from app.schemas.evaluation import EvaluationReport, EvaluationSummary
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("/evaluations", response_model=EvaluationReport)
async def create_evaluation(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationReport:
    return await service.create_report()


@router.get("/evaluations", response_model=list[EvaluationSummary])
async def list_evaluations(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[EvaluationSummary]:
    return service.history(limit)
