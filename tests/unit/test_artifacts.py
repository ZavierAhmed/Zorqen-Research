"""Unit and race tests for immutable no-clobber artifact publication."""

from __future__ import annotations

import errno
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

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


def test_same_bytes_same_key_and_first_metadata_wins(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    data = b"hello-artifact"
    first = store.publish_bytes(data, media_type=MediaType.OCTET_STREAM, original_filename="a.bin")
    second = store.publish_bytes(data, media_type=MediaType.CSV, original_filename="b.csv")
    assert first.key == second.key
    assert first.sha256 == sha256_hex(data)
    assert first.key == artifact_key_for_sha256(first.sha256)
    assert store.open_bytes(first.key) == data
    assert second.original_filename == "a.bin"
    assert second.media_type is MediaType.OCTET_STREAM
    assert store.get_metadata(first.key) == second


def test_different_bytes_different_keys(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    a = store.publish_bytes(b"one")
    b = store.publish_bytes(b"two")
    assert a.key != b.key


def test_path_traversal_and_absolute_keys_rejected() -> None:
    with pytest.raises(ValueError, match="traversal|Absolute|Invalid"):
        validate_artifact_key("../etc/passwd")
    with pytest.raises(ValueError, match="Absolute|Invalid"):
        validate_artifact_key("/tmp/abs")
    with pytest.raises(ValueError, match="Absolute|Invalid"):
        validate_artifact_key("C:/windows/system32")


def test_failed_link_cleans_temp_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated failure")

    monkeypatch.setattr(os, "link", boom)
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


def test_object_no_clobber_race_identical_reuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Destination appears between check and link; identical bytes are reused."""
    store = LocalFilesystemArtifactStore(tmp_path)
    data = b"race-identical"
    calls = {"n": 0}
    real_link = os.link

    def link_after_precreate(
        src: str | bytes | os.PathLike[str],
        dst: str | bytes | os.PathLike[str],
    ) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            Path(dst).write_bytes(data)
            raise OSError(errno.EEXIST, "File exists")
        return real_link(src, dst)

    monkeypatch.setattr(os, "link", link_after_precreate)
    meta = store.publish_bytes(data, original_filename="winner.bin")
    assert store.open_bytes(meta.key) == data
    assert meta.original_filename == "winner.bin"
    assert calls["n"] >= 1


def test_object_no_clobber_race_different_rejects_without_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    data = b"attempted-publish-bytes"
    first_writer_bytes = b"already-written-by-other"

    def link_precreate_other(
        src: str | bytes | os.PathLike[str],
        dst: str | bytes | os.PathLike[str],
    ) -> None:
        Path(dst).write_bytes(first_writer_bytes)
        raise OSError(errno.EEXIST, "File exists")

    monkeypatch.setattr(os, "link", link_precreate_other)
    with pytest.raises(ArtifactStoreError, match="collision"):
        store.publish_bytes(data)

    key = artifact_key_for_sha256(sha256_hex(data))
    path = store._resolve_object_path(key)
    assert path.read_bytes() == first_writer_bytes


def test_metadata_corruption_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    meta = store.publish_bytes(b"corrupt-me", media_type=MediaType.CSV, original_filename="c.csv")
    meta_path = store._resolve_meta_path(meta.key)
    original = json.loads(meta_path.read_text(encoding="utf-8"))

    def rewrite(**overrides: object) -> None:
        payload: dict[str, Any] = dict(original)
        payload.update(overrides)
        meta_path.write_text(json.dumps(payload), encoding="utf-8")

    cases: list[dict[str, object]] = [
        {"key": "sha256/00/00/" + ("0" * 64)},
        {"sha256": "0" * 64},
        {"byte_size": 999},
        {"media_type": "application/x-evil"},
        {"published_at": "not-a-timestamp"},
        {"published_at": datetime(2024, 1, 1, 12, 0, 0).isoformat()},
    ]
    for case in cases:
        rewrite(**case)
        with pytest.raises(ArtifactStoreError, match="integrity|invalid"):
            store.get_metadata(meta.key)
        # Restore a valid baseline between cases.
        meta_path.write_text(json.dumps(original), encoding="utf-8")


def test_missing_metadata_raises_and_publish_recovers(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    data = b"object-without-meta"
    meta = store.publish_bytes(data, original_filename="keep.csv", media_type=MediaType.CSV)
    meta_path = store._resolve_meta_path(meta.key)
    meta_path.unlink()

    with pytest.raises(ArtifactStoreError, match="metadata is missing"):
        store.get_metadata(meta.key)

    recovered = store.publish_bytes(
        data,
        original_filename="recovery.csv",
        media_type=MediaType.JSON,
    )
    assert recovered.original_filename == "recovery.csv"
    assert recovered.media_type is MediaType.JSON
    assert store.open_bytes(recovered.key) == data
    assert store.get_metadata(recovered.key) == recovered


def test_symlink_store_directories_rejected(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "objects").mkdir()
    (root / "meta").mkdir()
    (root / "tmp").mkdir()

    objects = root / "objects"
    objects.rmdir()
    try:
        objects.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")

    with pytest.raises(ArtifactStoreError, match="symlink|escapes"):
        LocalFilesystemArtifactStore(root)


def test_nested_hash_directory_symlink_escape_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    data = b"nested-symlink-probe"
    digest = sha256_hex(data)
    outside = tmp_path / "escape-target"
    outside.mkdir()
    # Object layout is objects/sha256/<aa>/<bb>/<digest>
    prefix = store._objects / "sha256" / digest[:2]
    prefix.mkdir(parents=True, exist_ok=True)
    nested = prefix / digest[2:4]
    try:
        nested.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")

    with pytest.raises(ArtifactStoreError, match="escapes|symlink"):
        store.publish_bytes(data)


def test_symlink_rejection_logic_unit(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")

    class FakePath:
        def is_symlink(self) -> bool:
            return True

        def is_dir(self) -> bool:
            return True

        def resolve(self, *, strict: bool = False) -> Path:
            return tmp_path / "outside"

    with pytest.raises(ArtifactStoreError, match="symlink"):
        store._require_real_directory(FakePath(), "objects")  # type: ignore[arg-type]
