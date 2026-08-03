"""Filesystem integration tests for the local artifact store."""

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


def test_concurrent_identical_publication(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    payload = b"concurrent-identical-content"

    def publish() -> str:
        return store.publish_bytes(payload).key

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(lambda _: publish(), range(16)))
    assert len(set(keys)) == 1
    assert store.open_bytes(keys[0]) == payload


def test_path_containment_rejects_escape(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "artifacts")
    with pytest.raises((ValueError, ArtifactStoreError)):
        store.open_bytes("../outside")
