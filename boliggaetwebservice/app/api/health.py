from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_health_service
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/health", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}})
async def get_health(
    response: Response, service: Annotated[HealthService, Depends(get_health_service)]
) -> HealthResponse:
    if await service.is_healthy():
        return HealthResponse(status="ok")
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="unavailable")
