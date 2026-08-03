"""Unit tests for local artifact store and content addressing."""

from __future__ import annotations

from pathlib import Path

import pytest

from zorqen_research.domain.artifacts import (
    MediaType,
    artifact_key_for_sha256,
    sha256_hex,
    validate_artifact_key,
)
from zorqen_research.infrastructure.artifacts.local import (
    ArtifactStoreError,
    LocalFilesystemArtifactStore,
)


def test_same_bytes_same_key_and_reuse(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    data = b"hello-artifact"
    first = store.publish_bytes(data, media_type=MediaType.OCTET_STREAM, original_filename="a.bin")
    second = store.publish_bytes(data, media_type=MediaType.CSV, original_filename="b.csv")
    assert first.key == second.key
    assert first.sha256 == sha256_hex(data)
    assert first.key == artifact_key_for_sha256(first.sha256)
    assert store.open_bytes(first.key) == data


def test_different_bytes_different_keys(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    a = store.publish_bytes(b"one")
    b = store.publish_bytes(b"two")
    assert a.key != b.key


def test_path_traversal_and_absolute_keys_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="traversal|Absolute|Invalid"):
        validate_artifact_key("../etc/passwd")
    with pytest.raises(ValueError, match="Absolute|Invalid"):
        validate_artifact_key("/tmp/abs")
    with pytest.raises(ValueError, match="Absolute|Invalid"):
        validate_artifact_key("C:/windows/system32")


def test_failed_write_cleans_temp_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated failure")

    monkeypatch.setattr("os.replace", boom)
    with pytest.raises(ArtifactStoreError):
        store.publish_bytes(b"will-fail")
    assert list(store._tmp.glob("artifact-*")) == []


def test_existing_identical_content_not_overwritten(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    meta = store.publish_bytes(b"stable", original_filename="first.bin")
    again = store.publish_bytes(b"stable", original_filename="second.bin")
    assert again.key == meta.key
    assert store.open_bytes(meta.key) == b"stable"
    assert store.get_metadata(meta.key).original_filename == "first.bin"


def test_api_metadata_has_no_filesystem_paths(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "nested")
    meta = store.publish_bytes(b"x", media_type=MediaType.JSON, original_filename="x.json")
    payload = {
        "key": meta.key,
        "sha256": meta.sha256,
        "byte_size": meta.byte_size,
        "media_type": meta.media_type.value,
        "original_filename": meta.original_filename,
        "published_at": meta.published_at.isoformat(),
    }
    serialized = str(payload)
    assert str(tmp_path.resolve()) not in serialized
    assert ":\\" not in serialized.replace("sha256:", "")
