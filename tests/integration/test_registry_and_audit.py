"""PostgreSQL integration tests for registry, audit, and migrations."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers import lifespan_client
from zorqen_research.api.app import create_app
from zorqen_research.application.audit.service import AuditEventService
from zorqen_research.core.config import Settings, clear_settings_cache
from zorqen_research.domain.audit import AuditEventAppendCommand
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
    SUPPORT_RESISTANCE_ID,
)
from zorqen_research.infrastructure.database.engine import check_database_ready
from zorqen_research.infrastructure.database.models.strategy_family import StrategyFamilyModel

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
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    async_url, sync_url = integration_urls
    monkeypatch.setenv("ZORQEN_ENVIRONMENT", "test")
    monkeypatch.setenv("ZORQEN_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ZORQEN_DATABASE_URL", async_url)
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", sync_url)
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", "artifacts-test")
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


@pytest.mark.asyncio
async def test_migration_creates_tables_and_stable_seeds(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")

    engine = create_async_engine(integration_settings.database_url)
    try:
        async with engine.connect() as conn:
            tables = (
                (
                    await conn.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = 'public' "
                            "AND table_name IN ('strategy_families', 'audit_events')"
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert set(tables) == {"strategy_families", "audit_events"}

            rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT id, code, research_priority, status "
                            "FROM strategy_families ORDER BY research_priority, code"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert len(rows) == 2
            assert rows[0]["code"] == "adaptive_mtf_trend_breakout"
            assert rows[0]["id"] == ADAPTIVE_MTF_TREND_BREAKOUT_ID
            assert rows[0]["research_priority"] == "primary"
            assert rows[0]["status"] == "active"
            assert rows[1]["code"] == "support_resistance"
            assert rows[1]["id"] == SUPPORT_RESISTANCE_ID
    finally:
        await engine.dispose()

    _alembic(alembic_env, "downgrade", "0001_baseline")
    _alembic(alembic_env, "upgrade", "head")

    engine = create_async_engine(integration_settings.database_url)
    try:
        async with engine.connect() as conn:
            ids = (
                (await conn.execute(text("SELECT id FROM strategy_families ORDER BY code")))
                .scalars()
                .all()
            )
            assert set(ids) == {
                ADAPTIVE_MTF_TREND_BREAKOUT_ID,
                SUPPORT_RESISTANCE_ID,
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_database_constraints_reject_invalid_values(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    engine = create_async_engine(integration_settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            session.add(
                StrategyFamilyModel(
                    id=uuid4(),
                    code="adaptive_mtf_trend_breakout",
                    display_name="dup",
                    description="dup",
                    research_priority="primary",
                    status="active",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(
                StrategyFamilyModel(
                    id=uuid4(),
                    code="invalid_priority_family",
                    display_name="bad priority",
                    description="bad",
                    research_priority="experimental",
                    status="active",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(
                StrategyFamilyModel(
                    id=uuid4(),
                    code="invalid_status_family",
                    display_name="bad status",
                    description="bad",
                    research_priority="secondary",
                    status="archived",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_strategy_family_api_against_postgres(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    app = create_app(integration_settings)

    async with lifespan_client(app) as client:
        listed = await client.get("/api/v1/strategy-families")
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["count"] == 2
        assert [item["code"] for item in payload["items"]] == [
            "adaptive_mtf_trend_breakout",
            "support_resistance",
        ]

        primary = await client.get("/api/v1/strategy-families/adaptive_mtf_trend_breakout")
        assert primary.status_code == 200
        assert primary.json()["id"] == str(ADAPTIVE_MTF_TREND_BREAKOUT_ID)

        missing = await client.get("/api/v1/strategy-families/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Strategy family not found."
        assert "Traceback" not in missing.text


@pytest.mark.asyncio
async def test_audit_append_persists_and_rolls_back(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    engine = create_async_engine(integration_settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    correlation_id = uuid4()

    try:
        async with session_factory() as session:
            service = AuditEventService(session)
            event = await service.append(
                AuditEventAppendCommand(
                    actor_type="system",
                    actor_id="integration-test",
                    action="test.append",
                    entity_type="strategy_family",
                    entity_id="adaptive_mtf_trend_breakout",
                    correlation_id=correlation_id,
                    payload={"reason": "integration", "count": 1},
                )
            )
            await session.commit()
            assert event.payload == {"reason": "integration", "count": 1}
            assert event.occurred_at.tzinfo is not None
            assert event.correlation_id == correlation_id
            persisted_id = event.id

        async with session_factory() as session:
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT actor_type, actor_id, action, entity_type, entity_id, "
                            "correlation_id, payload, occurred_at "
                            "FROM audit_events WHERE id = :id"
                        ),
                        {"id": persisted_id},
                    )
                )
                .mappings()
                .one()
            )
            assert row["actor_type"] == "system"
            assert row["actor_id"] == "integration-test"
            assert row["action"] == "test.append"
            assert row["entity_type"] == "strategy_family"
            assert row["entity_id"] == "adaptive_mtf_trend_breakout"
            assert row["correlation_id"] == correlation_id
            assert row["payload"] == {"reason": "integration", "count": 1}
            assert row["occurred_at"].tzinfo is not None

        async with session_factory() as session:
            service = AuditEventService(session)
            await service.append(
                AuditEventAppendCommand(
                    actor_type="system",
                    action="test.rollback",
                    entity_type="strategy_family",
                    payload={"should": "rollback"},
                )
            )
            await session.rollback()

        async with session_factory() as session:
            count = (
                await session.execute(
                    text("SELECT COUNT(*) FROM audit_events WHERE action = 'test.rollback'")
                )
            ).scalar_one()
            assert count == 0
    finally:
        await engine.dispose()


def test_alembic_full_round_trip(
    integration_settings: Settings,
    alembic_env: dict[str, str],
) -> None:
    _alembic(alembic_env, "upgrade", "head")
    _alembic(alembic_env, "downgrade", "0001_baseline")
    _alembic(alembic_env, "upgrade", "head")
    _alembic(alembic_env, "downgrade", "base")
    _alembic(alembic_env, "upgrade", "head")
