"""Canonical serialization and hashing for strategy definitions."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.instances import (
    BoundParameterValue,
    StrategyInstanceSpecification,
    StrategyParameterSet,
    bind_parameter_values,
    parameter_kind_label,
)
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)


def _canonical_json_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _parameter_to_document(param: StrategyParameterDefinition) -> dict[str, Any]:
    base: dict[str, Any] = {
        "key": param.key,
        "display_name": param.display_name,
        "description": param.description,
        "kind": parameter_kind_label(param),
        "researchable": param.researchable,
    }
    if isinstance(param, DecimalParameterDefinition):
        base["default_value"] = format_canonical_decimal(param.default_value)
        base["minimum"] = None if param.minimum is None else format_canonical_decimal(param.minimum)
        base["maximum"] = None if param.maximum is None else format_canonical_decimal(param.maximum)
        base["step"] = None if param.step is None else format_canonical_decimal(param.step)
        return base
    if isinstance(param, IntegerParameterDefinition):
        base["default_value"] = param.default_value
        base["minimum"] = param.minimum
        base["maximum"] = param.maximum
        base["step"] = param.step
        return base
    if isinstance(param, BooleanParameterDefinition):
        base["default_value"] = param.default_value
        return base
    if isinstance(param, EnumParameterDefinition):
        base["default_value"] = param.default_value
        base["choices"] = list(param.choices)
        return base
    msg = f"unsupported parameter type: {type(param)!r}"
    raise TypeError(msg)


def definition_to_document(definition: StrategyDefinition) -> dict[str, Any]:
    return {
        "schema_version": definition.schema_version,
        "definition_id": str(definition.definition_id),
        "family_id": str(definition.family_id),
        "family_code": definition.family_code,
        "definition_code": definition.definition_code,
        "display_name": definition.display_name,
        "description": definition.description,
        "version": definition.version,
        "status": definition.status.value,
        "execution_timeframe": definition.execution_timeframe.value,
        "execution_warmup_bars": definition.execution_warmup_bars,
        "context_requirements": [
            {
                "timeframe": req.timeframe.value,
                "warmup_bars": req.warmup_bars,
            }
            for req in definition.context_requirements
        ],
        "supported_directions": [d.value for d in definition.supported_directions],
        "parameters": [_parameter_to_document(p) for p in definition.parameters],
        "source_spec_sha256": definition.source_spec_sha256,
    }


def serialize_definition(definition: StrategyDefinition) -> bytes:
    return _canonical_json_bytes(definition_to_document(definition))


def hash_definition(definition: StrategyDefinition) -> str:
    return sha256_hex(serialize_definition(definition))


def _bound_value_document(value: BoundParameterValue) -> Decimal | int | bool | str:
    if isinstance(value.value, Decimal):
        return format_canonical_decimal(value.value)
    return value.value


def parameter_set_to_document(parameter_set: StrategyParameterSet) -> dict[str, Any]:
    return {
        "definition_hash": parameter_set.definition_hash,
        "parameters": {item.key: _bound_value_document(item) for item in parameter_set.values},
    }


def serialize_parameter_set(parameter_set: StrategyParameterSet) -> bytes:
    return _canonical_json_bytes(parameter_set_to_document(parameter_set))


def hash_parameter_set(parameter_set: StrategyParameterSet) -> str:
    return sha256_hex(serialize_parameter_set(parameter_set))


def instance_to_document(instance: StrategyInstanceSpecification) -> dict[str, Any]:
    return {
        "definition_hash": instance.definition_hash,
        "parameter_set_hash": instance.parameter_set_hash,
        "definition": definition_to_document(instance.definition),
        "parameter_set": parameter_set_to_document(instance.parameter_set),
    }


def serialize_instance(instance: StrategyInstanceSpecification) -> bytes:
    return _canonical_json_bytes(instance_to_document(instance))


def hash_instance_components(*, definition_hash: str, parameter_set_hash: str) -> str:
    payload = {
        "definition_hash": definition_hash,
        "parameter_set_hash": parameter_set_hash,
    }
    return sha256_hex(_canonical_json_bytes(payload))


def build_instance(
    definition: StrategyDefinition,
    raw_values: dict[str, object],
) -> StrategyInstanceSpecification:
    definition_hash = hash_definition(definition)
    parameter_set = bind_parameter_values(
        definition,
        definition_hash=definition_hash,
        raw_values=raw_values,
    )
    parameter_set_hash = hash_parameter_set(parameter_set)
    instance_hash = hash_instance_components(
        definition_hash=definition_hash,
        parameter_set_hash=parameter_set_hash,
    )
    return StrategyInstanceSpecification(
        definition=definition,
        parameter_set=parameter_set,
        definition_hash=definition_hash,
        parameter_set_hash=parameter_set_hash,
        instance_hash=instance_hash,
    )
