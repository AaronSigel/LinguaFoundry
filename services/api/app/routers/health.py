"""Health endpoints for service readiness checks."""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from services.api.app.dependencies import get_domain_context

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
    domain_context: Annotated[Mapping[str, str], Depends(get_domain_context)],
) -> HealthResponse:
    """Return basic process health and environment metadata."""

    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
        domain=domain_context["status"],
    )
