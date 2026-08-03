"""Parse and validate Binance /fapi/v1/klines rows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from zorqen_research.domain.candles import Candle, parse_decimal
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration
from zorqen_research.infrastructure.binance.errors import BinanceResponseError

# Binance kline array positions (unused index 11 is ignored consciously).
# 0 open time, 1 open, 2 high, 3 low, 4 close, 5 volume, 6 close time,
# 7 quote volume, 8 trades, 9 taker buy base, 10 taker buy quote, 11 ignore.


def _ms_to_utc(value: object, *, field: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be an integer millisecond timestamp"
        raise BinanceResponseError(msg)
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def parse_kline_row(row: object, *, timeframe: Timeframe) -> Candle:
    if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
        msg = "Kline row must be a sequence"
        raise BinanceResponseError(msg)
    if len(row) < 11:
        msg = "Kline row is missing required positions"
        raise BinanceResponseError(msg)
    try:
        open_time = _ms_to_utc(row[0], field="open_time")
        close_time = _ms_to_utc(row[6], field="close_time")
        open_ = parse_decimal(row[1], field="open")
        high = parse_decimal(row[2], field="high")
        low = parse_decimal(row[3], field="low")
        close = parse_decimal(row[4], field="close")
        volume = parse_decimal(row[5], field="volume")
        quote = parse_decimal(row[7], field="quote_asset_volume")
        trades = row[8]
        if isinstance(trades, bool) or not isinstance(trades, int):
            msg = "trade_count must be an integer"
            raise BinanceResponseError(msg)
        taker_base = parse_decimal(row[9], field="taker_buy_base_volume")
        taker_quote = parse_decimal(row[10], field="taker_buy_quote_volume")
        candle = Candle(
            open_time=open_time,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            close_time=close_time,
            quote_asset_volume=quote,
            trade_count=trades,
            taker_buy_base_volume=taker_base,
            taker_buy_quote_volume=taker_quote,
        )
    except (TypeError, ValueError) as exc:
        msg = "Invalid kline row"
        raise BinanceResponseError(msg) from exc

    duration = timeframe_duration(timeframe)
    expected_close = candle.open_time + duration - timedelta(milliseconds=1)
    if candle.close_time != expected_close:
        msg = "close_time does not match Binance closed-candle convention"
        raise BinanceResponseError(msg)
    from zorqen_research.application.market_data.ranges import is_aligned

    if not is_aligned(candle.open_time, timeframe):
        msg = "open_time is not aligned to the requested timeframe"
        raise BinanceResponseError(msg)
    return candle


def parse_kline_page(payload: object, *, timeframe: Timeframe) -> list[Candle]:
    if not isinstance(payload, list):
        msg = "Kline response must be a JSON array"
        raise BinanceResponseError(msg)
    return [parse_kline_row(row, timeframe=timeframe) for row in payload]
