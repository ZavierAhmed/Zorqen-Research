"""Milestone 0.7A integrity: hashes, family immutability, parser/Unicode boundaries."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from uuid import UUID

import pytest

from tests.unit.strategy_definition_helpers import (
    EXAMPLE_DEFINITION,
    sample_definition,
    sample_enum_param,
)
from zorqen_research.application.strategy_definitions.parsing import (
    loads_strict_json,
    parse_definition_bytes,
)
from zorqen_research.application.strategy_definitions.serialization import (
    build_instance,
    hash_definition,
    hash_parameter_set,
    serialize_definition,
    serialize_instance,
    serialize_parameter_set,
)
from zorqen_research.domain.strategy_definitions.errors import (
    StrategyDefinitionParseError,
    StrategyDefinitionValidationError,
)
from zorqen_research.domain.strategy_definitions.identifiers import (
    require_canonical_sha256,
    require_logical_sha256,
    require_unicode_scalars,
)
from zorqen_research.domain.strategy_definitions.instances import (
    BoundParameterValue,
    StrategyInstanceSpecification,
    StrategyParameterSet,
    bind_default_parameter_set,
)
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
    SEEDED_FAMILY_PAIRS,
    SUPPORT_RESISTANCE_CODE,
    SUPPORT_RESISTANCE_ID,
    require_seeded_family_pair,
)


def _default_values() -> dict[str, object]:
    return {
        "atr_multiplier": Decimal("2.5"),
        "atr_period": 14,
        "entry_mode": "strict",
        "use_confirmation": True,
    }


def test_canonical_sha256_rejects_forgeries() -> None:
    assert require_canonical_sha256("a" * 64, field="h") == "a" * 64
    for bad in (
        "z" * 64,
        "A" * 64,
        "a" * 63,
        "a" * 65,
        " sha256:" + ("a" * 64),
        "sha256:" + ("a" * 64),
        "a" * 63 + " ",
        123,
        None,
    ):
        with pytest.raises(StrategyDefinitionValidationError):
            require_canonical_sha256(bad, field="h")  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError, match="placeholder"):
        require_logical_sha256("0" * 64, field="definition_hash")
    with pytest.raises(StrategyDefinitionValidationError):
        require_logical_sha256("z" * 64, field="definition_hash")


def test_definition_parameter_instance_hashes_not_forgeable() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    parameter_set = bind_default_parameter_set(definition, definition_hash=digest)
    instance = StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)

    with pytest.raises(TypeError):
        StrategyParameterSet(  # type: ignore[call-arg]
            definition_hash=digest,
            values=parameter_set.values,
            parameter_set_hash="z" * 64,
        )
    with pytest.raises(TypeError):
        StrategyInstanceSpecification(  # type: ignore[call-arg]
            definition=definition,
            parameter_set=parameter_set,
            definition_hash="z" * 64,
            parameter_set_hash="z" * 64,
            instance_hash="z" * 64,
        )

    wrong_def = StrategyParameterSet(definition_hash="ab" * 32, values=parameter_set.values)
    with pytest.raises(StrategyDefinitionValidationError, match="does not match"):
        StrategyInstanceSpecification(definition=definition, parameter_set=wrong_def)

    # Tamper attempt: bind with forged definition hash string rejected against content.
    with pytest.raises(StrategyDefinitionValidationError, match="does not match"):
        bind_default_parameter_set(definition, definition_hash="cd" * 32)

    assert instance.definition_hash == digest
    assert instance.parameter_set_hash == parameter_set.parameter_set_hash
    assert instance.parameter_set.definition_hash == digest
    assert len(instance.instance_hash) == 64
    assert instance.instance_hash != "0" * 64


def test_bound_parameter_value_intrinsic_validation() -> None:
    BoundParameterValue(key="atr_period", value=14)
    BoundParameterValue(key="entry_mode", value="strict")
    BoundParameterValue(key="use_confirmation", value=True)
    BoundParameterValue(key="atr_multiplier", value=Decimal("2.5"))
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="atr_period", value=14.0)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="atr_multiplier", value=Decimal("NaN"))
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="atr_multiplier", value=Decimal("Infinity"))
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="entry_mode", value=object())  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="entry_mode", value="bad\x00")
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="entry_mode", value="\ud800")
    with pytest.raises(StrategyDefinitionValidationError):
        BoundParameterValue(key="BadKey", value=1)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyParameterSet(
            definition_hash="ab" * 32,
            values=(("atr_period", 14),),  # type: ignore[arg-type]
        )


def test_seeded_family_pairs_runtime_immutable() -> None:
    assert len(SEEDED_FAMILY_PAIRS) == 2
    assert list(SEEDED_FAMILY_PAIRS.items()) == [
        (ADAPTIVE_MTF_TREND_BREAKOUT_ID, ADAPTIVE_MTF_TREND_BREAKOUT_CODE),
        (SUPPORT_RESISTANCE_ID, SUPPORT_RESISTANCE_CODE),
    ]
    with pytest.raises(TypeError):
        SEEDED_FAMILY_PAIRS[ADAPTIVE_MTF_TREND_BREAKOUT_ID] = "mutated"  # type: ignore[index]
    with pytest.raises(TypeError):
        del SEEDED_FAMILY_PAIRS[ADAPTIVE_MTF_TREND_BREAKOUT_ID]  # type: ignore[misc]
    third = UUID("99999999-9999-4999-8999-999999999999")
    with pytest.raises(TypeError):
        SEEDED_FAMILY_PAIRS[third] = "third_family"  # type: ignore[index]
    require_seeded_family_pair(
        family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
        family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    )
    assert len(SEEDED_FAMILY_PAIRS) == 2


def test_huge_integer_and_deep_nesting_parser_boundary() -> None:
    from zorqen_research.domain.strategy_definitions.identifiers import MAX_JSON_NESTING_DEPTH

    limit = sys.get_int_max_str_digits()
    digits = "1" + ("0" * limit)
    payload = f'{{"n":{digits}}}'.encode()
    assert len(payload) < (1 << 20)
    with pytest.raises(StrategyDefinitionParseError) as huge_exc:
        loads_strict_json(payload)
    assert "Traceback" not in str(huge_exc.value)
    assert "\\" not in str(huge_exc.value) or "C:" not in str(huge_exc.value)

    # Explicit depth gate (not OS stack RecursionError) — regresses Ubuntu CI gap.
    depth = MAX_JSON_NESTING_DEPTH  # innermost object depth = depth + 1
    deep = b"{" + (b'"a":{' * depth) + b'"x":1' + (b"}" * depth) + b"}"
    assert len(deep) < (1 << 20)
    with pytest.raises(StrategyDefinitionParseError, match="nesting depth") as nest_exc:
        loads_strict_json(deep)
    assert "Traceback" not in str(nest_exc.value)

    # Adversarial deep document under size limit still fails on Linux and Windows.
    adversarial = b"{" + (b'"a":{' * 5000) + b'"x":1' + (b"}" * 5000) + b"}"
    assert len(adversarial) < (1 << 20)
    with pytest.raises(StrategyDefinitionParseError, match="nesting depth"):
        loads_strict_json(adversarial)


@pytest.mark.parametrize(
    "field",
    ["display_name", "description", "enum_choice", "enum_default"],
)
def test_lone_surrogate_rejected_in_definition_fields(field: str) -> None:
    doc = json.loads(serialize_definition(sample_definition()).decode("utf-8"))
    # Build via escaped JSON so the token is a lone surrogate scalar in the string.
    if field == "display_name":
        doc["display_name"] = "NAME_SURROGATE"
        raw = json.dumps(doc).replace('"NAME_SURROGATE"', '"\\ud800"').encode("utf-8")
    elif field == "description":
        doc["description"] = "DESC_SURROGATE"
        raw = json.dumps(doc).replace('"DESC_SURROGATE"', '"\\udfff"').encode("utf-8")
    elif field == "enum_choice":
        enum_p = next(p for p in doc["parameters"] if p["key"] == "entry_mode")
        enum_p["choices"] = ["strict", "CHOICE_SURROGATE"]
        raw = json.dumps(doc).replace('"CHOICE_SURROGATE"', '"\\ud800"').encode("utf-8")
    else:
        enum_p = next(p for p in doc["parameters"] if p["key"] == "entry_mode")
        enum_p["default_value"] = "DEFAULT_SURROGATE"
        enum_p["choices"] = ["DEFAULT_SURROGATE", "relaxed"]
        raw = json.dumps(doc).replace('"DEFAULT_SURROGATE"', '"\\ud800"').encode("utf-8")
    with pytest.raises(StrategyDefinitionParseError):
        parse_definition_bytes(raw)


def test_lone_surrogate_bound_enum_value() -> None:
    definition = sample_definition()
    raw = b'{"parameters":{"atr_multiplier":"2.5","atr_period":14,'
    raw += b'"entry_mode":"\\ud800","use_confirmation":true}}'
    from zorqen_research.application.strategy_definitions.parsing import (
        coerce_parameter_values_for_definition,
        parse_parameter_values_bytes,
    )
    from zorqen_research.application.strategy_definitions.serialization import build_instance

    values = parse_parameter_values_bytes(raw)
    typed = coerce_parameter_values_for_definition(definition, values)
    with pytest.raises(StrategyDefinitionValidationError):
        build_instance(definition, typed)


def test_enum_rejects_custom_equality_object() -> None:
    class PretendStrict:
        def __eq__(self, other: object) -> bool:
            return other == "strict"

        def __hash__(self) -> int:
            return hash("strict")

    param = sample_enum_param()
    with pytest.raises(StrategyDefinitionValidationError, match="real str"):
        param.validate_value(PretendStrict())  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(default_value=PretendStrict())  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices=("strict", PretendStrict()))  # type: ignore[arg-type]


def test_unicode_scalars_helper_and_non_ascii_ok() -> None:
    assert require_unicode_scalars("café — 東京", field="t") == "café — 東京"
    with pytest.raises(StrategyDefinitionValidationError):
        require_unicode_scalars("\ud800", field="t")
    with pytest.raises(StrategyDefinitionValidationError):
        require_unicode_scalars("ok\x00", field="t")
    definition = sample_definition(display_name="Café Strategy", description="東京テスト")
    payload = serialize_definition(definition)
    assert payload.decode("utf-8")
    assert hash_definition(definition)


def test_round_trip_definition_parameter_set_instance() -> None:
    original = parse_definition_bytes(EXAMPLE_DEFINITION.read_bytes())
    ser1 = serialize_definition(original)
    again = parse_definition_bytes(ser1)
    ser2 = serialize_definition(again)
    assert again == original
    assert ser1 == ser2
    assert hash_definition(again) == hash_definition(original)

    instance = build_instance(original, _default_values())
    ps_bytes = serialize_parameter_set(instance.parameter_set)
    assert ps_bytes.decode("utf-8")
    assert hash_parameter_set(instance.parameter_set) == instance.parameter_set_hash

    again_instance = StrategyInstanceSpecification(
        definition=again,
        parameter_set=instance.parameter_set,
    )
    assert again_instance.definition_hash == instance.definition_hash
    assert again_instance.parameter_set_hash == instance.parameter_set_hash
    assert again_instance.instance_hash == instance.instance_hash
    inst_bytes = serialize_instance(instance)
    assert inst_bytes.decode("utf-8")
    assert serialize_instance(again_instance) == inst_bytes


def test_every_accepted_model_serializes_utf8() -> None:
    definition = sample_definition()
    instance = build_instance(definition, _default_values())
    for payload in (
        serialize_definition(definition),
        serialize_parameter_set(instance.parameter_set),
        serialize_instance(instance),
    ):
        assert isinstance(payload, bytes)
        payload.decode("utf-8")
