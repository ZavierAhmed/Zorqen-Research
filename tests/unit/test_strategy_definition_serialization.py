"""Canonical serialization and hash stability tests."""

from __future__ import annotations

import json
from decimal import Decimal

from tests.unit.strategy_definition_helpers import EXAMPLE_DEFINITION, sample_definition
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.application.strategy_definitions.parsing import parse_definition_bytes
from zorqen_research.application.strategy_definitions.serialization import (
    build_instance,
    hash_definition,
    hash_parameter_set,
    serialize_definition,
    serialize_parameter_set,
)
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus


def test_repeated_serialization_identical() -> None:
    definition = sample_definition()
    first = serialize_definition(definition)
    second = serialize_definition(definition)
    assert first == second
    assert hash_definition(definition) == hash_definition(definition)


def test_json_key_order_does_not_affect_hash() -> None:
    raw = EXAMPLE_DEFINITION.read_bytes()
    document = json.loads(raw)
    # Rebuild with reversed key insertion order.
    reversed_doc = {k: document[k] for k in reversed(list(document.keys()))}
    a = parse_definition_bytes(json.dumps(document).encode("utf-8"))
    b = parse_definition_bytes(json.dumps(reversed_doc).encode("utf-8"))
    assert hash_definition(a) == hash_definition(b)
    assert serialize_definition(a) == serialize_definition(b)


def test_meaningful_changes_alter_hashes() -> None:
    base = sample_definition()
    base_hash = hash_definition(base)
    assert hash_definition(sample_definition(description="Changed description.")) != base_hash
    assert (
        hash_definition(
            sample_definition(
                status=DefinitionStatus.APPROVED,
                source_spec_sha256="ab" * 32,
            )
        )
        != base_hash
    )
    instance_a = build_instance(
        base,
        {
            "atr_multiplier": Decimal("2.5"),
            "atr_period": 14,
            "entry_mode": "strict",
            "use_confirmation": True,
        },
    )
    instance_b = build_instance(
        base,
        {
            "atr_multiplier": Decimal("3.0"),
            "atr_period": 14,
            "entry_mode": "strict",
            "use_confirmation": True,
        },
    )
    assert instance_a.parameter_set_hash != instance_b.parameter_set_hash
    assert instance_a.instance_hash != instance_b.instance_hash
    assert instance_a.definition_hash == instance_b.definition_hash


def test_no_runtime_metadata_and_decimal_zero() -> None:
    payload = serialize_definition(sample_definition()).decode("utf-8")
    assert "timestamp" not in payload
    assert "localhost" not in payload
    assert "C:\\\\" not in payload
    assert format_canonical_decimal(Decimal("-0")) == "0"
    instance = build_instance(
        sample_definition(),
        {
            "atr_multiplier": Decimal("2.5"),
            "atr_period": 14,
            "entry_mode": "strict",
            "use_confirmation": True,
        },
    )
    text = serialize_parameter_set(instance.parameter_set).decode("utf-8")
    assert hash_parameter_set(instance.parameter_set) == instance.parameter_set_hash
    assert "module" not in text
    assert "class" not in text
