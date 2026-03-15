from fastapi import APIRouter

from mangai_api.models.common import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="mangai-api", version="0.1.0")

