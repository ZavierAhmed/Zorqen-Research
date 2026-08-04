"""Shared helpers for indicator foundation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration

SYMBOL = Symbol(value="BTCUSDT")
TIMEFRAME = Timeframe.M1


def utc(*args: int) -> datetime:
    year, month, day = args[0], args[1], args[2]
    hour = args[3] if len(args) > 3 else 0
    minute = args[4] if len(args) > 4 else 0
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def make_candle(
    open_time: datetime,
    *,
    open: str | Decimal = "10",
    high: str | Decimal = "12",
    low: str | Decimal = "9",
    close: str | Decimal = "11",
    timeframe: Timeframe = TIMEFRAME,
) -> Candle:
    return Candle(
        open_time=open_time,
        open=Decimal(str(open)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal("1"),
        close_time=open_time + timeframe_duration(timeframe) - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("10"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.4"),
        taker_buy_quote_volume=Decimal("4"),
    )


def candle_series(
    specs: tuple[tuple[str, str, str, str], ...],
    *,
    start: datetime | None = None,
    timeframe: Timeframe = TIMEFRAME,
) -> tuple[Candle, ...]:
    origin = start or utc(2024, 1, 1)
    step = timeframe_duration(timeframe)
    return tuple(
        make_candle(
            origin + index * step,
            open=open_,
            high=high,
            low=low,
            close=close,
            timeframe=timeframe,
        )
        for index, (open_, high, low, close) in enumerate(specs)
    )


def indicator_input_from_specs(
    specs: tuple[tuple[str, str, str, str], ...],
) -> IndicatorInput:
    return IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candle_series(specs),
    )
