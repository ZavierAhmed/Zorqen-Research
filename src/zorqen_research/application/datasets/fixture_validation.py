"""Candle fixture structural validation (no network, no resampling)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

REQUIRED_FIELDS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True, slots=True)
class CandleRow:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class FixtureValidationResult:
    rows: tuple[CandleRow, ...]
    row_count: int
    minimum_open_time: datetime
    maximum_open_time: datetime
    summary: dict[str, Any]


def _parse_utc_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        msg = f"open_time must be timezone-aware UTC: {value!r}"
        raise ValueError(msg)
    return parsed.astimezone(UTC)


def _parse_decimal(field: str, value: str) -> Decimal:
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        msg = f"{field} must be numeric: {value!r}"
        raise ValueError(msg) from exc
    return number


def validate_fixture_csv(raw: bytes) -> FixtureValidationResult:
    """Validate a small deterministic candle CSV fixture."""
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        msg = "Fixture CSV is missing a header row"
        raise ValueError(msg)
    missing = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
    if missing:
        msg = f"Fixture CSV missing required fields: {missing}"
        raise ValueError(msg)

    candles: list[CandleRow] = []
    seen_times: set[datetime] = set()
    for index, row in enumerate(reader, start=2):
        open_time = _parse_utc_timestamp(row["open_time"])
        if open_time in seen_times:
            msg = f"Duplicate open_time at CSV line {index}: {open_time.isoformat()}"
            raise ValueError(msg)
        seen_times.add(open_time)

        open_ = _parse_decimal("open", row["open"])
        high = _parse_decimal("high", row["high"])
        low = _parse_decimal("low", row["low"])
        close = _parse_decimal("close", row["close"])
        volume = _parse_decimal("volume", row["volume"])

        if high < max(open_, close, low):
            msg = f"high must be >= max(open, close, low) at CSV line {index}"
            raise ValueError(msg)
        if low > min(open_, close, high):
            msg = f"low must be <= min(open, close, high) at CSV line {index}"
            raise ValueError(msg)
        if volume < 0:
            msg = f"volume must be non-negative at CSV line {index}"
            raise ValueError(msg)

        candles.append(
            CandleRow(
                open_time=open_time,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    if not candles:
        msg = "Fixture CSV contains no candle rows"
        raise ValueError(msg)

    for previous, current in zip(candles, candles[1:], strict=False):
        if current.open_time <= previous.open_time:
            msg = "open_time values must be strictly increasing"
            raise ValueError(msg)

    summary = {
        "checks": [
            "required_fields",
            "ordered_open_times",
            "unique_open_times",
            "numeric_ohlc",
            "high_low_bounds",
            "non_negative_volume",
        ],
        "passed": True,
        "row_count": len(candles),
        "symbol": "BTCUSDT",
        "timeframe": "1h",
    }
    return FixtureValidationResult(
        rows=tuple(candles),
        row_count=len(candles),
        minimum_open_time=candles[0].open_time,
        maximum_open_time=candles[-1].open_time,
        summary=summary,
    )
