"""Mocked Binance multi-page import integration tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers import lifespan_client
from tests.helpers_binance import make_kline_page, page_bytes
from zorqen_research.api.app import create_app
from zorqen_research.application.datasets.service import DatasetDuplicateError
from zorqen_research.application.market_data.import_service import BinanceImportService
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.core.config import Settings, clear_settings_cache
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.binance.client import (
    PAGE_LIMIT,
    PRODUCTION_HOST,
    BinanceFuturesPublicClient,
)
from zorqen_research.infrastructure.binance.errors import BinanceResponseError
from zorqen_research.infrastructure.binance.schemas import parse_kline_page
from zorqen_research.infrastructure.database.engine import check_database_ready
from zorqen_research.infrastructure.database.models.dataset_snapshot import (
    DatasetSnapshotModel,
)

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _mock_client_for_range(
    start: datetime,
    candle_count: int,
    *,
    page_limit: int = PAGE_LIMIT,
    mutate_after: int | None = None,
) -> tuple[BinanceFuturesPublicClient, list[httpx.Request]]:
    rows = make_kline_page(start, candle_count, Timeframe.H1)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert "X-MBX-APIKEY" not in request.headers
        assert request.url.path == "/fapi/v1/klines"
        start_ms = int(request.url.params["startTime"])
        limit = int(request.url.params["limit"])
        assert limit == page_limit
        offset = 0
        for index, row in enumerate(rows):
            if int(row[0]) >= start_ms:
                offset = index
                break
        else:
            return httpx.Response(200, content=b"[]")
        chunk = rows[offset : offset + limit]
        if mutate_after is not None and offset >= mutate_after:
            # Corrupt OHLC on a later page to reject publication.
            bad = list(chunk[0])
            bad[2] = "1"  # high too low
            chunk = [bad, *chunk[1:]]
        return httpx.Response(200, content=page_bytes(chunk))

    client = BinanceFuturesPublicClient(
        base_url=PRODUCTION_HOST,
        transport=httpx.MockTransport(handler),
        sleeper=lambda _: None,
        max_attempts=2,
    )
    return client, requests


@pytest.mark.asyncio
async def test_multipage_import_publish_api_and_idempotency(
    migrated_session: AsyncSession,
    integration_settings: Settings,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    # > 1000 candles forces multi-page with default PAGE_LIMIT.
    candle_count = 1005
    end = start + timedelta(hours=candle_count)
    # Clock must be after the exclusive end so all candles are fully closed.
    clock = lambda: datetime(2026, 12, 1, tzinfo=UTC)  # noqa: E731
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    client, requests = _mock_client_for_range(start, candle_count)
    service = BinanceImportService(
        migrated_session,
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

    assert result.created is True
    assert result.candle_count == candle_count
    assert result.source_page_count == 2
    assert len(requests) == 2
    assert result.normalized_sha256
    expected_csv = serialize_candles_csv(
        tuple(
            parse_kline_page(
                make_kline_page(start, candle_count, Timeframe.H1),
                timeframe=Timeframe.H1,
            )
        )
    )
    row = (
        await migrated_session.execute(
            select(DatasetSnapshotModel).where(DatasetSnapshotModel.id == result.snapshot_id)
        )
    ).scalar_one()
    assert row.manifest_version == "2"
    assert row.total_rows == candle_count
    provenance = (row.validation_summary or {})["provenance"]
    assert provenance["provider"] == "binance"
    assert provenance["endpoint_path"] == "/fapi/v1/klines"
    assert provenance["expected_candle_count"] == candle_count
    assert len(provenance["source_pages"]) == 2
    assert provenance["normalized_partition"]["sha256"] == result.normalized_sha256
    artifact_key = provenance["normalized_partition"]["artifact_key"]
    assert store.open_bytes(artifact_key) == expected_csv

    # API exposure
    app = create_app(settings=integration_settings)
    async with lifespan_client(app) as api:
        listed = await api.get("/api/v1/datasets")
        assert listed.status_code == 200
        ids = {item["id"] for item in listed.json()["items"]}
        assert str(result.snapshot_id) in ids

        detail = await api.get(f"/api/v1/datasets/{result.snapshot_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert len(body["partitions"]) == 1
        assert "\\" not in body["partitions"][0]["artifact_key"]
        assert not body["partitions"][0]["artifact_key"].startswith("/")

        manifest = await api.get(f"/api/v1/datasets/{result.snapshot_id}/manifest")
        assert manifest.status_code == 200
        man = manifest.json()
        assert man["manifest_version"] == "2"
        assert man["provenance"]["symbol"] == "BTCUSDT"
        assert man["content_hash"] == result.content_hash
        for page in man["provenance"]["source_pages"]:
            assert page["artifact_key"].startswith("sha256/")

        # No mutation routes
        assert (await api.post("/api/v1/datasets")).status_code in {404, 405, 422}
        assert (await api.post(f"/api/v1/datasets/{result.snapshot_id}/candles")).status_code in {
            404,
            405,
        }

    # Idempotent second import
    client2, _ = _mock_client_for_range(start, candle_count)
    service2 = BinanceImportService(
        migrated_session,
        store,
        client2,
        max_candles=100_000,
        clock=clock,
    )
    try:
        again = await service2.import_klines(
            symbol="BTCUSDT",
            timeframe="1h",
            start=start,
            end=end,
        )
    finally:
        client2.close()
    assert again.created is False
    assert again.snapshot_id == result.snapshot_id
    assert again.content_hash == result.content_hash


@pytest.mark.asyncio
async def test_source_drift_rejects_and_gap_rejects(
    migrated_session: AsyncSession,
    integration_settings: Settings,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=3)
    clock = lambda: datetime(2026, 7, 1, tzinfo=UTC)  # noqa: E731
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)

    client, _ = _mock_client_for_range(start, 3)
    service = BinanceImportService(
        migrated_session, store, client, max_candles=100_000, clock=clock
    )
    try:
        first = await service.import_klines(symbol="ETHUSDT", timeframe="1h", start=start, end=end)
    finally:
        client.close()
    assert first.created is True

    # Different OHLC under same identity -> conflict
    def drift_handler(request: httpx.Request) -> httpx.Response:
        rows = make_kline_page(start, 3, Timeframe.H1)
        rows[0][4] = "999"  # changed close
        # Keep high valid
        rows[0][2] = "1000"
        return httpx.Response(200, content=page_bytes(rows))

    drift_client = BinanceFuturesPublicClient(
        base_url=PRODUCTION_HOST,
        transport=httpx.MockTransport(drift_handler),
        sleeper=lambda _: None,
    )
    drift_service = BinanceImportService(
        migrated_session, store, drift_client, max_candles=100_000, clock=clock
    )
    try:
        with pytest.raises(DatasetDuplicateError, match="conflicting"):
            await drift_service.import_klines(
                symbol="ETHUSDT", timeframe="1h", start=start, end=end
            )
    finally:
        drift_client.close()

    # Gap: missing middle candle
    def gap_handler(request: httpx.Request) -> httpx.Response:
        rows = make_kline_page(start, 3, Timeframe.H1)
        del rows[1]
        return httpx.Response(200, content=page_bytes(rows))

    gap_client = BinanceFuturesPublicClient(
        base_url=PRODUCTION_HOST,
        transport=httpx.MockTransport(gap_handler),
        sleeper=lambda _: None,
    )
    gap_service = BinanceImportService(
        migrated_session, store, gap_client, max_candles=100_000, clock=clock
    )
    try:
        with pytest.raises(BinanceResponseError, match="coverage|Missing|gapped"):
            await gap_service.import_klines(
                symbol="BNBUSDT",
                timeframe="1h",
                start=start,
                end=end,
            )
    finally:
        gap_client.close()
    missing = await migrated_session.execute(
        select(DatasetSnapshotModel).where(DatasetSnapshotModel.name.like("%BNBUSDT%"))
    )
    assert missing.scalars().first() is None


@pytest.mark.asyncio
async def test_malformed_later_page_and_audit_rollback(
    migrated_session: AsyncSession,
    integration_settings: Settings,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    candle_count = 1005
    end = start + timedelta(hours=candle_count)
    clock = lambda: datetime(2026, 12, 1, tzinfo=UTC)  # noqa: E731
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    client, _ = _mock_client_for_range(start, candle_count, mutate_after=1000)
    service = BinanceImportService(
        migrated_session, store, client, max_candles=100_000, clock=clock
    )
    try:
        with pytest.raises(BinanceResponseError):
            await service.import_klines(
                symbol="BTCUSDT",
                timeframe="1h",
                start=start,
                end=end,
            )
    finally:
        client.close()

    # Audit failure rolls back DB rows
    client2, _ = _mock_client_for_range(start, 5)
    end5 = start + timedelta(hours=5)
    service2 = BinanceImportService(
        migrated_session, store, client2, max_candles=100_000, clock=clock
    )
    name = "binance_futures_BTCUSDT_1h_2026-06-01T000000Z_2026-06-01T050000Z_v1"
    try:
        with patch(
            "zorqen_research.application.market_data.import_service.AuditEventService.append",
            side_effect=RuntimeError("audit failed"),
        ):
            with pytest.raises(RuntimeError, match="audit failed"):
                await service2.import_klines(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    start=start,
                    end=end5,
                )
            await migrated_session.rollback()
    finally:
        client2.close()

    remaining = await migrated_session.execute(
        select(DatasetSnapshotModel).where(DatasetSnapshotModel.name == name)
    )
    assert remaining.scalars().first() is None


@pytest.mark.asyncio
async def test_import_max_candles_guardrail(
    migrated_session: AsyncSession,
    integration_settings: Settings,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=10)
    store = LocalFilesystemArtifactStore(integration_settings.artifact_root_resolved)
    client, _ = _mock_client_for_range(start, 10)
    service = BinanceImportService(
        migrated_session,
        store,
        client,
        max_candles=5,
        clock=lambda: datetime(2026, 7, 1, tzinfo=UTC),
    )
    try:
        with pytest.raises(ValueError, match="ZORQEN_IMPORT_MAX_CANDLES"):
            await service.import_klines(
                symbol="BTCUSDT",
                timeframe="1h",
                start=start,
                end=end,
            )
    finally:
        client.close()
