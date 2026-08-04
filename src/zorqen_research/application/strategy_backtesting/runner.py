"""Multi-timeframe backtest runner over the existing BacktestEngine."""

from __future__ import annotations

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeDecisionProvider,
    MultiTimeframeProviderAdapter,
)
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope


class MultiTimeframeBacktestRunner:
    """Runs the unchanged BacktestEngine behind an MTF decision-feed adapter."""

    @staticmethod
    def run(
        *,
        input_bundle: MultiTimeframeBacktestInput,
        policy: BacktestPolicy,
        provider: MultiTimeframeDecisionProvider,
    ) -> StrategyBacktestEnvelope:
        if not isinstance(input_bundle, MultiTimeframeBacktestInput):
            msg = "input_bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(policy, BacktestPolicy):
            msg = "policy must be a BacktestPolicy"
            raise StrategyBacktestValidationError(msg)

        feed = MultiTimeframeDecisionFeed.from_input(input_bundle)
        adapter = MultiTimeframeProviderAdapter(
            feed=feed,
            provider=provider,
        )
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
        return StrategyBacktestEnvelope.from_run(
            input_bundle=input_bundle,
            policy=policy,
            result=result,
            provider_invocation_count=adapter.provider_invocation_count,
            warmup_skipped_decision_count=adapter.warmup_skipped_decision_count,
        )
