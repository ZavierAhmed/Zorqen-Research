"""Artifact-store protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from zorqen_research.domain.artifacts import ArtifactMetadata, MediaType


class ArtifactStore(Protocol):
    """Content-addressed immutable artifact store."""

    def publish_bytes(
        self,
        data: bytes,
        *,
        media_type: MediaType = MediaType.OCTET_STREAM,
        original_filename: str | None = None,
    ) -> ArtifactMetadata:
        """Publish raw bytes immutably."""

    def publish_file(
        self,
        source: Path,
        *,
        media_type: MediaType = MediaType.OCTET_STREAM,
        original_filename: str | None = None,
    ) -> ArtifactMetadata:
        """Publish a local source file immutably."""

    def exists(self, key: str) -> bool:
        """Return True when the artifact key is present."""

    def open_bytes(self, key: str) -> bytes:
        """Read and verify published artifact bytes."""

    def get_metadata(self, key: str) -> ArtifactMetadata:
        """Return verified metadata for a published artifact."""
