"""Prefix-only content hash chain for provider-visible indicator histories."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.math_policy import IndicatorMathPolicy
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_PREFIX_SCHEMA = "1"


def canonical_value_token(value: Decimal | None) -> bytes:
    """Canonical token for one indicator value in the prefix hash chain."""
    if value is None:
        return b"null"
    if type(value) is not Decimal:
        msg = "prefix value token requires exact Decimal or None"
        raise TypeError(msg)
    return format_canonical_decimal(value).encode("utf-8")


def build_prefix_header_bytes(
    *,
    symbol: Symbol,
    timeframe: Timeframe,
    series_key: IndicatorSeriesKey,
    math_policy: IndicatorMathPolicy,
) -> bytes:
    document = {
        "indicator_code": series_key.indicator_code.value,
        "math_policy": {
            "decimal_precision": math_policy.decimal_precision,
            "policy_id": math_policy.policy_id,
            "rounding": math_policy.rounding,
            "schema_version": math_policy.schema_version,
        },
        "parameters": {key: value for key, value in series_key.parameters},
        "schema_version": _PREFIX_SCHEMA,
        "symbol": symbol.value,
        "timeframe": timeframe.value,
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def compute_prefix_hash_chain(
    *,
    symbol: Symbol,
    timeframe: Timeframe,
    series_key: IndicatorSeriesKey,
    math_policy: IndicatorMathPolicy,
    values: tuple[Decimal | None, ...],
) -> tuple[str, ...]:
    """
    Precompute prefix hashes once.

    ``prefix_hashes[0]`` covers zero visible values.
    ``prefix_hashes[N]`` covers values ``0..N-1``.
    """
    header = build_prefix_header_bytes(
        symbol=symbol,
        timeframe=timeframe,
        series_key=series_key,
        math_policy=math_policy,
    )
    current = hashlib.sha256(header).digest()
    out: list[str] = [current.hex()]
    for value in values:
        current = hashlib.sha256(current + b"\n" + canonical_value_token(value)).digest()
        out.append(current.hex())
    return tuple(out)
