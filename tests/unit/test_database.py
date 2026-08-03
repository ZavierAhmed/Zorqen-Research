"""Unit tests for database readiness helper sanitization."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zorqen_research.infrastructure.database.engine import check_database_ready


@pytest.mark.asyncio
async def test_check_database_ready_swallows_errors_without_raising() -> None:
    engine = MagicMock()
    connection = AsyncMock()
    connection.execute = AsyncMock(
        side_effect=RuntimeError(
            "connection failed for postgresql+asyncpg://zorqen:secret@127.0.0.1/db"
        )
    )

    class _Ctx:
        async def __aenter__(self) -> Any:
            return connection

        async def __aexit__(self, *_args: object) -> None:
            return None

    engine.connect = MagicMock(return_value=_Ctx())

    assert await check_database_ready(engine) is False
