"""Paginated Binance kline retrieval with gap-ready assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from zorqen_research.application.market_data.ranges import ImportRange
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import timeframe_duration
from zorqen_research.infrastructure.binance.client import PAGE_LIMIT
from zorqen_research.infrastructure.binance.errors import BinanceResponseError


@dataclass(frozen=True, slots=True)
class SourcePage:
    raw_bytes: bytes
    requested_start: datetime
    requested_end: datetime
    requested_limit: int
    returned_row_count: int


@dataclass(frozen=True, slots=True)
class FetchResult:
    candles: tuple[Candle, ...]
    pages: tuple[SourcePage, ...]


FetchPage = Callable[..., tuple[list[Candle], bytes]]


def fetch_klines_range(
    *,
    client_fetch: FetchPage,
    symbol: str,
    import_range: ImportRange,
    page_limit: int = PAGE_LIMIT,
) -> FetchResult:
    """
    Deterministically paginate forward across [start, end).

    Cursor advances to last_open_time + timeframe_duration.
    """
    duration = timeframe_duration(import_range.timeframe)
    cursor = import_range.start
    end = import_range.end
    collected: list[Candle] = []
    pages: list[SourcePage] = []
    seen_times: set[datetime] = set()

    while cursor < end:
        page_candles, raw = client_fetch(
            symbol=symbol,
            interval=import_range.timeframe,
            start_time=cursor,
            end_time=end,
            limit=page_limit,
        )
        pages.append(
            SourcePage(
                raw_bytes=raw,
                requested_start=cursor,
                requested_end=end,
                requested_limit=page_limit,
                returned_row_count=len(page_candles),
            )
        )
        if not page_candles:
            msg = "Binance returned an empty page before expected coverage was complete"
            raise BinanceResponseError(msg)

        in_range: list[Candle] = []
        for candle in page_candles:
            if candle.open_time < cursor:
                msg = "Binance returned out-of-order or stale open_time"
                raise BinanceResponseError(msg)
            if candle.open_time >= end:
                continue
            if candle.open_time in seen_times:
                msg = "Duplicate candle open_time in Binance response"
                raise BinanceResponseError(msg)
            if in_range and candle.open_time <= in_range[-1].open_time:
                msg = "Out-of-order candle open_time in Binance response"
                raise BinanceResponseError(msg)
            seen_times.add(candle.open_time)
            in_range.append(candle)

        if not in_range:
            msg = "Binance page produced no candles inside the requested range"
            raise BinanceResponseError(msg)

        last_open = in_range[-1].open_time
        next_cursor = last_open + duration
        if next_cursor <= cursor:
            msg = "Binance response did not advance the pagination cursor"
            raise BinanceResponseError(msg)
        collected.extend(in_range)
        cursor = next_cursor

    return FetchResult(candles=tuple(collected), pages=tuple(pages))


def assert_complete_coverage(candles: tuple[Candle, ...], import_range: ImportRange) -> None:
    expected = import_range.expected_candle_count
    if len(candles) != expected:
        msg = f"Candle coverage mismatch: expected {expected}, got {len(candles)}"
        raise BinanceResponseError(msg)
    duration = timeframe_duration(import_range.timeframe)
    expected_open = import_range.start
    for candle in candles:
        if candle.open_time != expected_open:
            msg = f"Missing or gapped candle at expected open_time {expected_open.isoformat()}"
            raise BinanceResponseError(msg)
        if candle.open_time < import_range.start or candle.open_time >= import_range.end:
            msg = "Candle open_time falls outside [start, end)"
            raise BinanceResponseError(msg)
        expected_open = expected_open + duration
