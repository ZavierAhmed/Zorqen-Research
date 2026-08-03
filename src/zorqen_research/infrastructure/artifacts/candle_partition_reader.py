"""Filesystem-backed verified candle partition reader."""

from __future__ import annotations

from datetime import datetime

from zorqen_research.application.market_data.csv_reader import (
    canonical_schema_version,
    parse_canonical_candles_csv,
)
from zorqen_research.application.market_data.errors import CandlePartitionIntegrityError
from zorqen_research.application.market_data.reader import VerifiedCandlePartition
from zorqen_research.domain.artifacts import MediaType, sha256_hex, validate_artifact_key
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.local import (
    ArtifactStoreError,
    LocalFilesystemArtifactStore,
)


class LocalCandlePartitionReader:
    """Read and verify canonical CSV partitions from the artifact store."""

    def __init__(self, artifact_store: LocalFilesystemArtifactStore) -> None:
        self._artifacts = artifact_store

    def read_verified(
        self,
        *,
        artifact_key: str,
        expected_sha256: str,
        expected_byte_size: int,
        symbol: Symbol,
        timeframe: Timeframe,
        expected_row_count: int,
        expected_minimum_open_time: datetime | None,
        expected_maximum_open_time: datetime | None,
    ) -> VerifiedCandlePartition:
        try:
            key = validate_artifact_key(artifact_key)
        except ValueError as exc:
            msg = "Partition artifact key is invalid"
            raise CandlePartitionIntegrityError(msg) from exc

        try:
            metadata = self._artifacts.get_metadata(key)
            data = self._artifacts.open_bytes(key)
        except ArtifactStoreError as exc:
            msg = "Partition artifact verification failed"
            raise CandlePartitionIntegrityError(msg) from exc

        if metadata.key != key:
            msg = "Partition artifact metadata key mismatch"
            raise CandlePartitionIntegrityError(msg)
        if metadata.sha256 != expected_sha256:
            msg = "Partition artifact SHA-256 mismatch"
            raise CandlePartitionIntegrityError(msg)
        if metadata.byte_size != expected_byte_size:
            msg = "Partition artifact byte size mismatch"
            raise CandlePartitionIntegrityError(msg)
        if metadata.media_type is not MediaType.CSV:
            msg = "Partition artifact media type must be text/csv"
            raise CandlePartitionIntegrityError(msg)
        if len(data) != expected_byte_size:
            msg = "Partition artifact byte length mismatch"
            raise CandlePartitionIntegrityError(msg)
        digest = sha256_hex(data)
        if digest != expected_sha256 or digest != key.rsplit("/", maxsplit=1)[-1]:
            msg = "Partition artifact content hash mismatch"
            raise CandlePartitionIntegrityError(msg)

        candles = parse_canonical_candles_csv(data, timeframe=timeframe)
        if len(candles) != expected_row_count:
            msg = "Partition row count mismatch"
            raise CandlePartitionIntegrityError(msg)
        if candles[0].open_time != expected_minimum_open_time:
            msg = "Partition minimum open_time mismatch"
            raise CandlePartitionIntegrityError(msg)
        if candles[-1].open_time != expected_maximum_open_time:
            msg = "Partition maximum open_time mismatch"
            raise CandlePartitionIntegrityError(msg)

        return VerifiedCandlePartition(
            candles=candles,
            artifact_key=key,
            sha256=expected_sha256,
            byte_size=expected_byte_size,
            row_count=len(candles),
            minimum_open_time=candles[0].open_time,
            maximum_open_time=candles[-1].open_time,
            symbol=symbol,
            timeframe=timeframe,
            canonical_schema_version=canonical_schema_version(),
        )
