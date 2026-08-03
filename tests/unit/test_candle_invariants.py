"""Canonical candle UTC and finite-decimal invariant tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from zorqen_research.domain.candles import Candle, parse_decimal


def _valid_kwargs(**overrides: object) -> dict[str, object]:
    open_time = datetime(2026, 6, 1, tzinfo=UTC)
    close_time = open_time + timedelta(hours=1) - timedelta(milliseconds=1)
    base: dict[str, object] = {
        "open_time": open_time,
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("90"),
        "close": Decimal("105"),
        "volume": Decimal("1"),
        "close_time": close_time,
        "quote_asset_volume": Decimal("100"),
        "trade_count": 1,
        "taker_buy_base_volume": Decimal("0.5"),
        "taker_buy_quote_volume": Decimal("50"),
    }
    base.update(overrides)
    return base


def test_utc_timestamps_accepted() -> None:
    candle = Candle(**_valid_kwargs())  # type: ignore[arg-type]
    assert candle.open_time.utcoffset() == timedelta(0)
    assert candle.close_time.utcoffset() == timedelta(0)


def test_naive_timestamps_rejected() -> None:
    naive = datetime(2026, 6, 1)
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        Candle(**_valid_kwargs(open_time=naive))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        Candle(**_valid_kwargs(close_time=naive))  # type: ignore[arg-type]


def test_nonzero_offset_timestamps_rejected() -> None:
    offset = timezone(timedelta(hours=5))
    open_local = datetime(2026, 6, 1, 5, tzinfo=offset)
    close_local = datetime(2026, 6, 1, 5, 59, 59, 999000, tzinfo=offset)
    with pytest.raises(ValueError, match="zero UTC offset"):
        Candle(**_valid_kwargs(open_time=open_local))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="zero UTC offset"):
        Candle(**_valid_kwargs(close_time=close_local))  # type: ignore[arg-type]


def test_close_before_open_rejected() -> None:
    open_time = datetime(2026, 6, 1, 1, tzinfo=UTC)
    close_time = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="close_time"):
        Candle(**_valid_kwargs(open_time=open_time, close_time=close_time))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field",
    [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ],
)
@pytest.mark.parametrize(
    "bad",
    [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_candle_rejects_nonfinite_decimals(field: str, bad: Decimal) -> None:
    overrides = {field: bad}
    # Keep OHLC consistent when mutating high/low/open/close.
    if field == "high":
        overrides["open"] = Decimal("1")
        overrides["close"] = Decimal("1")
        overrides["low"] = Decimal("1")
    if field == "low":
        overrides["open"] = Decimal("1")
        overrides["close"] = Decimal("1")
        overrides["high"] = Decimal("1")
    with pytest.raises(ValueError, match="finite"):
        Candle(**_valid_kwargs(**overrides))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    ["NaN", "sNaN", "Infinity", "-Infinity", Decimal("NaN"), Decimal("Infinity")],
)
def test_parse_decimal_rejects_nonfinite(bad: object) -> None:
    with pytest.raises(ValueError, match="finite"):
        parse_decimal(bad, field="open")


def test_parse_decimal_preserves_finite_values() -> None:
    assert parse_decimal("1.50", field="open") == Decimal("1.50")
    assert parse_decimal(3, field="volume") == Decimal(3)


@pytest.mark.parametrize("bad", [False, True, 1.5, Decimal("1"), "1"])
def test_trade_count_rejects_non_integers(bad: object) -> None:
    with pytest.raises(TypeError, match="trade_count must be an integer"):
        Candle(**_valid_kwargs(trade_count=bad))  # type: ignore[arg-type]


def test_trade_count_rejects_negative_integer() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Candle(**_valid_kwargs(trade_count=-1))  # type: ignore[arg-type]


@pytest.mark.parametrize("good", [0, 1, 42])
def test_trade_count_accepts_non_negative_integers(good: int) -> None:
    candle = Candle(**_valid_kwargs(trade_count=good))  # type: ignore[arg-type]
    assert candle.trade_count == good
