"""Unit tests for application settings."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from zorqen_research.core.config import Settings, clear_settings_cache, get_settings


def test_settings_load_expected_environment_values(
    test_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(".")
    clear_settings_cache()
    settings = get_settings()
    assert settings.environment == "test"
    assert settings.log_level == "WARNING"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.database_url == test_env["ZORQEN_DATABASE_URL"]
    assert settings.database_url_sync == test_env["ZORQEN_DATABASE_URL_SYNC"]
    assert settings.worker_idle_interval_seconds == 0.1
    assert settings.artifact_root.name == "artifacts-test"
    assert settings.artifact_root_configured == settings.artifact_root.expanduser()
    # Relative roots stay relative; settings must not resolve away path identity.
    assert not settings.artifact_root_configured.is_absolute()


def test_invalid_async_database_url_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZORQEN_DATABASE_URL", "postgresql://bad")
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "postgresql+asyncpg://" in str(exc_info.value)


def test_invalid_sync_database_url_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", "sqlite:///tmp.db")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "postgresql+psycopg://" in str(exc_info.value)


def test_empty_artifact_root_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", "   ")
    with pytest.raises(ValidationError):
        Settings()


def test_artifact_root_configured_preserves_symlink_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked-artifacts"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")

    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", str(linked))
    clear_settings_cache()
    settings = Settings()
    configured = settings.artifact_root_configured
    assert configured.is_symlink()
    assert configured == linked.expanduser()
    # Must not equal the resolved target merely via settings wiring.
    assert configured != linked.resolve()


def test_artifact_root_configured_does_not_call_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pathlib import Path as PathType

    calls: list[str] = []
    original_resolve = PathType.resolve

    def tracking_resolve(self: PathType, *args: object, **kwargs: object) -> PathType:
        calls.append(str(self))
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", "artifacts-relative")
    monkeypatch.setattr(PathType, "resolve", tracking_resolve)
    settings = Settings()
    _ = settings.artifact_root_configured
    assert calls == []


def test_settings_to_store_rejects_configured_root_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from zorqen_research.infrastructure.artifacts.local import (
        ArtifactStoreError,
        LocalFilesystemArtifactStore,
    )

    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked-artifacts"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")

    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", str(linked))
    settings = Settings()
    with pytest.raises(ArtifactStoreError, match="Configured artifact root must not be a symlink"):
        LocalFilesystemArtifactStore(settings.artifact_root_configured)
