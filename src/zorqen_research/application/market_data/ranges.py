"""Import range alignment and candle-count estimation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from zorqen_research.domain.timeframes import (
    Timeframe,
    align_floor,
    assert_aligned,
    ensure_utc,
    is_aligned,
    timeframe_duration,
)

__all__ = [
    "ImportRange",
    "align_floor",
    "assert_aligned",
    "current_open_boundary",
    "ensure_utc",
    "estimate_candle_count",
    "is_aligned",
    "parse_import_range",
]


@dataclass(frozen=True, slots=True)
class ImportRange:
    """Half-open UTC import interval [start, end)."""

    start: datetime
    end: datetime
    timeframe: Timeframe

    @property
    def duration(self) -> timedelta:
        return timeframe_duration(self.timeframe)

    @property
    def expected_candle_count(self) -> int:
        delta = self.end - self.start
        step = self.duration
        if delta % step != timedelta(0):
            msg = "Import range length must be an exact multiple of the timeframe"
            raise ValueError(msg)
        return int(delta / step)


def current_open_boundary(now: datetime, timeframe: Timeframe) -> datetime:
    """Return the open_time of the currently forming candle at `now`."""
    return align_floor(ensure_utc(now, field="now"), timeframe)


def parse_import_range(
    *,
    start: datetime,
    end: datetime,
    timeframe: Timeframe,
    now: datetime | None = None,
) -> ImportRange:
    """
    Validate a half-open [start, end) import range.

    Rejects misaligned bounds, inverted ranges, and ranges that would include
    the currently open candle.
    """
    start_utc = assert_aligned(start, timeframe, field="start")
    end_utc = assert_aligned(end, timeframe, field="end")
    if not start_utc < end_utc:
        msg = "start must be strictly less than end"
        raise ValueError(msg)
    clock = ensure_utc(now or datetime.now(UTC), field="now")
    open_boundary = current_open_boundary(clock, timeframe)
    if end_utc > open_boundary:
        msg = (
            "end would include the currently open candle; "
            f"use an end <= {open_boundary.isoformat()}"
        )
        raise ValueError(msg)
    return ImportRange(start=start_utc, end=end_utc, timeframe=timeframe)


def estimate_candle_count(start: datetime, end: datetime, timeframe: Timeframe) -> int:
    """Estimate candles for an aligned half-open range without open-candle checks."""
    start_utc = assert_aligned(start, timeframe, field="start")
    end_utc = assert_aligned(end, timeframe, field="end")
    if not start_utc < end_utc:
        msg = "start must be strictly less than end"
        raise ValueError(msg)
    return ImportRange(start=start_utc, end=end_utc, timeframe=timeframe).expected_candle_count
