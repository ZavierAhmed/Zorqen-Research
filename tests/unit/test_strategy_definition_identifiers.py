"""Identifier, version, text, and hash validation tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import (
    MAX_DESCRIPTION_LENGTH,
    MAX_IDENTIFIER_LENGTH,
    NIL_UUID,
    require_canonical_identifier,
    require_definition_uuid,
    require_display_text,
    require_semantic_version,
    require_source_spec_sha256,
)


@pytest.mark.parametrize(
    "value",
    ["atr_period", "a", "entry_mode", "use_confirmation", "x1_y2"],
)
def test_valid_identifiers(value: str) -> None:
    assert require_canonical_identifier(value, field="code") == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        " atr",
        "atr ",
        "ATR",
        "atr-period",
        "atr.period",
        "atr period",
        "_atr",
        "atr_",
        "atr__period",
        "аtr",  # Cyrillic lookalike
        "a" * (MAX_IDENTIFIER_LENGTH + 1),
    ],
)
def test_invalid_identifiers(value: str) -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        require_canonical_identifier(value, field="code")


@pytest.mark.parametrize("value", ["0.1.0", "1.0.0", "2.4.17", "10.20.30"])
def test_valid_versions(value: str) -> None:
    assert require_semantic_version(value) == value


@pytest.mark.parametrize(
    "value",
    ["v1.0.0", "1.0", "1", "1.0.0-alpha", "1.0.0+build", "01.0.0", "1.02.0", "1.0.03"],
)
def test_invalid_versions(value: str) -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        require_semantic_version(value)


def test_display_text_rejects_nul_and_bounds() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="NUL"):
        require_display_text("bad\x00name", field="display_name", max_length=200)
    with pytest.raises(StrategyDefinitionValidationError, match="maximum"):
        require_display_text(
            "x" * (MAX_DESCRIPTION_LENGTH + 1),
            field="description",
            max_length=MAX_DESCRIPTION_LENGTH,
        )


def test_definition_uuid_rejects_nil() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="nil"):
        require_definition_uuid(NIL_UUID)
    ok = UUID("11111111-1111-4111-8111-111111111111")
    assert require_definition_uuid(ok) == ok


def test_source_hash_rules() -> None:
    good = "a" * 64
    assert require_source_spec_sha256(good) == good
    with pytest.raises(StrategyDefinitionValidationError):
        require_source_spec_sha256("A" * 64)
    with pytest.raises(StrategyDefinitionValidationError):
        require_source_spec_sha256("sha256:" + "a" * 64)
    with pytest.raises(StrategyDefinitionValidationError):
        require_source_spec_sha256("0" * 64)
    with pytest.raises(StrategyDefinitionValidationError):
        require_source_spec_sha256("a" * 63)
