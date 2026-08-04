"""Canonical indicator-series serialization and hashing."""

from __future__ import annotations

import json
from decimal import Decimal

from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.math_policy import IndicatorMathPolicy
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def _parameter_document(
    parameters: tuple[tuple[str, int], ...],
) -> dict[str, int]:
    return {key: value for key, value in parameters}


def _value_document(values: tuple[Decimal | None, ...]) -> list[str | None]:
    out: list[str | None] = []
    for value in values:
        if value is None:
            out.append(None)
        else:
            out.append(format_canonical_decimal(value))
    return out


def build_indicator_series_document(
    *,
    schema_version: str,
    indicator_code: IndicatorCode,
    symbol: Symbol,
    timeframe: Timeframe,
    input_candle_sha256: str,
    input_candle_count: int,
    parameters: tuple[tuple[str, int], ...],
    first_defined_index: int | None,
    defined_value_count: int,
    math_policy: IndicatorMathPolicy,
    values: tuple[Decimal | None, ...],
) -> dict[str, object]:
    return {
        "defined_value_count": defined_value_count,
        "first_defined_index": first_defined_index,
        "indicator_code": indicator_code.value,
        "input_candle_count": input_candle_count,
        "input_candle_sha256": input_candle_sha256,
        "math_policy": {
            "decimal_precision": math_policy.decimal_precision,
            "policy_id": math_policy.policy_id,
            "rounding": math_policy.rounding,
            "schema_version": math_policy.schema_version,
        },
        "parameters": _parameter_document(parameters),
        "schema_version": schema_version,
        "symbol": symbol.value,
        "timeframe": timeframe.value,
        "values": _value_document(values),
    }


def serialize_indicator_series_bytes(
    *,
    schema_version: str,
    indicator_code: IndicatorCode,
    symbol: Symbol,
    timeframe: Timeframe,
    input_candle_sha256: str,
    input_candle_count: int,
    parameters: tuple[tuple[str, int], ...],
    first_defined_index: int | None,
    defined_value_count: int,
    math_policy: IndicatorMathPolicy,
    values: tuple[Decimal | None, ...],
) -> bytes:
    document = build_indicator_series_document(
        schema_version=schema_version,
        indicator_code=indicator_code,
        symbol=symbol,
        timeframe=timeframe,
        input_candle_sha256=input_candle_sha256,
        input_candle_count=input_candle_count,
        parameters=parameters,
        first_defined_index=first_defined_index,
        defined_value_count=defined_value_count,
        math_policy=math_policy,
        values=values,
    )
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def hash_indicator_series_payload(
    *,
    schema_version: str,
    indicator_code: IndicatorCode,
    symbol: Symbol,
    timeframe: Timeframe,
    input_candle_sha256: str,
    input_candle_count: int,
    parameters: tuple[tuple[str, int], ...],
    first_defined_index: int | None,
    defined_value_count: int,
    math_policy: IndicatorMathPolicy,
    values: tuple[Decimal | None, ...],
) -> str:
    return sha256_hex(
        serialize_indicator_series_bytes(
            schema_version=schema_version,
            indicator_code=indicator_code,
            symbol=symbol,
            timeframe=timeframe,
            input_candle_sha256=input_candle_sha256,
            input_candle_count=input_candle_count,
            parameters=parameters,
            first_defined_index=first_defined_index,
            defined_value_count=defined_value_count,
            math_policy=math_policy,
            values=values,
        )
    )


def serialize_indicator_series(series: IndicatorSeries) -> bytes:
    return serialize_indicator_series_bytes(
        schema_version=series.schema_version,
        indicator_code=series.indicator_code,
        symbol=series.symbol,
        timeframe=series.timeframe,
        input_candle_sha256=series.input_candle_sha256,
        input_candle_count=series.input_candle_count,
        parameters=series.parameters,
        first_defined_index=series.first_defined_index,
        defined_value_count=series.defined_value_count,
        math_policy=series.math_policy,
        values=series.values,
    )


def hash_indicator_series(series: IndicatorSeries) -> str:
    return hash_indicator_series_payload(
        schema_version=series.schema_version,
        indicator_code=series.indicator_code,
        symbol=series.symbol,
        timeframe=series.timeframe,
        input_candle_sha256=series.input_candle_sha256,
        input_candle_count=series.input_candle_count,
        parameters=series.parameters,
        first_defined_index=series.first_defined_index,
        defined_value_count=series.defined_value_count,
        math_policy=series.math_policy,
        values=series.values,
    )
