"""Local filesystem content-addressed artifact store (immutable no-clobber)."""

from __future__ import annotations

import errno
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


def _is_exist_error(exc: OSError) -> bool:
    return isinstance(exc, FileExistsError) or exc.errno == errno.EEXIST


def _without_extended_prefix(path: Path) -> Path:
    """
    Normalize Windows ``\\\\?\\`` extended paths for containment checks.

    ``Path.resolve()`` may return an extended-length prefix while the configured
    root does not, which breaks ``relative_to`` without changing actual location.
    """
    text = os.fspath(path)
    if text.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + text[8:])
    if text.startswith("\\\\?\\"):
        return Path(text[4:])
    return path


class LocalFilesystemArtifactStore:
    """
    SHA-256 content-addressed store rooted at a configured directory.

    Publication uses atomic hard-link no-clobber semantics: existing object and
    metadata files are never replaced or truncated. First successfully persisted
    metadata wins for descriptive fields (media type, original filename).
    """

    def __init__(self, root: Path) -> None:
        configured_root = root.expanduser()
        if configured_root.exists() and configured_root.is_symlink():
            msg = "Configured artifact root must not be a symlink"
            raise ArtifactStoreError(msg)
        configured_root.mkdir(parents=True, exist_ok=True)
        # Account for a race where another process replaces the root with a symlink.
        if configured_root.is_symlink():
            msg = "Configured artifact root must not be a symlink"
            raise ArtifactStoreError(msg)
        self._root = configured_root.resolve(strict=True)
        self._root = self._require_real_directory(self._root, "root")

        self._objects = self._root / "objects"
        self._tmp = self._root / "tmp"
        self._meta = self._root / "meta"
        for path in (self._objects, self._tmp, self._meta):
            path.mkdir(parents=True, exist_ok=True)
        self._objects = self._require_real_directory(self._objects, "objects")
        self._tmp = self._require_real_directory(self._tmp, "tmp")
        self._meta = self._require_real_directory(self._meta, "meta")

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
        self._assert_store_layout()
        digest = sha256_hex(data)
        key = artifact_key_for_sha256(digest)
        final_path = self._resolve_object_path(key)
        meta_path = self._resolve_meta_path(key)

        if final_path.exists():
            self._reject_if_symlink(final_path, "object")
            existing_bytes = self.open_bytes(key)
            if existing_bytes != data:
                msg = "Artifact key collision with different content"
                raise ArtifactStoreError(msg)
        else:
            self._publish_object_no_clobber(final_path, data)

        if not meta_path.exists():
            candidate = ArtifactMetadata(
                key=key,
                sha256=digest,
                byte_size=len(data),
                media_type=media_type,
                original_filename=original_filename,
                published_at=datetime.now(UTC),
            )
            self._publish_metadata_no_clobber(meta_path, candidate)

        # Always reload verified persisted metadata (first-writer-wins).
        return self.get_metadata(key)

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
        self._assert_store_layout()
        path = self._resolve_object_path(validate_artifact_key(key))
        return path.is_file() and not path.is_symlink()

    def open_bytes(self, key: str) -> bytes:
        self._assert_store_layout()
        validated = validate_artifact_key(key)
        path = self._resolve_object_path(validated)
        if not path.is_file() or path.is_symlink():
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
        """
        Return verified persisted metadata.

        If the object exists but metadata is missing, raises a sanitized error.
        Call publish_bytes again to recover metadata with no-clobber semantics.
        """
        self._assert_store_layout()
        validated = validate_artifact_key(key)
        meta_path = self._resolve_meta_path(validated)
        object_bytes = self.open_bytes(validated)
        actual_digest = sha256_hex(object_bytes)
        expected_digest = validated.rsplit("/", maxsplit=1)[-1]

        if not meta_path.is_file() or meta_path.is_symlink():
            msg = "Artifact metadata is missing"
            raise ArtifactStoreError(msg)

        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = "Artifact metadata is invalid"
            raise ArtifactStoreError(msg) from exc

        metadata = self._parse_and_verify_metadata(
            payload,
            requested_key=validated,
            expected_digest=expected_digest,
            actual_digest=actual_digest,
            actual_size=len(object_bytes),
        )
        return metadata

    def _publish_object_no_clobber(self, final_path: Path, data: bytes) -> None:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        self._reject_symlink_components(final_path, self._objects)
        tmp_path: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(prefix="artifact-", dir=self._tmp)
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())

            linked = self._hardlink_no_clobber(tmp_path, final_path)
            if linked:
                tmp_path.unlink(missing_ok=True)
                tmp_path = None
                return

            # Destination already existed: verify without replacing.
            self._reject_if_symlink(final_path, "object")
            existing_bytes = final_path.read_bytes()
            if existing_bytes != data:
                msg = "Artifact key collision with different content"
                raise ArtifactStoreError(msg)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _publish_metadata_no_clobber(
        self,
        meta_path: Path,
        metadata: ArtifactMetadata,
    ) -> None:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._reject_symlink_components(meta_path, self._meta)
        payload = {
            "key": metadata.key,
            "sha256": metadata.sha256,
            "byte_size": metadata.byte_size,
            "media_type": metadata.media_type.value,
            "original_filename": metadata.original_filename,
            "published_at": metadata.published_at.isoformat(),
        }
        tmp_path: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(prefix="meta-", dir=self._tmp)
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())

            linked = self._hardlink_no_clobber(tmp_path, meta_path)
            if linked:
                tmp_path.unlink(missing_ok=True)
                tmp_path = None
                return
            # First successfully persisted metadata wins; do not replace.
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _hardlink_no_clobber(self, source: Path, destination: Path) -> bool:
        """
        Atomically create destination as a hard link to source.

        Returns True when this caller created the destination.
        Returns False when the destination already existed (no replacement).
        """
        try:
            os.link(source, destination)
            return True
        except OSError as exc:
            if destination.exists() or _is_exist_error(exc):
                return False
            msg = "Failed to publish artifact safely"
            raise ArtifactStoreError(msg) from None

    def _parse_and_verify_metadata(
        self,
        payload: object,
        *,
        requested_key: str,
        expected_digest: str,
        actual_digest: str,
        actual_size: int,
    ) -> ArtifactMetadata:
        if not isinstance(payload, dict):
            msg = "Artifact metadata is invalid"
            raise ArtifactStoreError(msg)

        key = payload.get("key")
        digest = payload.get("sha256")
        byte_size = payload.get("byte_size")
        media_type_raw = payload.get("media_type")
        original_filename = payload.get("original_filename")
        published_raw = payload.get("published_at")

        if key != requested_key:
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        if not isinstance(digest, str) or digest != expected_digest or digest != actual_digest:
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        if (
            not isinstance(byte_size, int)
            or isinstance(byte_size, bool)
            or byte_size != actual_size
        ):
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        if not isinstance(media_type_raw, str):
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        try:
            media_type = MediaType(media_type_raw)
        except ValueError as exc:
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg) from exc
        if original_filename is not None and not isinstance(original_filename, str):
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        if not isinstance(published_raw, str):
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)
        try:
            published_at = datetime.fromisoformat(published_raw)
        except ValueError as exc:
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg) from exc
        if published_at.tzinfo is None:
            msg = "Artifact metadata integrity check failed"
            raise ArtifactStoreError(msg)

        return ArtifactMetadata(
            key=requested_key,
            sha256=expected_digest,
            byte_size=actual_size,
            media_type=media_type,
            original_filename=original_filename,
            published_at=published_at.astimezone(UTC),
        )

    def _assert_store_layout(self) -> None:
        self._objects = self._require_real_directory(self._objects, "objects")
        self._tmp = self._require_real_directory(self._tmp, "tmp")
        self._meta = self._require_real_directory(self._meta, "meta")

    def _require_real_directory(self, path: Path, label: str) -> Path:
        if path.is_symlink():
            msg = f"Artifact {label} directory must not be a symlink"
            raise ArtifactStoreError(msg)
        if not path.is_dir():
            msg = f"Artifact {label} path is not a directory"
            raise ArtifactStoreError(msg)
        resolved = _without_extended_prefix(path.resolve())
        try:
            resolved.relative_to(_without_extended_prefix(self._root))
        except ValueError as exc:
            msg = "Artifact path escapes configured root"
            raise ArtifactStoreError(msg) from exc
        return resolved

    def _resolve_object_path(self, key: str) -> Path:
        return self._safe_join(self._objects, key)

    def _resolve_meta_path(self, key: str) -> Path:
        return self._safe_join(self._meta, f"{key}.json")

    def _safe_join(self, base: Path, relative_key: str) -> Path:
        base_resolved = self._require_real_directory(base, "store")
        current = base_resolved
        for part in Path(relative_key).parts:
            if part in {"", ".", ".."}:
                msg = "Artifact path escapes configured root"
                raise ArtifactStoreError(msg)
            current = current / part
            if current.exists() and current.is_symlink():
                msg = "Artifact path escapes configured root"
                raise ArtifactStoreError(msg)
        candidate = _without_extended_prefix(current.resolve(strict=False))
        try:
            candidate.relative_to(_without_extended_prefix(base_resolved))
            candidate.relative_to(_without_extended_prefix(self._root))
        except ValueError as exc:
            msg = "Artifact path escapes configured root"
            raise ArtifactStoreError(msg) from exc
        if candidate.exists() and candidate.is_symlink():
            msg = "Artifact path escapes configured root"
            raise ArtifactStoreError(msg)
        return candidate

    def _reject_symlink_components(self, path: Path, base: Path) -> None:
        try:
            relative = path.relative_to(base)
        except ValueError as exc:
            msg = "Artifact path escapes configured root"
            raise ArtifactStoreError(msg) from exc
        current = base
        for part in relative.parts:
            current = current / part
            if current.exists() and current.is_symlink():
                msg = "Artifact path escapes configured root"
                raise ArtifactStoreError(msg)

    def _reject_if_symlink(self, path: Path, label: str) -> None:
        if path.is_symlink():
            msg = f"Artifact {label} path must not be a symlink"
            raise ArtifactStoreError(msg)
