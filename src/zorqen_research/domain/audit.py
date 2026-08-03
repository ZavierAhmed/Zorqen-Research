"""Audit-event domain values (append-only application events)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class AuditEventAppendCommand:
    """Command to append a single audit event."""

    actor_type: str
    action: str
    entity_type: str
    payload: dict[str, Any]
    actor_id: str | None = None
    entity_id: str | None = None
    correlation_id: UUID | None = None
    occurred_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.actor_type.strip():
            msg = "actor_type must be a non-empty string"
            raise ValueError(msg)
        if not self.action.strip():
            msg = "action must be a non-empty string"
            raise ValueError(msg)
        if not self.entity_type.strip():
            msg = "entity_type must be a non-empty string"
            raise ValueError(msg)
        if not isinstance(self.payload, dict):
            msg = "audit payload must be a JSON object (dict)"
            raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Persisted audit event read model."""

    id: UUID
    occurred_at: datetime
    actor_type: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    correlation_id: UUID | None
    payload: dict[str, Any]


def new_audit_event_id() -> UUID:
    """Allocate a new audit-event primary key."""
    return uuid4()


def resolve_occurred_at(value: datetime | None) -> datetime:
    """Return a timezone-aware UTC timestamp for the event."""
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
