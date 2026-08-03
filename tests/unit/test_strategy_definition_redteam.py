"""Red-team adversarial attacks against strategy-definition boundaries."""

from __future__ import annotations

import json

import pytest

from tests.unit.strategy_definition_helpers import sample_definition, sample_enum_param
from zorqen_research.application.strategy_definitions.parsing import (
    loads_strict_json,
    parse_definition_bytes,
)
from zorqen_research.application.strategy_definitions.serialization import (
    definition_to_document,
    hash_definition,
)
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.errors import (
    StrategyDefinitionParseError,
    StrategyDefinitionValidationError,
)
from zorqen_research.domain.strategy_definitions.identifiers import parse_uuid_string
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.timeframes import Timeframe


def test_mutable_containers_rejected() -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices=["a", "b"])  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(supported_directions=[PositionDirection.LONG])  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(
            context_requirements=[TimeframeRequirement(Timeframe.H4, 1)]  # type: ignore[arg-type]
        )


def test_uppercase_uuid_and_hash_prefix_rejected() -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        parse_uuid_string("AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE", field="definition_id")
    doc = definition_to_document(sample_definition())
    doc["definition_id"] = "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE"
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(
            status=DefinitionStatus.APPROVED,
            source_spec_sha256="sha256:" + ("a" * 64),
        )


def test_bool_as_warmup_and_float_as_int() -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(execution_warmup_bars=False)  # type: ignore[arg-type]
    doc = definition_to_document(sample_definition())
    params = doc["parameters"]
    assert isinstance(params, list)
    integer = next(p for p in params if p["key"] == "atr_period")
    integer["default_value"] = 14.0
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))


def test_short_before_long_and_unsorted_context() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="canonical order"):
        sample_definition(supported_directions=(PositionDirection.SHORT, PositionDirection.LONG))
    with pytest.raises(StrategyDefinitionValidationError, match="ordered"):
        sample_definition(
            context_requirements=(
                TimeframeRequirement(Timeframe.W1, 1),
                TimeframeRequirement(Timeframe.M15, 1),
            )
        )


def test_approved_placeholder_and_draft_optional_hash() -> None:
    draft = sample_definition(source_spec_sha256=None)
    assert hash_definition(draft)
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(status=DefinitionStatus.APPROVED, source_spec_sha256="0" * 64)


def test_parameter_values_duplicate_key_in_json() -> None:
    with pytest.raises(StrategyDefinitionParseError, match="Duplicate"):
        loads_strict_json(b'{"parameters":{"atr_period":1,"atr_period":2}}')


def test_no_dynamic_import_fields_in_schema() -> None:
    payload = json.dumps(definition_to_document(sample_definition()))
    assert "module_path" not in payload
    assert "class_name" not in payload
    assert "import" not in payload


def test_family_pair_enforced_in_parser() -> None:
    doc = definition_to_document(sample_definition())
    doc["family_code"] = "support_resistance"
    with pytest.raises(StrategyDefinitionParseError, match="mismatch"):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
