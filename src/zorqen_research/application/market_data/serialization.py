"""Canonical CSV serialization for candles."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from zorqen_research.domain.candles import Candle

CSV_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "trade_count",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
)

CANONICAL_SCHEMA_VERSION = "1"


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def format_canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _decimal_text(value: Decimal) -> str:
    return format_canonical_decimal(value)


def serialize_candles_csv(candles: Sequence[Candle]) -> bytes:
    """
    Serialize candles to deterministic UTF-8 CSV bytes.

    Always uses ``\\n`` endings (Windows and Linux) and a fixed header/order.
    """
    lines = [",".join(CSV_COLUMNS)]
    for candle in candles:
        row = [
            _iso_utc(candle.open_time),
            _decimal_text(candle.open),
            _decimal_text(candle.high),
            _decimal_text(candle.low),
            _decimal_text(candle.close),
            _decimal_text(candle.volume),
            _iso_utc(candle.close_time),
            _decimal_text(candle.quote_asset_volume),
            str(candle.trade_count),
            _decimal_text(candle.taker_buy_base_volume),
            _decimal_text(candle.taker_buy_quote_volume),
        ]
        lines.append(",".join(row))
    return ("\n".join(lines) + "\n").encode("utf-8")
