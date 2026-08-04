"""Milestone 0.9A: envelope/view identity binding and constant-time history proofs."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.goldens import (
    ScriptedMtfProvider,
    mtf_definition,
    run_direction_restriction,
)
from zorqen_research.application.strategy_backtesting.provider import MultiTimeframeProviderAdapter
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
)
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import (
    VerifiedHistorySource,
    VisibleCandleHistory,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


class InstrumentedCandles(Sequence[Candle]):
    """Tuple-like sequence that counts element and slice accesses."""

    def __init__(self, items: tuple[Candle, ...]) -> None:
        self._items = items
        self.access_count = 0
        self.slice_count = 0

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: int | slice) -> Candle | tuple[Candle, ...]:  # type: ignore[override]
        if isinstance(key, slice):
            self.slice_count += 1
            return self._items[key]
        self.access_count += 1
        return self._items[key]

    def __iter__(self) -> Iterator[Candle]:
        for index in range(len(self._items)):
            yield self[index]


def _bundle(*, definition_code: str = "mtf_09a") -> MultiTimeframeBacktestInput:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code=definition_code,
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    return MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )


def _long_intent(bundle: MultiTimeframeBacktestInput) -> EnterIntent:
    return EnterIntent(
        intent_id="09a-long",
        decision_open_time=bundle.execution_candles[3].open_time,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )


def _run(bundle: MultiTimeframeBacktestInput) -> StrategyBacktestEnvelope:
    return MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=ScriptedMtfProvider(first_ready_intent=(_long_intent(bundle),)),
    )


def test_envelope_rejects_raw_hash_factory_and_direct_construction() -> None:
    assert not hasattr(StrategyBacktestEnvelope, "from_verified")
    with pytest.raises(StrategyBacktestValidationError, match="from_run"):
        StrategyBacktestEnvelope()
    bundle = _bundle(definition_code="mtf_09a_hash_factory")
    envelope = _run(bundle)
    with pytest.raises(TypeError):
        StrategyBacktestEnvelope.from_run(  # type: ignore[call-arg]
            input_bundle=bundle,
            policy=default_policy(),
            result=envelope.result,
            provider_invocation_count=envelope.provider_invocation_count,
            warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
            strategy_instance_hash="ab" * 32,
        )


def test_envelope_cannot_forge_identity_hashes_or_mismatched_result() -> None:
    bundle = _bundle(definition_code="mtf_09a_forge")
    envelope = _run(bundle)

    assert envelope.strategy_instance_hash == bundle.strategy_instance_hash
    assert envelope.input_bundle_hash == bundle.input_bundle_hash
    assert envelope.multi_context_alignment_hash == (bundle.multi_context_alignment.alignment_hash)

    # Result from another execution series (different candle content / hash).
    other_definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_09a_forge",
    )
    other_instance = build_instance(other_definition, {"signal_strength": 1})
    other_execution = build_source_series(
        start=datetime(2024, 2, 1, tzinfo=UTC),
        timeframe=Timeframe.H1,
        count=8,
    )
    other_context = build_source_series(
        start=datetime(2024, 2, 1, tzinfo=UTC),
        timeframe=Timeframe.H4,
        count=2,
    )
    other_bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=other_instance,
        symbol=SYM,
        execution_candles=other_execution,
        context_series=((Timeframe.H4, other_context),),
    )
    other_env = _run(other_bundle)
    assert other_bundle.execution_candle_sha256 != bundle.execution_candle_sha256
    with pytest.raises(StrategyBacktestValidationError, match="input_candle_hash"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=other_env.result,
            provider_invocation_count=envelope.provider_invocation_count,
            warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
        )

    # Result from another policy (forged summary policy hash).
    forged_policy = replace(envelope.result.summary, policy_hash="cd" * 32)
    forged_result = replace(envelope.result, summary=forged_policy)
    with pytest.raises(StrategyBacktestValidationError, match="policy_hash"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=forged_result,
            provider_invocation_count=envelope.provider_invocation_count,
            warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
        )

    # Fake alignment / strategy / bundle hashes are not injectable; derived only from bundle.
    rebuilt = StrategyBacktestEnvelope.from_run(
        input_bundle=bundle,
        policy=default_policy(),
        result=envelope.result,
        provider_invocation_count=envelope.provider_invocation_count,
        warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
    )
    assert rebuilt.envelope_hash == envelope.envelope_hash
    assert rebuilt.strategy_instance_hash != "00" * 32
    assert rebuilt.input_bundle_hash != "11" * 32
    assert rebuilt.multi_context_alignment_hash != "22" * 32


def test_envelope_count_reconciliation_and_types() -> None:
    bundle = _bundle(definition_code="mtf_09a_counts")
    envelope = _run(bundle)
    with pytest.raises(StrategyBacktestValidationError, match="execution_candle_count"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=envelope.result,
            provider_invocation_count=0,
            warmup_skipped_decision_count=0,
        )
    with pytest.raises(StrategyBacktestValidationError, match="non-negative"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=envelope.result,
            provider_invocation_count=-1,
            warmup_skipped_decision_count=bundle.execution_candle_count + 1,
        )
    with pytest.raises(StrategyBacktestValidationError, match="real int"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=envelope.result,
            provider_invocation_count=True,  # type: ignore[arg-type]
            warmup_skipped_decision_count=bundle.execution_candle_count - 1,
        )
    with pytest.raises(StrategyBacktestValidationError, match="MultiTimeframeBacktestInput"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=object(),  # type: ignore[arg-type]
            policy=default_policy(),
            result=envelope.result,
            provider_invocation_count=envelope.provider_invocation_count,
            warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
        )
    with pytest.raises(StrategyBacktestValidationError, match="BacktestResult"):
        StrategyBacktestEnvelope.from_run(
            input_bundle=bundle,
            policy=default_policy(),
            result=object(),  # type: ignore[arg-type]
            provider_invocation_count=envelope.provider_invocation_count,
            warmup_skipped_decision_count=envelope.warmup_skipped_decision_count,
        )


def test_envelope_runner_output_remains_deterministic() -> None:
    bundle = _bundle(definition_code="mtf_09a_det")
    a = _run(bundle)
    b = _run(bundle)
    assert a.envelope_hash == b.envelope_hash
    assert a.strategy_instance_hash == bundle.strategy_instance_hash
    assert a.input_bundle_hash == bundle.input_bundle_hash
    assert a.multi_context_alignment_hash == bundle.multi_context_alignment.alignment_hash


def test_views_reject_caller_supplied_hashes_and_forged_factories() -> None:
    assert not hasattr(ContextDecisionView, "from_alignment")
    assert not hasattr(MultiTimeframeDecisionView, "from_parts")
    with pytest.raises(StrategyBacktestValidationError, match="from_context_series"):
        ContextDecisionView()
    with pytest.raises(StrategyBacktestValidationError, match="from_bundle"):
        MultiTimeframeDecisionView()

    bundle = _bundle(definition_code="mtf_09a_views")
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    view = feed.view_at(3)
    assert view.input_bundle_hash == bundle.input_bundle_hash
    assert view.contexts[0].context_candle_sha256 == bundle.contexts[0].candle_sha256
    assert view.contexts[0].alignment_hash == bundle.contexts[0].alignment.alignment_hash

    with pytest.raises(TypeError):
        ContextDecisionView.from_context_series(  # type: ignore[call-arg]
            context=bundle.contexts[0],
            history=view.contexts[0].history,
            latest_closed_index=0,
            context_candle_sha256="ff" * 32,
        )
    with pytest.raises(TypeError):
        ContextDecisionView.from_context_series(  # type: ignore[call-arg]
            context=bundle.contexts[0],
            history=view.contexts[0].history,
            latest_closed_index=0,
            alignment_hash="ee" * 32,
        )
    with pytest.raises(TypeError):
        MultiTimeframeDecisionView.from_bundle(  # type: ignore[call-arg]
            bundle=bundle,
            execution_bar_index=3,
            execution_history=view.execution_history,
            contexts=view.contexts,
            input_bundle_hash="dd" * 32,
        )


def test_adapter_identities_only_from_feed_and_base_checks() -> None:
    bundle = _bundle(definition_code="mtf_09a_adapter")
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    provider = ScriptedMtfProvider()
    with pytest.raises(TypeError):
        MultiTimeframeProviderAdapter(  # type: ignore[call-arg]
            feed=feed,
            provider=provider,
            definition=bundle.strategy_instance.definition,
        )
    with pytest.raises(TypeError):
        MultiTimeframeProviderAdapter(  # type: ignore[call-arg]
            feed=feed,
            provider=provider,
            strategy_instance_hash="aa" * 32,
        )
    adapter = MultiTimeframeProviderAdapter(feed=feed, provider=provider)
    candle = bundle.execution_candles[0]
    wrong_symbol = BacktestDecisionContext(
        candle=candle,
        bar_index=0,
        symbol=Symbol(value="ETHUSDT"),
        timeframe=Timeframe.H1,
        position=None,
        realized_equity=Decimal("10000"),
        last_closed_trade=None,
        candles_processed=1,
    )
    with pytest.raises(StrategyBacktestValidationError, match="symbol"):
        adapter.on_bar_close(wrong_symbol)

    wrong_processed = BacktestDecisionContext(
        candle=candle,
        bar_index=0,
        symbol=SYM,
        timeframe=Timeframe.H1,
        position=None,
        realized_equity=Decimal("10000"),
        last_closed_trade=None,
        candles_processed=2,
    )
    with pytest.raises(StrategyBacktestValidationError, match="candles_processed"):
        adapter.on_bar_close(wrong_processed)

    # Normal runner path unchanged.
    envelope = _run(bundle)
    assert envelope.provider_invocation_count == 5
    assert envelope.warmup_skipped_decision_count == 3


def test_visible_history_constant_time_construction() -> None:
    candles = build_source_series(start=START, timeframe=Timeframe.H1, count=100_001)
    instrumented = InstrumentedCandles(candles)
    source = VerifiedHistorySource.bind_trusted(candles)
    object.__setattr__(source, "_candles", instrumented)

    baseline_access = instrumented.access_count
    baseline_slice = instrumented.slice_count
    near_ten = VisibleCandleHistory.from_verified_source(source, end_exclusive=11)
    after_ten_access = instrumented.access_count
    after_ten_slice = instrumented.slice_count
    near_hundred_k = VisibleCandleHistory.from_verified_source(source, end_exclusive=100_001)
    after_large_access = instrumented.access_count
    after_large_slice = instrumented.slice_count

    assert after_ten_slice == baseline_slice == 0
    assert after_large_slice == 0
    ten_delta = after_ten_access - baseline_access
    large_delta = after_large_access - after_ten_access
    assert ten_delta == large_delta
    assert near_ten.source_object is instrumented
    assert near_hundred_k.source_object is instrumented
    assert near_ten.source_object is near_hundred_k.source_object

    # Iteration still yields exactly the visible candles.
    assert tuple(near_ten) == candles[:11]
    assert len(near_ten) == 11
    assert isinstance(near_ten.source_object, InstrumentedCandles)

    # Feed view_at also stays constant-time in source slice accesses.
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_09a_perf",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    # Use a smaller but still large execution series for feed readiness with H4 context.
    exec_n = 10_000
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=exec_n)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=exec_n // 4)
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    exec_instrumented = InstrumentedCandles(execution)
    object.__setattr__(feed._execution_source, "_candles", exec_instrumented)

    feed.view_at(10)
    access_a = exec_instrumented.access_count
    slice_a = exec_instrumented.slice_count
    feed.view_at(9_999)
    access_b = exec_instrumented.access_count
    slice_b = exec_instrumented.slice_count
    assert slice_a == 0
    assert slice_b == 0
    # Two view_at calls should add the same number of accesses each (constant).
    first_cost = access_a
    second_cost = access_b - access_a
    assert first_cost == second_cost
    assert feed.view_at(10).execution_history.source_object is exec_instrumented
    assert feed.view_at(9_999).execution_history.source_object is exec_instrumented


def test_provider_exact_tuple_contract() -> None:
    bundle = _bundle(definition_code="mtf_09a_tuple")

    class EmptyTupleProvider:
        def on_bar_close(self, context: Any) -> tuple[Any, ...]:
            return ()

    class OneIntentProvider:
        def __init__(self) -> None:
            self._emitted = False

        def on_bar_close(self, context: Any) -> tuple[Any, ...]:
            if self._emitted:
                return ()
            self._emitted = True
            return (
                EnterIntent(
                    intent_id="one",
                    decision_open_time=context.view.current_execution_candle.open_time,
                    direction=PositionDirection.LONG,
                    quantity=Decimal("1.000"),
                    stop_loss=Decimal("50"),
                    take_profit=Decimal("200"),
                ),
            )

    class ListProvider:
        def on_bar_close(self, context: Any) -> list[Any]:
            return []

    class GeneratorProvider:
        def on_bar_close(self, context: Any) -> Any:
            def gen() -> Any:
                if False:  # pragma: no cover
                    yield None

            return gen()

    class TupleSubclass(tuple):  # type: ignore[type-arg]
        pass

    class SubclassProvider:
        def on_bar_close(self, context: Any) -> Any:
            return TupleSubclass()

    class MultiIntentProvider:
        def on_bar_close(self, context: Any) -> tuple[Any, ...]:
            intent = EnterIntent(
                intent_id="multi",
                decision_open_time=context.view.current_execution_candle.open_time,
                direction=PositionDirection.LONG,
                quantity=Decimal("1.000"),
                stop_loss=Decimal("50"),
                take_profit=Decimal("200"),
            )
            return (intent, intent)

    # Valid exact tuples succeed.
    MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=EmptyTupleProvider(),  # type: ignore[arg-type]
    )
    MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=OneIntentProvider(),  # type: ignore[arg-type]
    )
    for provider in (ListProvider(), GeneratorProvider(), SubclassProvider()):
        with pytest.raises(BacktestExecutionError):
            MultiTimeframeBacktestRunner.run(
                input_bundle=bundle,
                policy=default_policy(),
                provider=provider,  # type: ignore[arg-type]
            )
    # Multiple intents cross the existing engine boundary as validation failure.
    with pytest.raises(BacktestValidationError, match="At most one intent"):
        MultiTimeframeBacktestRunner.run(
            input_bundle=bundle,
            policy=default_policy(),
            provider=MultiIntentProvider(),  # type: ignore[arg-type]
        )


def test_direction_golden_exact_cause_and_truthful_invocation_count() -> None:
    payload = run_direction_restriction()
    assert payload["controlled_failure"] is True
    assert payload["provider_invocation_count"] == 1
    assert payload["first_ready_index"] == 3
    assert payload["error_code"] == "unsupported_direction"
    assert payload["envelope_hash"] is None

    # Re-run through the runner to inspect the cause chain directly.
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        directions=(PositionDirection.LONG,),
        definition_code="mtf_long_only",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    intent = EnterIntent(
        intent_id="mtf-short-denied",
        decision_open_time=execution[3].open_time,
        direction=PositionDirection.SHORT,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("200"),
        take_profit=Decimal("50"),
    )
    provider = ScriptedMtfProvider(first_ready_intent=(intent,))
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    with pytest.raises(BacktestExecutionError, match="Decision provider failed") as raised:
        MultiTimeframeBacktestRunner.run(
            input_bundle=bundle,
            policy=default_policy(),
            provider=provider,
        )
    cause = raised.value.__cause__
    assert isinstance(cause, BacktestValidationError)
    assert "not supported by the strategy definition" in str(cause)
    assert "short" in str(cause)
    assert provider.calls == [3]
