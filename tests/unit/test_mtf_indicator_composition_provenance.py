"""Milestone 1.2A — seal MTF indicator composition provenance."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.mtf_indicator_helpers import (
    indicator_bundle_for,
    standard_composition,
    standard_mtf,
)
from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.strategy_backtesting.goldens import _enter_long
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.application.strategy_backtesting.indicator_goldens import (
    ScriptedMtfIndicatorProvider,
)
from zorqen_research.application.strategy_backtesting.indicator_runner import (
    MultiTimeframeIndicatorBacktestRunner,
)
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
    reverify_indicator_composition,
)
from zorqen_research.domain.strategy_backtesting.indicator_results import (
    IndicatorStrategyBacktestEnvelope,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.timeframes import Timeframe


def _clone_composition(
    template: MultiTimeframeIndicatorInput,
    *,
    schema_version: str | None = None,
    indicator_composition_hash: str | None = None,
    input_bundle: MultiTimeframeBacktestInput | None = None,
    execution_indicators: IndicatorSeriesBundle | None | object = ...,
    context_indicators: tuple[IndicatorSeriesBundle | None, ...] | None = None,
) -> MultiTimeframeIndicatorInput:
    forged = object.__new__(MultiTimeframeIndicatorInput)
    object.__setattr__(
        forged,
        "schema_version",
        template.schema_version if schema_version is None else schema_version,
    )
    object.__setattr__(
        forged,
        "input_bundle",
        template.input_bundle if input_bundle is None else input_bundle,
    )
    if execution_indicators is ...:
        object.__setattr__(forged, "execution_indicators", template.execution_indicators)
    else:
        object.__setattr__(forged, "execution_indicators", execution_indicators)
    object.__setattr__(
        forged,
        "context_indicators",
        template.context_indicators if context_indicators is None else context_indicators,
    )
    object.__setattr__(
        forged,
        "indicator_composition_hash",
        (
            template.indicator_composition_hash
            if indicator_composition_hash is None
            else indicator_composition_hash
        ),
    )
    return forged


def _clone_mtf(
    template: MultiTimeframeBacktestInput,
    *,
    input_bundle_hash: str | None = None,
) -> MultiTimeframeBacktestInput:
    forged = object.__new__(MultiTimeframeBacktestInput)
    for name in MultiTimeframeBacktestInput.__slots__:
        object.__setattr__(forged, name, getattr(template, name))
    if input_bundle_hash is not None:
        object.__setattr__(forged, "input_bundle_hash", input_bundle_hash)
    return forged


def _clone_bundle(
    template: IndicatorSeriesBundle,
    *,
    bundle_hash: str | None = None,
    series: tuple[IndicatorSeries, ...] | None = None,
) -> IndicatorSeriesBundle:
    forged = object.__new__(IndicatorSeriesBundle)
    for name in IndicatorSeriesBundle.__slots__:
        object.__setattr__(forged, name, getattr(template, name))
    if bundle_hash is not None:
        object.__setattr__(forged, "bundle_hash", bundle_hash)
    if series is not None:
        object.__setattr__(forged, "series", series)
        object.__setattr__(forged, "series_count", len(series))
    return forged


def _forge_series_false_values(template: IndicatorSeries) -> IndicatorSeries:
    from zorqen_research.application.indicators.serialization import (
        hash_indicator_series_payload,
    )

    false_values = tuple(Decimal("999") if value is not None else None for value in template.values)
    digest = hash_indicator_series_payload(
        schema_version=template.schema_version,
        indicator_code=template.indicator_code,
        symbol=template.symbol,
        timeframe=template.timeframe,
        input_candle_sha256=template.input_candle_sha256,
        input_candle_count=template.input_candle_count,
        parameters=template.parameters,
        first_defined_index=template.first_defined_index,
        defined_value_count=template.defined_value_count,
        math_policy=template.math_policy,
        values=false_values,
    )
    forged = object.__new__(IndicatorSeries)
    for name in IndicatorSeries.__slots__:
        object.__setattr__(forged, name, getattr(template, name))
    object.__setattr__(forged, "values", false_values)
    object.__setattr__(forged, "result_hash", digest)
    return forged


def _assert_rejected_everywhere(forged: MultiTimeframeIndicatorInput) -> None:
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorDecisionFeed.from_composition(forged)
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorBacktestRunner.run(
            composition=forged,
            policy=default_policy(),
            provider=ScriptedMtfIndicatorProvider(),
        )
    # Envelope path: need a real run result for from_run; use a valid run then swap.
    valid = standard_composition()
    execution = valid.input_bundle.execution_candles
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="prov-env")
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=valid,
        policy=default_policy(),
        provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
    )
    with pytest.raises(StrategyBacktestValidationError):
        IndicatorStrategyBacktestEnvelope.from_run(
            composition=forged,
            policy=default_policy(),
            result=envelope.base.result,
            provider_invocation_count=envelope.base.provider_invocation_count,
            warmup_skipped_decision_count=envelope.base.warmup_skipped_decision_count,
        )


def test_composition_provenance_false_schema_and_hash_rejected() -> None:
    valid = standard_composition()
    _assert_rejected_everywhere(_clone_composition(valid, schema_version="99"))
    _assert_rejected_everywhere(_clone_composition(valid, indicator_composition_hash="ff" * 32))


def test_composition_provenance_false_mtf_hash_and_forged_mtf_rejected() -> None:
    valid = standard_composition()
    forged_mtf_hash = _clone_mtf(valid.input_bundle, input_bundle_hash="ab" * 32)
    _assert_rejected_everywhere(_clone_composition(valid, input_bundle=forged_mtf_hash))

    forged_mtf = object.__new__(MultiTimeframeBacktestInput)
    for name in MultiTimeframeBacktestInput.__slots__:
        object.__setattr__(forged_mtf, name, getattr(valid.input_bundle, name))
    object.__setattr__(forged_mtf, "execution_candle_sha256", "cd" * 32)
    object.__setattr__(forged_mtf, "input_bundle_hash", valid.input_bundle.input_bundle_hash)
    _assert_rejected_everywhere(_clone_composition(valid, input_bundle=forged_mtf))


def test_composition_provenance_execution_bundle_mutations_rejected() -> None:
    valid = standard_composition()
    assert valid.execution_indicators is not None
    mtf, execution, context = standard_mtf(definition_code="mtf_ind_prov_exec")
    other_exec = indicator_bundle_for(execution, Timeframe.H1, period=2)
    other_ctx = indicator_bundle_for(context, Timeframe.H4, period=1)

    _assert_rejected_everywhere(_clone_composition(valid, execution_indicators=other_exec))
    _assert_rejected_everywhere(_clone_composition(valid, execution_indicators=None))
    # Added execution when originally None — use context-only composition.
    ctx_only = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(other_ctx,),
    )
    _assert_rejected_everywhere(_clone_composition(ctx_only, execution_indicators=other_exec))


def test_composition_provenance_swapped_and_reordered_slots_rejected() -> None:
    mtf, execution, context = standard_mtf(definition_code="mtf_ind_prov_swap")
    exec_ind = indicator_bundle_for(execution, Timeframe.H1, period=1)
    ctx_ind = indicator_bundle_for(context, Timeframe.H4, period=1)
    valid = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=exec_ind,
        context_indicators=(ctx_ind,),
    )
    # Swap execution and context bundles (wrong TF for each slot).
    _assert_rejected_everywhere(
        _clone_composition(
            valid,
            execution_indicators=ctx_ind,
            context_indicators=(exec_ind,),
        )
    )


def test_composition_provenance_context_slot_count_and_order_rejected() -> None:
    from tests.unit.mtf_indicator_helpers import START, SYMBOL
    from zorqen_research.application.market_data.goldens import build_source_series
    from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
    from zorqen_research.application.strategy_definitions.serialization import build_instance
    from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement

    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_ind_prov_slots",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    mtf = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    atr = indicator_bundle_for(c4, Timeframe.H4, period=1)
    day = indicator_bundle_for(c1d, Timeframe.D1, period=1)
    valid = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(atr, day),
    )
    _assert_rejected_everywhere(_clone_composition(valid, context_indicators=(day, atr)))
    _assert_rejected_everywhere(_clone_composition(valid, context_indicators=(atr,)))
    _assert_rejected_everywhere(_clone_composition(valid, context_indicators=(atr, day, None)))
    _assert_rejected_everywhere(
        _clone_composition(
            valid,
            context_indicators=(_clone_bundle(atr, bundle_hash="cd" * 32), day),
        )
    )


def test_composition_provenance_nested_forged_series_rejected() -> None:
    valid = standard_composition()
    assert valid.execution_indicators is not None
    forged_series = _forge_series_false_values(valid.execution_indicators.series[0])
    forged_bundle = _clone_bundle(valid.execution_indicators, series=(forged_series,))
    _assert_rejected_everywhere(_clone_composition(valid, execution_indicators=forged_bundle))


def test_composition_provenance_unrelated_composition_rejected() -> None:
    valid = standard_composition(period=1)
    other = standard_composition(period=2)
    # Cross-wire an unrelated MTF input with this composition's indicator slots.
    _assert_rejected_everywhere(
        _clone_composition(
            valid,
            input_bundle=other.input_bundle,
            indicator_composition_hash=valid.indicator_composition_hash,
        )
    )
    # Fully populated unrelated content claiming this composition's hash.
    _assert_rejected_everywhere(
        _clone_composition(
            valid,
            input_bundle=other.input_bundle,
            execution_indicators=other.execution_indicators,
            context_indicators=other.context_indicators,
            indicator_composition_hash=valid.indicator_composition_hash,
        )
    )


def test_composition_provenance_incomplete_exact_class_controlled_error() -> None:
    incomplete = object.__new__(MultiTimeframeIndicatorInput)
    object.__setattr__(incomplete, "schema_version", "1")
    # Missing remaining required attributes — controlled domain error everywhere.
    _assert_rejected_everywhere(incomplete)
    with pytest.raises(StrategyBacktestValidationError):
        reverify_indicator_composition(incomplete)
    try:
        MultiTimeframeIndicatorDecisionFeed.from_composition(incomplete)
    except Exception as exc:  # noqa: BLE001 — assert boundary type
        assert type(exc) is StrategyBacktestValidationError
        assert not isinstance(exc, AttributeError | TypeError | ValueError | IndexError)


def test_composition_provenance_byte_identical_forged_replaced_by_trusted() -> None:
    valid = standard_composition()
    forged = _clone_composition(valid)
    assert forged is not valid
    assert forged.indicator_composition_hash == valid.indicator_composition_hash
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(forged)
    assert feed.composition is not forged
    assert feed.composition.indicator_composition_hash == valid.indicator_composition_hash
    assert feed.composition.input_bundle.input_bundle_hash == valid.input_bundle.input_bundle_hash

    execution = valid.input_bundle.execution_candles
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="byte-ident")
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=forged,
        policy=default_policy(),
        provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
    )
    trusted_run = MultiTimeframeIndicatorBacktestRunner.run(
        composition=valid,
        policy=default_policy(),
        provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
    )
    assert envelope.indicator_composition_hash == trusted_run.indicator_composition_hash
    assert envelope.indicator_aware_envelope_hash == trusted_run.indicator_aware_envelope_hash


def test_composition_provenance_false_hash_never_reaches_envelope() -> None:
    valid = standard_composition()
    forged = _clone_composition(valid, indicator_composition_hash="00" * 32)
    execution = valid.input_bundle.execution_candles
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="false-hash")
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorBacktestRunner.run(
            composition=forged,
            policy=default_policy(),
            provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
        )


def test_composition_provenance_feed_never_retains_caller() -> None:
    valid = standard_composition()
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(valid)
    assert feed.composition is not valid or feed.composition is reverify_indicator_composition(
        valid
    )
    # Always a rebuilt trusted object (distinct instance from a second reverify).
    trusted = reverify_indicator_composition(valid)
    feed2 = MultiTimeframeIndicatorDecisionFeed.from_composition(valid)
    assert feed2.composition.indicator_composition_hash == trusted.indicator_composition_hash
    assert feed2.composition is not valid
