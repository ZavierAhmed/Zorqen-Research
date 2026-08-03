"""Artifact domain models and content-addressing helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

ARTIFACT_KEY_PATTERN = re.compile(r"^sha256/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}$")


class MediaType(StrEnum):
    """Supported artifact media types."""

    OCTET_STREAM = "application/octet-stream"
    CSV = "text/csv"
    JSON = "application/json"
    PARQUET = "application/vnd.apache.parquet"


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Immutable published artifact read model (no filesystem paths)."""

    key: str
    sha256: str
    byte_size: int
    media_type: MediaType
    original_filename: str | None
    published_at: datetime


def sha256_hex(data: bytes) -> str:
    """Return the lowercase SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def artifact_key_for_sha256(digest: str) -> str:
    """Derive the content-addressed artifact key from a SHA-256 digest."""
    normalized = digest.lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        msg = f"Invalid SHA-256 digest: {digest!r}"
        raise ValueError(msg)
    return f"sha256/{normalized[:2]}/{normalized[2:4]}/{normalized}"


def validate_artifact_key(key: str) -> str:
    """Validate an internal artifact key and reject path escapes."""
    if not key or key != key.strip():
        msg = "Artifact key must be a non-empty trimmed string"
        raise ValueError(msg)
    if key.startswith("/") or key.startswith("\\") or ":" in key[:3]:
        msg = "Absolute artifact keys are not allowed"
        raise ValueError(msg)
    if ".." in key.split("/"):
        msg = "Artifact key must not contain path traversal segments"
        raise ValueError(msg)
    if not ARTIFACT_KEY_PATTERN.fullmatch(key):
        msg = f"Invalid artifact key format: {key!r}"
        raise ValueError(msg)
    return key


def utc_now() -> datetime:
    return datetime.now(UTC)
