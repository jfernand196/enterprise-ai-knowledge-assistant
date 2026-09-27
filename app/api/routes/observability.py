from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_observability_service
from app.schemas.observability import MetricsResponse, TraceResponse
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
) -> list[TraceResponse]:
    return service.list_traces()


@router.get("/traces/{request_id}", response_model=TraceResponse)
async def get_trace(
    request_id: str,
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
) -> TraceResponse:
    trace = service.get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
