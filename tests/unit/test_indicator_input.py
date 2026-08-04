"""IndicatorInput factory and integrity tests."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import (
    SYMBOL,
    TIMEFRAME,
    candle_series,
    make_candle,
    utc,
)
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def test_indicator_input_accepts_exact_valid_tuple() -> None:
    candles = candle_series(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
    )
    assert indicator_input.candle_count == 3
    assert indicator_input.minimum_open_time == candles[0].open_time
    assert indicator_input.maximum_open_time == candles[-1].open_time
    assert indicator_input.candle_sha256 == hash_candle_tuple(candles)
    assert len(indicator_input.input_hash) == 64


def test_indicator_input_rejects_empty_tuple() -> None:
    with pytest.raises(IndicatorValidationError, match="non-empty"):
        IndicatorInput.from_verified(symbol=SYMBOL, timeframe=TIMEFRAME, candles=())


def test_indicator_input_rejects_mutable_list() -> None:
    candles = list(candle_series((("10", "11", "9", "10"), ("11", "12", "10", "11"))))
    with pytest.raises(IndicatorValidationError, match="exact tuple"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=candles,  # type: ignore[arg-type]
        )


def test_indicator_input_rejects_non_candle_item() -> None:
    candles = candle_series((("10", "11", "9", "10"), ("11", "12", "10", "11")))
    bad = (candles[0], "not-a-candle")  # type: ignore[assignment]
    with pytest.raises(IndicatorValidationError, match="exact Candle"):
        IndicatorInput.from_verified(symbol=SYMBOL, timeframe=TIMEFRAME, candles=bad)


def test_indicator_input_rejects_duplicate_candle() -> None:
    first = make_candle(utc(2024, 1, 1), open="10", high="11", low="9", close="10")
    with pytest.raises(IndicatorValidationError, match="duplicates"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=(first, first),
        )


def test_indicator_input_rejects_out_of_order_candle() -> None:
    later = make_candle(utc(2024, 1, 1, 0, 1), open="11", high="12", low="10", close="11")
    earlier = make_candle(utc(2024, 1, 1), open="10", high="11", low="9", close="10")
    with pytest.raises(IndicatorValidationError, match="out of order"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=(later, earlier),
        )


def test_indicator_input_rejects_gap() -> None:
    first = make_candle(utc(2024, 1, 1), open="10", high="11", low="9", close="10")
    skipped = make_candle(utc(2024, 1, 1, 0, 2), open="12", high="13", low="11", close="12")
    with pytest.raises(IndicatorValidationError, match="gap"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=(first, skipped),
        )


def test_indicator_input_rejects_misaligned_candle() -> None:
    from zorqen_research.domain.candles import Candle

    open_time = utc(2024, 1, 1, 0, 0) + timedelta(seconds=30)
    candle = Candle(
        open_time=open_time,
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10"),
        volume=Decimal("1"),
        close_time=open_time + timeframe_duration(TIMEFRAME) - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("10"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.4"),
        taker_buy_quote_volume=Decimal("4"),
    )
    with pytest.raises(IndicatorValidationError, match="misaligned"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=(candle,),
        )


def test_indicator_input_rejects_invalid_timeframe_type() -> None:
    candles = candle_series((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="timeframe"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe="1m",  # type: ignore[arg-type]
            candles=candles,
        )


def test_indicator_input_rejects_invalid_symbol_type() -> None:
    candles = candle_series((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="symbol"):
        IndicatorInput.from_verified(
            symbol="BTCUSDT",  # type: ignore[arg-type]
            timeframe=TIMEFRAME,
            candles=candles,
        )


def test_indicator_input_rejects_direct_forged_construction() -> None:
    with pytest.raises(IndicatorValidationError, match="from_verified"):
        IndicatorInput(  # type: ignore[call-arg]
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=candle_series((("10", "11", "9", "10"),)),
            candle_count=1,
            minimum_open_time=utc(2024, 1, 1),
            maximum_open_time=utc(2024, 1, 1),
            candle_sha256="0" * 64,
            input_hash="0" * 64,
        )


def test_indicator_input_computed_hash_and_bounds() -> None:
    candles = candle_series(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    a = IndicatorInput.from_verified(symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles)
    b = IndicatorInput.from_verified(symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles)
    assert a.candle_sha256 == b.candle_sha256
    assert a.input_hash == b.input_hash
    assert a.symbol == Symbol(value="BTCUSDT")
    assert a.timeframe == Timeframe.M1
