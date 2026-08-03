"""Strict JSON parser adversarial tests for strategy definitions."""

from __future__ import annotations

import json

import pytest

from tests.unit.strategy_definition_helpers import EXAMPLE_DEFINITION, sample_definition
from zorqen_research.application.strategy_definitions.parsing import (
    loads_strict_json,
    parse_definition_bytes,
    parse_parameter_values_bytes,
)
from zorqen_research.application.strategy_definitions.serialization import (
    definition_to_document,
    serialize_definition,
)
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionParseError
from zorqen_research.domain.strategy_definitions.identifiers import MAX_JSON_BYTES


def _base_doc() -> dict[str, object]:
    return definition_to_document(sample_definition())


def test_fixture_parses() -> None:
    definition = parse_definition_bytes(EXAMPLE_DEFINITION.read_bytes())
    assert definition.definition_code == "example_test_definition"
    assert len(definition.parameters) == 4


def test_bom_and_invalid_utf8() -> None:
    with pytest.raises(StrategyDefinitionParseError, match="BOM"):
        loads_strict_json(b"\xef\xbb\xbf{}")
    with pytest.raises(StrategyDefinitionParseError, match="UTF-8"):
        loads_strict_json(b"\xff\xfe{}")


def test_duplicate_keys_top_and_nested() -> None:
    with pytest.raises(StrategyDefinitionParseError, match="Duplicate"):
        loads_strict_json(b'{"a":1,"a":2}')
    with pytest.raises(StrategyDefinitionParseError, match="Duplicate"):
        loads_strict_json(b'{"parameters":{"x":1,"x":2}}')


def test_trailing_and_array_toplevel() -> None:
    with pytest.raises(StrategyDefinitionParseError):
        loads_strict_json(b'{"a":1}{"b":2}')
    with pytest.raises(StrategyDefinitionParseError, match="object"):
        loads_strict_json(b"[1,2,3]")


def test_unknown_and_missing_fields() -> None:
    doc = _base_doc()
    doc["extra_field"] = "nope"
    with pytest.raises(StrategyDefinitionParseError, match="unknown"):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
    doc = _base_doc()
    del doc["version"]
    with pytest.raises(StrategyDefinitionParseError, match="missing"):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))


def test_oversized_input() -> None:
    huge = b"{" + b'"a":' + b'"' + (b"x" * (MAX_JSON_BYTES + 10)) + b'"}'
    with pytest.raises(StrategyDefinitionParseError, match="maximum size"):
        loads_strict_json(huge)


def test_json_nan_infinity() -> None:
    with pytest.raises(StrategyDefinitionParseError):
        loads_strict_json(b'{"a":NaN}')
    with pytest.raises(StrategyDefinitionParseError):
        loads_strict_json(b'{"a":Infinity}')


def test_decimal_must_be_canonical_string() -> None:
    doc = _base_doc()
    params = doc["parameters"]
    assert isinstance(params, list)
    decimal_param = next(p for p in params if p["key"] == "atr_multiplier")
    decimal_param["default_value"] = 2.5
    with pytest.raises(StrategyDefinitionParseError, match="canonical decimal string"):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
    for bad in ("2.500", "+2.5", "02.5", "-0"):
        decimal_param["default_value"] = bad
        with pytest.raises(StrategyDefinitionParseError, match="canonical"):
            parse_definition_bytes(json.dumps(doc).encode("utf-8"))


def test_nul_and_long_text() -> None:
    doc = _base_doc()
    doc["display_name"] = "bad\x00name"
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
    doc = _base_doc()
    doc["definition_code"] = "a" * 65
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))
    doc = _base_doc()
    doc["description"] = "x" * 4001
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(json.dumps(doc).encode("utf-8"))


def test_parser_never_leaks_raw_exceptions() -> None:
    cases = [
        b"\xef\xbb\xbf{}",
        b'{"a":1,"a":2}',
        b"[1]",
        b'{"a":NaN}',
        b"{",
        b"\xff\xfe",
    ]
    for raw in cases:
        with pytest.raises(StrategyDefinitionParseError):
            loads_strict_json(raw)


def test_round_trip_serialized_definition() -> None:
    original = sample_definition()
    again = parse_definition_bytes(serialize_definition(original))
    assert hash_definition_safe(original) == hash_definition_safe(again)


def hash_definition_safe(definition: object) -> str:
    from zorqen_research.application.strategy_definitions.serialization import hash_definition

    return hash_definition(definition)  # type: ignore[arg-type]


def test_parameter_values_object() -> None:
    values = parse_parameter_values_bytes(
        b'{"parameters":{"atr_period":14,"atr_multiplier":"2.5"}}'
    )
    assert values["atr_period"] == 14
    assert values["atr_multiplier"] == "2.5"
    with pytest.raises(StrategyDefinitionParseError):
        parse_parameter_values_bytes(b'{"parameters":[]}')
