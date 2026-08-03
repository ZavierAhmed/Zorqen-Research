"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from zorqen_research.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Provide application settings."""
    return get_settings()


def get_engine(request: Request) -> AsyncEngine:
    """Provide the application async engine from app state."""
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        msg = "Database engine is not initialized"
        raise RuntimeError(msg)
    return engine  # type: ignore[no-any-return]


def get_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    """Provide the async session factory from app state."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        msg = "Database session factory is not initialized"
        raise RuntimeError(msg)
    return factory  # type: ignore[no-any-return]


async def get_db_session(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session."""
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
