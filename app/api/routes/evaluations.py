from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_evaluation_service
from app.schemas.evaluation import EvaluationReport
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("/evaluations", response_model=EvaluationReport)
async def create_evaluation(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationReport:
    return await service.create_report()
