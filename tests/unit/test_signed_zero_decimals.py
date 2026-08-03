"""Signed-zero canonical decimal normalization tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zorqen_research.api.schemas.datasets import candle_to_response
from zorqen_research.application.market_data.csv_reader import parse_canonical_candles_csv
from zorqen_research.application.market_data.errors import CandlePartitionIntegrityError
from zorqen_research.application.market_data.serialization import (
    format_canonical_decimal,
    serialize_candles_csv,
)
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe

ZERO_FORMS = (
    Decimal("0"),
    Decimal("0.000"),
    Decimal("-0"),
    Decimal("-0.000"),
)


@pytest.mark.parametrize("value", ZERO_FORMS)
def test_format_canonical_decimal_signed_zero(value: Decimal) -> None:
    assert format_canonical_decimal(value) == "0"


def test_serializer_emits_identical_bytes_for_signed_zeros() -> None:
    open_time = datetime(2026, 6, 1, tzinfo=UTC)
    close_time = open_time + timedelta(hours=1) - timedelta(milliseconds=1)

    def candle(zero: Decimal) -> Candle:
        return Candle(
            open_time=open_time,
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume=zero,
            close_time=close_time,
            quote_asset_volume=zero,
            trade_count=0,
            taker_buy_base_volume=zero,
            taker_buy_quote_volume=zero,
        )

    positive = serialize_candles_csv((candle(Decimal("0")),))
    negative = serialize_candles_csv((candle(Decimal("-0")),))
    assert positive == negative
    fields = positive.decode("utf-8").rstrip("\n").split("\n")[1].split(",")
    assert fields[5] == "0"
    assert fields[7] == "0"
    assert fields[9] == "0"
    assert fields[10] == "0"


def test_api_response_emits_canonical_zero_strings() -> None:
    open_time = datetime(2026, 6, 1, tzinfo=UTC)
    candle = Candle(
        open_time=open_time,
        open=Decimal("0"),
        high=Decimal("0"),
        low=Decimal("0"),
        close=Decimal("0"),
        volume=Decimal("-0.000"),
        close_time=open_time + timedelta(hours=1) - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("0.0"),
        trade_count=0,
        taker_buy_base_volume=Decimal("-0"),
        taker_buy_quote_volume=Decimal("0.000"),
    )
    payload = candle_to_response(candle).model_dump(mode="json")
    for field in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ):
        assert payload[field] == "0"


def test_reader_rejects_signed_zero_csv_as_non_canonical() -> None:
    open_time = datetime(2026, 6, 1, tzinfo=UTC)
    candle = Candle(
        open_time=open_time,
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        volume=Decimal("0"),
        close_time=open_time + timedelta(hours=1) - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("0"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0"),
        taker_buy_quote_volume=Decimal("0"),
    )
    canonical = serialize_candles_csv((candle,))
    # Force a non-canonical signed zero into the volume field.
    header, row = canonical.decode("utf-8").rstrip("\n").split("\n")
    fields = row.split(",")
    fields[5] = "-0"
    mutated = (header + "\n" + ",".join(fields) + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError, match="reserialization"):
        parse_canonical_candles_csv(mutated, timeframe=Timeframe.H1)


def test_nonzero_values_remain_stable() -> None:
    assert format_canonical_decimal(Decimal("1.50")) == "1.5"
    assert format_canonical_decimal(Decimal("-2.50")) == "-2.5"
    assert format_canonical_decimal(Decimal("100")) == "100"
