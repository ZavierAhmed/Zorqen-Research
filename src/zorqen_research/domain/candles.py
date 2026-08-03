"""Canonical immutable OHLCV candle model (no indicators)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class Candle:
    """One fully closed UTC candle."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: datetime
    quote_asset_volume: Decimal
    trade_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal

    def __post_init__(self) -> None:
        if self.open_time.tzinfo is None or self.close_time.tzinfo is None:
            msg = "Candle timestamps must be timezone-aware UTC"
            raise ValueError(msg)
        if self.trade_count < 0:
            msg = "trade_count must be non-negative"
            raise ValueError(msg)
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
            ("volume", self.volume),
            ("quote_asset_volume", self.quote_asset_volume),
            ("taker_buy_base_volume", self.taker_buy_base_volume),
            ("taker_buy_quote_volume", self.taker_buy_quote_volume),
        ):
            if not isinstance(value, Decimal):
                msg = f"{name} must be Decimal"
                raise TypeError(msg)
        if self.high < max(self.open, self.close, self.low):
            msg = "high must be >= max(open, close, low)"
            raise ValueError(msg)
        if self.low > min(self.open, self.close, self.high):
            msg = "low must be <= min(open, close, high)"
            raise ValueError(msg)
        for name, value in (
            ("volume", self.volume),
            ("quote_asset_volume", self.quote_asset_volume),
            ("taker_buy_base_volume", self.taker_buy_base_volume),
            ("taker_buy_quote_volume", self.taker_buy_quote_volume),
        ):
            if value < 0:
                msg = f"{name} must be non-negative"
                raise ValueError(msg)


def parse_decimal(value: object, *, field: str) -> Decimal:
    """Parse an exact decimal from Binance string/int/float-like values."""
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, bool):
            msg = f"{field} must be numeric"
            raise ValueError(msg)
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            msg = f"{field} must not use binary float; got {value!r}"
            raise ValueError(msg)
        text = str(value).strip()
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError) as exc:
        msg = f"{field} must be an exact decimal: {value!r}"
        raise ValueError(msg) from exc
