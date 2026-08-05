"""Strict loading of baseline JSON documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from zorqen_research.application.strategy_definitions.parsing import loads_strict_json
from zorqen_research.domain.baselines.errors import BaselineParseError, BaselineValidationError
from zorqen_research.domain.strategy_definitions.errors import (
    StrategyDefinitionParseError,
    StrategyDefinitionValidationError,
)
from zorqen_research.domain.strategy_definitions.identifiers import MAX_JSON_BYTES


def load_json_object(path: Path, *, field: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        msg = f"{field} file not found"
        raise BaselineValidationError(msg) from exc
    except OSError as exc:
        msg = f"unable to read {field}"
        raise BaselineValidationError(msg) from exc
    if len(raw) > MAX_JSON_BYTES:
        msg = f"{field} exceeds maximum size of {MAX_JSON_BYTES} bytes"
        raise BaselineParseError(msg)
    try:
        document = loads_strict_json(raw, field=field)
    except (StrategyDefinitionParseError, StrategyDefinitionValidationError) as exc:
        raise BaselineParseError(str(exc)) from exc
    if not isinstance(document, dict):
        msg = f"{field} must be a JSON object"
        raise BaselineParseError(msg)
    return document
