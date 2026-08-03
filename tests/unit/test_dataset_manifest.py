"""Unit tests for dataset manifests and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from zorqen_research.application.datasets.manifest import (
    build_and_hash_manifest,
    build_manifest_document,
    canonical_manifest_bytes,
    hash_manifest_document,
)
from zorqen_research.domain.datasets import (
    DatasetPartition,
    DatasetSnapshot,
    DatasetSnapshotStatus,
    assert_can_modify,
    assert_can_publish,
)
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def _snapshot(**overrides: object) -> DatasetSnapshot:
    snapshot_id = uuid4()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    partition = DatasetPartition(
        id=uuid4(),
        dataset_snapshot_id=snapshot_id,
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.H1,
        artifact_key="sha256/ab/cd/" + ("a" * 64),
        sha256="a" * 64,
        byte_size=10,
        row_count=2,
        minimum_open_time=now,
        maximum_open_time=now,
        created_at=now,
    )
    base = {
        "id": snapshot_id,
        "name": "demo",
        "description": None,
        "exchange": Market.BINANCE_FUTURES,
        "status": DatasetSnapshotStatus.PUBLISHED,
        "manifest_version": "1",
        "content_hash": None,
        "total_rows": 2,
        "minimum_open_time": now,
        "maximum_open_time": now,
        "created_at": now,
        "published_at": now,
        "validation_summary": {"passed": True},
        "partitions": (partition,),
    }
    base.update(overrides)
    return DatasetSnapshot(**base)  # type: ignore[arg-type]


def test_manifest_ordering_and_stable_hash() -> None:
    snap = _snapshot()
    doc1, hash1, raw1 = build_and_hash_manifest(snap)
    # Different identity/timestamp must not change the logical content hash.
    snap2 = _snapshot(
        id=uuid4(),
        published_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
        created_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
    )
    # Keep partition content identical to snap for a fair logical comparison.
    part = snap.partitions[0]
    snap2 = DatasetSnapshot(
        id=uuid4(),
        name=snap.name,
        description=snap.description,
        exchange=snap.exchange,
        status=snap.status,
        manifest_version=snap.manifest_version,
        content_hash=None,
        total_rows=snap.total_rows,
        minimum_open_time=snap.minimum_open_time,
        maximum_open_time=snap.maximum_open_time,
        created_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
        published_at=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
        validation_summary=snap.validation_summary,
        partitions=(part,),
    )
    doc2, hash2, _raw2 = build_and_hash_manifest(snap2)
    assert hash1 == hash2
    assert list(doc1.keys()) == sorted(doc1.keys())
    assert list(doc1["partitions"][0].keys()) == sorted(doc1["partitions"][0].keys())
    assert hash_manifest_document(doc1) == hash1
    assert canonical_manifest_bytes(build_manifest_document(snap)).startswith(b"{")
    assert doc1["dataset_snapshot_id"] != doc2["dataset_snapshot_id"]
    assert raw1 != canonical_manifest_bytes(doc2)


def test_lifecycle_transitions() -> None:
    assert_can_publish(DatasetSnapshotStatus.DRAFT)
    with pytest.raises(ValueError, match="Rejected"):
        assert_can_publish(DatasetSnapshotStatus.REJECTED)
    with pytest.raises(ValueError, match="immutable"):
        assert_can_publish(DatasetSnapshotStatus.PUBLISHED)
    with pytest.raises(ValueError, match="immutable"):
        assert_can_modify(DatasetSnapshotStatus.PUBLISHED)
    assert_can_modify(DatasetSnapshotStatus.DRAFT)
