"""Factory-bound trusted indicator series bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.application.indicators.serialization import (
    hash_indicator_series,
    serialize_indicator_series,
)
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import default_math_policy
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_BUNDLE_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False)
class IndicatorSeriesBundle:
    """Offline bundle of trusted indicator series for one symbol/timeframe."""

    schema_version: str
    symbol: Symbol
    timeframe: Timeframe
    input_candle_count: int
    input_candle_hash: str
    input_hash: str
    series: tuple[IndicatorSeries, ...]
    series_count: int
    series_keys: tuple[IndicatorSeriesKey, ...]
    bundle_hash: str
    indicator_input: IndicatorInput

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorSeriesBundle must be created via from_verified"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def from_verified(
        cls,
        *,
        indicator_input: IndicatorInput,
        series: object,
    ) -> IndicatorSeriesBundle:
        if not isinstance(indicator_input, IndicatorInput):
            msg = "indicator_input must be an IndicatorInput"
            raise IndicatorViewValidationError(msg)
        if type(series) is not tuple:
            msg = "series must be an exact tuple"
            raise IndicatorViewValidationError(msg)
        if len(series) == 0:
            msg = "bundle must contain at least one series"
            raise IndicatorViewValidationError(msg)

        policy = default_math_policy()
        keyed: list[tuple[IndicatorSeriesKey, IndicatorSeries]] = []
        seen_hashes: set[str] = set()
        for index, item in enumerate(series):
            if type(item) is not IndicatorSeries:
                msg = f"series[{index}] must be an exact IndicatorSeries"
                raise IndicatorViewValidationError(msg)
            try:
                _ = (
                    item.symbol,
                    item.timeframe,
                    item.input_candle_count,
                    item.input_candle_sha256,
                    item.math_policy,
                    item.parameters,
                    item.values,
                    item.result_hash,
                    item.indicator_code,
                )
            except AttributeError as exc:
                msg = f"series[{index}] must be an exact IndicatorSeries"
                raise IndicatorViewValidationError(msg) from exc
            if item.symbol != indicator_input.symbol:
                msg = f"series[{index}] symbol does not match indicator input"
                raise IndicatorViewValidationError(msg)
            if item.timeframe is not indicator_input.timeframe:
                msg = f"series[{index}] timeframe does not match indicator input"
                raise IndicatorViewValidationError(msg)
            if item.input_candle_count != indicator_input.candle_count:
                msg = f"series[{index}] candle count does not match indicator input"
                raise IndicatorViewValidationError(msg)
            if item.input_candle_sha256 != indicator_input.candle_sha256:
                msg = f"series[{index}] candle hash does not match indicator input"
                raise IndicatorViewValidationError(msg)
            if item.math_policy is not policy:
                msg = f"series[{index}] math policy is not the fixed Milestone policy"
                raise IndicatorViewValidationError(msg)
            try:
                serialize_indicator_series(item).decode("utf-8")
            except Exception as exc:  # noqa: BLE001
                msg = f"series[{index}] failed UTF-8 serialization"
                raise IndicatorViewValidationError(msg) from exc
            recomputed = hash_indicator_series(item)
            if recomputed != item.result_hash:
                msg = f"series[{index}] result hash does not match recomputed hash"
                raise IndicatorViewValidationError(msg)
            key = IndicatorSeriesKey.from_series_parameters(
                indicator_code=item.indicator_code,
                parameters=item.parameters,
            )
            if key.key_hash in seen_hashes:
                msg = "duplicate indicator series keys are not permitted"
                raise IndicatorViewValidationError(msg)
            seen_hashes.add(key.key_hash)
            keyed.append((key, item))

        keyed.sort(key=lambda pair: pair[0].sort_tuple())
        ordered_keys = tuple(key for key, _ in keyed)
        ordered_series = tuple(item for _, item in keyed)

        digest = sha256_hex(
            json.dumps(
                {
                    "input_candle_count": indicator_input.candle_count,
                    "input_candle_hash": indicator_input.candle_sha256,
                    "input_hash": indicator_input.input_hash,
                    "schema_version": _BUNDLE_SCHEMA,
                    "series_count": len(ordered_series),
                    "series_keys": [
                        {
                            "indicator_code": key.indicator_code.value,
                            "key_hash": key.key_hash,
                            "parameters": {k: v for k, v in key.parameters},
                        }
                        for key in ordered_keys
                    ],
                    "series_result_hashes": [item.result_hash for item in ordered_series],
                    "symbol": indicator_input.symbol.value,
                    "timeframe": indicator_input.timeframe.value,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )

        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _BUNDLE_SCHEMA)
        object.__setattr__(self, "symbol", indicator_input.symbol)
        object.__setattr__(self, "timeframe", indicator_input.timeframe)
        object.__setattr__(self, "input_candle_count", indicator_input.candle_count)
        object.__setattr__(self, "input_candle_hash", indicator_input.candle_sha256)
        object.__setattr__(self, "input_hash", indicator_input.input_hash)
        object.__setattr__(self, "series", ordered_series)
        object.__setattr__(self, "series_count", len(ordered_series))
        object.__setattr__(self, "series_keys", ordered_keys)
        object.__setattr__(self, "bundle_hash", digest)
        object.__setattr__(self, "indicator_input", indicator_input)
        return self
