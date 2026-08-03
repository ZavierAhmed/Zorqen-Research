"""Parse and validate canonical candle CSV bytes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from zorqen_research.application.market_data.errors import CandlePartitionIntegrityError
from zorqen_research.application.market_data.ranges import is_aligned
from zorqen_research.application.market_data.serialization import (
    CANONICAL_SCHEMA_VERSION,
    CSV_COLUMNS,
    serialize_candles_csv,
)
from zorqen_research.domain.candles import Candle, parse_decimal
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration

_HEADER = ",".join(CSV_COLUMNS)
_EXPECTED_FIELD_COUNT = len(CSV_COLUMNS)


def _parse_canonical_utc(value: str, *, field: str) -> datetime:
    text = value.strip()
    if text != value:
        msg = f"{field} must not have surrounding whitespace"
        raise CandlePartitionIntegrityError(msg)
    if not text.endswith("Z"):
        msg = f"{field} must be a canonical UTC timestamp ending in Z"
        raise CandlePartitionIntegrityError(msg)
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        msg = f"{field} is not a valid UTC timestamp"
        raise CandlePartitionIntegrityError(msg) from exc
    if parsed.utcoffset() != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise CandlePartitionIntegrityError(msg)
    return parsed.astimezone(UTC)


def _parse_trade_count(value: str) -> int:
    text = value.strip()
    if text != value or text == "":
        msg = "trade_count must be a non-negative integer"
        raise CandlePartitionIntegrityError(msg)
    if text.startswith("-") or not text.isdigit():
        msg = "trade_count must be a non-negative integer"
        raise CandlePartitionIntegrityError(msg)
    return int(text)


def _parse_row(fields: list[str], *, timeframe: Timeframe, line_no: int) -> Candle:
    if len(fields) != _EXPECTED_FIELD_COUNT:
        msg = f"Row {line_no} must have exactly {_EXPECTED_FIELD_COUNT} fields"
        raise CandlePartitionIntegrityError(msg)
    try:
        open_time = _parse_canonical_utc(fields[0], field="open_time")
        close_time = _parse_canonical_utc(fields[6], field="close_time")
        candle = Candle(
            open_time=open_time,
            open=parse_decimal(fields[1], field="open"),
            high=parse_decimal(fields[2], field="high"),
            low=parse_decimal(fields[3], field="low"),
            close=parse_decimal(fields[4], field="close"),
            volume=parse_decimal(fields[5], field="volume"),
            close_time=close_time,
            quote_asset_volume=parse_decimal(fields[7], field="quote_asset_volume"),
            trade_count=_parse_trade_count(fields[8]),
            taker_buy_base_volume=parse_decimal(fields[9], field="taker_buy_base_volume"),
            taker_buy_quote_volume=parse_decimal(fields[10], field="taker_buy_quote_volume"),
        )
    except (TypeError, ValueError) as exc:
        msg = f"Row {line_no} failed candle validation"
        raise CandlePartitionIntegrityError(msg) from exc

    duration = timeframe_duration(timeframe)
    expected_close = candle.open_time + duration - timedelta(milliseconds=1)
    if candle.close_time != expected_close:
        msg = f"Row {line_no} close_time does not match Binance closed-candle convention"
        raise CandlePartitionIntegrityError(msg)
    if not is_aligned(candle.open_time, timeframe):
        msg = f"Row {line_no} open_time is not aligned to timeframe {timeframe.value}"
        raise CandlePartitionIntegrityError(msg)
    return candle


def parse_canonical_candles_csv(data: bytes, *, timeframe: Timeframe) -> tuple[Candle, ...]:
    """
    Parse canonical candle CSV bytes into validated candles.

    Rejects non-canonical encodings and requires that
    ``serialize_candles_csv(result) == data``.
    """
    if b"\x00" in data:
        msg = "Canonical candle CSV must not contain NUL bytes"
        raise CandlePartitionIntegrityError(msg)
    if data.startswith(b"\xef\xbb\xbf"):
        msg = "Canonical candle CSV must not include a UTF-8 BOM"
        raise CandlePartitionIntegrityError(msg)
    if b"\r" in data:
        msg = "Canonical candle CSV must use \\n line endings only"
        raise CandlePartitionIntegrityError(msg)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = "Canonical candle CSV must be valid UTF-8"
        raise CandlePartitionIntegrityError(msg) from exc
    if not text.endswith("\n"):
        msg = "Canonical candle CSV must end with a newline"
        raise CandlePartitionIntegrityError(msg)

    lines = text.split("\n")
    # Final empty segment from trailing newline.
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        msg = "Canonical candle CSV is empty"
        raise CandlePartitionIntegrityError(msg)
    header = lines[0]
    if header != _HEADER:
        msg = "Canonical candle CSV header is invalid"
        raise CandlePartitionIntegrityError(msg)
    if len(lines) < 2:
        msg = "Published candle partitions must contain at least one row"
        raise CandlePartitionIntegrityError(msg)

    candles: list[Candle] = []
    duration = timeframe_duration(timeframe)
    for index, line in enumerate(lines[1:], start=2):
        if line == "":
            msg = f"Row {index} is blank"
            raise CandlePartitionIntegrityError(msg)
        if line.strip() != line:
            msg = f"Row {index} must not have leading or trailing whitespace"
            raise CandlePartitionIntegrityError(msg)
        fields = line.split(",")
        candle = _parse_row(fields, timeframe=timeframe, line_no=index)
        if candles:
            expected_open = candles[-1].open_time + duration
            if candle.open_time == candles[-1].open_time:
                msg = f"Row {index} has a duplicate open_time"
                raise CandlePartitionIntegrityError(msg)
            if candle.open_time < candles[-1].open_time:
                msg = f"Row {index} is out of open_time order"
                raise CandlePartitionIntegrityError(msg)
            if candle.open_time != expected_open:
                msg = f"Row {index} has a gap at expected open_time {expected_open.isoformat()}"
                raise CandlePartitionIntegrityError(msg)
        candles.append(candle)

    encoded = serialize_candles_csv(candles)
    if encoded != data:
        msg = "Canonical candle CSV bytes do not match deterministic reserialization"
        raise CandlePartitionIntegrityError(msg)
    return tuple(candles)


def canonical_schema_version() -> str:
    return CANONICAL_SCHEMA_VERSION
