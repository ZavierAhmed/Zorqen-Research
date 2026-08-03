"""Unit tests for audit domain and append service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from zorqen_research.application.audit.service import AuditEventService
from zorqen_research.domain.audit import AuditEvent, AuditEventAppendCommand


def test_audit_command_requires_json_object_payload() -> None:
    with pytest.raises(TypeError, match="JSON object"):
        AuditEventAppendCommand(
            actor_type="system",
            action="seed",
            entity_type="strategy_family",
            payload=["not", "an", "object"],  # type: ignore[arg-type]
        )


def test_audit_command_rejects_blank_actor_type() -> None:
    with pytest.raises(ValueError, match="actor_type"):
        AuditEventAppendCommand(
            actor_type="  ",
            action="seed",
            entity_type="strategy_family",
            payload={},
        )


@pytest.mark.asyncio
async def test_audit_service_append_delegates_without_update_api() -> None:
    service = AuditEventService(MagicMock())
    expected = AuditEvent(
        id=uuid4(),
        occurred_at=datetime.now(UTC),
        actor_type="system",
        actor_id="migrate",
        action="seed.strategy_family",
        entity_type="strategy_family",
        entity_id="adaptive_mtf_trend_breakout",
        correlation_id=uuid4(),
        payload={"source": "test"},
    )
    service._repo.append = AsyncMock(return_value=expected)  # type: ignore[method-assign]

    command = AuditEventAppendCommand(
        actor_type="system",
        actor_id="migrate",
        action="seed.strategy_family",
        entity_type="strategy_family",
        entity_id="adaptive_mtf_trend_breakout",
        correlation_id=expected.correlation_id,
        payload={"source": "test"},
    )
    result = await service.append(command)

    assert result == expected
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")
    assert not hasattr(service._repo, "update")
    assert not hasattr(service._repo, "delete")
