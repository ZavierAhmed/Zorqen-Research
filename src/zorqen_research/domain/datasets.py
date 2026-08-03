"""Dataset snapshot / partition domain models and lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


class DatasetSnapshotStatus(StrEnum):
    """Allowed dataset snapshot statuses."""

    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"


MANIFEST_VERSION = "1"


@dataclass(frozen=True, slots=True)
class DatasetPartition:
    """One immutable artifact belonging to a dataset snapshot."""

    id: UUID
    dataset_snapshot_id: UUID
    symbol: Symbol
    timeframe: Timeframe
    artifact_key: str
    sha256: str
    byte_size: int
    row_count: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    """Dataset snapshot metadata (large data lives in the artifact store)."""

    id: UUID
    name: str
    description: str | None
    exchange: Market
    status: DatasetSnapshotStatus
    manifest_version: str
    content_hash: str | None
    total_rows: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime
    published_at: datetime | None
    validation_summary: dict[str, Any]
    partitions: tuple[DatasetPartition, ...] = ()


def assert_can_publish(status: DatasetSnapshotStatus) -> None:
    """Reject illegal publication transitions."""
    if status is DatasetSnapshotStatus.REJECTED:
        msg = "Rejected snapshots cannot be published"
        raise ValueError(msg)
    if status is DatasetSnapshotStatus.PUBLISHED:
        msg = "Published snapshots are immutable and cannot be republished"
        raise ValueError(msg)


def assert_can_modify(status: DatasetSnapshotStatus) -> None:
    """Published snapshots reject modification through application services."""
    if status is DatasetSnapshotStatus.PUBLISHED:
        msg = "Published snapshots are immutable"
        raise ValueError(msg)
