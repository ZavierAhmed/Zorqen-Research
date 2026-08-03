"""Canonical immutable dataset manifest encoding."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from zorqen_research.domain.datasets import MANIFEST_VERSION, DatasetSnapshot

# Fields that identify a specific publication instance. They appear in the
# returned document but are excluded from the content hash so identical
# logical datasets produce a stable digest across republish attempts.
_HASH_EXCLUDED_FIELDS = frozenset(
    {
        "content_hash",
        "dataset_snapshot_id",
        "publication_timestamp",
    }
)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        msg = "Manifest timestamps must be timezone-aware UTC"
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_manifest_document(snapshot: DatasetSnapshot) -> dict[str, Any]:
    """Build a deterministic manifest document for a published snapshot."""
    partitions = sorted(
        snapshot.partitions,
        key=lambda item: (item.symbol.value, item.timeframe.value),
    )
    return {
        "content_hash": snapshot.content_hash,
        "dataset_name": snapshot.name,
        "dataset_snapshot_id": str(snapshot.id),
        "exchange": snapshot.exchange.value,
        "manifest_version": snapshot.manifest_version or MANIFEST_VERSION,
        "maximum_open_time": _iso_utc(snapshot.maximum_open_time),
        "minimum_open_time": _iso_utc(snapshot.minimum_open_time),
        "partitions": [
            {
                "artifact_key": part.artifact_key,
                "byte_size": part.byte_size,
                "maximum_open_time": _iso_utc(part.maximum_open_time),
                "minimum_open_time": _iso_utc(part.minimum_open_time),
                "row_count": part.row_count,
                "sha256": part.sha256,
                "symbol": part.symbol.value,
                "timeframe": part.timeframe.value,
            }
            for part in partitions
        ],
        "publication_timestamp": _iso_utc(snapshot.published_at),
        "total_rows": snapshot.total_rows,
        "validation_summary": snapshot.validation_summary,
    }


def manifest_hash_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Return the logical subset of a manifest used for content hashing."""
    return {key: value for key, value in document.items() if key not in _HASH_EXCLUDED_FIELDS}


def canonical_manifest_bytes(document: dict[str, Any]) -> bytes:
    """Encode a manifest document as canonical UTF-8 JSON bytes."""
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def hash_manifest_document(document: dict[str, Any]) -> str:
    """Return SHA-256 of the canonical logical manifest bytes."""
    return hashlib.sha256(canonical_manifest_bytes(manifest_hash_payload(document))).hexdigest()


def build_and_hash_manifest(snapshot: DatasetSnapshot) -> tuple[dict[str, Any], str, bytes]:
    """
    Build a manifest, hash its logical content, and return document/hash/bytes.

    The content_hash field stores the digest of the logical payload (stable for
    identical partition content). Snapshot id and publication timestamp remain
    in the document for consumers but do not affect the digest.
    """
    document = build_manifest_document(snapshot)
    digest = hash_manifest_document(document)
    final_document = dict(document)
    final_document["content_hash"] = digest
    encoded = canonical_manifest_bytes(final_document)
    return json.loads(encoded.decode("utf-8")), digest, encoded


def parse_snapshot_id(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
