"""Strategy-family application service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.domain.strategy_families import StrategyFamily, priority_sort_key
from zorqen_research.infrastructure.database.repositories.strategy_families import (
    StrategyFamilyRepository,
)


class StrategyFamilyNotFoundError(Exception):
    """Raised when an active strategy family cannot be found by code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Strategy family not found: {code}")


class StrategyFamilyService:
    """Read-only application service for strategy-family metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = StrategyFamilyRepository(session)

    async def list_active(self) -> list[StrategyFamily]:
        """Return active families in deterministic priority order."""
        families = await self._repo.list_active()
        return sorted(
            families,
            key=lambda family: (priority_sort_key(family.research_priority), family.code),
        )

    async def get_active_by_code(self, code: str) -> StrategyFamily:
        """Return one active family or raise StrategyFamilyNotFoundError."""
        family = await self._repo.get_active_by_code(code)
        if family is None:
            raise StrategyFamilyNotFoundError(code)
        return family
