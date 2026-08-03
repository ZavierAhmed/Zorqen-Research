"""Dataset repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from zorqen_research.domain.datasets import (
    DatasetPartition,
    DatasetSnapshot,
    DatasetSnapshotStatus,
)
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.database.models.dataset_partition import (
    DatasetPartitionModel,
)
from zorqen_research.infrastructure.database.models.dataset_snapshot import (
    DatasetSnapshotModel,
)


def _partition_to_domain(row: DatasetPartitionModel) -> DatasetPartition:
    return DatasetPartition(
        id=row.id,
        dataset_snapshot_id=row.dataset_snapshot_id,
        symbol=Symbol(value=row.symbol),
        timeframe=Timeframe(row.timeframe),
        artifact_key=row.artifact_key,
        sha256=row.sha256,
        byte_size=row.byte_size,
        row_count=row.row_count,
        minimum_open_time=row.minimum_open_time,
        maximum_open_time=row.maximum_open_time,
        created_at=row.created_at,
    )


def _snapshot_to_domain(row: DatasetSnapshotModel) -> DatasetSnapshot:
    partitions = tuple(_partition_to_domain(item) for item in row.partitions)
    return DatasetSnapshot(
        id=row.id,
        name=row.name,
        description=row.description,
        exchange=Market(row.exchange),
        status=DatasetSnapshotStatus(row.status),
        manifest_version=row.manifest_version,
        content_hash=row.content_hash,
        total_rows=row.total_rows,
        minimum_open_time=row.minimum_open_time,
        maximum_open_time=row.maximum_open_time,
        created_at=row.created_at,
        published_at=row.published_at,
        validation_summary=dict(row.validation_summary or {}),
        partitions=partitions,
    )


class DatasetRepository:
    """Persistence for dataset snapshots and partitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> DatasetSnapshot | None:
        stmt = (
            select(DatasetSnapshotModel)
            .options(selectinload(DatasetSnapshotModel.partitions))
            .where(DatasetSnapshotModel.name == name)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else _snapshot_to_domain(row)

    async def get_published_by_id(self, snapshot_id: UUID) -> DatasetSnapshot | None:
        stmt = (
            select(DatasetSnapshotModel)
            .options(selectinload(DatasetSnapshotModel.partitions))
            .where(
                DatasetSnapshotModel.id == snapshot_id,
                DatasetSnapshotModel.status == DatasetSnapshotStatus.PUBLISHED.value,
            )
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else _snapshot_to_domain(row)

    async def list_published(self) -> list[DatasetSnapshot]:
        stmt = (
            select(DatasetSnapshotModel)
            .options(selectinload(DatasetSnapshotModel.partitions))
            .where(DatasetSnapshotModel.status == DatasetSnapshotStatus.PUBLISHED.value)
            .order_by(
                DatasetSnapshotModel.published_at.desc(),
                DatasetSnapshotModel.name.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return [_snapshot_to_domain(row) for row in result.scalars().all()]

    async def create_published_snapshot(
        self,
        *,
        name: str,
        description: str | None,
        exchange: Market,
        manifest_version: str,
        content_hash: str,
        total_rows: int,
        minimum_open_time: datetime | None,
        maximum_open_time: datetime | None,
        published_at: datetime,
        validation_summary: dict[str, Any],
        partitions: list[dict[str, Any]],
        snapshot_id: UUID | None = None,
    ) -> DatasetSnapshot:
        """Create a published snapshot and partitions in the current transaction."""
        snap_id = snapshot_id or uuid4()
        snapshot = DatasetSnapshotModel(
            id=snap_id,
            name=name,
            description=description,
            exchange=exchange.value,
            status=DatasetSnapshotStatus.PUBLISHED.value,
            manifest_version=manifest_version,
            content_hash=content_hash,
            total_rows=total_rows,
            minimum_open_time=minimum_open_time,
            maximum_open_time=maximum_open_time,
            published_at=published_at,
            validation_summary=validation_summary,
        )
        self._session.add(snapshot)
        await self._session.flush()

        for item in partitions:
            self._session.add(
                DatasetPartitionModel(
                    id=item.get("id", uuid4()),
                    dataset_snapshot_id=snap_id,
                    symbol=item["symbol"],
                    timeframe=item["timeframe"],
                    artifact_key=item["artifact_key"],
                    sha256=item["sha256"],
                    byte_size=item["byte_size"],
                    row_count=item["row_count"],
                    minimum_open_time=item["minimum_open_time"],
                    maximum_open_time=item["maximum_open_time"],
                )
            )
        await self._session.flush()

        loaded = await self.get_published_by_id(snap_id)
        if loaded is None:
            msg = "Failed to load published snapshot after insert"
            raise RuntimeError(msg)
        return loaded
