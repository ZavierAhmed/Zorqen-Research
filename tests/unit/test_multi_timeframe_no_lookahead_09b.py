"""Milestone 0.9B: seal no-lookahead history and decision-view boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

import zorqen_research.domain.strategy_backtesting as strategy_backtesting_pkg
from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.goldens import (
    NoLookaheadProbeProvider,
    mtf_definition,
    run_no_lookahead_probe,
)
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
)
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import (
    VisibleCandleHistory,
    _VerifiedHistorySource,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)
_FORBIDDEN_SOURCE_ATTRS = (
    "source_object",
    "candles",
    "source",
    "to_tuple",
    "full",
    "all",
    "as_tuple",
    "to_list",
)


def _bundle(*, definition_code: str = "mtf_09b") -> MultiTimeframeBacktestInput:
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


def _assert_history_sealed(
    history: VisibleCandleHistory,
    *,
    full_series: tuple[Candle, ...],
    visible_count: int,
) -> None:
    for name in _FORBIDDEN_SOURCE_ATTRS:
        assert not hasattr(history, name), name
    assert len(history) == visible_count
    with pytest.raises(IndexError):
        _ = history[visible_count]
    assert history[0:1_000_000] == full_series[:visible_count]
    assert tuple(history) == full_series[:visible_count]
    if visible_count > 0:
        assert history[-1] == full_series[visible_count - 1]
        with pytest.raises(IndexError):
            _ = history[-(visible_count + 1)]
    else:
        assert history.latest is None


def test_provider_cannot_obtain_future_candles_through_public_apis() -> None:
    bundle = _bundle(definition_code="mtf_09b_provider_seal")
    intent = EnterIntent(
        intent_id="09b-probe",
        decision_open_time=bundle.execution_candles[3].open_time,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    provider = NoLookaheadProbeProvider(
        first_ready_intent=(intent,),
        expected_execution_visible=4,
        expected_context_visible=(1,),
        full_execution=bundle.execution_candles,
        full_contexts=tuple(item.candles for item in bundle.contexts),
    )
    envelope = MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=provider,
    )
    assert provider.calls[0] == 3
    assert provider.probe_ok is True
    assert envelope.result.summary.closed_trade_count == 1

    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    view = feed.view_at(3)
    _assert_history_sealed(
        view.execution_history,
        full_series=bundle.execution_candles,
        visible_count=4,
    )
    for context_view, series in zip(view.contexts, bundle.contexts, strict=True):
        _assert_history_sealed(
            context_view.history,
            full_series=series.candles,
            visible_count=context_view.visible_count,
        )


def test_trusted_source_is_internal_only() -> None:
    assert "VerifiedHistorySource" not in strategy_backtesting_pkg.__all__
    assert "_VerifiedHistorySource" not in strategy_backtesting_pkg.__all__
    assert not hasattr(strategy_backtesting_pkg, "VerifiedHistorySource")
    assert not hasattr(_VerifiedHistorySource, "bind_trusted")
    assert not hasattr(_VerifiedHistorySource, "from_verified_tuple")
    assert not hasattr(VisibleCandleHistory, "from_verified_source")
    assert not hasattr(VisibleCandleHistory, "source_object")
    with pytest.raises(StrategyBacktestValidationError, match="internal"):
        _VerifiedHistorySource()
    # No public unchecked constructor that accepts arbitrary non-candle tuples.
    with pytest.raises(StrategyBacktestValidationError):
        VisibleCandleHistory.from_prefix(("not-a-candle",), end_exclusive=1)  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        VisibleCandleHistory.from_verified_source(  # type: ignore[attr-defined]
            object(),
            end_exclusive=1,
        )


def test_view_content_bound_to_exact_feed_sources() -> None:
    bundle = _bundle(definition_code="mtf_09b_bind")
    other = _bundle(definition_code="mtf_09b_bind_other")
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    view = feed.view_at(3)

    assert not hasattr(ContextDecisionView, "from_context_series")
    assert not hasattr(MultiTimeframeDecisionView, "from_bundle")

    # Context A identity cannot bind Context B history/source.
    foreign_source = _VerifiedHistorySource._bind_trusted(other.contexts[0].candles)
    with pytest.raises(StrategyBacktestValidationError, match="exact ContextSeriesInput"):
        ContextDecisionView._from_feed(
            context=bundle.contexts[0],
            source=foreign_source,
            latest_closed_index=0,
        )

    # Fake execution prefix ending with the same current candle still fails identity.
    current = bundle.execution_candles[3]
    fake_prefix = (bundle.execution_candles[0], bundle.execution_candles[1], current, current)
    fake_source = _VerifiedHistorySource._bind_trusted(fake_prefix)
    with pytest.raises(StrategyBacktestValidationError, match="exact input-bundle execution"):
        MultiTimeframeDecisionView._from_feed(
            bundle=bundle,
            execution_source=fake_source,
            context_sources=feed._context_sources,
            execution_bar_index=3,
        )

    # History from another symbol/timeframe series cannot bind.
    foreign_exec = _VerifiedHistorySource._bind_trusted(other.execution_candles)
    with pytest.raises(StrategyBacktestValidationError, match="exact input-bundle execution"):
        MultiTimeframeDecisionView._from_feed(
            bundle=bundle,
            execution_source=foreign_exec,
            context_sources=feed._context_sources,
            execution_bar_index=3,
        )

    # Separately created history cannot be injected via public factories.
    with pytest.raises(AttributeError):
        ContextDecisionView.from_context_series(  # type: ignore[attr-defined]
            context=bundle.contexts[0],
            history=view.contexts[0].history,
            latest_closed_index=0,
        )
    with pytest.raises(AttributeError):
        MultiTimeframeDecisionView.from_bundle(  # type: ignore[attr-defined]
            bundle=bundle,
            execution_bar_index=3,
            execution_history=view.execution_history,
            contexts=view.contexts,
        )

    # Public path remains feed.view_at only.
    again = feed.view_at(3)
    assert again.decision_view_hash == view.decision_view_hash
    assert again.execution_history._source is feed._execution_source._candles


def test_no_lookahead_probe_golden_preserves_exact_close_hashes() -> None:
    payload = run_no_lookahead_probe()
    assert payload["ok"] is True
    assert payload["scenario"] == "no-lookahead-probe"
    assert payload["provider_invocation_count"] == 5
    assert (
        payload["input_bundle_hash"]
        == "1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167"
    )
    assert (
        payload["backtest_result_hash"]
        == "966418dd3fb45a8695b171d4cfca92029f94dd7cb208178761002d62f65a0b19"
    )
    assert (
        payload["envelope_hash"]
        == "8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d"
    )
    assert payload["closed_trade_count"] == 1
    assert payload["first_ready_index"] == 3
    assert payload["execution_visible_at_ready"] == 4
    assert payload["context_visible_at_ready"] == (1,)
    assert payload["public_source_exposed"] is False
