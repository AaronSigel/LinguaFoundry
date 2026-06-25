"""Health endpoints for service readiness checks."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response schema for the health endpoint."""

    status: str
    service: str
    environment: str
    domain: str


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
) -> HealthResponse:
    """Return basic process health and environment metadata."""

    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
        domain="ready",
    )
