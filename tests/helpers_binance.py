"""Helpers for deterministic Binance kline fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def make_kline_row(
    open_time: datetime,
    timeframe: Timeframe,
    *,
    open_: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume: str = "1.5",
    trades: int = 10,
) -> list[object]:
    duration = timeframe_duration(timeframe)
    close_time = open_time + duration - timedelta(milliseconds=1)
    return [
        ms(open_time),
        open_,
        high,
        low,
        close,
        volume,
        ms(close_time),
        "150.0",
        trades,
        "0.7",
        "70.0",
        "0",  # unused field consciously ignored
    ]


def make_kline_page(
    start: datetime,
    count: int,
    timeframe: Timeframe,
) -> list[list[object]]:
    step = timeframe_duration(timeframe)
    rows: list[list[object]] = []
    cursor = start
    for index in range(count):
        rows.append(
            make_kline_row(
                cursor,
                timeframe,
                open_=str(100 + index),
                high=str(110 + index),
                low=str(90 + index),
                close=str(105 + index),
                volume=str(Decimal("1.5") + index),
                trades=10 + index,
            )
        )
        cursor = cursor + step
    return rows


def page_bytes(rows: list[list[object]]) -> bytes:
    return json.dumps(rows, separators=(",", ":")).encode("utf-8")
