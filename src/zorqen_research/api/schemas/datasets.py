"""Read-only dataset API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zorqen_research.domain.datasets import DatasetPartition, DatasetSnapshot


class ErrorResponse(BaseModel):
    detail: str


class DatasetPartitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    symbol: str
    timeframe: str
    artifact_key: str
    sha256: str
    byte_size: int
    row_count: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime


class DatasetSnapshotSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    description: str | None
    exchange: str
    status: str
    manifest_version: str
    content_hash: str
    total_rows: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime
    published_at: datetime
    validation_summary: dict[str, Any]
    partition_count: int = Field(ge=0)


class DatasetSnapshotDetailResponse(DatasetSnapshotSummaryResponse):
    partitions: list[DatasetPartitionResponse]


class DatasetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DatasetSnapshotSummaryResponse]
    count: int


def partition_to_response(partition: DatasetPartition) -> DatasetPartitionResponse:
    return DatasetPartitionResponse(
        id=partition.id,
        symbol=partition.symbol.value,
        timeframe=partition.timeframe.value,
        artifact_key=partition.artifact_key,
        sha256=partition.sha256,
        byte_size=partition.byte_size,
        row_count=partition.row_count,
        minimum_open_time=partition.minimum_open_time,
        maximum_open_time=partition.maximum_open_time,
        created_at=partition.created_at,
    )


def snapshot_to_summary(snapshot: DatasetSnapshot) -> DatasetSnapshotSummaryResponse:
    if snapshot.content_hash is None or snapshot.published_at is None:
        msg = "Published snapshot is missing content_hash or published_at"
        raise RuntimeError(msg)
    return DatasetSnapshotSummaryResponse(
        id=snapshot.id,
        name=snapshot.name,
        description=snapshot.description,
        exchange=snapshot.exchange.value,
        status=snapshot.status.value,
        manifest_version=snapshot.manifest_version,
        content_hash=snapshot.content_hash,
        total_rows=snapshot.total_rows,
        minimum_open_time=snapshot.minimum_open_time,
        maximum_open_time=snapshot.maximum_open_time,
        created_at=snapshot.created_at,
        published_at=snapshot.published_at,
        validation_summary=dict(snapshot.validation_summary),
        partition_count=len(snapshot.partitions),
    )


def snapshot_to_detail(snapshot: DatasetSnapshot) -> DatasetSnapshotDetailResponse:
    summary = snapshot_to_summary(snapshot)
    partitions = sorted(
        snapshot.partitions,
        key=lambda item: (item.symbol.value, item.timeframe.value),
    )
    return DatasetSnapshotDetailResponse(
        **summary.model_dump(),
        partitions=[partition_to_response(item) for item in partitions],
    )
