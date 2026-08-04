"""Factory-bound trusted indicator series bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.application.indicator_views.recalculation import recalculate_indicator_series
from zorqen_research.application.indicators.serialization import serialize_indicator_series
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_BUNDLE_SCHEMA = "1"


def _reverify_indicator_input(indicator_input: object) -> IndicatorInput:
    """Reject subclasses before attribute access; rebuild from candles."""
    if type(indicator_input) is not IndicatorInput:
        msg = "indicator_input must be an exact IndicatorInput"
        raise IndicatorViewValidationError(msg)
    try:
        trusted = IndicatorInput.from_verified(
            symbol=indicator_input.symbol,
            timeframe=indicator_input.timeframe,
            candles=indicator_input.candles,
        )
    except IndicatorValidationError as exc:
        msg = "indicator_input failed candle reconstruction"
        raise IndicatorViewValidationError(msg) from exc

    if trusted.symbol != indicator_input.symbol:
        msg = "indicator_input symbol does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.timeframe is not indicator_input.timeframe:
        msg = "indicator_input timeframe does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.candles is not indicator_input.candles:
        msg = "indicator_input candle tuple identity does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.candle_count != indicator_input.candle_count:
        msg = "indicator_input candle_count does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.minimum_open_time != indicator_input.minimum_open_time:
        msg = "indicator_input minimum_open_time does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.maximum_open_time != indicator_input.maximum_open_time:
        msg = "indicator_input maximum_open_time does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.candle_sha256 != indicator_input.candle_sha256:
        msg = "indicator_input candle_sha256 does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    if trusted.input_hash != indicator_input.input_hash:
        msg = "indicator_input input_hash does not match reconstructed input"
        raise IndicatorViewValidationError(msg)
    return trusted


def _require_series_matches_recalculation(
    *,
    supplied: IndicatorSeries,
    expected: IndicatorSeries,
    index: int,
) -> None:
    try:
        supplied_bytes = serialize_indicator_series(supplied)
        expected_bytes = serialize_indicator_series(expected)
    except Exception as exc:  # noqa: BLE001
        msg = f"series[{index}] failed UTF-8 serialization"
        raise IndicatorViewValidationError(msg) from exc
    if supplied_bytes != expected_bytes:
        msg = f"series[{index}] is not byte-identical to calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.schema_version != expected.schema_version:
        msg = f"series[{index}] schema_version does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.indicator_code is not expected.indicator_code:
        msg = f"series[{index}] indicator_code does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.symbol != expected.symbol:
        msg = f"series[{index}] symbol does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.timeframe is not expected.timeframe:
        msg = f"series[{index}] timeframe does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.input_candle_sha256 != expected.input_candle_sha256:
        msg = f"series[{index}] input candle hash does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.input_candle_count != expected.input_candle_count:
        msg = f"series[{index}] input candle count does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.parameters != expected.parameters:
        msg = f"series[{index}] parameters do not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.value_count != expected.value_count:
        msg = f"series[{index}] value_count does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.values != expected.values:
        msg = f"series[{index}] values do not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.first_defined_index != expected.first_defined_index:
        msg = f"series[{index}] first_defined_index does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.defined_value_count != expected.defined_value_count:
        msg = f"series[{index}] defined_value_count does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.math_policy is not expected.math_policy:
        msg = f"series[{index}] math_policy does not match calculator output"
        raise IndicatorViewValidationError(msg)
    if supplied.result_hash != expected.result_hash:
        msg = f"series[{index}] result_hash does not match calculator output"
        raise IndicatorViewValidationError(msg)


def build_bundle_document(
    *,
    trusted_input: IndicatorInput,
    ordered_keys: tuple[IndicatorSeriesKey, ...],
    ordered_series: tuple[IndicatorSeries, ...],
) -> dict[str, object]:
    """Canonical bundle document derived only from trusted content."""
    return {
        "input_candle_count": trusted_input.candle_count,
        "input_candle_hash": trusted_input.candle_sha256,
        "input_hash": trusted_input.input_hash,
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
        "symbol": trusted_input.symbol.value,
        "timeframe": trusted_input.timeframe.value,
    }


def hash_bundle_document(document: dict[str, object]) -> str:
    return sha256_hex(
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def require_bundle_identity_match(
    *,
    submitted: IndicatorSeriesBundle,
    trusted: IndicatorSeriesBundle,
) -> None:
    """Require submitted bundle metadata matches a rebuilt trusted bundle."""
    if submitted.schema_version != trusted.schema_version:
        msg = "bundle schema_version does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.symbol != trusted.symbol:
        msg = "bundle symbol does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.timeframe is not trusted.timeframe:
        msg = "bundle timeframe does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.input_candle_count != trusted.input_candle_count:
        msg = "bundle input_candle_count does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.input_candle_hash != trusted.input_candle_hash:
        msg = "bundle input_candle_hash does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.input_hash != trusted.input_hash:
        msg = "bundle input_hash does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.series_count != trusted.series_count:
        msg = "bundle series_count does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if submitted.series_keys != trusted.series_keys:
        msg = "bundle series_keys do not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    if len(submitted.series) != len(trusted.series):
        msg = "bundle series length does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)
    for index, (left, right) in enumerate(zip(submitted.series, trusted.series, strict=True)):
        if serialize_indicator_series(left) != serialize_indicator_series(right):
            msg = f"bundle series[{index}] does not match rebuilt trusted series"
            raise IndicatorViewValidationError(msg)
        if left.result_hash != right.result_hash:
            msg = f"bundle series[{index}] result_hash does not match rebuilt trusted series"
            raise IndicatorViewValidationError(msg)
    if submitted.bundle_hash != trusted.bundle_hash:
        msg = "bundle_hash does not match rebuilt trusted bundle"
        raise IndicatorViewValidationError(msg)


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
        trusted_input = _reverify_indicator_input(indicator_input)
        if type(series) is not tuple:
            msg = "series must be an exact tuple"
            raise IndicatorViewValidationError(msg)
        if len(series) == 0:
            msg = "bundle must contain at least one series"
            raise IndicatorViewValidationError(msg)

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
                    item.schema_version,
                    item.value_count,
                    item.first_defined_index,
                    item.defined_value_count,
                )
            except AttributeError as exc:
                msg = f"series[{index}] must be an exact IndicatorSeries"
                raise IndicatorViewValidationError(msg) from exc

            try:
                key = IndicatorSeriesKey.from_series_parameters(
                    indicator_code=item.indicator_code,
                    parameters=item.parameters,
                )
            except IndicatorViewValidationError:
                raise
            except Exception as exc:  # noqa: BLE001
                msg = f"series[{index}] key derivation failed"
                raise IndicatorViewValidationError(msg) from exc

            expected = recalculate_indicator_series(
                indicator_input=trusted_input,
                series_key=key,
            )
            _require_series_matches_recalculation(
                supplied=item,
                expected=expected,
                index=index,
            )
            if key.key_hash in seen_hashes:
                msg = "duplicate indicator series keys are not permitted"
                raise IndicatorViewValidationError(msg)
            seen_hashes.add(key.key_hash)
            # Retain freshly recalculated trusted series, never the caller object.
            keyed.append((key, expected))

        keyed.sort(key=lambda pair: pair[0].sort_tuple())
        ordered_keys = tuple(key for key, _ in keyed)
        ordered_series = tuple(item for _, item in keyed)
        document = build_bundle_document(
            trusted_input=trusted_input,
            ordered_keys=ordered_keys,
            ordered_series=ordered_series,
        )
        digest = hash_bundle_document(document)

        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _BUNDLE_SCHEMA)
        object.__setattr__(self, "symbol", trusted_input.symbol)
        object.__setattr__(self, "timeframe", trusted_input.timeframe)
        object.__setattr__(self, "input_candle_count", trusted_input.candle_count)
        object.__setattr__(self, "input_candle_hash", trusted_input.candle_sha256)
        object.__setattr__(self, "input_hash", trusted_input.input_hash)
        object.__setattr__(self, "series", ordered_series)
        object.__setattr__(self, "series_count", len(ordered_series))
        object.__setattr__(self, "series_keys", ordered_keys)
        object.__setattr__(self, "bundle_hash", digest)
        object.__setattr__(self, "indicator_input", trusted_input)
        return self
