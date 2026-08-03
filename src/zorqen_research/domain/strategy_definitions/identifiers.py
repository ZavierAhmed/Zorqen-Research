"""Identifier, version, text, and hash validation helpers."""

from __future__ import annotations

import re
from uuid import UUID

from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError

SCHEMA_VERSION = "1"
MAX_IDENTIFIER_LENGTH = 64
MAX_DISPLAY_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 4000
MAX_ENUM_CHOICE_LENGTH = 64
MAX_JSON_BYTES = 1 << 20  # 1 MiB
MAX_WARMUP_BARS = 1_000_000
NIL_UUID = UUID(int=0)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def require_canonical_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        msg = f"{field} must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not value or value != value.strip():
        msg = f"{field} must be a non-empty trimmed canonical identifier"
        raise StrategyDefinitionValidationError(msg)
    if len(value) > MAX_IDENTIFIER_LENGTH:
        msg = f"{field} exceeds maximum length {MAX_IDENTIFIER_LENGTH}"
        raise StrategyDefinitionValidationError(msg)
    if not _IDENTIFIER_RE.fullmatch(value):
        msg = f"{field} must be canonical lower_snake_case: {value!r}"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_display_text(value: object, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        msg = f"{field} must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not value or value != value.strip():
        msg = f"{field} must be a non-empty trimmed string"
        raise StrategyDefinitionValidationError(msg)
    if "\x00" in value:
        msg = f"{field} must not contain NUL characters"
        raise StrategyDefinitionValidationError(msg)
    if len(value) > max_length:
        msg = f"{field} exceeds maximum length {max_length}"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_semantic_version(value: object) -> str:
    if not isinstance(value, str):
        msg = "version must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not _VERSION_RE.fullmatch(value):
        msg = f"version must be strict MAJOR.MINOR.PATCH without prefixes/metadata: {value!r}"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_definition_uuid(value: object, *, field: str = "definition_id") -> UUID:
    if not isinstance(value, UUID):
        msg = f"{field} must be a UUID"
        raise StrategyDefinitionValidationError(msg)
    if value == NIL_UUID:
        msg = f"{field} must not be the nil UUID"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_source_spec_sha256(value: object) -> str:
    if not isinstance(value, str):
        msg = "source_spec_sha256 must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not _SHA256_RE.fullmatch(value):
        msg = "source_spec_sha256 must be exactly 64 lowercase hex characters"
        raise StrategyDefinitionValidationError(msg)
    if value == "0" * 64:
        msg = "source_spec_sha256 must not be a placeholder all-zero hash"
        raise StrategyDefinitionValidationError(msg)
    return value


def parse_uuid_string(value: object, *, field: str) -> UUID:
    if isinstance(value, UUID):
        return require_definition_uuid(value, field=field)
    if not isinstance(value, str):
        msg = f"{field} must be a UUID string"
        raise StrategyDefinitionValidationError(msg)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as exc:
        msg = f"{field} must be a valid UUID"
        raise StrategyDefinitionValidationError(msg) from exc
    if value != str(parsed):
        msg = f"{field} must be a lowercase canonical UUID string"
        raise StrategyDefinitionValidationError(msg)
    return require_definition_uuid(parsed, field=field)
