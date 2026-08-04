"""Calculator-owned IndicatorSeries assembly (not a public values factory)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from zorqen_research.application.indicators.serialization import hash_indicator_series_payload
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    IndicatorMathPolicy,
    default_math_policy,
    require_period,
)
from zorqen_research.domain.indicators.results import IndicatorSeries

_RESULT_SCHEMA = "1"
_PERIOD_KEY = "period"
_PERIOD_CODES = frozenset(
    {
        IndicatorCode.EMA_CLOSE,
        IndicatorCode.WILDER_ATR,
        IndicatorCode.ROLLING_HIGHEST,
        IndicatorCode.ROLLING_LOWEST,
        IndicatorCode.PRIOR_ROLLING_HIGHEST,
        IndicatorCode.PRIOR_ROLLING_LOWEST,
    }
)
_NONNEGATIVE_CODES = frozenset(
    {
        IndicatorCode.TRUE_RANGE,
        IndicatorCode.WILDER_ATR,
    }
)


def _require_safe_utf8_text(value: str, *, label: str) -> str:
    if "\x00" in value:
        msg = f"{label} must not contain NUL"
        raise IndicatorValidationError(msg)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        msg = f"{label} must be valid UTF-8 text"
        raise IndicatorValidationError(msg) from exc
    return value


def _canonicalize_parameters(
    indicator_code: IndicatorCode,
    parameters: object,
) -> tuple[tuple[str, int], ...]:
    if not isinstance(parameters, Mapping):
        msg = "parameters must be a mapping"
        raise IndicatorValidationError(msg)
    try:
        items = list(parameters.items())
    except Exception as exc:  # noqa: BLE001 — map adversarial mappings
        msg = "parameters mapping is not readable"
        raise IndicatorValidationError(msg) from exc

    if indicator_code is IndicatorCode.TRUE_RANGE:
        if items:
            msg = "true_range accepts no parameters"
            raise IndicatorValidationError(msg)
        return ()

    if indicator_code not in _PERIOD_CODES:
        msg = "unsupported indicator code for parameter validation"
        raise IndicatorValidationError(msg)

    if len(items) != 1:
        msg = "parameters must contain exactly period"
        raise IndicatorValidationError(msg)

    key, value = items[0]
    if type(key) is not str:
        msg = "parameter keys must be exact str"
        raise IndicatorValidationError(msg)
    _require_safe_utf8_text(key, label="parameter key")
    if key != _PERIOD_KEY:
        msg = "parameter key must be 'period'"
        raise IndicatorValidationError(msg)
    period = require_period(value)
    return ((_PERIOD_KEY, period),)


def _validate_values(
    values: object,
    *,
    expected_count: int,
) -> tuple[Decimal | None, ...]:
    if type(values) is not tuple:
        msg = "values must be an exact tuple"
        raise IndicatorValidationError(msg)
    if len(values) != expected_count:
        msg = "values length must equal input candle count"
        raise IndicatorValidationError(msg)
    normalized: list[Decimal | None] = []
    for index, value in enumerate(values):
        if value is None:
            normalized.append(None)
            continue
        if type(value) is not Decimal:
            msg = f"values[{index}] must be an exact Decimal or None"
            raise IndicatorValidationError(msg)
        if not value.is_finite():
            msg = f"values[{index}] must be a finite Decimal"
            raise IndicatorValidationError(msg)
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


def _require_warmup_shape(
    values: tuple[Decimal | None, ...],
    *,
    undefined_prefix: int,
) -> None:
    n = len(values)
    if undefined_prefix >= n:
        if any(value is not None for value in values):
            msg = "warmup shape requires an entirely undefined series"
            raise IndicatorValidationError(msg)
        return
    for index in range(undefined_prefix):
        if values[index] is not None:
            msg = f"values[{index}] must be undefined warmup None"
            raise IndicatorValidationError(msg)
    for index in range(undefined_prefix, n):
        if values[index] is None:
            msg = f"values[{index}] must be defined after warmup"
            raise IndicatorValidationError(msg)


def _enforce_code_invariants(
    indicator_code: IndicatorCode,
    parameters: tuple[tuple[str, int], ...],
    values: tuple[Decimal | None, ...],
) -> None:
    n = len(values)
    if indicator_code is IndicatorCode.TRUE_RANGE:
        if parameters:
            msg = "true_range parameters must be empty"
            raise IndicatorValidationError(msg)
        if any(value is None for value in values):
            msg = "true_range values must all be defined"
            raise IndicatorValidationError(msg)
        for index, value in enumerate(values):
            assert value is not None
            if value < 0:
                msg = f"true_range values[{index}] must be non-negative"
                raise IndicatorValidationError(msg)
        return

    if len(parameters) != 1 or parameters[0][0] != _PERIOD_KEY:
        msg = "parameters must be exactly period"
        raise IndicatorValidationError(msg)
    period = parameters[0][1]

    if indicator_code in (
        IndicatorCode.EMA_CLOSE,
        IndicatorCode.WILDER_ATR,
        IndicatorCode.ROLLING_HIGHEST,
        IndicatorCode.ROLLING_LOWEST,
    ):
        if period > n:
            _require_warmup_shape(values, undefined_prefix=n)
        else:
            _require_warmup_shape(values, undefined_prefix=period - 1)
    elif indicator_code in (
        IndicatorCode.PRIOR_ROLLING_HIGHEST,
        IndicatorCode.PRIOR_ROLLING_LOWEST,
    ):
        if period >= n:
            _require_warmup_shape(values, undefined_prefix=n)
        else:
            _require_warmup_shape(values, undefined_prefix=period)
    else:
        msg = "unsupported indicator code"
        raise IndicatorValidationError(msg)

    if indicator_code in _NONNEGATIVE_CODES:
        for index, value in enumerate(values):
            if value is not None and value < 0:
                msg = f"values[{index}] must be non-negative"
                raise IndicatorValidationError(msg)


def _calculated_indicator_series(
    *,
    indicator_code: IndicatorCode,
    indicator_input: IndicatorInput,
    parameters: Mapping[str, int] | Mapping[object, object],
    values: tuple[Decimal | None, ...],
    math_policy: IndicatorMathPolicy | None = None,
) -> IndicatorSeries:
    """
    Trusted calculator-owned result builder.

    Not exported from package ``__init__``. Ordinary callers must use the
    public indicator calculators, which never accept arbitrary result values.
    """
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

    ordered_params = _canonicalize_parameters(indicator_code, parameters)
    verified_values = _validate_values(
        values,
        expected_count=indicator_input.candle_count,
    )
    _enforce_code_invariants(indicator_code, ordered_params, verified_values)

    first = _first_defined_index(verified_values)
    defined = _defined_value_count(verified_values)

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

    self = object.__new__(IndicatorSeries)
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
