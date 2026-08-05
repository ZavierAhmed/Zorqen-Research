"""Provenance-sealed multi-timeframe + indicator composition input."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.timeframes import Timeframe

_COMPOSITION_SCHEMA = "1"


def _reverify_mtf_input(input_bundle: object) -> MultiTimeframeBacktestInput:
    if type(input_bundle) is not MultiTimeframeBacktestInput:
        msg = "input_bundle must be an exact MultiTimeframeBacktestInput"
        raise StrategyBacktestValidationError(msg)
    try:
        _ = (
            input_bundle.strategy_instance,
            input_bundle.symbol,
            input_bundle.execution_candles,
            input_bundle.contexts,
            input_bundle.input_bundle_hash,
        )
    except AttributeError as exc:
        msg = "input_bundle must be an exact MultiTimeframeBacktestInput"
        raise StrategyBacktestValidationError(msg) from exc

    context_series = tuple((ctx.timeframe, ctx.candles) for ctx in input_bundle.contexts)
    trusted = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=input_bundle.strategy_instance,
        symbol=input_bundle.symbol,
        execution_candles=input_bundle.execution_candles,
        context_series=context_series,
    )
    _require_mtf_identity_match(submitted=input_bundle, trusted=trusted)
    return trusted


def _require_mtf_identity_match(
    *,
    submitted: MultiTimeframeBacktestInput,
    trusted: MultiTimeframeBacktestInput,
) -> None:
    if submitted.strategy_instance_hash != trusted.strategy_instance_hash:
        msg = "strategy_instance_hash does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.symbol != trusted.symbol:
        msg = "symbol does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_timeframe is not trusted.execution_timeframe:
        msg = "execution_timeframe does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_warmup_bars != trusted.execution_warmup_bars:
        msg = "execution_warmup_bars does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_candle_count != trusted.execution_candle_count:
        msg = "execution_candle_count does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_candle_sha256 != trusted.execution_candle_sha256:
        msg = "execution_candle_sha256 does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_candles is not trusted.execution_candles:
        msg = "execution candle tuple identity does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if len(submitted.contexts) != len(trusted.contexts):
        msg = "context count does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    for index, (left, right) in enumerate(zip(submitted.contexts, trusted.contexts, strict=True)):
        if left.timeframe is not right.timeframe:
            msg = f"context[{index}] timeframe does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
        if left.warmup_bars != right.warmup_bars:
            msg = f"context[{index}] warmup_bars does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
        if left.candle_count != right.candle_count:
            msg = f"context[{index}] candle_count does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
        if left.candle_sha256 != right.candle_sha256:
            msg = f"context[{index}] candle_sha256 does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
        if left.candles is not right.candles:
            msg = f"context[{index}] candle tuple identity does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
        if left.alignment.alignment_hash != right.alignment.alignment_hash:
            msg = f"context[{index}] alignment_hash does not match rebuilt MTF input"
            raise StrategyBacktestValidationError(msg)
    if (
        submitted.multi_context_alignment.alignment_hash
        != trusted.multi_context_alignment.alignment_hash
    ):
        msg = "multi_context_alignment_hash does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_bundle_hash != trusted.input_bundle_hash:
        msg = "input_bundle_hash does not match rebuilt MTF input"
        raise StrategyBacktestValidationError(msg)


def _rebind_indicator_bundle(
    *,
    bundle: object,
    expected_symbol: object,
    expected_timeframe: Timeframe,
    expected_candles: tuple[Candle, ...],
    expected_candle_count: int,
    expected_candle_sha256: str,
    slot_label: str,
) -> IndicatorSeriesBundle:
    if type(bundle) is not IndicatorSeriesBundle:
        msg = f"{slot_label} must be an exact IndicatorSeriesBundle or None"
        raise StrategyBacktestValidationError(msg)
    try:
        trusted = IndicatorSeriesBundle.from_verified(
            indicator_input=bundle.indicator_input,
            series=bundle.series,
        )
    except IndicatorViewValidationError as exc:
        msg = f"{slot_label} failed indicator bundle provenance rebuild"
        raise StrategyBacktestValidationError(msg) from exc

    if trusted.symbol != expected_symbol:
        msg = f"{slot_label} symbol does not match MTF symbol"
        raise StrategyBacktestValidationError(msg)
    if trusted.timeframe is not expected_timeframe:
        msg = f"{slot_label} timeframe does not match the assigned MTF slot"
        raise StrategyBacktestValidationError(msg)
    if trusted.input_candle_count != expected_candle_count:
        msg = f"{slot_label} candle count does not match MTF candles"
        raise StrategyBacktestValidationError(msg)
    if trusted.input_candle_hash != expected_candle_sha256:
        msg = f"{slot_label} candle hash does not match MTF candles"
        raise StrategyBacktestValidationError(msg)
    if trusted.indicator_input.candles is not expected_candles:
        msg = f"{slot_label} indicator candles must be the exact MTF candle tuple"
        raise StrategyBacktestValidationError(msg)
    if trusted.bundle_hash != bundle.bundle_hash:
        msg = f"{slot_label} bundle_hash does not match rebuilt canonical content"
        raise StrategyBacktestValidationError(msg)
    return trusted


def build_indicator_composition_document(
    *,
    trusted_mtf: MultiTimeframeBacktestInput,
    execution_indicators: IndicatorSeriesBundle | None,
    context_indicators: tuple[IndicatorSeriesBundle | None, ...],
) -> dict[str, object]:
    return {
        "context_indicator_bundle_hashes": [
            None if item is None else item.bundle_hash for item in context_indicators
        ],
        "context_timeframes": [ctx.timeframe.value for ctx in trusted_mtf.contexts],
        "execution_indicator_bundle_hash": (
            None if execution_indicators is None else execution_indicators.bundle_hash
        ),
        "execution_timeframe": trusted_mtf.execution_timeframe.value,
        "mtf_input_bundle_hash": trusted_mtf.input_bundle_hash,
        "schema_version": _COMPOSITION_SCHEMA,
    }


def hash_indicator_composition_document(document: dict[str, object]) -> str:
    return sha256_hex(
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _require_indicator_bundle_canonical_identity(
    *,
    submitted: IndicatorSeriesBundle,
    trusted: IndicatorSeriesBundle,
    slot_label: str,
) -> None:
    """Compare indicator bundles by canonical identity, not object identity."""
    if submitted.symbol != trusted.symbol:
        msg = f"{slot_label} symbol does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.timeframe is not trusted.timeframe:
        msg = f"{slot_label} timeframe does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_candle_count != trusted.input_candle_count:
        msg = f"{slot_label} input_candle_count does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_candle_hash != trusted.input_candle_hash:
        msg = f"{slot_label} input_candle_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_hash != trusted.input_hash:
        msg = f"{slot_label} input_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.series_count != trusted.series_count:
        msg = f"{slot_label} series_count does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.series_keys != trusted.series_keys:
        msg = f"{slot_label} series_keys do not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if len(submitted.series) != len(trusted.series):
        msg = f"{slot_label} series length does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    for index, (left, right) in enumerate(zip(submitted.series, trusted.series, strict=True)):
        if left.result_hash != right.result_hash:
            msg = f"{slot_label} series[{index}] result_hash does not match rebuilt composition"
            raise StrategyBacktestValidationError(msg)
    if submitted.bundle_hash != trusted.bundle_hash:
        msg = f"{slot_label} bundle_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)


def require_indicator_composition_identity_match(
    *,
    submitted: MultiTimeframeIndicatorInput,
    trusted: MultiTimeframeIndicatorInput,
) -> None:
    """Require submitted composition metadata matches a rebuilt trusted composition."""
    if submitted.schema_version != trusted.schema_version:
        msg = "schema_version does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    _require_mtf_identity_match(
        submitted=submitted.input_bundle,
        trusted=trusted.input_bundle,
    )
    if submitted.input_bundle.input_bundle_hash != trusted.input_bundle.input_bundle_hash:
        msg = "MTF input_bundle_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_bundle.strategy_instance_hash != trusted.input_bundle.strategy_instance_hash:
        msg = "strategy_instance_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_bundle.execution_timeframe is not trusted.input_bundle.execution_timeframe:
        msg = "execution_timeframe does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.input_bundle.execution_candle_count != trusted.input_bundle.execution_candle_count:
        msg = "execution_candle_count does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if (
        submitted.input_bundle.execution_candle_sha256
        != trusted.input_bundle.execution_candle_sha256
    ):
        msg = "execution_candle_sha256 does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if len(submitted.input_bundle.contexts) != len(trusted.input_bundle.contexts):
        msg = "context count does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    for index, (left_ctx, right_ctx) in enumerate(
        zip(submitted.input_bundle.contexts, trusted.input_bundle.contexts, strict=True)
    ):
        if left_ctx.timeframe is not right_ctx.timeframe:
            msg = f"context[{index}] timeframe does not match rebuilt composition"
            raise StrategyBacktestValidationError(msg)
        if left_ctx.alignment.alignment_hash != right_ctx.alignment.alignment_hash:
            msg = f"context[{index}] alignment_hash does not match rebuilt composition"
            raise StrategyBacktestValidationError(msg)

    if (submitted.execution_indicators is None) != (trusted.execution_indicators is None):
        msg = "execution_indicators presence does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    if submitted.execution_indicators is not None and trusted.execution_indicators is not None:
        _require_indicator_bundle_canonical_identity(
            submitted=submitted.execution_indicators,
            trusted=trusted.execution_indicators,
            slot_label="execution_indicators",
        )

    if type(submitted.context_indicators) is not tuple:
        msg = "context_indicators must be an exact tuple"
        raise StrategyBacktestValidationError(msg)
    if len(submitted.context_indicators) != len(trusted.context_indicators):
        msg = "context_indicators length does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)
    for index, (left_slot, right_slot) in enumerate(
        zip(submitted.context_indicators, trusted.context_indicators, strict=True)
    ):
        if (left_slot is None) != (right_slot is None):
            msg = f"context_indicators[{index}] presence does not match rebuilt composition"
            raise StrategyBacktestValidationError(msg)
        if left_slot is not None and right_slot is not None:
            _require_indicator_bundle_canonical_identity(
                submitted=left_slot,
                trusted=right_slot,
                slot_label=f"context_indicators[{index}]",
            )

    if submitted.indicator_composition_hash != trusted.indicator_composition_hash:
        msg = "indicator_composition_hash does not match rebuilt composition"
        raise StrategyBacktestValidationError(msg)


def reverify_indicator_composition(submitted: object) -> MultiTimeframeIndicatorInput:
    """Rebuild and verify a composition; return only the trusted reconstructed object."""
    if type(submitted) is not MultiTimeframeIndicatorInput:
        msg = "composition must be an exact MultiTimeframeIndicatorInput"
        raise StrategyBacktestValidationError(msg)
    try:
        _ = (
            submitted.schema_version,
            submitted.input_bundle,
            submitted.execution_indicators,
            submitted.context_indicators,
            submitted.indicator_composition_hash,
        )
        trusted = MultiTimeframeIndicatorInput.from_verified(
            input_bundle=submitted.input_bundle,
            execution_indicators=submitted.execution_indicators,
            context_indicators=submitted.context_indicators,
        )
        require_indicator_composition_identity_match(submitted=submitted, trusted=trusted)
    except StrategyBacktestValidationError:
        raise
    except IndicatorViewValidationError as exc:
        msg = "composition failed indicator provenance rebuild"
        raise StrategyBacktestValidationError(msg) from exc
    except (AttributeError, TypeError, ValueError, IndexError) as exc:
        msg = "composition must be an exact MultiTimeframeIndicatorInput"
        raise StrategyBacktestValidationError(msg) from exc
    return trusted


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeIndicatorInput:
    """Trusted MTF candle input bound to optional per-timeframe indicator bundles."""

    schema_version: str
    input_bundle: MultiTimeframeBacktestInput
    execution_indicators: IndicatorSeriesBundle | None
    context_indicators: tuple[IndicatorSeriesBundle | None, ...]
    indicator_composition_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeIndicatorInput must be created via from_verified"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_verified(
        cls,
        *,
        input_bundle: MultiTimeframeBacktestInput,
        execution_indicators: IndicatorSeriesBundle | None,
        context_indicators: object,
    ) -> MultiTimeframeIndicatorInput:
        trusted_mtf = _reverify_mtf_input(input_bundle)
        if type(context_indicators) is not tuple:
            msg = "context_indicators must be an exact tuple"
            raise StrategyBacktestValidationError(msg)
        if len(context_indicators) != len(trusted_mtf.contexts):
            msg = "context_indicators length must equal MTF context count"
            raise StrategyBacktestValidationError(msg)

        if execution_indicators is None:
            trusted_execution: IndicatorSeriesBundle | None = None
        else:
            trusted_execution = _rebind_indicator_bundle(
                bundle=execution_indicators,
                expected_symbol=trusted_mtf.symbol,
                expected_timeframe=trusted_mtf.execution_timeframe,
                expected_candles=trusted_mtf.execution_candles,
                expected_candle_count=trusted_mtf.execution_candle_count,
                expected_candle_sha256=trusted_mtf.execution_candle_sha256,
                slot_label="execution_indicators",
            )

        trusted_contexts: list[IndicatorSeriesBundle | None] = []
        for index, (slot, context) in enumerate(
            zip(context_indicators, trusted_mtf.contexts, strict=True)
        ):
            if slot is None:
                trusted_contexts.append(None)
                continue
            trusted_contexts.append(
                _rebind_indicator_bundle(
                    bundle=slot,
                    expected_symbol=trusted_mtf.symbol,
                    expected_timeframe=context.timeframe,
                    expected_candles=context.candles,
                    expected_candle_count=context.candle_count,
                    expected_candle_sha256=context.candle_sha256,
                    slot_label=f"context_indicators[{index}]",
                )
            )

        if trusted_execution is None and all(item is None for item in trusted_contexts):
            msg = "at least one execution or context indicator bundle must be configured"
            raise StrategyBacktestValidationError(msg)

        context_tuple = tuple(trusted_contexts)
        document = build_indicator_composition_document(
            trusted_mtf=trusted_mtf,
            execution_indicators=trusted_execution,
            context_indicators=context_tuple,
        )
        digest = hash_indicator_composition_document(document)

        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _COMPOSITION_SCHEMA)
        object.__setattr__(self, "input_bundle", trusted_mtf)
        object.__setattr__(self, "execution_indicators", trusted_execution)
        object.__setattr__(self, "context_indicators", context_tuple)
        object.__setattr__(self, "indicator_composition_hash", digest)
        return self
