"""Audit-event append service (no update/delete)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.domain.audit import AuditEvent, AuditEventAppendCommand
from zorqen_research.infrastructure.database.repositories.audit_events import (
    AuditEventRepository,
)


class AuditEventService:
    """Application service for appending audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditEventRepository(session)

    async def append(self, command: AuditEventAppendCommand) -> AuditEvent:
        """
        Append an audit event within the caller's transaction.

        Does not commit and does not expose update/delete operations.
        """
        return await self._repo.append(command)
