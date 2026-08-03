"""Async SQLAlchemy engine and readiness helpers."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine for PostgreSQL."""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def dispose_engine(engine: AsyncEngine | None) -> None:
    """Dispose the engine and release connection pool resources."""
    if engine is not None:
        await engine.dispose()


async def check_database_ready(engine: AsyncEngine) -> bool:
    """Return True when a lightweight SELECT 1 succeeds against PostgreSQL."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("PostgreSQL readiness check failed", exc_info=False)
        return False


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Provide a transactional session scope."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
