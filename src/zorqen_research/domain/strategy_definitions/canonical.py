"""Canonical UTF-8 JSON bytes and deterministic hashes for strategy definitions."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import require_logical_sha256
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)


def format_strategy_decimal(value: Decimal) -> str:
    """Canonical decimal text (signed zero → \"0\")."""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def canonical_json_bytes(document: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (UnicodeEncodeError, ValueError, TypeError, OverflowError) as exc:
        msg = "canonical strategy document is not serializable as UTF-8 JSON"
        raise StrategyDefinitionValidationError(msg) from exc


def parameter_kind_label(param: StrategyParameterDefinition) -> str:
    if isinstance(param, DecimalParameterDefinition):
        return "decimal"
    if isinstance(param, IntegerParameterDefinition):
        return "integer"
    if isinstance(param, BooleanParameterDefinition):
        return "boolean"
    if isinstance(param, EnumParameterDefinition):
        return "enum"
    msg = "unknown parameter definition type"
    raise StrategyDefinitionValidationError(msg)


def _parameter_to_document(param: StrategyParameterDefinition) -> dict[str, Any]:
    base: dict[str, Any] = {
        "key": param.key,
        "display_name": param.display_name,
        "description": param.description,
        "kind": parameter_kind_label(param),
        "researchable": param.researchable,
    }
    if isinstance(param, DecimalParameterDefinition):
        base["default_value"] = format_strategy_decimal(param.default_value)
        base["minimum"] = None if param.minimum is None else format_strategy_decimal(param.minimum)
        base["maximum"] = None if param.maximum is None else format_strategy_decimal(param.maximum)
        base["step"] = None if param.step is None else format_strategy_decimal(param.step)
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
    raise StrategyDefinitionValidationError(msg)


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
    return canonical_json_bytes(definition_to_document(definition))


def hash_definition(definition: StrategyDefinition) -> str:
    return require_logical_sha256(
        sha256_hex(serialize_definition(definition)),
        field="definition_hash",
    )


def bound_value_to_json(value: Decimal | int | bool | str) -> Decimal | int | bool | str:
    if isinstance(value, Decimal):
        return format_strategy_decimal(value)
    return value


def parameter_set_document(
    *,
    definition_hash: str,
    values: tuple[tuple[str, Decimal | int | bool | str], ...],
) -> dict[str, Any]:
    return {
        "definition_hash": definition_hash,
        "parameters": {key: bound_value_to_json(val) for key, val in values},
    }


def compute_parameter_set_hash(
    *,
    definition_hash: str,
    values: tuple[tuple[str, Decimal | int | bool | str], ...],
) -> str:
    payload = parameter_set_document(definition_hash=definition_hash, values=values)
    return require_logical_sha256(
        sha256_hex(canonical_json_bytes(payload)),
        field="parameter_set_hash",
    )


def hash_instance_components(*, definition_hash: str, parameter_set_hash: str) -> str:
    payload = {
        "definition_hash": definition_hash,
        "parameter_set_hash": parameter_set_hash,
    }
    return require_logical_sha256(
        sha256_hex(canonical_json_bytes(payload)),
        field="instance_hash",
    )
