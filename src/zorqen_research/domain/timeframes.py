"""Canonical timeframe value objects and UTC alignment helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


def duration_milliseconds(duration: timedelta) -> int:
    """Exact millisecond length without binary floating-point ratio math."""
    return duration.days * 86_400_000 + duration.seconds * 1000 + duration.microseconds // 1000


def ensure_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise ValueError(msg)
    return value.astimezone(UTC)


def align_floor(value: datetime, timeframe: Timeframe) -> datetime:
    """Return the greatest timeframe-aligned instant <= value (UTC)."""
    utc = ensure_utc(value, field="timestamp")
    if timeframe in {
        Timeframe.M1,
        Timeframe.M3,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.M30,
        Timeframe.H1,
        Timeframe.H4,
    }:
        minutes = duration_milliseconds(timeframe_duration(timeframe)) // 60_000
        total_minutes = utc.hour * 60 + utc.minute
        floored = total_minutes - (total_minutes % minutes)
        return utc.replace(
            hour=floored // 60,
            minute=floored % 60,
            second=0,
            microsecond=0,
        )
    if timeframe is Timeframe.D1:
        return utc.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monday 00:00 UTC for 1w
    monday = utc - timedelta(days=utc.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def is_aligned(value: datetime, timeframe: Timeframe) -> bool:
    utc = ensure_utc(value, field="timestamp")
    return utc == align_floor(utc, timeframe)


def assert_aligned(value: datetime, timeframe: Timeframe, *, field: str) -> datetime:
    utc = ensure_utc(value, field=field)
    if not is_aligned(utc, timeframe):
        msg = f"{field} must align exactly to timeframe {timeframe.value}: {utc.isoformat()}"
        raise ValueError(msg)
    return utc
