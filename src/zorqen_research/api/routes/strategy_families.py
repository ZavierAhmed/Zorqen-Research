"""Read-only strategy-family API routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.api.dependencies import get_db_session
from zorqen_research.api.schemas.strategy_families import (
    ErrorResponse,
    StrategyFamilyListResponse,
    StrategyFamilyResponse,
    strategy_family_to_response,
)
from zorqen_research.application.strategy_families.service import (
    StrategyFamilyNotFoundError,
    StrategyFamilyService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strategy-families", tags=["strategy-families"])


def get_strategy_family_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StrategyFamilyService:
    return StrategyFamilyService(session)


@router.get(
    "",
    response_model=StrategyFamilyListResponse,
    summary="List active strategy families",
)
async def list_strategy_families(
    service: Annotated[StrategyFamilyService, Depends(get_strategy_family_service)],
) -> StrategyFamilyListResponse:
    """Return active strategy families with primary before secondary."""
    try:
        families = await service.list_active()
    except Exception:
        logger.exception("Failed to list strategy families")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Strategy family registry is temporarily unavailable.",
        ) from None

    items = [strategy_family_to_response(family) for family in families]
    return StrategyFamilyListResponse(items=items, count=len(items))


@router.get(
    "/{code}",
    response_model=StrategyFamilyResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Get an active strategy family by code",
)
async def get_strategy_family(
    code: str,
    service: Annotated[StrategyFamilyService, Depends(get_strategy_family_service)],
) -> StrategyFamilyResponse:
    """Return one active family by canonical code."""
    try:
        family = await service.get_active_by_code(code)
    except StrategyFamilyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy family not found.",
        ) from None
    except Exception:
        logger.exception("Failed to load strategy family code=%s", code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Strategy family registry is temporarily unavailable.",
        ) from None

    return strategy_family_to_response(family)
