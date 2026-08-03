"""Local filesystem content-addressed artifact store."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from zorqen_research.domain.artifacts import (
    ArtifactMetadata,
    MediaType,
    artifact_key_for_sha256,
    sha256_hex,
    validate_artifact_key,
)


class ArtifactStoreError(RuntimeError):
    """Sanitized artifact-store failure."""


class LocalFilesystemArtifactStore:
    """SHA-256 content-addressed store rooted at a configured directory."""

    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._objects = self._root / "objects"
        self._tmp = self._root / "tmp"
        self._meta = self._root / "meta"
        self._objects.mkdir(parents=True, exist_ok=True)
        self._tmp.mkdir(parents=True, exist_ok=True)
        self._meta.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def publish_bytes(
        self,
        data: bytes,
        *,
        media_type: MediaType = MediaType.OCTET_STREAM,
        original_filename: str | None = None,
    ) -> ArtifactMetadata:
        digest = sha256_hex(data)
        key = artifact_key_for_sha256(digest)
        final_path = self._resolve_object_path(key)
        meta_path = self._resolve_meta_path(key)

        if final_path.exists():
            existing = self.get_metadata(key)
            existing_bytes = self.open_bytes(key)
            if existing_bytes != data:
                msg = "Artifact key collision with different content"
                raise ArtifactStoreError(msg)
            return existing

        tmp_path: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(prefix="artifact-", dir=self._tmp)
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())

            final_path.parent.mkdir(parents=True, exist_ok=True)
            published = False
            source_tmp = tmp_path
            for _attempt in range(5):
                try:
                    os.replace(source_tmp, final_path)
                    tmp_path = None
                    published = True
                    break
                except OSError:
                    if final_path.exists():
                        existing_bytes = final_path.read_bytes()
                        if existing_bytes != data:
                            msg = "Artifact key collision with different content"
                            raise ArtifactStoreError(msg) from None
                        # Another writer published identical bytes.
                        published = True
                        break
            if not published:
                msg = "Failed to publish artifact safely"
                raise ArtifactStoreError(msg)

            if meta_path.exists():
                return self.get_metadata(key)

            published_at = datetime.now(UTC)
            metadata = ArtifactMetadata(
                key=key,
                sha256=digest,
                byte_size=len(data),
                media_type=media_type,
                original_filename=original_filename,
                published_at=published_at,
            )
            self._write_metadata(meta_path, metadata)
            return metadata
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def publish_file(
        self,
        source: Path,
        *,
        media_type: MediaType = MediaType.OCTET_STREAM,
        original_filename: str | None = None,
    ) -> ArtifactMetadata:
        data = source.read_bytes()
        filename = original_filename if original_filename is not None else source.name
        return self.publish_bytes(data, media_type=media_type, original_filename=filename)

    def exists(self, key: str) -> bool:
        path = self._resolve_object_path(validate_artifact_key(key))
        return path.is_file()

    def open_bytes(self, key: str) -> bytes:
        validated = validate_artifact_key(key)
        path = self._resolve_object_path(validated)
        if not path.is_file():
            msg = "Artifact not found"
            raise ArtifactStoreError(msg)
        data = path.read_bytes()
        expected = validated.rsplit("/", maxsplit=1)[-1]
        actual = sha256_hex(data)
        if actual != expected:
            msg = "Artifact integrity check failed"
            raise ArtifactStoreError(msg)
        return data

    def get_metadata(self, key: str) -> ArtifactMetadata:
        validated = validate_artifact_key(key)
        meta_path = self._resolve_meta_path(validated)
        if not meta_path.is_file():
            data = self.open_bytes(validated)
            return ArtifactMetadata(
                key=validated,
                sha256=sha256_hex(data),
                byte_size=len(data),
                media_type=MediaType.OCTET_STREAM,
                original_filename=None,
                published_at=datetime.fromtimestamp(
                    self._resolve_object_path(validated).stat().st_mtime,
                    tz=UTC,
                ),
            )
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return ArtifactMetadata(
            key=payload["key"],
            sha256=payload["sha256"],
            byte_size=int(payload["byte_size"]),
            media_type=MediaType(payload["media_type"]),
            original_filename=payload.get("original_filename"),
            published_at=datetime.fromisoformat(payload["published_at"]),
        )

    def _write_metadata(self, meta_path: Path, metadata: ArtifactMetadata) -> None:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "key": metadata.key,
            "sha256": metadata.sha256,
            "byte_size": metadata.byte_size,
            "media_type": metadata.media_type.value,
            "original_filename": metadata.original_filename,
            "published_at": metadata.published_at.isoformat(),
        }
        fd, tmp_name = tempfile.mkstemp(prefix="meta-", dir=self._tmp)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(tmp_path, meta_path)
            except OSError:
                # Concurrent identical publication may already own the meta file.
                if meta_path.is_file():
                    return
                msg = "Failed to publish artifact metadata safely"
                raise ArtifactStoreError(msg) from None
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _resolve_object_path(self, key: str) -> Path:
        return self._safe_join(self._objects, key)

    def _resolve_meta_path(self, key: str) -> Path:
        return self._safe_join(self._meta, f"{key}.json")

    def _safe_join(self, base: Path, relative_key: str) -> Path:
        candidate = (base / relative_key).resolve()
        try:
            candidate.relative_to(base.resolve())
        except ValueError as exc:
            msg = "Artifact path escapes configured root"
            raise ArtifactStoreError(msg) from exc
        return candidate
