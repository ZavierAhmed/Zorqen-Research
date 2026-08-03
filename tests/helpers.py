"""HTTPX helpers that run FastAPI lifespan (httpx 0.28+ no longer does this)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def lifespan_client(app: Any, base_url: str = "http://test") -> AsyncIterator[AsyncClient]:
    """Yield an AsyncClient after starting the application lifespan."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            yield client
