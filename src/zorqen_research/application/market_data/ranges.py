"""Import range alignment and candle-count estimation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


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
        minutes = int(timeframe_duration(timeframe).total_seconds() // 60)
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
