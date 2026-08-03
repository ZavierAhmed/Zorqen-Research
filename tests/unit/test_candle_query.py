"""Unit tests for candle query validation and pagination."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from tests.helpers_binance import make_kline_page
from zorqen_research.application.market_data.errors import CandleQueryValidationError
from zorqen_research.application.market_data.query import (
    MAX_CANDLE_LIMIT,
    CandleQuery,
    CandleQueryService,
    build_candle_query,
    collect_matching_page,
    paginate_candles,
)
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


def _candles(count: int = 10):
    start = datetime(2026, 6, 1, tzinfo=UTC)
    return tuple(
        parse_kline_page(make_kline_page(start, count, Timeframe.H1), timeframe=Timeframe.H1)
    )


def _valid_kwargs(**overrides):
    base = {
        "snapshot_id": uuid4(),
        "symbol": parse_symbol("BTCUSDT"),
        "timeframe": Timeframe.H1,
        "limit": 10,
    }
    base.update(overrides)
    return base


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


def test_direct_candle_query_rejects_invalid_invariants() -> None:
    with pytest.raises(CandleQueryValidationError, match="limit"):
        CandleQuery(**_valid_kwargs(limit=0))
    with pytest.raises(CandleQueryValidationError, match="limit"):
        CandleQuery(**_valid_kwargs(limit=5001))
    with pytest.raises(CandleQueryValidationError, match="limit"):
        CandleQuery(**_valid_kwargs(limit=True))  # type: ignore[arg-type]
    with pytest.raises(CandleQueryValidationError, match="limit"):
        CandleQuery(**_valid_kwargs(limit=1.5))  # type: ignore[arg-type]
    with pytest.raises(CandleQueryValidationError, match="timezone-aware"):
        CandleQuery(**_valid_kwargs(start=datetime(2026, 6, 1)))
    with pytest.raises(CandleQueryValidationError, match="zero UTC offset"):
        CandleQuery(
            **_valid_kwargs(start=datetime(2026, 6, 1, tzinfo=timezone(timedelta(hours=5))))
        )
    with pytest.raises(CandleQueryValidationError, match="align"):
        CandleQuery(**_valid_kwargs(start=datetime(2026, 6, 1, 0, 30, tzinfo=UTC)))
    start = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(CandleQueryValidationError, match="strictly less"):
        CandleQuery(**_valid_kwargs(start=start, end=start))
    with pytest.raises(CandleQueryValidationError, match="strictly less"):
        CandleQuery(**_valid_kwargs(start=start + timedelta(hours=2), end=start))
    with pytest.raises(CandleQueryValidationError, match="before start"):
        CandleQuery(
            **_valid_kwargs(
                start=start + timedelta(hours=2),
                after=start,
            )
        )
    with pytest.raises(CandleQueryValidationError, match="before end"):
        CandleQuery(
            **_valid_kwargs(
                end=start + timedelta(hours=2),
                after=start + timedelta(hours=2),
            )
        )
    with pytest.raises(CandleQueryValidationError, match="Symbol"):
        CandleQuery(**_valid_kwargs(symbol="BTCUSDT"))  # type: ignore[arg-type]
    with pytest.raises(CandleQueryValidationError, match="Timeframe"):
        CandleQuery(**_valid_kwargs(timeframe="1h"))  # type: ignore[arg-type]


def test_valid_zero_offset_aligned_query_succeeds() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    query = CandleQuery(
        **_valid_kwargs(
            start=start,
            end=start + timedelta(hours=5),
            after=start,
            limit=100,
        )
    )
    assert query.limit == 100
    assert query.after == start


@pytest.mark.asyncio
async def test_service_rejects_bypassed_invalid_query() -> None:
    """Service boundary re-validates even if __post_init__ was skipped."""
    bypassed = object.__new__(CandleQuery)
    object.__setattr__(bypassed, "snapshot_id", uuid4())
    object.__setattr__(bypassed, "symbol", parse_symbol("BTCUSDT"))
    object.__setattr__(bypassed, "timeframe", Timeframe.H1)
    object.__setattr__(bypassed, "start", None)
    object.__setattr__(bypassed, "end", None)
    object.__setattr__(bypassed, "after", None)
    object.__setattr__(bypassed, "limit", 0)

    class _Unused:  # placeholders; query fails before DB
        pass

    service = CandleQueryService(_Unused(), _Unused(), _Unused())  # type: ignore[arg-type]
    with pytest.raises(CandleQueryValidationError, match="limit"):
        await service.query(bypassed)


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


def test_bounded_pagination_stops_after_lookahead() -> None:
    candles = _candles(100)
    seen = {"n": 0}

    def tracked():
        for candle in candles:
            seen["n"] += 1
            yield candle

    query = build_candle_query(
        snapshot_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        limit=10,
    )
    collected = collect_matching_page(tracked(), query)
    assert len(collected) == 11
    assert seen["n"] == 11
    page = paginate_candles(candles, query)
    assert page.count == 10
    assert page.has_more is True


def test_bounded_pagination_against_large_partition() -> None:
    candles = _candles(20)

    class LongStream:
        def __init__(self) -> None:
            self.yielded = 0
            self._base = candles

        def __iter__(self):
            index = 0
            while self.yielded < 100_000:
                candle = self._base[index % len(self._base)]
                self.yielded += 1
                index += 1
                yield candle

    stream = LongStream()
    query = build_candle_query(
        snapshot_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        limit=1000,
    )
    collected = collect_matching_page(stream, query)
    assert len(collected) == 1001
    assert stream.yielded == 1001


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
    # Exclusive cursor: second page starts after first candle.
    q2 = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        after=page.next_cursor,
        limit=1,
    )
    page2 = paginate_candles(candles, q2)
    assert page2.items[0].open_time == candles[1].open_time


def test_repeated_query_is_deterministic() -> None:
    candles = _candles(20)
    query = build_candle_query(
        snapshot_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        start=candles[2].open_time,
        end=candles[15].open_time,
        after=candles[4].open_time,
        limit=5,
    )
    first = paginate_candles(candles, query)
    second = paginate_candles(candles, query)
    assert first == second


def test_maximum_limit_accepted() -> None:
    sid = uuid4()
    query = build_candle_query(
        snapshot_id=sid,
        symbol="BTCUSDT",
        timeframe="1h",
        limit=MAX_CANDLE_LIMIT,
    )
    assert query.limit == MAX_CANDLE_LIMIT
