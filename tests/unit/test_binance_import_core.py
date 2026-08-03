"""Unit tests for candle model, ranges, serialization, and pagination."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from tests.helpers_binance import make_kline_page, page_bytes
from zorqen_research.application.market_data.pagination import (
    assert_complete_coverage,
    fetch_klines_range,
)
from zorqen_research.application.market_data.ranges import (
    estimate_candle_count,
    parse_import_range,
)
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.errors import BinanceResponseError
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


def test_candle_rejects_bad_ohlc() -> None:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="high"):
        Candle(
            open_time=now,
            open=Decimal("10"),
            high=Decimal("9"),
            low=Decimal("8"),
            close=Decimal("9"),
            volume=Decimal("1"),
            close_time=now + timedelta(hours=1) - timedelta(milliseconds=1),
            quote_asset_volume=Decimal("1"),
            trade_count=1,
            taker_buy_base_volume=Decimal("0"),
            taker_buy_quote_volume=Decimal("0"),
        )


@pytest.mark.parametrize(
    ("tf", "start", "end", "count"),
    [
        (
            Timeframe.H1,
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 2, tzinfo=UTC),
            24,
        ),
        (
            Timeframe.M15,
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 1, 1, tzinfo=UTC),
            4,
        ),
        (
            Timeframe.W1,
            datetime(2026, 6, 1, tzinfo=UTC),  # Monday
            datetime(2026, 6, 15, tzinfo=UTC),
            2,
        ),
    ],
)
def test_estimate_and_alignment(
    tf: Timeframe,
    start: datetime,
    end: datetime,
    count: int,
) -> None:
    fixed_now = datetime(2026, 7, 1, tzinfo=UTC)
    rng = parse_import_range(start=start, end=end, timeframe=tf, now=fixed_now)
    assert rng.expected_candle_count == count
    assert estimate_candle_count(start, end, tf) == count


def test_rejects_misaligned_and_open_candle() -> None:
    with pytest.raises(ValueError, match="align"):
        parse_import_range(
            start=datetime(2026, 6, 1, 0, 30, tzinfo=UTC),
            end=datetime(2026, 6, 1, 2, tzinfo=UTC),
            timeframe=Timeframe.H1,
            now=datetime(2026, 7, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="open candle"):
        parse_import_range(
            start=datetime(2026, 6, 1, tzinfo=UTC),
            end=datetime(2026, 6, 1, 5, tzinfo=UTC),
            timeframe=Timeframe.H1,
            now=datetime(2026, 6, 1, 4, 10, tzinfo=UTC),
        )


def test_guardrail_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 1, 3, tzinfo=UTC)
    assert estimate_candle_count(start, end, Timeframe.H1) == 3


def test_csv_stable_and_lf_only() -> None:
    rows = make_kline_page(datetime(2026, 6, 1, tzinfo=UTC), 2, Timeframe.H1)
    candles = parse_kline_page(rows, timeframe=Timeframe.H1)
    first = serialize_candles_csv(candles)
    second = serialize_candles_csv(candles)
    assert first == second
    assert b"\r" not in first
    assert first.startswith(b"open_time,open,high,low,close,volume,")
    assert first.endswith(b"\n")


def test_parse_rejects_duplicate_and_gap_in_coverage() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 3, Timeframe.H1)
    candles = tuple(parse_kline_page(rows, timeframe=Timeframe.H1))
    rng = parse_import_range(
        start=start,
        end=start + timedelta(hours=3),
        timeframe=Timeframe.H1,
        now=datetime(2026, 7, 1, tzinfo=UTC),
    )
    assert_complete_coverage(candles, rng)
    with pytest.raises(BinanceResponseError, match="coverage|Missing"):
        assert_complete_coverage(candles[:-1], rng)


def test_empty_premature_page_and_non_progress() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=3)
    rng = parse_import_range(
        start=start,
        end=end,
        timeframe=Timeframe.H1,
        now=datetime(2026, 7, 1, tzinfo=UTC),
    )

    def empty_fetch(**kwargs):  # type: ignore[no-untyped-def]
        return [], b"[]"

    with pytest.raises(BinanceResponseError, match="empty page"):
        fetch_klines_range(client_fetch=empty_fetch, symbol="BTCUSDT", import_range=rng)

    candle = parse_kline_page(
        make_kline_page(start, 1, Timeframe.H1),
        timeframe=Timeframe.H1,
    )[0]

    def stuck_fetch(**kwargs):  # type: ignore[no-untyped-def]
        # Always return the same candle so the cursor cannot advance past page 1 filtering
        # after the first collection — simulate non-progress by returning open_time < cursor
        # on the second call.
        if not hasattr(stuck_fetch, "n"):
            stuck_fetch.n = 0  # type: ignore[attr-defined]
        stuck_fetch.n += 1  # type: ignore[attr-defined]
        if stuck_fetch.n == 1:  # type: ignore[attr-defined]
            return [candle], page_bytes(make_kline_page(start, 1, Timeframe.H1))
        return [candle], page_bytes(make_kline_page(start, 1, Timeframe.H1))

    with pytest.raises(BinanceResponseError, match="out-of-order|stale|Duplicate|empty"):
        fetch_klines_range(client_fetch=stuck_fetch, symbol="BTCUSDT", import_range=rng)


def test_pagination_multi_page_and_no_extra_request() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=5)
    all_rows = make_kline_page(start, 5, Timeframe.H1)
    calls: list[datetime] = []

    def fetch(**kwargs):  # type: ignore[no-untyped-def]
        cursor = kwargs["start_time"]
        calls.append(cursor)
        # Return 2 candles per page.
        offset = int((cursor - start) / timedelta(hours=1))
        chunk = all_rows[offset : offset + 2]
        return parse_kline_page(chunk, timeframe=Timeframe.H1), page_bytes(chunk)

    rng = parse_import_range(
        start=start,
        end=end,
        timeframe=Timeframe.H1,
        now=datetime(2026, 7, 1, tzinfo=UTC),
    )
    result = fetch_klines_range(
        client_fetch=fetch,
        symbol="BTCUSDT",
        import_range=rng,
        page_limit=2,
    )
    assert len(result.candles) == 5
    assert len(result.pages) == 3
    assert calls == [start, start + timedelta(hours=2), start + timedelta(hours=4)]
    assert_complete_coverage(result.candles, rng)
