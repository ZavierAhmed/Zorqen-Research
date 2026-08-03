"""Platform-independent Windows extended-path normalization tests."""

from __future__ import annotations

from pathlib import Path

from zorqen_research.infrastructure.artifacts.local import _without_extended_prefix


def test_strip_drive_extended_prefix() -> None:
    raw = Path("\\\\?\\C:\\Users\\example\\artifacts\\obj")
    normalized = _without_extended_prefix(raw)
    assert str(normalized) == "C:\\Users\\example\\artifacts\\obj"
    assert not str(normalized).startswith("\\\\?\\")


def test_strip_unc_extended_prefix() -> None:
    raw = Path("\\\\?\\UNC\\server\\share\\artifacts\\obj")
    normalized = _without_extended_prefix(raw)
    text = str(normalized)
    assert text.startswith("\\\\server\\share")
    assert "\\\\?\\UNC" not in text
    assert text.endswith("artifacts\\obj") or text.endswith("artifacts/obj")


def test_non_extended_path_unchanged() -> None:
    raw = Path("C:\\Users\\example\\artifacts")
    assert _without_extended_prefix(raw) is raw or str(_without_extended_prefix(raw)) == str(raw)
