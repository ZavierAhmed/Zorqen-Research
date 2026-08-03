"""Harden audit payload validation for fully JSON-serializable objects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

_JSON_PRIMITIVES = (str, int, float, bool, type(None))


def assert_json_serializable(value: object, *, path: str = "payload") -> None:
    """
    Recursively reject values that are not JSON primitives/objects/arrays.

    Intentionally rejects datetime, UUID, bytes, and other non-JSON types.
    """
    if isinstance(value, _JSON_PRIMITIVES):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            msg = f"{path} contains a non-finite float"
            raise ValueError(msg)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_json_serializable(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                msg = f"{path} keys must be strings"
                raise TypeError(msg)
            assert_json_serializable(item, path=f"{path}.{key}")
        return
    msg = f"{path} contains a non-JSON-serializable value of type {type(value).__name__}"
    raise TypeError(msg)


def ensure_json_round_trip(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a deep JSON round-tripped copy of the payload."""
    assert_json_serializable(payload)
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    loaded = json.loads(encoded)
    if not isinstance(loaded, dict):
        msg = "audit payload must be a JSON object (dict)"
        raise TypeError(msg)
    return loaded


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
        object.__setattr__(self, "payload", ensure_json_round_trip(self.payload))


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
