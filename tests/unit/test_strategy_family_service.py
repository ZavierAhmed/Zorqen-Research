"""Unit tests for strategy-family application service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from zorqen_research.application.strategy_families.service import (
    StrategyFamilyNotFoundError,
    StrategyFamilyService,
)
from zorqen_research.domain.strategy_families import (
    ResearchPriority,
    StrategyFamily,
    StrategyFamilyStatus,
)
from zorqen_research.infrastructure.database.models.strategy_family import StrategyFamilyModel


def _family(
    *,
    code: str,
    priority: ResearchPriority,
) -> StrategyFamily:
    return StrategyFamily(
        id=uuid4(),
        code=code,
        display_name=code,
        description="metadata only",
        research_priority=priority,
        status=StrategyFamilyStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_list_active_orders_primary_before_secondary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = StrategyFamilyService(MagicMock())
    monkeypatch.setattr(
        service._repo,
        "list_active",
        AsyncMock(
            return_value=[
                _family(code="support_resistance", priority=ResearchPriority.SECONDARY),
                _family(
                    code="adaptive_mtf_trend_breakout",
                    priority=ResearchPriority.PRIMARY,
                ),
            ]
        ),
    )

    result = await service.list_active()

    assert [item.code for item in result] == [
        "adaptive_mtf_trend_breakout",
        "support_resistance",
    ]
    assert not isinstance(result[0], StrategyFamilyModel)


@pytest.mark.asyncio
async def test_get_active_by_code_unknown_raises() -> None:
    service = StrategyFamilyService(MagicMock())
    service._repo.get_active_by_code = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(StrategyFamilyNotFoundError) as exc_info:
        await service.get_active_by_code("missing")

    assert exc_info.value.code == "missing"
