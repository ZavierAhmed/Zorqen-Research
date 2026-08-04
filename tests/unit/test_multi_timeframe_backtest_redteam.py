"""Red-team attacks for multi-timeframe backtest decision feed."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.backtesting.cli import main as backtest_main
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def _standard_bundle() -> MultiTimeframeBacktestInput:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_redteam",
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


def test_redteam_future_access_paths() -> None:
    candles = build_source_series(start=START, timeframe=Timeframe.H1, count=5)
    history = VisibleCandleHistory.from_prefix(candles, end_exclusive=2)
    with pytest.raises(IndexError):
        _ = history[2]
    with pytest.raises(IndexError):
        _ = history[-3]
    assert candles[4] not in history[:]
    assert candles[4] not in tuple(history)
    assert history[0:99] == (candles[0], candles[1])


def test_redteam_bundle_forgeries_and_order() -> None:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_redteam_two",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=((Timeframe.D1, c1d), (Timeframe.H4, c4)),
        )
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeBacktestInput.from_verified(
            strategy_instance=instance,
            symbol=SYM,
            execution_candles=execution,
            context_series=((Timeframe.H4, c4),),
        )
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeBacktestInput(input_bundle_hash="ab" * 32)  # type: ignore[call-arg]
    with pytest.raises(StrategyBacktestValidationError):
        StrategyBacktestEnvelope(envelope_hash="cd" * 32)  # type: ignore[call-arg]


def test_redteam_provider_timing_and_cli() -> None:
    bundle = _standard_bundle()
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    assert feed.view_at(2).overall_ready is False
    assert feed.view_at(3).overall_ready is True
    assert feed.view_at(3).contexts[0].latest_closed_index == 0
    assert backtest_main(["run-mtf-golden", "--scenario", "not-real"]) == 1
    assert backtest_main(["run-mtf-golden", "--scenario", "exact-close-readiness"]) == 0
