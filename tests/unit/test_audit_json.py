"""Unit tests for audit payload JSON hardening."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from zorqen_research.domain.audit import AuditEventAppendCommand, assert_json_serializable


def test_audit_payload_rejects_datetime() -> None:
    with pytest.raises(TypeError, match="non-JSON-serializable"):
        AuditEventAppendCommand(
            actor_type="system",
            action="x",
            entity_type="y",
            payload={"when": datetime.now(UTC)},
        )


def test_audit_payload_rejects_nested_uuid_and_bytes() -> None:
    with pytest.raises(TypeError, match="non-JSON-serializable"):
        assert_json_serializable({"nested": {"id": uuid4()}})
    with pytest.raises(TypeError, match="non-JSON-serializable"):
        assert_json_serializable({"blob": b"nope"})


def test_audit_payload_accepts_plain_json() -> None:
    command = AuditEventAppendCommand(
        actor_type="system",
        action="dataset_snapshot.published",
        entity_type="dataset_snapshot",
        payload={"manifest_hash": "abc", "total_rows": 5, "ok": True, "nested": {"a": [1, 2]}},
    )
    assert command.payload["total_rows"] == 5
