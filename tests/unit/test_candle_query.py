"""Unit tests for candle query validation and pagination."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tests.helpers_binance import make_kline_page
from zorqen_research.application.market_data.errors import CandleQueryValidationError
from zorqen_research.application.market_data.query import (
    MAX_CANDLE_LIMIT,
    build_candle_query,
    paginate_candles,
)
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


def _candles(count: int = 10):
    start = datetime(2026, 6, 1, tzinfo=UTC)
    return tuple(
        parse_kline_page(make_kline_page(start, count, Timeframe.H1), timeframe=Timeframe.H1)
    )


def test_build_query_rejects_bad_limit_and_alignment() -> None:
    sid = uuid4()
    with pytest.raises(CandleQueryValidationError, match="limit"):
        build_candle_query(snapshot_id=sid, symbol="BTCUSDT", timeframe="1h", limit=0)
    with pytest.raises(CandleQueryValidationError, match="limit"):
        build_candle_query(
            snapshot_id=sid, symbol="BTCUSDT", timeframe="1h", limit=MAX_CANDLE_LIMIT + 1
        )
    with pytest.raises(CandleQueryValidationError, match="align"):
        build_candle_query(
            snapshot_id=sid,
            symbol="BTCUSDT",
            timeframe="1h",
            start=datetime(2026, 6, 1, 0, 30, tzinfo=UTC),
        )


def test_pagination_pages_without_duplicates_or_gaps() -> None:
    candles = _candles(15)
    sid = uuid4()
    q1 = build_candle_query(snapshot_id=sid, symbol="BTCUSDT", timeframe="1h", limit=10)
    page1 = paginate_candles(candles, q1)
    assert page1.count == 10
    assert page1.has_more is True
    assert page1.next_cursor == candles[9].open_time

    q2 = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        after=page1.next_cursor,
        limit=10,
    )
    page2 = paginate_candles(candles, q2)
    assert page2.count == 5
    assert page2.has_more is False
    assert page2.next_cursor is None
    combined = page1.items + page2.items
    assert combined == candles
    assert serialize_candles_csv(combined) == serialize_candles_csv(candles)


def test_range_filters() -> None:
    candles = _candles(10)
    sid = uuid4()
    start = candles[2].open_time
    end = candles[7].open_time
    query = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        start=start,
        end=end,
        limit=100,
    )
    page = paginate_candles(candles, query)
    assert [c.open_time for c in page.items] == [c.open_time for c in candles[2:7]]


def test_empty_range() -> None:
    candles = _candles(5)
    sid = uuid4()
    query = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        start=datetime(2026, 7, 1, tzinfo=UTC),
        end=datetime(2026, 7, 2, tzinfo=UTC),
        limit=10,
    )
    page = paginate_candles(candles, query)
    assert page.count == 0
    assert page.has_more is False
    assert page.next_cursor is None


def test_start_only_and_end_only() -> None:
    candles = _candles(10)
    sid = uuid4()
    start_only = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        start=candles[5].open_time,
        limit=100,
    )
    assert [c.open_time for c in paginate_candles(candles, start_only).items] == [
        c.open_time for c in candles[5:]
    ]
    end_only = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        end=candles[3].open_time,
        limit=100,
    )
    assert [c.open_time for c in paginate_candles(candles, end_only).items] == [
        c.open_time for c in candles[:3]
    ]


def test_cursor_bounds_and_limit_one() -> None:
    candles = _candles(5)
    sid = uuid4()
    with pytest.raises(CandleQueryValidationError, match="before start"):
        build_candle_query(
            snapshot_id=sid,
            symbol="BTCUSDT",
            timeframe="1h",
            start=candles[2].open_time,
            after=candles[1].open_time,
        )
    with pytest.raises(CandleQueryValidationError, match="before end"):
        build_candle_query(
            snapshot_id=sid,
            symbol="BTCUSDT",
            timeframe="1h",
            end=candles[2].open_time,
            after=candles[2].open_time,
        )
    q = build_candle_query(snapshot_id=sid, symbol="BTCUSDT", timeframe="1h", limit=1)
    page = paginate_candles(candles, q)
    assert page.count == 1
    assert page.has_more is True
    assert page.next_cursor == candles[0].open_time


def test_maximum_limit_accepted() -> None:
    sid = uuid4()
    query = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        limit=MAX_CANDLE_LIMIT,
    )
    assert query.limit == MAX_CANDLE_LIMIT
