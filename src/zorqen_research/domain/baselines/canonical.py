"""Canonical UTF-8 JSON bytes and hashes for baseline documents."""

from __future__ import annotations

import json
import re
from typing import Any

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.baselines.errors import BaselineValidationError
from zorqen_research.domain.strategy_definitions.identifiers import require_logical_sha256

_ABSOLUTE_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/Users/|/home/|\\\\[a-z0-9_.$-]+\\)")
_HOSTNAME_LEAK_RE = re.compile(r"(?i)\b(?:localhost|127\.0\.0\.1)\b")


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
        msg = "canonical baseline document is not serializable as UTF-8 JSON"
        raise BaselineValidationError(msg) from exc


def hash_canonical_document(document: dict[str, Any], *, field: str) -> str:
    return require_logical_sha256(sha256_hex(canonical_json_bytes(document)), field=field)


def reject_local_path_leakage(document: object, *, field: str = "document") -> None:
    """Reject absolute local paths or hostnames in string leaves."""
    stack: list[object] = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str) and (
            _ABSOLUTE_PATH_RE.search(node) or _HOSTNAME_LEAK_RE.search(node)
        ):
            msg = f"{field} must not contain local absolute paths or hostnames"
            raise BaselineValidationError(msg)
