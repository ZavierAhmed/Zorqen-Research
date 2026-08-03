"""PostgreSQL integration tests for dataset manifests and fixture publication."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers import lifespan_client
from zorqen_research.api.app import create_app
from zorqen_research.application.datasets.service import (
    FIXTURE_DATASET_NAME,
    DatasetDuplicateError,
    DatasetService,
)
from zorqen_research.core.config import Settings, clear_settings_cache
from zorqen_research.domain.datasets import DatasetSnapshotStatus
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.database.engine import check_database_ready
from zorqen_research.infrastructure.database.models.dataset_partition import (
    DatasetPartitionModel,
)
from zorqen_research.infrastructure.database.models.dataset_snapshot import (
    DatasetSnapshotModel,
)

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "market_data" / "btcusdt_1h_fixture.csv"


def _require_postgres(async_url: str) -> None:
    import asyncio

    async def _probe() -> bool:
        engine = create_async_engine(async_url)
        try:
            return await check_database_ready(engine)
        finally:
            await engine.dispose()

    if not asyncio.run(_probe()):
        if os.environ.get("CI"):
            pytest.fail("PostgreSQL is required for integration tests in CI")
        pytest.skip("PostgreSQL is not available for integration tests")


@pytest.fixture(scope="module")
def integration_urls() -> tuple[str, str]:
    async_url = os.environ.get(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    sync_url = os.environ.get(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    _require_postgres(async_url)
    return async_url, sync_url


@pytest.fixture
def integration_settings(
    integration_urls: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    async_url, sync_url = integration_urls
    monkeypatch.setenv("ZORQEN_ENVIRONMENT", "test")
    monkeypatch.setenv("ZORQEN_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ZORQEN_DATABASE_URL", async_url)
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", sync_url)
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    clear_settings_cache()
    return Settings()


def _alembic(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def alembic_env(integration_settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    env["ZORQEN_DATABASE_URL"] = integration_settings.database_url
    env["ZORQEN_DATABASE_URL_SYNC"] = integration_settings.database_url_sync
    return env


@pytest.fixture
async def migrated_session(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> AsyncSession:
    _alembic(alembic_env, "upgrade", "head")
    engine = create_async_engine(integration_settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_migration_creates_dataset_tables(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    engine = create_async_engine(integration_settings.database_url)
    try:
        async with engine.connect() as conn:
            snaps = await conn.execute(text("SELECT to_regclass('public.dataset_snapshots')"))
            parts = await conn.execute(text("SELECT to_regclass('public.dataset_partitions')"))
            assert snaps.scalar_one() == "dataset_snapshots"
            assert parts.scalar_one() == "dataset_partitions"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_constraints_reject_invalid_status_symbol_timeframe(
    migrated_session: AsyncSession,
) -> None:
    session = migrated_session
    snap_id = uuid4()
    session.add(
        DatasetSnapshotModel(
            id=snap_id,
            name=f"draft-{snap_id}",
            description=None,
            exchange="binance_futures",
            status="draft",
            manifest_version="1",
            content_hash=None,
            total_rows=0,
            validation_summary={},
        )
    )
    await session.commit()

    session.add(
        DatasetSnapshotModel(
            id=uuid4(),
            name=f"bad-status-{uuid4()}",
            description=None,
            exchange="binance_futures",
            status="live",
            manifest_version="1",
            content_hash=None,
            total_rows=0,
            validation_summary={},
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    session.add(
        DatasetPartitionModel(
            id=uuid4(),
            dataset_snapshot_id=snap_id,
            symbol="SOLUSDT",
            timeframe="1h",
            artifact_key="sha256/aa/bb/" + ("a" * 64),
            sha256="a" * 64,
            byte_size=1,
            row_count=1,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    session.add(
        DatasetPartitionModel(
            id=uuid4(),
            dataset_snapshot_id=snap_id,
            symbol="BTCUSDT",
            timeframe="60m",
            artifact_key="sha256/aa/bb/" + ("b" * 64),
            sha256="b" * 64,
            byte_size=1,
            row_count=1,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_duplicate_partition_and_orphan_rejected(
    migrated_session: AsyncSession,
) -> None:
    session = migrated_session
    snap_id = uuid4()
    session.add(
        DatasetSnapshotModel(
            id=snap_id,
            name=f"parts-{snap_id}",
            description=None,
            exchange="binance_futures",
            status="draft",
            manifest_version="1",
            content_hash=None,
            total_rows=0,
            validation_summary={},
        )
    )
    await session.flush()
    key = "sha256/aa/bb/" + ("c" * 64)
    session.add(
        DatasetPartitionModel(
            id=uuid4(),
            dataset_snapshot_id=snap_id,
            symbol="BTCUSDT",
            timeframe="1h",
            artifact_key=key,
            sha256="c" * 64,
            byte_size=1,
            row_count=1,
        )
    )
    await session.commit()

    session.add(
        DatasetPartitionModel(
            id=uuid4(),
            dataset_snapshot_id=snap_id,
            symbol="BTCUSDT",
            timeframe="1h",
            artifact_key="sha256/aa/bb/" + ("d" * 64),
            sha256="d" * 64,
            byte_size=1,
            row_count=1,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    session.add(
        DatasetPartitionModel(
            id=uuid4(),
            dataset_snapshot_id=uuid4(),
            symbol="BTCUSDT",
            timeframe="1h",
            artifact_key="sha256/aa/bb/" + ("e" * 64),
            sha256="e" * 64,
            byte_size=1,
            row_count=1,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_fixture_publication_api_and_idempotency(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    engine = create_async_engine(integration_settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await session.execute(text("DELETE FROM dataset_partitions"))
            await session.execute(
                text("DELETE FROM dataset_snapshots WHERE name = :name"),
                {"name": FIXTURE_DATASET_NAME},
            )
            await session.execute(
                text("DELETE FROM audit_events WHERE action = 'dataset_snapshot.published'")
            )
            await session.commit()

        async with factory() as session:
            service = DatasetService(session, store)
            first = await service.publish_fixture(fixture_path=FIXTURE_PATH)
            assert first.created is True
            assert first.partition_count == 1
            assert first.total_rows == 5

        async with factory() as session:
            service = DatasetService(session, store)
            second = await service.publish_fixture(fixture_path=FIXTURE_PATH)
            assert second.created is False
            assert second.snapshot_id == first.snapshot_id
            assert second.content_hash == first.content_hash

        async with factory() as session:
            result = await session.execute(
                text(
                    "SELECT status, content_hash, total_rows FROM dataset_snapshots WHERE id = :id"
                ),
                {"id": first.snapshot_id},
            )
            row = result.one()
            assert row.status == "published"
            assert row.content_hash == first.content_hash
            assert row.total_rows == 5

            parts = await session.execute(
                text(
                    "SELECT symbol, timeframe, sha256, row_count, byte_size, artifact_key "
                    "FROM dataset_partitions WHERE dataset_snapshot_id = :id"
                ),
                {"id": first.snapshot_id},
            )
            part = parts.one()
            assert part.symbol == "BTCUSDT"
            assert part.timeframe == "1h"
            assert part.row_count == 5
            artifact_bytes = store.open_bytes(part.artifact_key)
            verified_meta = store.get_metadata(part.artifact_key)
            assert verified_meta.sha256 == part.sha256
            assert verified_meta.key == part.artifact_key
            assert verified_meta.byte_size == part.byte_size
            from zorqen_research.domain.artifacts import sha256_hex

            assert sha256_hex(artifact_bytes) == part.sha256
            assert sha256_hex(artifact_bytes) == verified_meta.sha256
            assert len(artifact_bytes) == verified_meta.byte_size

            audits = await session.execute(
                text(
                    "SELECT actor_type, action, entity_type, entity_id, payload "
                    "FROM audit_events WHERE entity_id = :id"
                ),
                {"id": str(first.snapshot_id)},
            )
            audit = audits.one()
            assert audit.actor_type == "system"
            assert audit.action == "dataset_snapshot.published"
            assert audit.entity_type == "dataset_snapshot"
            assert audit.payload["manifest_hash"] == first.content_hash
            assert audit.payload["partition_count"] == 1
            assert audit.payload["total_rows"] == 5

        # Hidden draft/rejected
        async with factory() as session:
            draft_id = uuid4()
            rejected_id = uuid4()
            session.add(
                DatasetSnapshotModel(
                    id=draft_id,
                    name=f"draft-hidden-{draft_id}",
                    description=None,
                    exchange="binance_futures",
                    status=DatasetSnapshotStatus.DRAFT.value,
                    manifest_version="1",
                    content_hash=None,
                    total_rows=0,
                    validation_summary={},
                )
            )
            session.add(
                DatasetSnapshotModel(
                    id=rejected_id,
                    name=f"rejected-hidden-{rejected_id}",
                    description=None,
                    exchange="binance_futures",
                    status=DatasetSnapshotStatus.REJECTED.value,
                    manifest_version="1",
                    content_hash=None,
                    total_rows=0,
                    validation_summary={},
                )
            )
            await session.commit()

        clear_settings_cache()
        app = create_app(integration_settings)
        async with lifespan_client(app) as client:
            listed = await client.get("/api/v1/datasets")
            assert listed.status_code == 200
            body = listed.json()
            assert body["count"] >= 1
            ids = {item["id"] for item in body["items"]}
            assert str(first.snapshot_id) in ids
            assert str(draft_id) not in ids
            assert str(rejected_id) not in ids
            assert all("C:\\" not in str(item) for item in body["items"])

            detail = await client.get(f"/api/v1/datasets/{first.snapshot_id}")
            assert detail.status_code == 200
            detail_body = detail.json()
            assert detail_body["content_hash"] == first.content_hash
            assert len(detail_body["partitions"]) == 1
            assert detail_body["partitions"][0]["symbol"] == "BTCUSDT"

            manifest = await client.get(f"/api/v1/datasets/{first.snapshot_id}/manifest")
            assert manifest.status_code == 200
            manifest_body = manifest.json()
            assert manifest_body["content_hash"] == first.content_hash
            assert (
                ":"
                not in str(manifest_body.get("partitions", [{}])[0].get("artifact_key", "")).split(
                    "/"
                )[0]
            )

            missing = await client.get(f"/api/v1/datasets/{uuid4()}")
            assert missing.status_code == 404
            unpublished = await client.get(f"/api/v1/datasets/{draft_id}")
            assert unpublished.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_publication_rollback_leaves_no_partial_state(
    integration_settings: Settings,
    alembic_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    engine = create_async_engine(integration_settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await session.execute(text("DELETE FROM dataset_partitions"))
            await session.execute(
                text("DELETE FROM dataset_snapshots WHERE name = :name"),
                {"name": FIXTURE_DATASET_NAME},
            )
            await session.execute(
                text("DELETE FROM audit_events WHERE action = 'dataset_snapshot.published'")
            )
            await session.commit()

        async with factory() as session:
            service = DatasetService(session, store)

            async def boom(_command: object) -> None:
                raise RuntimeError("audit failed")

            monkeypatch.setattr(service._audit, "append", boom)
            with pytest.raises(RuntimeError, match="audit failed"):
                await service.publish_fixture(fixture_path=FIXTURE_PATH)
            await session.rollback()

        async with factory() as session:
            snaps = await session.execute(
                text("SELECT count(*) FROM dataset_snapshots WHERE name = :name"),
                {"name": FIXTURE_DATASET_NAME},
            )
            audits = await session.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE action = 'dataset_snapshot.published'"
                )
            )
            assert snaps.scalar_one() == 0
            assert audits.scalar_one() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_downgrade_and_reupgrade_dataset_migration(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    _alembic(alembic_env, "downgrade", "0002_core_registry_and_audit")
    engine = create_async_engine(integration_settings.database_url)
    try:
        async with engine.connect() as conn:
            snaps = await conn.execute(text("SELECT to_regclass('public.dataset_snapshots')"))
            assert snaps.scalar_one() is None
    finally:
        await engine.dispose()
    _alembic(alembic_env, "upgrade", "head")
    _alembic(alembic_env, "downgrade", "base")
    _alembic(alembic_env, "upgrade", "head")


@pytest.mark.asyncio
async def test_conflicting_duplicate_fixture_raises(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    engine = create_async_engine(integration_settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await session.execute(text("DELETE FROM dataset_partitions"))
            await session.execute(
                text("DELETE FROM dataset_snapshots WHERE name = :name"),
                {"name": FIXTURE_DATASET_NAME},
            )
            await session.commit()
            session.add(
                DatasetSnapshotModel(
                    id=uuid4(),
                    name=FIXTURE_DATASET_NAME,
                    description=None,
                    exchange="binance_futures",
                    status="published",
                    manifest_version="1",
                    content_hash="f" * 64,
                    total_rows=1,
                    published_at=datetime.now(UTC),
                    validation_summary={},
                )
            )
            await session.commit()

        async with factory() as session:
            service = DatasetService(session, store)
            with pytest.raises(DatasetDuplicateError):
                await service.publish_fixture(fixture_path=FIXTURE_PATH)
    finally:
        await engine.dispose()
