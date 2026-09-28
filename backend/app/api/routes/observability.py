from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_observability_service
from app.schemas.observability import FeedbackRequest, MetricsResponse, TraceResponse
from app.services.observability_service import ObservabilityService

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
) -> MetricsResponse:
    return service.get_metrics()


@router.get("/traces", response_model=list[TraceResponse])
async def list_traces(
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[TraceResponse]:
    return service.list_traces(limit)


@router.get("/traces/{request_id}", response_model=TraceResponse)
async def get_trace(
    request_id: str,
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
) -> TraceResponse:
    trace = service.get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def create_feedback(
    feedback: FeedbackRequest,
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
) -> Response:
    if not service.add_feedback(feedback):
        raise HTTPException(status_code=404, detail="Trace not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
