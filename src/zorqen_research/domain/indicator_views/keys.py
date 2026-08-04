"""Canonical indicator series keys for bundle identity."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.math_policy import require_period

_KEY_SCHEMA = "1"
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


@dataclass(frozen=True, slots=True, init=False)
class IndicatorSeriesKey:
    """Immutable canonical identity for one indicator series within a bundle."""

    indicator_code: IndicatorCode
    parameters: tuple[tuple[str, int], ...]
    key_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorSeriesKey must be created via from_verified"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def from_verified(
        cls,
        *,
        indicator_code: IndicatorCode,
        parameters: object,
    ) -> IndicatorSeriesKey:
        if not isinstance(indicator_code, IndicatorCode):
            msg = "indicator_code must be an IndicatorCode"
            raise IndicatorViewValidationError(msg)
        ordered = _canonicalize_key_parameters(indicator_code, parameters)
        digest = sha256_hex(
            json.dumps(
                {
                    "indicator_code": indicator_code.value,
                    "parameters": {key: value for key, value in ordered},
                    "schema_version": _KEY_SCHEMA,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "indicator_code", indicator_code)
        object.__setattr__(self, "parameters", ordered)
        object.__setattr__(self, "key_hash", digest)
        return self

    @classmethod
    def from_series_parameters(
        cls,
        *,
        indicator_code: IndicatorCode,
        parameters: tuple[tuple[str, int], ...],
    ) -> IndicatorSeriesKey:
        return cls.from_verified(indicator_code=indicator_code, parameters=dict(parameters))

    def sort_tuple(self) -> tuple[str, tuple[tuple[str, int], ...]]:
        return (self.indicator_code.value, self.parameters)

    def __repr__(self) -> str:
        if not self.parameters:
            return f"IndicatorSeriesKey({self.indicator_code.value})"
        period = self.parameters[0][1]
        return f"IndicatorSeriesKey({self.indicator_code.value}, period={period})"

    def __str__(self) -> str:
        return self.__repr__()


def _canonicalize_key_parameters(
    indicator_code: IndicatorCode,
    parameters: object,
) -> tuple[tuple[str, int], ...]:
    if parameters is None:
        parameters = {}
    if type(parameters) is tuple:
        # Accept already-canonical series parameters.
        if indicator_code is IndicatorCode.TRUE_RANGE:
            if parameters:
                msg = "true_range key accepts no parameters"
                raise IndicatorViewValidationError(msg)
            return ()
        if len(parameters) != 1:
            msg = "period indicator key requires exactly period"
            raise IndicatorViewValidationError(msg)
        key, value = parameters[0]
        if type(key) is not str or key != "period":
            msg = "parameter key must be 'period'"
            raise IndicatorViewValidationError(msg)
        try:
            return (("period", require_period(value)),)
        except IndicatorValidationError as exc:
            raise IndicatorViewValidationError(str(exc)) from exc

    if not isinstance(parameters, dict):
        msg = "parameters must be a mapping or canonical tuple"
        raise IndicatorViewValidationError(msg)
    if indicator_code is IndicatorCode.TRUE_RANGE:
        if parameters:
            msg = "true_range key accepts no parameters"
            raise IndicatorViewValidationError(msg)
        return ()
    if indicator_code not in _PERIOD_CODES:
        msg = "unsupported indicator code for series key"
        raise IndicatorViewValidationError(msg)
    if set(parameters.keys()) != {"period"}:
        msg = "period indicator key requires exactly period"
        raise IndicatorViewValidationError(msg)
    try:
        return (("period", require_period(parameters["period"])),)
    except IndicatorValidationError as exc:
        raise IndicatorViewValidationError(str(exc)) from exc
