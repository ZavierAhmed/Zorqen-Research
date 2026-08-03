"""Unit tests for LocalCandlePartitionReader verification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.helpers_binance import make_kline_page
from zorqen_research.application.market_data.errors import CandlePartitionIntegrityError
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.artifacts import MediaType, sha256_hex
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.candle_partition_reader import (
    LocalCandlePartitionReader,
)
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


def test_reader_verifies_canonical_partition(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candles = tuple(
        parse_kline_page(make_kline_page(start, 3, Timeframe.H1), timeframe=Timeframe.H1)
    )
    raw = serialize_candles_csv(candles)
    meta = store.publish_bytes(raw, media_type=MediaType.CSV, original_filename="part.csv")
    reader = LocalCandlePartitionReader(store)
    symbol = parse_symbol("BTCUSDT")
    verified = reader.read_verified(
        artifact_key=meta.key,
        expected_sha256=meta.sha256,
        expected_byte_size=meta.byte_size,
        symbol=symbol,
        timeframe=Timeframe.H1,
        expected_row_count=3,
        expected_minimum_open_time=candles[0].open_time,
        expected_maximum_open_time=candles[-1].open_time,
    )
    assert verified.row_count == 3
    assert verified.sha256 == sha256_hex(raw)
    assert verified.candles == candles


def test_reader_rejects_row_count_and_media_mismatch(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candles = tuple(
        parse_kline_page(make_kline_page(start, 2, Timeframe.H1), timeframe=Timeframe.H1)
    )
    raw = serialize_candles_csv(candles)
    meta = store.publish_bytes(raw, media_type=MediaType.CSV, original_filename="part.csv")
    reader = LocalCandlePartitionReader(store)
    symbol = parse_symbol("BTCUSDT")
    with pytest.raises(CandlePartitionIntegrityError, match="row count"):
        reader.read_verified(
            artifact_key=meta.key,
            expected_sha256=meta.sha256,
            expected_byte_size=meta.byte_size,
            symbol=symbol,
            timeframe=Timeframe.H1,
            expected_row_count=99,
            expected_minimum_open_time=candles[0].open_time,
            expected_maximum_open_time=candles[-1].open_time,
        )
    with pytest.raises(CandlePartitionIntegrityError, match="byte"):
        reader.read_verified(
            artifact_key=meta.key,
            expected_sha256=meta.sha256,
            expected_byte_size=meta.byte_size + 1,
            symbol=symbol,
            timeframe=Timeframe.H1,
            expected_row_count=2,
            expected_minimum_open_time=candles[0].open_time,
            expected_maximum_open_time=candles[-1].open_time,
        )
    with pytest.raises(CandlePartitionIntegrityError, match="SHA-256|hash"):
        reader.read_verified(
            artifact_key=meta.key,
            expected_sha256="0" * 64,
            expected_byte_size=meta.byte_size,
            symbol=symbol,
            timeframe=Timeframe.H1,
            expected_row_count=2,
            expected_minimum_open_time=candles[0].open_time,
            expected_maximum_open_time=candles[-1].open_time,
        )
