"""Filesystem integration tests for immutable artifact publication."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest

from zorqen_research.domain.artifacts import MediaType, sha256_hex
from zorqen_research.infrastructure.artifacts.local import (
    ArtifactStoreError,
    LocalFilesystemArtifactStore,
)

pytestmark = pytest.mark.integration


def test_atomic_publication_and_hash_verification(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    data = b"filesystem-integration-bytes"
    meta = store.publish_bytes(data, media_type=MediaType.OCTET_STREAM)
    assert store.exists(meta.key)
    loaded = store.open_bytes(meta.key)
    assert loaded == data
    assert sha256_hex(loaded) == meta.sha256
    assert store.get_metadata(meta.key) == meta


def test_concurrent_identical_publication(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    payload = b"concurrent-identical-content"

    def publish() -> str:
        return store.publish_bytes(payload).key

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(lambda _: publish(), range(16)))
    assert len(set(keys)) == 1
    assert store.open_bytes(keys[0]) == payload


def test_concurrent_metadata_first_writer_wins(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    payload = b"concurrent-metadata-content"
    variants = [(MediaType.CSV, f"file-{index}.csv") for index in range(16)] + [
        (MediaType.JSON, f"file-{index}.json") for index in range(16, 32)
    ]

    def publish(item: tuple[MediaType, str]):
        media_type, filename = item
        return store.publish_bytes(payload, media_type=media_type, original_filename=filename)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(publish, variants))

    verified = store.get_metadata(results[0].key)
    assert all(result == verified for result in results)
    assert store.open_bytes(verified.key) == payload
    assert verified.original_filename is not None
    assert verified.media_type in {MediaType.CSV, MediaType.JSON}


def test_concurrent_missing_metadata_recovery(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    payload = b"recover-me-concurrently"
    first = store.publish_bytes(payload, original_filename="seed.bin")
    store._resolve_meta_path(first.key).unlink()

    def recover(index: int):
        return store.publish_bytes(
            payload,
            media_type=MediaType.CSV if index % 2 == 0 else MediaType.JSON,
            original_filename=f"recover-{index}.dat",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(recover, range(16)))

    verified = store.get_metadata(first.key)
    assert all(result == verified for result in results)
    assert store.open_bytes(verified.key) == payload


def test_path_containment_rejects_escape(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    with pytest.raises((ValueError, ArtifactStoreError)):
        store.open_bytes("../outside")


@pytest.mark.parametrize("label", ["objects", "meta", "tmp"])
def test_top_level_store_symlink_rejected(tmp_path: Path, label: str) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    outside = tmp_path / f"outside-{label}"
    outside.mkdir()
    for name in ("objects", "meta", "tmp"):
        (root / name).mkdir()
    target = root / label
    target.rmdir()
    try:
        target.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")
    with pytest.raises(ArtifactStoreError, match="symlink|escapes"):
        LocalFilesystemArtifactStore(root)


def test_configured_root_symlink_rejected_filesystem(tmp_path: Path) -> None:
    outside = tmp_path / "outside-root"
    outside.mkdir()
    linked_root = tmp_path / "linked-artifacts"
    try:
        linked_root.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")
    with pytest.raises(ArtifactStoreError, match="Configured artifact root must not be a symlink"):
        LocalFilesystemArtifactStore(linked_root)
