"""Multi-timeframe backtest input bundle and decision-feed tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.goldens import (
    ScriptedMtfProvider,
    mtf_definition,
)
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestExecutionError
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def _bundle(
    *,
    execution_warmup: int = 4,
    contexts: tuple[TimeframeRequirement, ...] = (
        TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
    ),
    execution_count: int = 8,
    context_specs: tuple[tuple[Timeframe, int], ...] = ((Timeframe.H4, 2),),
    directions: tuple[PositionDirection, ...] = (PositionDirection.LONG, PositionDirection.SHORT),
    definition_code: str = "mtf_unit",
) -> MultiTimeframeBacktestInput:
    definition = mtf_definition(
        execution_warmup=execution_warmup,
        contexts=contexts,
        directions=directions,
        definition_code=definition_code,
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=execution_count)
    series = tuple(
        (tf, build_source_series(start=START, timeframe=tf, count=count))
        for tf, count in context_specs
    )
    return MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=series,
    )


def test_bundle_rejects_execution_timeframe_mismatch_and_mutable_inputs() -> None:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_mismatch",
    )
    # Force wrong execution series timeframe by using M15 candles labeled as H1 definition.
    instance = build_instance(definition, {"signal_strength": 1})
    wrong = build_source_series(start=START, timeframe=Timeframe.M15, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=wrong,
            context_series=((Timeframe.H4, context),),
        )
    good_exec = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    with pytest.raises(StrategyBacktestValidationError, match="immutable"):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=list(good_exec),  # type: ignore[arg-type]
            context_series=((Timeframe.H4, context),),
        )
    with pytest.raises(StrategyBacktestValidationError, match="immutable"):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=good_exec,
            context_series=((Timeframe.H4, list(context)),),  # type: ignore[arg-type]
        )


def test_bundle_rejects_missing_extra_unsorted_duplicate_context() -> None:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_two_req",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    with pytest.raises(StrategyBacktestValidationError, match="count"):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=((Timeframe.H4, c4),),
        )
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d), (Timeframe.H4, c4)),
        )
    with pytest.raises(StrategyBacktestValidationError, match="order"):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=((Timeframe.D1, c1d), (Timeframe.H4, c4)),
        )


def test_bundle_rejects_no_context_definition_and_forged_construction() -> None:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(),
        definition_code="mtf_single_tf",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    with pytest.raises(StrategyBacktestValidationError, match="single-timeframe"):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=(),
        )
    with pytest.raises(StrategyBacktestValidationError, match="from_verified"):
        MultiTimeframeBacktestInput()


def test_visible_history_bounds_and_no_future_access() -> None:
    candles = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    history = VisibleCandleHistory.from_prefix(candles, end_exclusive=2)
    assert len(history) == 2
    assert history[0] == candles[0]
    assert history[-1] == candles[1]
    assert history.latest == candles[1]
    with pytest.raises(IndexError):
        _ = history[2]
    with pytest.raises(IndexError):
        _ = history[-3]
    assert history[0:10] == (candles[0], candles[1])
    assert history[:] == (candles[0], candles[1])
    assert tuple(history) == (candles[0], candles[1])
    assert not hasattr(history, "candles")
    with pytest.raises(StrategyBacktestValidationError):
        VisibleCandleHistory(candles, end_exclusive=2)  # type: ignore[call-arg]
    empty = VisibleCandleHistory.from_prefix(candles, end_exclusive=0)
    assert empty.latest is None
    assert len(empty) == 0


def test_decision_feed_indexes_readiness_and_determinism() -> None:
    bundle = _bundle()
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    with pytest.raises(StrategyBacktestValidationError):
        feed.view_at(True)  # type: ignore[arg-type]
    with pytest.raises(StrategyBacktestValidationError):
        feed.view_at(-1)
    with pytest.raises(StrategyBacktestValidationError):
        feed.view_at(bundle.execution_candle_count)
    first = feed.view_at(0)
    assert first.overall_ready is False
    assert first.contexts[0].latest_closed_index is None
    ready = feed.view_at(3)
    assert ready.overall_ready is True
    assert ready.contexts[0].latest_closed_index == 0
    again = feed.view_at(3)
    assert again.decision_view_hash == ready.decision_view_hash
    assert again == ready
    # One millisecond too late: before first 4h close, context remains unavailable.
    early = feed.view_at(2)
    assert early.contexts[0].latest_closed_index is None


def test_adapter_warmup_direction_and_runner_envelope() -> None:
    bundle = _bundle(definition_code="mtf_adapter")
    intent = EnterIntent(
        intent_id="unit-long",
        decision_open_time=bundle.execution_candles[3].open_time,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    provider = ScriptedMtfProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=provider,
    )
    assert envelope.warmup_skipped_decision_count == 3
    assert envelope.provider_invocation_count == 5
    assert envelope.result.summary.closed_trade_count == 1
    assert provider.calls[0] == 3
    with pytest.raises(StrategyBacktestValidationError):
        StrategyBacktestEnvelope()

    # Unsupported direction.
    long_only = _bundle(
        directions=(PositionDirection.LONG,),
        definition_code="mtf_long_only_unit",
    )
    short = EnterIntent(
        intent_id="unit-short",
        decision_open_time=long_only.execution_candles[3].open_time,
        direction=PositionDirection.SHORT,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("200"),
        take_profit=Decimal("50"),
    )
    with pytest.raises(BacktestExecutionError, match="Decision provider failed"):
        MultiTimeframeBacktestRunner.run(
            input_bundle=long_only,
            policy=default_policy(),
            provider=ScriptedMtfProvider(first_ready_intent=(short,)),
        )


def test_provider_list_output_and_exception_sanitization() -> None:
    bundle = _bundle(definition_code="mtf_bad_provider")

    class ListProvider:
        def on_bar_close(self, context):  # noqa: ANN001
            return []  # list not tuple

    class BoomProvider:
        def on_bar_close(self, context):  # noqa: ANN001
            msg = "boom"
            raise RuntimeError(msg)

    with pytest.raises(BacktestExecutionError):
        MultiTimeframeBacktestRunner.run(
            input_bundle=bundle,
            policy=default_policy(),
            provider=ListProvider(),  # type: ignore[arg-type]
        )
    with pytest.raises(BacktestExecutionError, match="Decision provider failed"):
        MultiTimeframeBacktestRunner.run(
            input_bundle=bundle,
            policy=default_policy(),
            provider=BoomProvider(),  # type: ignore[arg-type]
        )


def test_envelope_hash_sensitivity_to_parameters_and_context() -> None:
    base = _bundle(definition_code="mtf_env_base")
    intent = EnterIntent(
        intent_id="env-long",
        decision_open_time=base.execution_candles[3].open_time,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    env1 = MultiTimeframeBacktestRunner.run(
        input_bundle=base,
        policy=default_policy(),
        provider=ScriptedMtfProvider(first_ready_intent=(intent,)),
    )
    env1b = MultiTimeframeBacktestRunner.run(
        input_bundle=base,
        policy=default_policy(),
        provider=ScriptedMtfProvider(first_ready_intent=(intent,)),
    )
    assert env1.envelope_hash == env1b.envelope_hash

    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_env_base",
    )
    other_instance = build_instance(definition, {"signal_strength": 2})
    other_bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=other_instance,
        symbol=SYM,
        execution_candles=base.execution_candles,
        context_series=tuple((c.timeframe, c.candles) for c in base.contexts),
    )
    env2 = MultiTimeframeBacktestRunner.run(
        input_bundle=other_bundle,
        policy=default_policy(),
        provider=ScriptedMtfProvider(first_ready_intent=(intent,)),
    )
    assert env2.envelope_hash != env1.envelope_hash
    assert other_bundle.execution_candle_sha256 == base.execution_candle_sha256


def test_warmup_zero_still_requires_closed_context() -> None:
    bundle = _bundle(
        execution_warmup=1,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=0),),
        execution_count=3,
        context_specs=((Timeframe.H4, 1),),
        definition_code="mtf_warmup_zero",
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    assert feed.view_at(0).overall_ready is False
    assert feed.view_at(2).overall_ready is False
    # With only 3 execution bars, first 4h never closes.
    assert all(feed.view_at(i).contexts[0].visible_count == 0 for i in range(3))
