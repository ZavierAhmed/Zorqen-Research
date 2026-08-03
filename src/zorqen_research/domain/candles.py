"""Canonical immutable OHLCV candle model (no indicators)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation


def _require_canonical_utc(value: datetime, *, field: str) -> None:
    """
    Reject naive and non-zero-offset timestamps.

    Policy (Milestone 0.4A): only zero-offset UTC timestamps are canonical.
    Infrastructure adapters must convert source values to UTC before constructing
    ``Candle``. A ``+00:00`` / ``UTC`` timezone is accepted; offsets such as
    ``+05:00`` are rejected even when timezone-aware.
    """
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise ValueError(msg)
    offset = value.utcoffset()
    if offset is None or offset != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise ValueError(msg)


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
        _require_canonical_utc(self.open_time, field="open_time")
        _require_canonical_utc(self.close_time, field="close_time")
        if self.close_time < self.open_time:
            msg = "close_time must be greater than or equal to open_time"
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
            if not value.is_finite():
                msg = f"{name} must be a finite Decimal"
                raise ValueError(msg)
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
    """Parse an exact finite decimal from Binance string/int values."""
    try:
        if isinstance(value, Decimal):
            parsed = value
        elif isinstance(value, bool):
            msg = f"{field} must be numeric"
            raise ValueError(msg)
        elif isinstance(value, int):
            parsed = Decimal(value)
        elif isinstance(value, float):
            msg = f"{field} must not use binary float; got {value!r}"
            raise ValueError(msg)
        else:
            parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        msg = f"{field} must be an exact decimal: {value!r}"
        raise ValueError(msg) from exc
    except (TypeError, ValueError) as exc:
        # Preserve explicit field validation messages raised above.
        if str(exc).startswith(f"{field} must"):
            raise
        msg = f"{field} must be an exact decimal: {value!r}"
        raise ValueError(msg) from exc
    if not parsed.is_finite():
        msg = f"{field} must be a finite decimal: {value!r}"
        raise ValueError(msg)
    return parsed
