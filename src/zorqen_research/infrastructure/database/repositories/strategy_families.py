"""Strategy-family repository — maps ORM rows to domain objects."""

from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.domain.strategy_families import (
    ResearchPriority,
    StrategyFamily,
    StrategyFamilyStatus,
    parse_research_priority,
    parse_strategy_family_status,
)
from zorqen_research.infrastructure.database.models.strategy_family import StrategyFamilyModel


def _to_domain(row: StrategyFamilyModel) -> StrategyFamily:
    return StrategyFamily(
        id=row.id,
        code=row.code,
        display_name=row.display_name,
        description=row.description,
        research_priority=parse_research_priority(row.research_priority),
        status=parse_strategy_family_status(row.status),
    )


class StrategyFamilyRepository:
    """Read-focused repository for the strategy-family registry."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[StrategyFamily]:
        """Return active families with primary before secondary, then by code."""
        priority_order = case(
            (StrategyFamilyModel.research_priority == ResearchPriority.PRIMARY.value, 0),
            (StrategyFamilyModel.research_priority == ResearchPriority.SECONDARY.value, 1),
            else_=2,
        )
        stmt = (
            select(StrategyFamilyModel)
            .where(StrategyFamilyModel.status == StrategyFamilyStatus.ACTIVE.value)
            .order_by(priority_order, StrategyFamilyModel.code.asc())
        )
        result = await self._session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]

    async def get_active_by_code(self, code: str) -> StrategyFamily | None:
        """Return an active family by canonical code, or None."""
        stmt = select(StrategyFamilyModel).where(
            StrategyFamilyModel.code == code,
            StrategyFamilyModel.status == StrategyFamilyStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_domain(row)
