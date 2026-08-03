"""Dataset application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.application.audit.service import AuditEventService
from zorqen_research.application.datasets.fixture_validation import validate_fixture_csv
from zorqen_research.application.datasets.manifest import (
    build_and_hash_manifest,
    build_manifest_document,
    canonical_manifest_bytes,
    hash_manifest_document,
)
from zorqen_research.domain.artifacts import MediaType
from zorqen_research.domain.audit import AuditEventAppendCommand
from zorqen_research.domain.datasets import (
    MANIFEST_VERSION,
    DatasetPartition,
    DatasetSnapshot,
    DatasetSnapshotStatus,
    assert_can_modify,
    assert_can_publish,
)
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.database.repositories.datasets import DatasetRepository

FIXTURE_DATASET_NAME = "fixture_binance_futures_btcusdt_1h"
FIXTURE_FILENAME = "btcusdt_1h_fixture.csv"
# Test-tree path (also mirrored under zorqen_research.datasets.fixtures for packaging).
DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "market_data" / FIXTURE_FILENAME
)


class DatasetNotFoundError(LookupError):
    """Published dataset snapshot was not found."""


class DatasetDuplicateError(RuntimeError):
    """Fixture (or named dataset) already exists with conflicting content."""


@dataclass(frozen=True, slots=True)
class FixturePublishResult:
    snapshot_id: UUID
    content_hash: str
    created: bool
    partition_count: int
    total_rows: int


def _provisional_partition(
    *,
    snapshot_id: UUID,
    artifact_key: str,
    sha256: str,
    byte_size: int,
    row_count: int,
    minimum_open_time: datetime,
    maximum_open_time: datetime,
    created_at: datetime,
) -> DatasetPartition:
    return DatasetPartition(
        id=uuid4(),
        dataset_snapshot_id=snapshot_id,
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.H1,
        artifact_key=artifact_key,
        sha256=sha256,
        byte_size=byte_size,
        row_count=row_count,
        minimum_open_time=minimum_open_time,
        maximum_open_time=maximum_open_time,
        created_at=created_at,
    )


class DatasetService:
    """Read-only dataset queries and fixture publication."""

    def __init__(
        self,
        session: AsyncSession,
        artifact_store: LocalFilesystemArtifactStore,
    ) -> None:
        self._session = session
        self._repo = DatasetRepository(session)
        self._audit = AuditEventService(session)
        self._artifacts = artifact_store

    async def list_published(self) -> list[DatasetSnapshot]:
        return await self._repo.list_published()

    async def get_published(self, snapshot_id: UUID) -> DatasetSnapshot:
        snapshot = await self._repo.get_published_by_id(snapshot_id)
        if snapshot is None:
            msg = f"Published dataset snapshot not found: {snapshot_id}"
            raise DatasetNotFoundError(msg)
        return snapshot

    async def get_published_manifest(self, snapshot_id: UUID) -> dict[str, Any]:
        snapshot = await self.get_published(snapshot_id)
        document = build_manifest_document(snapshot)
        digest = hash_manifest_document(document)
        if snapshot.content_hash is None or digest != snapshot.content_hash:
            msg = "Stored manifest hash does not match canonical bytes"
            raise RuntimeError(msg)
        document["content_hash"] = snapshot.content_hash
        return document

    def assert_immutable(self, snapshot: DatasetSnapshot) -> None:
        assert_can_modify(snapshot.status)

    def assert_publishable(self, status: DatasetSnapshotStatus) -> None:
        assert_can_publish(status)

    async def publish_fixture(
        self,
        *,
        fixture_path: Path | None = None,
    ) -> FixturePublishResult:
        """
        Publish the deterministic local BTCUSDT 1h fixture.

        Idempotency policy:
        - If a published snapshot with the fixture name already exists and its
          content_hash matches the newly computed manifest hash, return it.
        - If a snapshot with the same name exists with a different hash or
          non-published status, raise DatasetDuplicateError.
        """
        path = fixture_path or DEFAULT_FIXTURE_PATH
        raw = path.read_bytes()
        validation = validate_fixture_csv(raw)

        artifact = self._artifacts.publish_bytes(
            raw,
            media_type=MediaType.CSV,
            original_filename=path.name,
        )

        published_at = datetime.now(UTC)
        snapshot_id = uuid4()
        provisional = DatasetSnapshot(
            id=snapshot_id,
            name=FIXTURE_DATASET_NAME,
            description="Deterministic BTCUSDT 1h fixture for storage/manifest verification",
            exchange=Market.BINANCE_FUTURES,
            status=DatasetSnapshotStatus.PUBLISHED,
            manifest_version=MANIFEST_VERSION,
            content_hash=None,
            total_rows=validation.row_count,
            minimum_open_time=validation.minimum_open_time,
            maximum_open_time=validation.maximum_open_time,
            created_at=published_at,
            published_at=published_at,
            validation_summary=validation.summary,
            partitions=(
                _provisional_partition(
                    snapshot_id=snapshot_id,
                    artifact_key=artifact.key,
                    sha256=artifact.sha256,
                    byte_size=artifact.byte_size,
                    row_count=validation.row_count,
                    minimum_open_time=validation.minimum_open_time,
                    maximum_open_time=validation.maximum_open_time,
                    created_at=published_at,
                ),
            ),
        )
        _document, content_hash, _encoded = build_and_hash_manifest(provisional)

        existing = await self._repo.get_by_name(FIXTURE_DATASET_NAME)
        if existing is not None:
            if (
                existing.status is DatasetSnapshotStatus.PUBLISHED
                and existing.content_hash == content_hash
            ):
                return FixturePublishResult(
                    snapshot_id=existing.id,
                    content_hash=content_hash,
                    created=False,
                    partition_count=len(existing.partitions),
                    total_rows=existing.total_rows,
                )
            msg = (
                f"Dataset {FIXTURE_DATASET_NAME!r} already exists with conflicting state "
                f"(status={existing.status.value}, content_hash={existing.content_hash!r})"
            )
            raise DatasetDuplicateError(msg)

        partition_payload: list[dict[str, Any]] = [
            {
                "symbol": "BTCUSDT",
                "timeframe": Timeframe.H1.value,
                "artifact_key": artifact.key,
                "sha256": artifact.sha256,
                "byte_size": artifact.byte_size,
                "row_count": validation.row_count,
                "minimum_open_time": validation.minimum_open_time,
                "maximum_open_time": validation.maximum_open_time,
            }
        ]

        snapshot = await self._repo.create_published_snapshot(
            snapshot_id=snapshot_id,
            name=FIXTURE_DATASET_NAME,
            description=provisional.description,
            exchange=Market.BINANCE_FUTURES,
            manifest_version=MANIFEST_VERSION,
            content_hash=content_hash,
            total_rows=validation.row_count,
            minimum_open_time=validation.minimum_open_time,
            maximum_open_time=validation.maximum_open_time,
            published_at=published_at,
            validation_summary=validation.summary,
            partitions=partition_payload,
        )

        await self._audit.append(
            AuditEventAppendCommand(
                actor_type="system",
                action="dataset_snapshot.published",
                entity_type="dataset_snapshot",
                entity_id=str(snapshot.id),
                payload={
                    "dataset_name": snapshot.name,
                    "exchange": snapshot.exchange.value,
                    "manifest_hash": content_hash,
                    "partition_count": len(snapshot.partitions),
                    "total_rows": snapshot.total_rows,
                },
            )
        )
        await self._session.commit()

        return FixturePublishResult(
            snapshot_id=snapshot.id,
            content_hash=content_hash,
            created=True,
            partition_count=len(snapshot.partitions),
            total_rows=snapshot.total_rows,
        )


def canonical_manifest_text(document: dict[str, Any]) -> str:
    """Return UTF-8 canonical manifest text (for tests/CLI)."""
    return canonical_manifest_bytes(document).decode("utf-8")
