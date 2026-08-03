"""Additional Binance schema and identity unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.helpers_binance import make_kline_row
from zorqen_research.application.market_data.import_service import build_import_dataset_name
from zorqen_research.application.market_data.ranges import estimate_candle_count, parse_import_range
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.errors import BinanceResponseError
from zorqen_research.infrastructure.binance.schemas import parse_kline_row


@pytest.mark.parametrize(
    "bad",
    [
        [],
        [1],
        "not-a-row",
        [
            "bad-ms",
            "1",
            "2",
            "0",
            "1",
            "1",
            1,
            "1",
            1,
            "1",
            "1",
        ],
    ],
)
def test_malformed_rows(bad: object) -> None:
    with pytest.raises(BinanceResponseError):
        parse_kline_row(bad, timeframe=Timeframe.H1)


def test_negative_volume_and_trade_count() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    row = make_kline_row(start, Timeframe.H1)
    row[5] = "-1"
    with pytest.raises(BinanceResponseError):
        parse_kline_row(row, timeframe=Timeframe.H1)
    row = make_kline_row(start, Timeframe.H1)
    row[8] = -1
    with pytest.raises((BinanceResponseError, ValueError)):
        parse_kline_row(row, timeframe=Timeframe.H1)


def test_invalid_ohlc_row() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    row = make_kline_row(start, Timeframe.H1, high="50", open_="100", close="100", low="90")
    with pytest.raises(BinanceResponseError):
        parse_kline_row(row, timeframe=Timeframe.H1)


def test_misaligned_open_time_row() -> None:
    start = datetime(2026, 6, 1, 0, 30, tzinfo=UTC)
    row = make_kline_row(start, Timeframe.H1)
    with pytest.raises(BinanceResponseError, match="aligned"):
        parse_kline_row(row, timeframe=Timeframe.H1)


def test_all_timeframe_alignment() -> None:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    cases = [
        (
            Timeframe.M1,
            datetime(2026, 6, 1, 12, 3, tzinfo=UTC),
            datetime(2026, 6, 1, 12, 8, tzinfo=UTC),
            5,
        ),
        (
            Timeframe.M3,
            datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 6, 1, 12, 15, tzinfo=UTC),
            5,
        ),
        (
            Timeframe.M5,
            datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 6, 1, 12, 25, tzinfo=UTC),
            5,
        ),
        (
            Timeframe.M15,
            datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 6, 1, 13, 0, tzinfo=UTC),
            4,
        ),
        (
            Timeframe.M30,
            datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
            4,
        ),
        (Timeframe.H1, datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 1, 5, tzinfo=UTC), 5),
        (Timeframe.H4, datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 1, 8, tzinfo=UTC), 2),
        (Timeframe.D1, datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 4, tzinfo=UTC), 3),
        (Timeframe.W1, datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 22, tzinfo=UTC), 3),
    ]
    for tf, start, end, count in cases:
        rng = parse_import_range(start=start, end=end, timeframe=tf, now=now)
        assert rng.expected_candle_count == count
        assert estimate_candle_count(start, end, tf) == count


def test_week_rejects_non_monday() -> None:
    with pytest.raises(ValueError, match="align"):
        parse_import_range(
            start=datetime(2026, 6, 2, tzinfo=UTC),  # Tuesday
            end=datetime(2026, 6, 9, tzinfo=UTC),
            timeframe=Timeframe.W1,
            now=datetime(2026, 8, 1, tzinfo=UTC),
        )


def test_import_identity_stable() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 2, tzinfo=UTC)
    name = build_import_dataset_name(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        start=start,
        end=end,
    )
    assert name == "binance_futures_BTCUSDT_1h_2026-06-01T000000Z_2026-06-02T000000Z_v1"
    assert name == build_import_dataset_name(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        start=start,
        end=end,
    )


def test_exact_guardrail_boundary() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=100)
    assert estimate_candle_count(start, end, Timeframe.H1) == 100
