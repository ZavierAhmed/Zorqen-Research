"""Immutable indicator-series results."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    IndicatorMathPolicy,
    default_math_policy,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_RESULT_SCHEMA = "1"


def _require_defined_value(value: object, *, index: int) -> Decimal:
    if value is None:
        msg = f"values[{index}] cannot be None when validating a defined slot"
        raise IndicatorValidationError(msg)
    if type(value) is bool or not isinstance(value, Decimal):
        msg = f"values[{index}] must be Decimal or None"
        raise IndicatorValidationError(msg)
    if not value.is_finite():
        msg = f"values[{index}] must be a finite Decimal"
        raise IndicatorValidationError(msg)
    return value


def _validate_values(
    values: object,
    *,
    expected_count: int,
) -> tuple[Decimal | None, ...]:
    if not isinstance(values, tuple):
        msg = "values must be an immutable tuple"
        raise IndicatorValidationError(msg)
    if len(values) != expected_count:
        msg = "values length must equal input candle count"
        raise IndicatorValidationError(msg)
    normalized: list[Decimal | None] = []
    for index, value in enumerate(values):
        if value is None:
            normalized.append(None)
            continue
        if type(value) is bool or type(value) is int or type(value) is float:
            msg = f"values[{index}] must be Decimal or None"
            raise IndicatorValidationError(msg)
        if not isinstance(value, Decimal):
            msg = f"values[{index}] must be Decimal or None"
            raise IndicatorValidationError(msg)
        if not value.is_finite():
            msg = f"values[{index}] must be a finite Decimal"
            raise IndicatorValidationError(msg)
        # Canonicalize signed zero to Decimal("0") for stable serialization.
        if value == 0:
            normalized.append(Decimal("0"))
        else:
            normalized.append(value)
    return tuple(normalized)


def _first_defined_index(values: tuple[Decimal | None, ...]) -> int | None:
    for index, value in enumerate(values):
        if value is not None:
            return index
    return None


def _defined_value_count(values: tuple[Decimal | None, ...]) -> int:
    return sum(1 for value in values if value is not None)


@dataclass(frozen=True, slots=True, init=False)
class IndicatorSeries:
    """Complete offline indicator value series — not provider-safe."""

    schema_version: str
    indicator_code: IndicatorCode
    symbol: Symbol
    timeframe: Timeframe
    input_candle_sha256: str
    input_candle_count: int
    parameters: tuple[tuple[str, int | str | bool], ...]
    value_count: int
    values: tuple[Decimal | None, ...]
    first_defined_index: int | None
    defined_value_count: int
    math_policy: IndicatorMathPolicy
    result_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorSeries must be created via from_calculation"
        raise IndicatorValidationError(msg)

    @classmethod
    def from_calculation(
        cls,
        *,
        indicator_code: IndicatorCode,
        indicator_input: IndicatorInput,
        parameters: Mapping[str, int | str | bool],
        values: tuple[Decimal | None, ...],
        math_policy: IndicatorMathPolicy | None = None,
    ) -> IndicatorSeries:
        if not isinstance(indicator_code, IndicatorCode):
            msg = "indicator_code must be an IndicatorCode"
            raise IndicatorValidationError(msg)
        if not isinstance(indicator_input, IndicatorInput):
            msg = "indicator_input must be an IndicatorInput"
            raise IndicatorValidationError(msg)
        policy = math_policy if math_policy is not None else default_math_policy()
        if policy is not default_math_policy():
            msg = "only the fixed Milestone 1.0 math policy is permitted"
            raise IndicatorValidationError(msg)
        if not isinstance(parameters, Mapping):
            msg = "parameters must be a mapping"
            raise IndicatorValidationError(msg)
        ordered_params = tuple((key, parameters[key]) for key in sorted(parameters.keys()))
        for key, value in ordered_params:
            if not isinstance(key, str):
                msg = "parameter keys must be strings"
                raise IndicatorValidationError(msg)
            if type(value) is bool:
                continue
            if type(value) is int:
                continue
            if type(value) is str:
                continue
            msg = "parameter values must be int, str, or bool"
            raise IndicatorValidationError(msg)

        verified_values = _validate_values(
            values,
            expected_count=indicator_input.candle_count,
        )
        first = _first_defined_index(verified_values)
        defined = _defined_value_count(verified_values)

        from zorqen_research.application.indicators.serialization import (
            hash_indicator_series_payload,
        )

        digest = hash_indicator_series_payload(
            schema_version=_RESULT_SCHEMA,
            indicator_code=indicator_code,
            symbol=indicator_input.symbol,
            timeframe=indicator_input.timeframe,
            input_candle_sha256=indicator_input.candle_sha256,
            input_candle_count=indicator_input.candle_count,
            parameters=ordered_params,
            first_defined_index=first,
            defined_value_count=defined,
            math_policy=policy,
            values=verified_values,
        )

        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _RESULT_SCHEMA)
        object.__setattr__(self, "indicator_code", indicator_code)
        object.__setattr__(self, "symbol", indicator_input.symbol)
        object.__setattr__(self, "timeframe", indicator_input.timeframe)
        object.__setattr__(self, "input_candle_sha256", indicator_input.candle_sha256)
        object.__setattr__(self, "input_candle_count", indicator_input.candle_count)
        object.__setattr__(self, "parameters", ordered_params)
        object.__setattr__(self, "value_count", len(verified_values))
        object.__setattr__(self, "values", verified_values)
        object.__setattr__(self, "first_defined_index", first)
        object.__setattr__(self, "defined_value_count", defined)
        object.__setattr__(self, "math_policy", policy)
        object.__setattr__(self, "result_hash", digest)
        return self


# Re-export helper for tests that need defined-value checks.
require_defined_decimal = _require_defined_value
