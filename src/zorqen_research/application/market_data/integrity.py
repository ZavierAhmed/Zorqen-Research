"""Dataset and manifest verification for candle access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zorqen_research.application.datasets.manifest import (
    build_manifest_document,
    hash_manifest_document,
)
from zorqen_research.application.market_data.errors import (
    CandlePartitionIntegrityError,
    CandlePartitionNotFoundError,
    DatasetIntegrityError,
    UnsupportedCandleDatasetError,
)
from zorqen_research.application.market_data.reader import (
    CandlePartitionReader,
    VerifiedCandlePartition,
)
from zorqen_research.application.market_data.serialization import CANONICAL_SCHEMA_VERSION
from zorqen_research.domain.artifacts import MediaType, sha256_hex, validate_artifact_key
from zorqen_research.domain.datasets import DatasetPartition, DatasetSnapshot, DatasetSnapshotStatus
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.local import (
    ArtifactStoreError,
    LocalFilesystemArtifactStore,
)

SUPPORTED_MANIFEST_VERSION = "2"
SUPPORTED_PROVIDER = "binance"
SUPPORTED_MARKET = "binance_futures"
SUPPORTED_DATA_TYPE = "contract_klines"
SUPPORTED_ENDPOINT_PATH = "/fapi/v1/klines"


@dataclass(frozen=True, slots=True)
class VerifiedCandleDataset:
    """Fully verified published candle dataset for one partition."""

    snapshot: DatasetSnapshot
    partition: DatasetPartition
    provenance: dict[str, Any]
    verified_partition: VerifiedCandlePartition
    verified_source_page_count: int
    content_hash: str


def _require_mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"{label} is missing or invalid"
        raise DatasetIntegrityError(msg)
    return value


def assert_supported_candle_dataset(snapshot: DatasetSnapshot) -> dict[str, Any]:
    """
    Return provenance when the snapshot is a supported candle dataset.

    Raises UnsupportedCandleDatasetError for legacy/unsupported formats.
    """
    if snapshot.status is not DatasetSnapshotStatus.PUBLISHED:
        msg = "Dataset snapshot is not published"
        raise DatasetIntegrityError(msg)
    if snapshot.exchange is not Market.BINANCE_FUTURES:
        msg = "Candle querying supports only binance_futures exchange snapshots"
        raise UnsupportedCandleDatasetError(msg)
    if snapshot.manifest_version != SUPPORTED_MANIFEST_VERSION:
        msg = (
            "Candle querying supports only manifest version 2 canonical Binance "
            "imports; this dataset uses an unsupported candle schema"
        )
        raise UnsupportedCandleDatasetError(msg)

    summary = snapshot.validation_summary or {}
    provenance = summary.get("provenance")
    if not isinstance(provenance, dict):
        msg = "Supported candle datasets must include provenance"
        raise DatasetIntegrityError(msg)

    if provenance.get("provider") != SUPPORTED_PROVIDER:
        msg = "Candle querying supports only Binance-imported datasets"
        raise UnsupportedCandleDatasetError(msg)
    if provenance.get("market") != SUPPORTED_MARKET:
        msg = "Candle querying supports only binance_futures market datasets"
        raise UnsupportedCandleDatasetError(msg)
    if provenance.get("data_type") != SUPPORTED_DATA_TYPE:
        msg = "Candle querying supports only contract_klines datasets"
        raise UnsupportedCandleDatasetError(msg)
    if provenance.get("canonical_schema_version") != CANONICAL_SCHEMA_VERSION:
        msg = "Candle querying supports only canonical schema version 1"
        raise UnsupportedCandleDatasetError(msg)
    if provenance.get("endpoint_path") != SUPPORTED_ENDPOINT_PATH:
        msg = "Provenance endpoint path does not match the supported Binance klines path"
        raise DatasetIntegrityError(msg)
    return provenance


def find_partition(
    snapshot: DatasetSnapshot,
    *,
    symbol: Symbol,
    timeframe: Timeframe,
) -> DatasetPartition:
    matches = [
        part
        for part in snapshot.partitions
        if part.symbol.value == symbol.value and part.timeframe == timeframe
    ]
    if not matches:
        msg = f"Partition not found for {symbol.value}/{timeframe.value}"
        raise CandlePartitionNotFoundError(msg)
    if len(matches) != 1:
        msg = "Partition metadata is ambiguous"
        raise DatasetIntegrityError(msg)
    return matches[0]


def verify_snapshot_manifest(snapshot: DatasetSnapshot) -> str:
    if snapshot.content_hash is None:
        msg = "Published snapshot is missing content_hash"
        raise DatasetIntegrityError(msg)
    document = build_manifest_document(snapshot)
    digest = hash_manifest_document(document)
    if digest != snapshot.content_hash:
        msg = "Stored manifest hash does not match rebuilt canonical hash"
        raise DatasetIntegrityError(msg)
    return digest


def verify_source_page_artifacts(
    provenance: dict[str, Any],
    artifact_store: LocalFilesystemArtifactStore,
) -> int:
    pages = provenance.get("source_pages")
    if not isinstance(pages, list) or not pages:
        msg = "Provenance is missing raw source-page artifacts"
        raise DatasetIntegrityError(msg)
    verified = 0
    for page in pages:
        meta = _require_mapping(page, label="source page metadata")
        try:
            key = validate_artifact_key(str(meta["artifact_key"]))
            expected_sha = str(meta["sha256"])
            expected_size = int(meta["byte_size"])
        except (KeyError, TypeError, ValueError) as exc:
            msg = "Source page metadata is invalid"
            raise DatasetIntegrityError(msg) from exc
        try:
            stored = artifact_store.get_metadata(key)
            data = artifact_store.open_bytes(key)
        except ArtifactStoreError as exc:
            msg = "Source page artifact verification failed"
            raise DatasetIntegrityError(msg) from exc
        if stored.key != key:
            msg = "Source page artifact metadata key mismatch"
            raise DatasetIntegrityError(msg)
        if stored.media_type is not MediaType.JSON:
            msg = "Source page artifact media type must be application/json"
            raise DatasetIntegrityError(msg)
        if stored.sha256 != expected_sha or stored.byte_size != expected_size:
            msg = "Source page artifact metadata mismatch"
            raise DatasetIntegrityError(msg)
        digest = sha256_hex(data)
        if digest != expected_sha or len(data) != expected_size:
            msg = "Source page artifact content mismatch"
            raise DatasetIntegrityError(msg)
        if key.rsplit("/", maxsplit=1)[-1] != digest:
            msg = "Source page artifact key does not match content hash"
            raise DatasetIntegrityError(msg)
        verified += 1
    return verified


def verify_partition_against_provenance(
    partition: DatasetPartition,
    provenance: dict[str, Any],
) -> None:
    normalized = _require_mapping(
        provenance.get("normalized_partition"),
        label="normalized partition provenance",
    )
    if normalized.get("artifact_key") != partition.artifact_key:
        msg = "Normalized partition artifact key mismatch"
        raise DatasetIntegrityError(msg)
    if normalized.get("sha256") != partition.sha256:
        msg = "Normalized partition SHA-256 mismatch"
        raise DatasetIntegrityError(msg)
    if int(normalized.get("byte_size", -1)) != partition.byte_size:
        msg = "Normalized partition byte size mismatch"
        raise DatasetIntegrityError(msg)
    if int(normalized.get("row_count", -1)) != partition.row_count:
        msg = "Normalized partition row count mismatch"
        raise DatasetIntegrityError(msg)
    if normalized.get("media_type") != MediaType.CSV.value:
        msg = "Normalized partition media type mismatch"
        raise DatasetIntegrityError(msg)
    if provenance.get("symbol") != partition.symbol.value:
        msg = "Provenance symbol mismatch"
        raise DatasetIntegrityError(msg)
    if provenance.get("timeframe") != partition.timeframe.value:
        msg = "Provenance timeframe mismatch"
        raise DatasetIntegrityError(msg)


def verify_snapshot_partition_totals(snapshot: DatasetSnapshot) -> None:
    partition_rows = sum(part.row_count for part in snapshot.partitions)
    if partition_rows != snapshot.total_rows:
        msg = "Snapshot total_rows does not equal partition totals"
        raise DatasetIntegrityError(msg)
    if not snapshot.partitions:
        msg = "Published candle dataset has no partitions"
        raise DatasetIntegrityError(msg)
    mins = [part.minimum_open_time for part in snapshot.partitions if part.minimum_open_time]
    maxs = [part.maximum_open_time for part in snapshot.partitions if part.maximum_open_time]
    if mins and snapshot.minimum_open_time not in (None, min(mins)):
        msg = "Snapshot minimum_open_time is inconsistent with partitions"
        raise DatasetIntegrityError(msg)
    if maxs and snapshot.maximum_open_time not in (None, max(maxs)):
        msg = "Snapshot maximum_open_time is inconsistent with partitions"
        raise DatasetIntegrityError(msg)


def verify_candle_dataset(
    snapshot: DatasetSnapshot,
    *,
    symbol: Symbol,
    timeframe: Timeframe,
    artifact_store: LocalFilesystemArtifactStore,
    reader: CandlePartitionReader,
) -> VerifiedCandleDataset:
    """Fully verify a published candle dataset partition before querying."""
    provenance = assert_supported_candle_dataset(snapshot)
    content_hash = verify_snapshot_manifest(snapshot)
    verify_snapshot_partition_totals(snapshot)
    partition = find_partition(snapshot, symbol=symbol, timeframe=timeframe)
    verify_partition_against_provenance(partition, provenance)

    # Manifest partitions must agree with DB partition metadata.
    document = build_manifest_document(snapshot)
    manifest_parts = document.get("partitions")
    if not isinstance(manifest_parts, list):
        msg = "Manifest partitions are missing"
        raise DatasetIntegrityError(msg)
    matched = [
        item
        for item in manifest_parts
        if isinstance(item, dict)
        and item.get("symbol") == symbol.value
        and item.get("timeframe") == timeframe.value
    ]
    if len(matched) != 1:
        msg = "Manifest partition metadata mismatch"
        raise DatasetIntegrityError(msg)
    item = matched[0]
    if (
        item.get("artifact_key") != partition.artifact_key
        or item.get("sha256") != partition.sha256
        or int(item.get("byte_size", -1)) != partition.byte_size
        or int(item.get("row_count", -1)) != partition.row_count
    ):
        msg = "Manifest partition fields do not match stored partition"
        raise DatasetIntegrityError(msg)

    source_pages = verify_source_page_artifacts(provenance, artifact_store)
    try:
        verified = reader.read_verified(
            artifact_key=partition.artifact_key,
            expected_sha256=partition.sha256,
            expected_byte_size=partition.byte_size,
            symbol=symbol,
            timeframe=timeframe,
            expected_row_count=partition.row_count,
            expected_minimum_open_time=partition.minimum_open_time,
            expected_maximum_open_time=partition.maximum_open_time,
        )
    except CandlePartitionIntegrityError:
        raise
    except Exception as exc:  # noqa: BLE001 — sanitize unexpected store failures
        msg = "Partition verification failed"
        raise CandlePartitionIntegrityError(msg) from exc

    expected_count = provenance.get("expected_candle_count")
    actual_count = provenance.get("actual_candle_count")
    if expected_count != verified.row_count or actual_count != verified.row_count:
        msg = "Provenance candle counts do not match verified partition"
        raise DatasetIntegrityError(msg)

    return VerifiedCandleDataset(
        snapshot=snapshot,
        partition=partition,
        provenance=provenance,
        verified_partition=verified,
        verified_source_page_count=source_pages,
        content_hash=content_hash,
    )
