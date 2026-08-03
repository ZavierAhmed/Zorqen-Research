"""Unit tests for canonical candle CSV reader."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.helpers_binance import make_kline_page
from zorqen_research.application.market_data.csv_reader import parse_canonical_candles_csv
from zorqen_research.application.market_data.errors import CandlePartitionIntegrityError
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


def _canonical_bytes(count: int = 3) -> bytes:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candles = parse_kline_page(make_kline_page(start, count, Timeframe.H1), timeframe=Timeframe.H1)
    return serialize_candles_csv(candles)


def test_round_trip_bytes() -> None:
    raw = _canonical_bytes(5)
    candles = parse_canonical_candles_csv(raw, timeframe=Timeframe.H1)
    assert serialize_candles_csv(candles) == raw
    assert len(candles) == 5


@pytest.mark.parametrize(
    "mutator",
    [
        lambda b: b"\xef\xbb\xbf" + b,
        lambda b: b.replace(b"\n", b"\r\n"),
        lambda b: b[:-1],  # missing final newline
        lambda b: b.replace(b"open_time,", b" open_time,"),
        lambda b: b"\x00" + b,
        lambda b: b.replace(
            b"open_time,open,high,low,close,volume,close_time,",
            b"open,open_time,high,low,close,volume,close_time,",
        ),
    ],
)
def test_rejects_non_canonical_bytes(mutator) -> None:  # type: ignore[no-untyped-def]
    raw = _canonical_bytes(2)
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(mutator(raw), timeframe=Timeframe.H1)


def test_rejects_invalid_utf8() -> None:
    raw = _canonical_bytes(1) + b"\xff"
    with pytest.raises(CandlePartitionIntegrityError, match="UTF-8"):
        parse_canonical_candles_csv(raw, timeframe=Timeframe.H1)


def test_rejects_extra_and_missing_columns() -> None:
    raw = _canonical_bytes(1)
    text = raw.decode("utf-8")
    lines = text.split("\n")
    # Extra field
    bad_extra = (lines[0] + "\n" + lines[1] + ",0\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(bad_extra, timeframe=Timeframe.H1)
    # Missing field
    parts = lines[1].split(",")
    bad_missing = (lines[0] + "\n" + ",".join(parts[:-1]) + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(bad_missing, timeframe=Timeframe.H1)


def test_rejects_blank_row() -> None:
    raw = _canonical_bytes(2)
    text = raw.decode("utf-8")
    lines = text.rstrip("\n").split("\n")
    bad = (lines[0] + "\n" + lines[1] + "\n\n" + lines[2] + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError, match="blank"):
        parse_canonical_candles_csv(bad, timeframe=Timeframe.H1)


def test_rejects_empty_partition() -> None:
    header = (
        "open_time,open,high,low,close,volume,close_time,"
        "quote_asset_volume,trade_count,taker_buy_base_volume,taker_buy_quote_volume\n"
    )
    with pytest.raises(CandlePartitionIntegrityError, match="at least one"):
        parse_canonical_candles_csv(header.encode("utf-8"), timeframe=Timeframe.H1)


def test_rejects_gap_and_duplicate() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 3, Timeframe.H1)
    candles = parse_kline_page(rows, timeframe=Timeframe.H1)
    # Gap: drop middle candle then serialize wouldn't be continuous - build by hand
    gapped = serialize_candles_csv((candles[0], candles[2]))
    with pytest.raises(CandlePartitionIntegrityError, match="gap"):
        parse_canonical_candles_csv(gapped, timeframe=Timeframe.H1)

    duplicated = serialize_candles_csv((candles[0], candles[0]))
    with pytest.raises(CandlePartitionIntegrityError, match="duplicate|order|gap"):
        parse_canonical_candles_csv(duplicated, timeframe=Timeframe.H1)


def test_rejects_bad_trade_count_and_nonfinite() -> None:
    raw = _canonical_bytes(1).decode("utf-8")
    header, row = raw.rstrip("\n").split("\n")
    fields = row.split(",")
    fields[8] = "1.5"
    bad = (header + "\n" + ",".join(fields) + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(bad, timeframe=Timeframe.H1)
    fields[8] = "1"
    fields[1] = "NaN"
    bad2 = (header + "\n" + ",".join(fields) + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(bad2, timeframe=Timeframe.H1)


def test_rejects_trailing_zero_decimal_as_non_canonical() -> None:
    # Semantically valid candle with non-canonical decimal formatting.
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candles = parse_kline_page(make_kline_page(start, 1, Timeframe.H1), timeframe=Timeframe.H1)
    canonical = serialize_candles_csv(candles)
    # Force a trailing zero in open that serializer would strip.
    text = canonical.decode("utf-8")
    header, row = text.rstrip("\n").split("\n")
    fields = row.split(",")
    fields[1] = fields[1] + "0" if "." in fields[1] else fields[1] + ".0"
    mutated = (header + "\n" + ",".join(fields) + "\n").encode("utf-8")
    with pytest.raises(CandlePartitionIntegrityError, match="reserialization"):
        parse_canonical_candles_csv(mutated, timeframe=Timeframe.H1)


def test_rejects_negative_trade_count_and_invalid_ohlc() -> None:
    raw = _canonical_bytes(1).decode("utf-8")
    header, row = raw.rstrip("\n").split("\n")
    fields = row.split(",")
    fields[8] = "-1"
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(
            (header + "\n" + ",".join(fields) + "\n").encode(), timeframe=Timeframe.H1
        )
    fields[8] = "10"
    fields[2] = "1"  # high too low
    with pytest.raises(CandlePartitionIntegrityError):
        parse_canonical_candles_csv(
            (header + "\n" + ",".join(fields) + "\n").encode(), timeframe=Timeframe.H1
        )


def test_rejects_invalid_close_time_and_misaligned_open() -> None:
    raw = _canonical_bytes(1).decode("utf-8")
    header, row = raw.rstrip("\n").split("\n")
    fields = row.split(",")
    # Wrong close_time (not open+1h-1ms)
    fields[6] = "2026-06-01T00:30:00Z"
    with pytest.raises(CandlePartitionIntegrityError, match="close_time"):
        parse_canonical_candles_csv(
            (header + "\n" + ",".join(fields) + "\n").encode(), timeframe=Timeframe.H1
        )

    fields = row.split(",")
    fields[0] = "2026-06-01T00:30:00Z"
    fields[6] = "2026-06-01T01:29:59.999Z"
    with pytest.raises(CandlePartitionIntegrityError, match="align"):
        parse_canonical_candles_csv(
            (header + "\n" + ",".join(fields) + "\n").encode(), timeframe=Timeframe.H1
        )


def test_rejects_non_z_timestamp() -> None:
    raw = _canonical_bytes(1).decode("utf-8")
    header, row = raw.rstrip("\n").split("\n")
    fields = row.split(",")
    fields[0] = fields[0].replace("Z", "+00:00")
    with pytest.raises(CandlePartitionIntegrityError, match="Z"):
        parse_canonical_candles_csv(
            (header + "\n" + ",".join(fields) + "\n").encode(), timeframe=Timeframe.H1
        )


def test_rejects_out_of_order() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candles = parse_kline_page(make_kline_page(start, 3, Timeframe.H1), timeframe=Timeframe.H1)
    reordered = serialize_candles_csv((candles[0], candles[2], candles[1]))
    with pytest.raises(CandlePartitionIntegrityError, match="gap|order"):
        parse_canonical_candles_csv(reordered, timeframe=Timeframe.H1)
