"""PostgreSQL integration tests for verified candle query and integrity."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers import lifespan_client
from tests.helpers_binance import make_kline_page
from tests.integration.test_binance_import import _mock_client_for_range
from zorqen_research.api.app import create_app
from zorqen_research.application.datasets.service import DatasetService
from zorqen_research.application.market_data.import_service import BinanceImportService
from zorqen_research.application.market_data.query import CandleQueryService
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.core.config import Settings, clear_settings_cache
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.candle_partition_reader import (
    LocalCandlePartitionReader,
)
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.binance.schemas import parse_kline_page
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
EXPECTED_FIXTURE_HASH = "5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80"
EXPECTED_NORMALIZED_SHA256 = "e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159"
EXPECTED_CONTENT_HASH = "ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e"


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


def _alembic(env: dict[str, str], *args: str):
    import subprocess
    import sys

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
        await session.execute(text("DELETE FROM audit_events"))
        await session.execute(text("DELETE FROM dataset_partitions"))
        await session.execute(text("DELETE FROM dataset_snapshots"))
        await session.commit()
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _import_1005(
    session: AsyncSession,
    settings: Settings,
) -> tuple[object, LocalFilesystemArtifactStore]:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candle_count = 1005
    end = start + timedelta(hours=candle_count)
    clock = lambda: datetime(2026, 12, 1, tzinfo=UTC)  # noqa: E731
    store = LocalFilesystemArtifactStore(settings.artifact_root_configured)
    client, _ = _mock_client_for_range(start, candle_count)
    service = BinanceImportService(
        session,
        store,
        client,
        max_candles=100_000,
        clock=clock,
    )
    try:
        result = await service.import_klines(
            symbol="BTCUSDT",
            timeframe="1h",
            start=start,
            end=end,
        )
    finally:
        client.close()
    return result, store


def _object_path(root: Path, artifact_key: str) -> Path:
    return root / "objects" / Path(*artifact_key.split("/"))


def _meta_path(root: Path, artifact_key: str) -> Path:
    return root / "meta" / Path(*f"{artifact_key}.json".split("/"))


@pytest.mark.asyncio
async def test_candle_query_pages_and_cli_verify(
    migrated_session: AsyncSession,
    integration_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, store = await _import_1005(migrated_session, integration_settings)
    assert result.candle_count == 1005
    assert result.normalized_sha256 == EXPECTED_NORMALIZED_SHA256
    assert result.content_hash == EXPECTED_CONTENT_HASH

    start = datetime(2026, 6, 1, tzinfo=UTC)
    expected = tuple(
        parse_kline_page(
            make_kline_page(start, 1005, Timeframe.H1),
            timeframe=Timeframe.H1,
        )
    )
    assert serialize_candles_csv(expected) == store.open_bytes(
        (
            await migrated_session.execute(
                select(DatasetPartitionModel).where(
                    DatasetPartitionModel.dataset_snapshot_id == result.snapshot_id
                )
            )
        )
        .scalar_one()
        .artifact_key
    )

    audit_before = (
        await migrated_session.execute(text("SELECT count(*) FROM audit_events"))
    ).scalar_one()

    app = create_app(settings=integration_settings)
    async with lifespan_client(app) as api:
        page1 = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 1000},
        )
        assert page1.status_code == 200
        body1 = page1.json()
        assert body1["count"] == 1000
        assert body1["has_more"] is True
        assert body1["partition_sha256"] == EXPECTED_NORMALIZED_SHA256
        assert isinstance(body1["items"][0]["open"], str)
        assert body1["items"][0]["open_time"].endswith("Z")
        assert isinstance(body1["items"][0]["trade_count"], int)

        page2 = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "limit": 1000,
                "after": body1["next_cursor"],
            },
        )
        assert page2.status_code == 200
        body2 = page2.json()
        assert body2["count"] == 5
        assert body2["has_more"] is False
        assert body2["next_cursor"] is None

        # Deterministic repeat
        page1b = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h", "limit": 1000},
        )
        assert page1b.json() == body1

        combined_times = [item["open_time"] for item in body1["items"] + body2["items"]]
        assert combined_times == [
            c.open_time.astimezone(UTC).isoformat().replace("+00:00", "Z") for c in expected
        ]

        wrong_symbol = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "ETHUSDT", "timeframe": "1h"},
        )
        assert wrong_symbol.status_code == 404

        unknown = await api.get(
            f"/api/v1/datasets/{uuid4()}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert unknown.status_code == 404

        # No mutation routes for candles
        assert (await api.post(f"/api/v1/datasets/{result.snapshot_id}/candles")).status_code in {
            404,
            405,
        }
        assert (await api.delete(f"/api/v1/datasets/{result.snapshot_id}/candles")).status_code in {
            404,
            405,
        }

    audit_after = (
        await migrated_session.execute(text("SELECT count(*) FROM audit_events"))
    ).scalar_one()
    assert audit_after == audit_before

    # CLI verification (subprocess avoids nested asyncio.run)
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", str(integration_settings.artifact_root_configured))
    monkeypatch.setenv("ZORQEN_DATABASE_URL", integration_settings.database_url)
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", integration_settings.database_url_sync)
    clear_settings_cache()
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "zorqen_research.datasets",
            "verify-snapshot",
            "--snapshot-id",
            str(result.snapshot_id),
        ],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert '"ok":true' in completed.stdout.replace(" ", "")


@pytest.mark.asyncio
async def test_legacy_fixture_unsupported_for_candle_query(
    migrated_session: AsyncSession,
    integration_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_configured)
    service = DatasetService(migrated_session, store)
    published = await service.publish_fixture(fixture_path=FIXTURE_PATH)
    assert published.content_hash == EXPECTED_FIXTURE_HASH

    app = create_app(settings=integration_settings)
    async with lifespan_client(app) as api:
        response = await api.get(
            f"/api/v1/datasets/{published.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert response.status_code == 409
        assert "unsupported" in response.json()["detail"].lower()

        # Fixture metadata APIs still work
        detail = await api.get(f"/api/v1/datasets/{published.snapshot_id}")
        assert detail.status_code == 200
        assert detail.json()["content_hash"] == EXPECTED_FIXTURE_HASH

    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", str(integration_settings.artifact_root_configured))
    monkeypatch.setenv("ZORQEN_DATABASE_URL", integration_settings.database_url)
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", integration_settings.database_url_sync)
    clear_settings_cache()
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "zorqen_research.datasets",
            "verify-snapshot",
            "--snapshot-id",
            str(published.snapshot_id),
        ],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2, completed.stderr + completed.stdout
    assert "unsupported" in (completed.stderr + completed.stdout).lower()


@pytest.mark.asyncio
async def test_integrity_failures_are_sanitized(
    migrated_session: AsyncSession,
    integration_settings: Settings,
) -> None:
    result, store = await _import_1005(migrated_session, integration_settings)
    root = Path(integration_settings.artifact_root_configured)
    partition = (
        await migrated_session.execute(
            select(DatasetPartitionModel).where(
                DatasetPartitionModel.dataset_snapshot_id == result.snapshot_id
            )
        )
    ).scalar_one()
    artifact_key = partition.artifact_key
    object_path = _object_path(root, artifact_key)

    app = create_app(settings=integration_settings)

    # Corrupt normalized bytes (same path; hash no longer matches key)
    original = object_path.read_bytes()
    object_path.write_bytes(original + b"x")
    async with lifespan_client(app) as api:
        corrupted = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert corrupted.status_code == 409
        detail = corrupted.json()["detail"]
        assert "integrity" in detail.lower()
        assert str(root) not in detail
        assert "\\" not in detail or "C:" not in detail
    object_path.write_bytes(original)

    # Missing artifact
    object_path.unlink()
    async with lifespan_client(app) as api:
        missing = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert missing.status_code == 409
    # Restore by republishing identical bytes via store layout rewrite
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(original)

    # Corrupt metadata
    meta = _meta_path(root, artifact_key)
    meta_original = meta.read_text(encoding="utf-8")
    payload = json.loads(meta_original)
    payload["sha256"] = "0" * 64
    meta.write_text(json.dumps(payload), encoding="utf-8")
    async with lifespan_client(app) as api:
        bad_meta = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert bad_meta.status_code == 409
    meta.write_text(meta_original, encoding="utf-8")

    # Partition DB hash mismatch
    partition.sha256 = "1" * 64
    await migrated_session.commit()
    async with lifespan_client(app) as api:
        bad_hash = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert bad_hash.status_code == 409
    partition.sha256 = EXPECTED_NORMALIZED_SHA256
    await migrated_session.commit()

    # Partition row-count mismatch
    partition.row_count = 999
    await migrated_session.commit()
    async with lifespan_client(app) as api:
        bad_rows = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert bad_rows.status_code == 409
    partition.row_count = 1005
    await migrated_session.commit()

    # Snapshot content-hash mismatch
    snap = (
        await migrated_session.execute(
            select(DatasetSnapshotModel).where(DatasetSnapshotModel.id == result.snapshot_id)
        )
    ).scalar_one()
    snap.content_hash = "2" * 64
    await migrated_session.commit()
    async with lifespan_client(app) as api:
        bad_content = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert bad_content.status_code == 409
    snap.content_hash = EXPECTED_CONTENT_HASH
    await migrated_session.commit()

    # Raw source-page artifact mismatch
    provenance = snap.validation_summary["provenance"]
    source_key = provenance["source_pages"][0]["artifact_key"]
    source_path = _object_path(root, source_key)
    source_original = source_path.read_bytes()
    source_path.write_bytes(source_original + b"corrupt")
    async with lifespan_client(app) as api:
        bad_source = await api.get(
            f"/api/v1/datasets/{result.snapshot_id}/candles",
            params={"symbol": "BTCUSDT", "timeframe": "1h"},
        )
        assert bad_source.status_code == 409
    source_path.write_bytes(source_original)

    # Service-level CLI-style verify after restore
    reader = LocalCandlePartitionReader(store)
    query_service = CandleQueryService(migrated_session, store, reader)
    verified = await query_service.verify_snapshot(result.snapshot_id)
    assert verified.ok is True
    assert verified.candle_count == 1005
    assert verified.verified_artifact_count == 3  # 1 partition + 2 source pages
    assert verified.content_hash == EXPECTED_CONTENT_HASH
