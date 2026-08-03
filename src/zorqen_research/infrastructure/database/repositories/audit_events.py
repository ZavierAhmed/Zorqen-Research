"""Audit-event repository — append-only (no update/delete API)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.domain.audit import (
    AuditEvent,
    AuditEventAppendCommand,
    new_audit_event_id,
    resolve_occurred_at,
)
from zorqen_research.infrastructure.database.models.audit_event import AuditEventModel


class AuditEventRepository:
    """Append-only persistence for application audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, command: AuditEventAppendCommand) -> AuditEvent:
        """
        Stage a new audit event in the current session.

        Does not commit. Callers own the transaction boundary.
        No update or delete operations are provided.
        """
        event_id = new_audit_event_id()
        occurred_at = resolve_occurred_at(command.occurred_at)
        row = AuditEventModel(
            id=event_id,
            occurred_at=occurred_at,
            actor_type=command.actor_type.strip(),
            actor_id=command.actor_id,
            action=command.action.strip(),
            entity_type=command.entity_type.strip(),
            entity_id=command.entity_id,
            correlation_id=command.correlation_id,
            payload=dict(command.payload),
        )
        self._session.add(row)
        await self._session.flush()
        return AuditEvent(
            id=row.id,
            occurred_at=row.occurred_at,
            actor_type=row.actor_type,
            actor_id=row.actor_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            correlation_id=row.correlation_id,
            payload=dict(row.payload),
        )
