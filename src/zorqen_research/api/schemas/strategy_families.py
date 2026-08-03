"""Strategy-family API schemas (not SQLAlchemy models)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zorqen_research.domain.strategy_families import StrategyFamily


class StrategyFamilyResponse(BaseModel):
    """Public strategy-family metadata response."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    code: str
    display_name: str
    description: str
    research_priority: Literal["primary", "secondary"]
    status: Literal["active", "inactive"]


class StrategyFamilyListResponse(BaseModel):
    """List wrapper for strategy families."""

    items: list[StrategyFamilyResponse] = Field(default_factory=list)
    count: int


class ErrorResponse(BaseModel):
    """Sanitized API error body."""

    detail: str


def strategy_family_to_response(family: StrategyFamily) -> StrategyFamilyResponse:
    """Map a domain entity to an API response model."""
    return StrategyFamilyResponse(
        id=family.id,
        code=family.code,
        display_name=family.display_name,
        description=family.description,
        research_priority=family.research_priority.value,
        status=family.status.value,
    )
