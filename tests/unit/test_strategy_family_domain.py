"""Unit tests for strategy-family domain values."""

from __future__ import annotations

import pytest

from zorqen_research.domain.strategy_families import (
    ResearchPriority,
    StrategyFamilyStatus,
    parse_research_priority,
    parse_strategy_family_status,
    priority_sort_key,
)


def test_parse_research_priority_accepts_allowed_values() -> None:
    assert parse_research_priority("primary") is ResearchPriority.PRIMARY
    assert parse_research_priority("secondary") is ResearchPriority.SECONDARY


def test_parse_research_priority_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid research_priority"):
        parse_research_priority("experimental")


def test_parse_status_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid strategy-family status"):
        parse_strategy_family_status("archived")


def test_priority_sort_key_orders_primary_first() -> None:
    assert priority_sort_key(ResearchPriority.PRIMARY) < priority_sort_key(
        ResearchPriority.SECONDARY
    )
    assert StrategyFamilyStatus.ACTIVE.value == "active"
