"""Canonical timeframe value objects (metadata only — no resampling)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum


class Timeframe(StrEnum):
    """Supported research timeframes (canonical lowercase)."""

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


_DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M3: timedelta(minutes=3),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.M30: timedelta(minutes=30),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(weeks=1),
}


@dataclass(frozen=True, slots=True)
class TimeframeSpec:
    """Timeframe with deterministic UTC duration mapping."""

    value: Timeframe

    @property
    def duration(self) -> timedelta:
        return _DURATIONS[self.value]

    def __str__(self) -> str:
        return self.value.value


def parse_timeframe(value: str) -> TimeframeSpec:
    """
    Parse a canonical timeframe.

    Rejects unsupported aliases such as 60m, H1, 1D, or 1W.
    """
    normalized = value.strip()
    if normalized != normalized.lower():
        msg = f"Unsupported timeframe alias (use lowercase canonical form): {value!r}"
        raise ValueError(msg)
    try:
        timeframe = Timeframe(normalized)
    except ValueError as exc:
        msg = f"Unsupported timeframe: {value!r}"
        raise ValueError(msg) from exc
    return TimeframeSpec(value=timeframe)


def timeframe_duration(timeframe: Timeframe | TimeframeSpec | str) -> timedelta:
    """Return the deterministic duration for a timeframe."""
    if isinstance(timeframe, TimeframeSpec):
        return timeframe.duration
    if isinstance(timeframe, Timeframe):
        return _DURATIONS[timeframe]
    return parse_timeframe(timeframe).duration
