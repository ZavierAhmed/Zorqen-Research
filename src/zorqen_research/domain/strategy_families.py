"""Strategy-family domain values (metadata only — no executable definitions)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

# Stable seed identifiers — identical on every installation (Milestone 0.2).
ADAPTIVE_MTF_TREND_BREAKOUT_ID = UUID("a1b2c3d4-e5f6-4789-a012-3456789abc01")
SUPPORT_RESISTANCE_ID = UUID("a1b2c3d4-e5f6-4789-a012-3456789abc02")

ADAPTIVE_MTF_TREND_BREAKOUT_CODE = "adaptive_mtf_trend_breakout"
SUPPORT_RESISTANCE_CODE = "support_resistance"

# Exact seeded pairs. Runtime-immutable mapping (no third family).
_SEEDED_FAMILY_PAIR_ITEMS: tuple[tuple[UUID, str], ...] = (
    (ADAPTIVE_MTF_TREND_BREAKOUT_ID, ADAPTIVE_MTF_TREND_BREAKOUT_CODE),
    (SUPPORT_RESISTANCE_ID, SUPPORT_RESISTANCE_CODE),
)
SEEDED_FAMILY_PAIRS: Mapping[UUID, str] = MappingProxyType(dict(_SEEDED_FAMILY_PAIR_ITEMS))


def require_seeded_family_pair(*, family_id: UUID, family_code: str) -> None:
    """
    Require ``family_id`` and ``family_code`` to be one exact seeded pair.

    Raises ``ValueError`` when either side is unknown or the pair does not match.
    """
    expected = SEEDED_FAMILY_PAIRS.get(family_id)
    if expected is None:
        msg = f"Unknown strategy family_id: {family_id}"
        raise ValueError(msg)
    if family_code not in SEEDED_FAMILY_PAIRS.values():
        msg = f"Unknown strategy family_code: {family_code!r}"
        raise ValueError(msg)
    if expected != family_code:
        msg = (
            f"Strategy family_id/code mismatch: id={family_id} "
            f"expects code={expected!r}, got {family_code!r}"
        )
        raise ValueError(msg)


class ResearchPriority(StrEnum):
    """Allowed research_priority values for strategy families."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class StrategyFamilyStatus(StrEnum):
    """Allowed status values for strategy families."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class StrategyFamily:
    """Metadata describing a supported research family (not executable logic)."""

    id: UUID
    code: str
    display_name: str
    description: str
    research_priority: ResearchPriority
    status: StrategyFamilyStatus


def parse_research_priority(value: str) -> ResearchPriority:
    """Parse and validate a research priority string."""
    try:
        return ResearchPriority(value)
    except ValueError as exc:
        msg = f"Invalid research_priority: {value!r}"
        raise ValueError(msg) from exc


def parse_strategy_family_status(value: str) -> StrategyFamilyStatus:
    """Parse and validate a strategy-family status string."""
    try:
        return StrategyFamilyStatus(value)
    except ValueError as exc:
        msg = f"Invalid strategy-family status: {value!r}"
        raise ValueError(msg) from exc


def priority_sort_key(priority: ResearchPriority) -> int:
    """Return a deterministic sort key: primary before secondary."""
    if priority is ResearchPriority.PRIMARY:
        return 0
    if priority is ResearchPriority.SECONDARY:
        return 1
    return 99
