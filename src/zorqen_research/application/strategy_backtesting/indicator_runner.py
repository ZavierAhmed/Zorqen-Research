"""Indicator-aware multi-timeframe backtest runner."""

from __future__ import annotations

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.application.strategy_backtesting.indicator_provider import (
    MultiTimeframeIndicatorDecisionProvider,
    MultiTimeframeIndicatorProviderAdapter,
)
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.indicator_results import (
    IndicatorStrategyBacktestEnvelope,
)


class MultiTimeframeIndicatorBacktestRunner:
    """Runs the unchanged BacktestEngine behind an indicator-aware MTF adapter."""

    @staticmethod
    def run(
        *,
        composition: MultiTimeframeIndicatorInput,
        policy: BacktestPolicy,
        provider: MultiTimeframeIndicatorDecisionProvider,
    ) -> IndicatorStrategyBacktestEnvelope:
        if type(composition) is not MultiTimeframeIndicatorInput:
            msg = "composition must be an exact MultiTimeframeIndicatorInput"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(policy, BacktestPolicy):
            msg = "policy must be a BacktestPolicy"
            raise StrategyBacktestValidationError(msg)

        feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
        adapter = MultiTimeframeIndicatorProviderAdapter(feed=feed, provider=provider)
        input_bundle = composition.input_bundle
        engine = BacktestEngine(
            symbol=input_bundle.symbol,
            timeframe=input_bundle.execution_timeframe,
            policy=policy,
            provider=adapter,
        )
        result = engine.run(
            input_bundle.execution_candles,
            expected_input_hash=input_bundle.execution_candle_sha256,
        )
        return IndicatorStrategyBacktestEnvelope.from_run(
            composition=composition,
            policy=policy,
            result=result,
            provider_invocation_count=adapter.provider_invocation_count,
            warmup_skipped_decision_count=adapter.warmup_skipped_decision_count,
        )
