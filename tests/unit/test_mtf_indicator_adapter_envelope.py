"""Adapter / envelope adversarial tests for Milestone 1.2."""

from __future__ import annotations

import pytest

from tests.unit.mtf_indicator_helpers import standard_composition
from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.strategy_backtesting.goldens import (
    _enter_long,
    _enter_short,
    mtf_definition,
    run_mtf_scenario,
)
from zorqen_research.application.strategy_backtesting.indicator_goldens import (
    ScriptedMtfIndicatorProvider,
)
from zorqen_research.application.strategy_backtesting.indicator_runner import (
    MultiTimeframeIndicatorBacktestRunner,
)
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_results import (
    IndicatorStrategyBacktestEnvelope,
)
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope


def test_mtf_indicator_adapter_rejects_non_exact_tuple_outputs() -> None:
    composition = standard_composition(period=1)

    class ListProvider:
        def on_bar_close(self, context):  # noqa: ANN001, ARG002
            return []  # type: ignore[return-value]

    class GenProvider:
        def on_bar_close(self, context):  # noqa: ANN001, ARG002
            def gen():
                if False:
                    yield None

            return gen()  # type: ignore[return-value]

    class TupleSub(tuple):
        pass

    class SubProvider:
        def on_bar_close(self, context):  # noqa: ANN001, ARG002
            return TupleSub()

    for provider in (ListProvider(), GenProvider(), SubProvider()):
        with pytest.raises((BacktestValidationError, BacktestExecutionError)):
            MultiTimeframeIndicatorBacktestRunner.run(
                composition=composition,
                policy=default_policy(),
                provider=provider,  # type: ignore[arg-type]
            )


def test_mtf_indicator_unsupported_direction_before_fill() -> None:
    from tests.unit.mtf_indicator_helpers import START, SYMBOL, indicator_bundle_for
    from zorqen_research.application.market_data.goldens import build_source_series
    from zorqen_research.application.strategy_definitions.serialization import build_instance
    from zorqen_research.domain.strategy_backtesting.indicator_composition import (
        MultiTimeframeIndicatorInput,
    )
    from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
    from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
    from zorqen_research.domain.timeframes import Timeframe

    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        directions=(PositionDirection.LONG,),
        definition_code="mtf_ind_adapter_dir",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    mtf = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=indicator_bundle_for(execution, Timeframe.H1, period=1),
        context_indicators=(None,),
    )
    intent = _enter_short(decision_open=execution[3].open_time, intent_id="bad-short")
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    with pytest.raises(BacktestExecutionError) as exc_info:
        MultiTimeframeIndicatorBacktestRunner.run(
            composition=composition,
            policy=default_policy(),
            provider=provider,
        )
    assert "Decision provider failed" in str(exc_info.value)
    assert provider.calls == [3]


def test_mtf_indicator_raw_envelope_hashes_rejected() -> None:
    with pytest.raises(StrategyBacktestValidationError):
        IndicatorStrategyBacktestEnvelope(  # type: ignore[call-arg]
            indicator_aware_envelope_hash="ab" * 32
        )
    with pytest.raises(StrategyBacktestValidationError):
        StrategyBacktestEnvelope(envelope_hash="cd" * 32)  # type: ignore[call-arg]


def test_mtf_indicator_counts_reconcile_on_success() -> None:
    composition = standard_composition(period=1)
    execution = composition.input_bundle.execution_candles
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="count-check")
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=composition,
        policy=default_policy(),
        provider=provider,
    )
    assert envelope.base.provider_invocation_count == len(provider.calls)
    assert (
        envelope.base.provider_invocation_count + envelope.base.warmup_skipped_decision_count
        == composition.input_bundle.execution_candle_count
    )
    assert envelope.indicator_composition_hash == composition.indicator_composition_hash
    assert envelope.base.input_bundle_hash == composition.input_bundle.input_bundle_hash


def test_existing_mtf_runner_regression_exact_close() -> None:
    payload = run_mtf_scenario("exact-close-readiness")
    assert payload["ok"] is True
    assert payload["input_bundle_hash"] == (
        "1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167"
    )
    assert payload["envelope_hash"] == (
        "8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d"
    )
