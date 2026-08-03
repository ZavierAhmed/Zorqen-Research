"""Identifier, version, text, Unicode, and hash validation helpers."""

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
_ALL_ZERO_HASH = "0" * 64

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def require_unicode_scalars(value: str, *, field: str) -> str:
    """Reject NUL and lone UTF-16 surrogate code points (U+D800–U+DFFF)."""
    if "\x00" in value:
        msg = f"{field} must not contain NUL characters"
        raise StrategyDefinitionValidationError(msg)
    for index, char in enumerate(value):
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            msg = f"{field} must not contain lone Unicode surrogate code points"
            raise StrategyDefinitionValidationError(msg)
        _ = index
    return value


def require_canonical_sha256(value: object, *, field: str) -> str:
    """Require exactly 64 lowercase hex characters (no prefix/whitespace)."""
    if not isinstance(value, str):
        msg = f"{field} must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not _SHA256_RE.fullmatch(value):
        msg = f"{field} must be exactly 64 lowercase hexadecimal characters"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_logical_sha256(value: object, *, field: str) -> str:
    """Canonical SHA-256 for computed logical hashes; rejects all-zero placeholders."""
    digest = require_canonical_sha256(value, field=field)
    if digest == _ALL_ZERO_HASH:
        msg = f"{field} must not be a placeholder all-zero hash"
        raise StrategyDefinitionValidationError(msg)
    return digest


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
    require_unicode_scalars(value, field=field)
    return value


def require_display_text(value: object, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        msg = f"{field} must be a string"
        raise StrategyDefinitionValidationError(msg)
    if not value or value != value.strip():
        msg = f"{field} must be a non-empty trimmed string"
        raise StrategyDefinitionValidationError(msg)
    require_unicode_scalars(value, field=field)
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
    return require_logical_sha256(value, field="source_spec_sha256")


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
