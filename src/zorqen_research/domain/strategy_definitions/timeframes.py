"""Timeframe requirement models for strategy definitions."""

from __future__ import annotations

from dataclasses import dataclass

from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import MAX_WARMUP_BARS
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def _require_warmup_bars(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be a real int"
        raise StrategyDefinitionValidationError(msg)
    if value < 0:
        msg = f"{field} must be greater than or equal to zero"
        raise StrategyDefinitionValidationError(msg)
    if value > MAX_WARMUP_BARS:
        msg = f"{field} exceeds maximum {MAX_WARMUP_BARS}"
        raise StrategyDefinitionValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class TimeframeRequirement:
    timeframe: Timeframe
    warmup_bars: int

    def __post_init__(self) -> None:
        if not isinstance(self.timeframe, Timeframe):
            msg = "timeframe must be a Timeframe"
            raise StrategyDefinitionValidationError(msg)
        _require_warmup_bars(self.warmup_bars, field="warmup_bars")


def require_canonical_context_requirements(
    requirements: object,
    *,
    execution_timeframe: Timeframe,
) -> tuple[TimeframeRequirement, ...]:
    if not isinstance(requirements, tuple):
        msg = "context_requirements must be an immutable tuple"
        raise StrategyDefinitionValidationError(msg)
    out: list[TimeframeRequirement] = []
    seen: set[Timeframe] = set()
    for item in requirements:
        if not isinstance(item, TimeframeRequirement):
            msg = "context_requirements must contain TimeframeRequirement values"
            raise StrategyDefinitionValidationError(msg)
        if item.timeframe is execution_timeframe:
            msg = "execution timeframe cannot also appear as a context timeframe"
            raise StrategyDefinitionValidationError(msg)
        if item.timeframe in seen:
            msg = f"duplicate context timeframe: {item.timeframe.value}"
            raise StrategyDefinitionValidationError(msg)
        seen.add(item.timeframe)
        out.append(item)
    expected = tuple(sorted(out, key=lambda req: timeframe_duration(req.timeframe)))
    if tuple(out) != expected:
        msg = "context_requirements must be ordered by ascending timeframe duration"
        raise StrategyDefinitionValidationError(msg)
    return expected
