"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from zorqen_research.api.dependencies import get_engine
from zorqen_research.infrastructure.database.engine import check_database_ready

router = APIRouter(prefix="/api/v1/health", tags=["health"])

SERVICE_NAME = "zorqen-research-api"


class LivenessResponse(BaseModel):
    """Liveness probe response — process is alive."""

    service: str = SERVICE_NAME
    status: Literal["healthy"] = "healthy"


class ComponentStatus(BaseModel):
    """Status of a single readiness component."""

    status: Literal["healthy", "unhealthy"]


class ReadinessComponents(BaseModel):
    """Component readiness map."""

    database: ComponentStatus


class ReadinessResponse(BaseModel):
    """Readiness probe response — dependencies are reachable."""

    service: str = SERVICE_NAME
    status: Literal["ready", "not_ready"]
    components: ReadinessComponents = Field(
        ...,
        description="Component readiness without secrets or stack traces",
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def liveness() -> LivenessResponse:
    """Return healthy while the API process is alive. Does not touch PostgreSQL."""
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_200_OK: {"model": ReadinessResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse},
    },
    summary="Readiness probe",
)
async def readiness(
    response: Response,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> ReadinessResponse:
    """Check PostgreSQL with SELECT 1. Returns 503 when the database is unavailable."""
    database_ok = await check_database_ready(engine)
    if database_ok:
        return ReadinessResponse(
            status="ready",
            components=ReadinessComponents(database=ComponentStatus(status="healthy")),
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="not_ready",
        components=ReadinessComponents(database=ComponentStatus(status="unhealthy")),
    )
