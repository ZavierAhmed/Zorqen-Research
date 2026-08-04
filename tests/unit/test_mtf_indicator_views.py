"""Decision-view adversarial tests for Milestone 1.2 composition."""

from __future__ import annotations

from decimal import Decimal, getcontext

import pytest

from tests.unit.mtf_indicator_helpers import (
    indicator_bundle_for,
    standard_composition,
    standard_mtf,
)
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.indicator_decision_views import (
    ContextIndicatorDecisionView,
    MultiTimeframeIndicatorDecisionView,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def test_mtf_indicator_view_rejects_bad_indices() -> None:
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(standard_composition())
    for bad in (-1, True, 1.5, 8):
        with pytest.raises((StrategyBacktestValidationError, TypeError, IndexError)):
            feed.view_at(bad)  # type: ignore[arg-type]


def test_mtf_indicator_context_unavailable_and_exact_close_mapping() -> None:
    mtf, execution, context = standard_mtf()
    ctx_ind = indicator_bundle_for(context, Timeframe.H4, period=1)
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(ctx_ind,),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    before = feed.view_at(2)
    assert before.base_view.contexts[0].latest_closed_index is None
    assert before.context_indicator_views[0].indicator_view is None
    assert before.context_indicator_views[0].ready is False
    assert before.overall_ready is False

    ready = feed.view_at(3)
    assert ready.base_view.contexts[0].latest_closed_index == 0
    assert ready.context_indicator_views[0].indicator_view is not None
    assert ready.context_indicator_views[0].indicator_view.bar_index == 0
    assert ready.context_indicator_views[0].indicator_view.bar_index != (
        ready.base_view.execution_bar_index
    )
    assert ready.overall_ready is True


def test_mtf_indicator_view_no_future_leak_and_safe_repr() -> None:
    composition = standard_composition(period=1)
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    view = feed.view_at(3)
    history = view.base_view.execution_history
    future = composition.input_bundle.execution_candles[4]
    assert future not in history[:]
    assert future.open_time.isoformat() not in repr(view)
    assert future.open_time.isoformat() not in str(view)
    if view.execution_indicator_view is not None:
        assert "result_hash" not in repr(view.execution_indicator_view)
        assert not hasattr(view.execution_indicator_view, "series")
        assert not hasattr(view, "indicator_composition_hash")
        assert "bundle_hash" not in repr(view)
        assert str(len(composition.input_bundle.execution_candles)) not in repr(
            view.execution_indicator_view
        )


def test_mtf_indicator_direct_view_construction_blocked() -> None:
    with pytest.raises(StrategyBacktestValidationError):
        ContextIndicatorDecisionView(  # type: ignore[call-arg]
            timeframe=Timeframe.H4,
            latest_closed_index=0,
            indicator_view=None,
            configured=False,
            ready=True,
        )
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorDecisionView(  # type: ignore[call-arg]
            schema_version="1",
        )


def test_mtf_indicator_decimal_context_independence() -> None:
    composition = standard_composition(period=1)
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    getcontext().prec = 9
    hash_a = feed.view_at(3).provider_visible_indicator_hash
    getcontext().prec = 50
    hash_b = feed.view_at(3).provider_visible_indicator_hash
    assert hash_a == hash_b


def test_mtf_indicator_future_independence_of_provider_visible_hash() -> None:
    """Earlier composed view hash must ignore later candle/indicator changes."""
    mtf_a, execution_a, context_a = standard_mtf(execution_count=8, context_count=2)
    # Same prefix, different future execution candles after bar 3.
    from zorqen_research.application.market_data.goldens import make_candle
    from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
    from zorqen_research.application.strategy_definitions.serialization import build_instance
    from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
    from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement

    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_ind_future",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    prefix = list(execution_a[:4])
    future_a = list(execution_a[4:])
    future_b = [
        make_candle(
            c.open_time,
            timeframe=Timeframe.H1,
            open=Decimal("999"),
            high=Decimal("1000"),
            low=Decimal("998"),
            close=Decimal("999.5"),
            volume=Decimal("9"),
            quote_asset_volume=Decimal("90"),
            trade_count=9,
            taker_buy_base_volume=Decimal("0.5"),
            taker_buy_quote_volume=Decimal("5"),
        )
        for c in future_a
    ]
    exec_a = tuple(prefix + future_a)
    exec_b = tuple(prefix + future_b)
    bundle_a = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=Symbol(value="BTCUSDT"),
        execution_candles=exec_a,
        context_series=((Timeframe.H4, context_a),),
    )
    bundle_b = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=Symbol(value="BTCUSDT"),
        execution_candles=exec_b,
        context_series=((Timeframe.H4, context_a),),
    )
    ind_a = indicator_bundle_for(exec_a, Timeframe.H1, period=1)
    ind_b = indicator_bundle_for(exec_b, Timeframe.H1, period=1)
    comp_a = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=bundle_a,
        execution_indicators=ind_a,
        context_indicators=(None,),
    )
    comp_b = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=bundle_b,
        execution_indicators=ind_b,
        context_indicators=(None,),
    )
    assert comp_a.indicator_composition_hash != comp_b.indicator_composition_hash
    view_a = MultiTimeframeIndicatorDecisionFeed.from_composition(comp_a).view_at(3)
    view_b = MultiTimeframeIndicatorDecisionFeed.from_composition(comp_b).view_at(3)
    assert view_a.provider_visible_indicator_hash == view_b.provider_visible_indicator_hash
    assert view_a.execution_indicator_view is not None
    assert view_b.execution_indicator_view is not None
    assert (
        view_a.execution_indicator_view.decision_view_hash
        == view_b.execution_indicator_view.decision_view_hash
    )


def test_mtf_indicator_provider_visible_hash_excludes_composition() -> None:
    composition = standard_composition()
    view = MultiTimeframeIndicatorDecisionFeed.from_composition(composition).view_at(3)
    assert composition.indicator_composition_hash not in view.provider_visible_indicator_hash
    assert not hasattr(view, "indicator_composition_hash")
    assert not hasattr(view, "bundle_hash")
    if view.execution_indicators_configured and composition.execution_indicators is not None:
        assert composition.execution_indicators.bundle_hash not in repr(view)
