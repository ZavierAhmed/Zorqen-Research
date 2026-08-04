"""Strict JSON parsing for strategy definitions and parameter values."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.enums import (
    ParameterKind,
    parse_definition_status,
    parse_parameter_kind,
)
from zorqen_research.domain.strategy_definitions.errors import (
    StrategyDefinitionParseError,
    StrategyDefinitionValidationError,
)
from zorqen_research.domain.strategy_definitions.identifiers import (
    MAX_JSON_BYTES,
    MAX_JSON_NESTING_DEPTH,
    parse_uuid_string,
)
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.timeframes import Timeframe, parse_timeframe


def _reject_nonfinite(name: str) -> None:
    msg = f"JSON non-finite constant is not allowed: {name}"
    raise StrategyDefinitionParseError(msg)


def _object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            msg = f"Duplicate JSON object key: {key!r}"
            raise StrategyDefinitionParseError(msg)
        out[key] = value
    return out


def _enforce_max_json_nesting(document: object, *, field: str) -> None:
    """Reject documents deeper than MAX_JSON_NESTING_DEPTH (platform-independent)."""
    stack: list[tuple[object, int]] = [(document, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > MAX_JSON_NESTING_DEPTH:
            msg = f"{field} exceeds maximum JSON nesting depth"
            raise StrategyDefinitionParseError(msg)
        if isinstance(node, dict):
            stack.extend((value, depth + 1) for value in node.values())
        elif isinstance(node, list):
            stack.extend((value, depth + 1) for value in node)


def loads_strict_json(raw: bytes, *, field: str = "document") -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        msg = f"{field} exceeds maximum size of {MAX_JSON_BYTES} bytes"
        raise StrategyDefinitionParseError(msg)
    if raw.startswith(b"\xef\xbb\xbf"):
        msg = f"{field} must not include a UTF-8 BOM"
        raise StrategyDefinitionParseError(msg)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"{field} must be valid UTF-8"
        raise StrategyDefinitionParseError(msg) from exc
    try:
        document = json.loads(
            text,
            parse_constant=_reject_nonfinite,
            object_pairs_hook=_object_pairs_hook,
        )
    except StrategyDefinitionParseError:
        raise
    except json.JSONDecodeError as exc:
        msg = f"{field} is not valid JSON"
        raise StrategyDefinitionParseError(msg) from exc
    except RecursionError as exc:
        msg = f"{field} exceeds maximum JSON nesting depth"
        raise StrategyDefinitionParseError(msg) from exc
    except ValueError as exc:
        msg = f"{field} contains an invalid JSON value"
        raise StrategyDefinitionParseError(msg) from exc
    except OverflowError as exc:
        msg = f"{field} contains an out-of-range JSON value"
        raise StrategyDefinitionParseError(msg) from exc
    if not isinstance(document, dict):
        msg = f"{field} must be a JSON object"
        raise StrategyDefinitionParseError(msg)
    decoder = json.JSONDecoder(
        object_pairs_hook=_object_pairs_hook, parse_constant=_reject_nonfinite
    )
    try:
        _, end = decoder.raw_decode(text)
    except json.JSONDecodeError as exc:
        msg = f"{field} is not valid JSON"
        raise StrategyDefinitionParseError(msg) from exc
    except RecursionError as exc:
        msg = f"{field} exceeds maximum JSON nesting depth"
        raise StrategyDefinitionParseError(msg) from exc
    except ValueError as exc:
        msg = f"{field} contains an invalid JSON value"
        raise StrategyDefinitionParseError(msg) from exc
    except OverflowError as exc:
        msg = f"{field} contains an out-of-range JSON value"
        raise StrategyDefinitionParseError(msg) from exc
    if text[end:].strip():
        msg = f"{field} contains trailing non-whitespace content"
        raise StrategyDefinitionParseError(msg)
    _enforce_max_json_nesting(document, field=field)
    return document


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        msg = "definition file not found"
        raise StrategyDefinitionParseError(msg) from exc
    except OSError as exc:
        msg = "unable to read definition file"
        raise StrategyDefinitionParseError(msg) from exc
    return loads_strict_json(raw, field="file")


def _require_keys(document: dict[str, Any], required: set[str], *, label: str) -> None:
    missing = required - set(document)
    unknown = set(document) - required
    if missing:
        msg = f"{label} missing required fields: {sorted(missing)}"
        raise StrategyDefinitionParseError(msg)
    if unknown:
        msg = f"{label} contains unknown fields: {sorted(unknown)}"
        raise StrategyDefinitionParseError(msg)


def _parse_canonical_decimal_string(value: object, *, field: str) -> Decimal:
    if not isinstance(value, str):
        msg = f"{field} must be a canonical decimal string"
        raise StrategyDefinitionParseError(msg)
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        msg = f"{field} is not a valid decimal string"
        raise StrategyDefinitionParseError(msg) from exc
    if not parsed.is_finite():
        msg = f"{field} must be a finite decimal"
        raise StrategyDefinitionParseError(msg)
    if format_canonical_decimal(parsed) != value:
        msg = f"{field} must use canonical decimal string form"
        raise StrategyDefinitionParseError(msg)
    return parsed


def _parse_optional_decimal(value: object, *, field: str) -> Decimal | None:
    if value is None:
        return None
    return _parse_canonical_decimal_string(value, field=field)


def _parse_optional_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be a JSON integer or null"
        raise StrategyDefinitionParseError(msg)
    return value


def _parse_parameter(document: object) -> StrategyParameterDefinition:
    if not isinstance(document, dict):
        msg = "parameter must be a JSON object"
        raise StrategyDefinitionParseError(msg)
    kind = parse_parameter_kind(document.get("kind"))
    common = {"key", "display_name", "description", "kind", "researchable", "default_value"}
    if kind is ParameterKind.DECIMAL:
        _require_keys(document, common | {"minimum", "maximum", "step"}, label="decimal parameter")
        return DecimalParameterDefinition(
            key=document["key"],
            display_name=document["display_name"],
            description=document["description"],
            researchable=document["researchable"],
            default_value=_parse_canonical_decimal_string(
                document["default_value"], field="default_value"
            ),
            minimum=_parse_optional_decimal(document["minimum"], field="minimum"),
            maximum=_parse_optional_decimal(document["maximum"], field="maximum"),
            step=_parse_optional_decimal(document["step"], field="step"),
        )
    if kind is ParameterKind.INTEGER:
        _require_keys(document, common | {"minimum", "maximum", "step"}, label="integer parameter")
        if isinstance(document["default_value"], bool) or not isinstance(
            document["default_value"], int
        ):
            msg = "integer default_value must be a JSON integer"
            raise StrategyDefinitionParseError(msg)
        return IntegerParameterDefinition(
            key=document["key"],
            display_name=document["display_name"],
            description=document["description"],
            researchable=document["researchable"],
            default_value=document["default_value"],
            minimum=_parse_optional_int(document["minimum"], field="minimum"),
            maximum=_parse_optional_int(document["maximum"], field="maximum"),
            step=_parse_optional_int(document["step"], field="step"),
        )
    if kind is ParameterKind.BOOLEAN:
        _require_keys(document, common, label="boolean parameter")
        if not isinstance(document["default_value"], bool):
            msg = "boolean default_value must be a JSON boolean"
            raise StrategyDefinitionParseError(msg)
        return BooleanParameterDefinition(
            key=document["key"],
            display_name=document["display_name"],
            description=document["description"],
            researchable=document["researchable"],
            default_value=document["default_value"],
        )
    if kind is ParameterKind.ENUM:
        _require_keys(document, common | {"choices"}, label="enum parameter")
        choices = document["choices"]
        if not isinstance(choices, list):
            msg = "enum choices must be a JSON array"
            raise StrategyDefinitionParseError(msg)
        return EnumParameterDefinition(
            key=document["key"],
            display_name=document["display_name"],
            description=document["description"],
            researchable=document["researchable"],
            default_value=document["default_value"],
            choices=tuple(choices),
        )
    msg = f"Unsupported parameter kind: {kind!r}"
    raise StrategyDefinitionParseError(msg)


def _parse_direction(value: object) -> PositionDirection:
    if not isinstance(value, str):
        msg = "supported_directions values must be strings"
        raise StrategyDefinitionParseError(msg)
    try:
        return PositionDirection(value)
    except ValueError as exc:
        msg = f"Unsupported direction: {value!r}"
        raise StrategyDefinitionParseError(msg) from exc


def _parse_timeframe(value: object, *, field: str) -> Timeframe:
    if not isinstance(value, str):
        msg = f"{field} must be a string"
        raise StrategyDefinitionParseError(msg)
    try:
        return parse_timeframe(value).value
    except ValueError as exc:
        raise StrategyDefinitionParseError(str(exc)) from exc


def parse_definition_document(document: dict[str, Any]) -> StrategyDefinition:
    required = {
        "schema_version",
        "definition_id",
        "family_id",
        "family_code",
        "definition_code",
        "display_name",
        "description",
        "version",
        "status",
        "execution_timeframe",
        "execution_warmup_bars",
        "context_requirements",
        "supported_directions",
        "parameters",
        "source_spec_sha256",
    }
    _require_keys(document, required, label="definition")
    try:
        status = parse_definition_status(document["status"])
        context_raw = document["context_requirements"]
        if not isinstance(context_raw, list):
            msg = "context_requirements must be a JSON array"
            raise StrategyDefinitionParseError(msg)
        context: list[TimeframeRequirement] = []
        for item in context_raw:
            if not isinstance(item, dict):
                msg = "context requirement must be a JSON object"
                raise StrategyDefinitionParseError(msg)
            _require_keys(item, {"timeframe", "warmup_bars"}, label="context requirement")
            context.append(
                TimeframeRequirement(
                    timeframe=_parse_timeframe(item["timeframe"], field="timeframe"),
                    warmup_bars=item["warmup_bars"],
                )
            )
        directions_raw = document["supported_directions"]
        if not isinstance(directions_raw, list):
            msg = "supported_directions must be a JSON array"
            raise StrategyDefinitionParseError(msg)
        parameters_raw = document["parameters"]
        if not isinstance(parameters_raw, list):
            msg = "parameters must be a JSON array"
            raise StrategyDefinitionParseError(msg)
        parameters = tuple(_parse_parameter(item) for item in parameters_raw)
        return StrategyDefinition(
            schema_version=document["schema_version"],
            definition_id=parse_uuid_string(document["definition_id"], field="definition_id"),
            family_id=parse_uuid_string(document["family_id"], field="family_id"),
            family_code=document["family_code"],
            definition_code=document["definition_code"],
            display_name=document["display_name"],
            description=document["description"],
            version=document["version"],
            status=status,
            execution_timeframe=_parse_timeframe(
                document["execution_timeframe"], field="execution_timeframe"
            ),
            execution_warmup_bars=document["execution_warmup_bars"],
            context_requirements=tuple(context),
            supported_directions=tuple(_parse_direction(d) for d in directions_raw),
            parameters=parameters,
            source_spec_sha256=document["source_spec_sha256"],
        )
    except StrategyDefinitionParseError:
        raise
    except StrategyDefinitionValidationError as exc:
        raise StrategyDefinitionParseError(str(exc)) from exc
    except (TypeError, AttributeError, KeyError, InvalidOperation) as exc:
        msg = "definition document contains invalid values"
        raise StrategyDefinitionParseError(msg) from exc


def parse_definition_bytes(raw: bytes) -> StrategyDefinition:
    return parse_definition_document(loads_strict_json(raw, field="definition"))


def parse_definition_file(path: Path) -> StrategyDefinition:
    return parse_definition_document(load_json_file(path))


def parse_parameter_values_document(document: dict[str, Any]) -> dict[str, object]:
    _require_keys(document, {"parameters"}, label="parameter values")
    raw = document["parameters"]
    if not isinstance(raw, dict):
        msg = "parameters must be a JSON object"
        raise StrategyDefinitionParseError(msg)
    # Duplicate keys already rejected by object_pairs_hook.
    return dict(raw)


def parse_parameter_values_bytes(raw: bytes) -> dict[str, object]:
    return parse_parameter_values_document(loads_strict_json(raw, field="parameters"))


def parse_parameter_values_file(path: Path) -> dict[str, object]:
    return parse_parameter_values_document(load_json_file(path))


def coerce_parameter_values_for_definition(
    definition: StrategyDefinition,
    raw_values: dict[str, object],
) -> dict[str, object]:
    """
    Convert JSON-decoded values into typed Python values for binding.

    Decimal parameters must remain canonical strings in JSON and are converted
    to Decimal here. Integers/bools/enums keep their JSON types.
    """
    by_key = {param.key: param for param in definition.parameters}
    out: dict[str, object] = {}
    for key, value in raw_values.items():
        param = by_key.get(key)
        if param is None:
            out[key] = value
            continue
        if isinstance(param, DecimalParameterDefinition):
            out[key] = _parse_canonical_decimal_string(value, field=f"parameters.{key}")
        else:
            out[key] = value
    return out
