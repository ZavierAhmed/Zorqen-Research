"""Candle resampling validation, buckets, and aggregation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zorqen_research.application.market_data.goldens import build_source_series, make_candle
from zorqen_research.application.market_data.resampling import resample
from zorqen_research.application.market_data.serialization import (
    format_canonical_decimal,
    serialize_candles_csv,
)
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def test_empty_and_mutable_source_rejected() -> None:
    with pytest.raises(ResamplingValidationError, match="non-empty"):
        resample((), symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    source = list(build_source_series(start=START, timeframe=Timeframe.M1, count=5))
    with pytest.raises(ResamplingValidationError, match="tuple"):
        resample(source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)  # type: ignore[arg-type]


def test_non_candle_duplicate_gap_order() -> None:
    good = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    with pytest.raises(ResamplingValidationError, match="Candle"):
        resample(
            (good[0], "x", good[2], good[3], good[4]),  # type: ignore[arg-type]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )
    dup = (good[0], good[0], good[2], good[3], good[4])
    with pytest.raises(ResamplingValidationError):
        resample(dup, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    swapped = (good[0], good[2], good[1], good[3], good[4])
    with pytest.raises(ResamplingValidationError):
        resample(swapped, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    gapped = (good[0], good[1], good[3], good[4], good[2])
    with pytest.raises(ResamplingValidationError):
        resample(gapped, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)


def test_misaligned_open_and_invalid_close() -> None:
    bad_open = make_candle(
        START + timedelta(minutes=1),
        timeframe=Timeframe.M5,
        open=Decimal("1"),
        high=Decimal("2"),
        low=Decimal("1"),
        close=Decimal("1.5"),
    )
    # Force M1 series starting misaligned for M5 target boundary via 00:01 start
    source = build_source_series(
        start=START + timedelta(minutes=1), timeframe=Timeframe.M1, count=5
    )
    with pytest.raises(ResamplingValidationError, match="boundary"):
        resample(source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    good = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    broken = list(good)
    broken[0] = make_candle(
        START,
        timeframe=Timeframe.M1,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
    )
    # Corrupt close_time via object replace — Candle is frozen; rebuild wrong close manually
    from zorqen_research.domain.candles import Candle

    wrong = Candle(
        open_time=START,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("1"),
        close_time=START + timedelta(minutes=1),  # missing -1ms
        quote_asset_volume=Decimal("10"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.5"),
        taker_buy_quote_volume=Decimal("5"),
    )
    with pytest.raises(ResamplingValidationError, match="close_time"):
        resample(
            (wrong, *good[1:]),
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )
    _ = bad_open


def test_source_hash_mismatch_and_input_unchanged() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    before = serialize_candles_csv(source)
    with pytest.raises(ResamplingValidationError, match="hash"):
        resample(
            source,
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            expected_source_sha256="ab" * 32,
        )
    assert serialize_candles_csv(source) == before


def test_partial_buckets_and_missing_child() -> None:
    with pytest.raises(ResamplingValidationError, match="divisible"):
        resample(
            build_source_series(start=START, timeframe=Timeframe.M1, count=9),
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )
    # Tuesday weekly start
    tuesday = datetime(2024, 1, 2, tzinfo=UTC)
    with pytest.raises(ResamplingValidationError, match="boundary"):
        resample(
            build_source_series(start=tuesday, timeframe=Timeframe.D1, count=7),
            symbol=SYM,
            source_timeframe=Timeframe.D1,
            target_timeframe=Timeframe.W1,
        )
    # 1h → 4h starting 02:00
    with pytest.raises(ResamplingValidationError, match="boundary"):
        resample(
            build_source_series(start=START + timedelta(hours=2), timeframe=Timeframe.H1, count=4),
            symbol=SYM,
            source_timeframe=Timeframe.H1,
            target_timeframe=Timeframe.H4,
        )


def test_exact_aggregation_and_signed_zero_and_large_trades() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    series = resample(
        source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )
    candle = series.candles[0]
    assert candle.open == Decimal("100")
    assert candle.high == Decimal("105")
    assert candle.low == Decimal("99")
    assert candle.close == Decimal("104.5")
    assert candle.volume == Decimal("15")
    assert candle.trade_count == 15
    assert series.target_candle_sha256 == sha256_hex(serialize_candles_csv(series.candles))

    zero_child = make_candle(
        START,
        timeframe=Timeframe.M1,
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        volume=Decimal("-0"),
        quote_asset_volume=Decimal("-0"),
        trade_count=10**18,
        taker_buy_base_volume=Decimal("-0"),
        taker_buy_quote_volume=Decimal("-0"),
    )
    children = []
    for index in range(5):
        if index == 0:
            children.append(zero_child)
        else:
            children.append(
                make_candle(
                    START + timedelta(minutes=index),
                    timeframe=Timeframe.M1,
                    open=Decimal("1"),
                    high=Decimal("1"),
                    low=Decimal("1"),
                    close=Decimal("1"),
                    volume=Decimal("0"),
                    quote_asset_volume=Decimal("0"),
                    trade_count=10**18,
                    taker_buy_base_volume=Decimal("0"),
                    taker_buy_quote_volume=Decimal("0"),
                )
            )
    big = resample(
        tuple(children),
        symbol=SYM,
        source_timeframe=Timeframe.M1,
        target_timeframe=Timeframe.M5,
    )
    assert big.candles[0].trade_count == 5 * (10**18)
    assert format_canonical_decimal(Decimal("-0")) == "0"
    assert b",0," in serialize_candles_csv(big.candles)


def test_determinism_and_hash_sensitivity() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=10)
    a = resample(source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    b = resample(source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5)
    assert serialize_candles_csv(a.candles) == serialize_candles_csv(b.candles)
    assert a.target_candle_sha256 == b.target_candle_sha256
    tweaked = list(source)
    tweaked[-1] = make_candle(
        tweaked[-1].open_time,
        timeframe=Timeframe.M1,
        open=Decimal("999"),
        high=Decimal("1000"),
        low=Decimal("998"),
        close=Decimal("999.5"),
        volume=Decimal("9"),
        quote_asset_volume=Decimal("9"),
        trade_count=9,
        taker_buy_base_volume=Decimal("0.5"),
        taker_buy_quote_volume=Decimal("5"),
    )
    c = resample(
        tuple(tweaked), symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )
    assert c.target_candle_sha256 != a.target_candle_sha256
