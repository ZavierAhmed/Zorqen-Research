"""Indicator-aware multi-timeframe provider protocol and engine adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.intents import BacktestIntent, EnterIntent
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_decision_views import (
    MultiTimeframeIndicatorDecisionView,
)
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition


@dataclass(frozen=True, slots=True)
class MultiTimeframeIndicatorBacktestDecisionContext:
    """Engine base context plus composed candle/indicator decision view."""

    base: BacktestDecisionContext
    strategy_instance_hash: str
    input_bundle_hash: str
    view: MultiTimeframeIndicatorDecisionView


class MultiTimeframeIndicatorDecisionProvider(Protocol):
    def on_bar_close(
        self,
        context: MultiTimeframeIndicatorBacktestDecisionContext,
    ) -> tuple[BacktestIntent, ...]:
        """Return intents eligible only on the next candle open."""


class MultiTimeframeIndicatorProviderAdapter:
    """Adapts an indicator-aware MTF provider to BacktestDecisionProvider."""

    def __init__(
        self,
        *,
        feed: MultiTimeframeIndicatorDecisionFeed,
        provider: MultiTimeframeIndicatorDecisionProvider,
    ) -> None:
        if type(feed) is not MultiTimeframeIndicatorDecisionFeed:
            msg = "feed must be an exact MultiTimeframeIndicatorDecisionFeed"
            raise StrategyBacktestValidationError(msg)
        self._feed = feed
        self._provider = provider
        bundle = feed.composition.input_bundle
        self._definition: StrategyDefinition = bundle.strategy_instance.definition
        self._strategy_instance_hash = bundle.strategy_instance_hash
        self._input_bundle_hash = bundle.input_bundle_hash
        self.provider_invocation_count = 0
        self.warmup_skipped_decision_count = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> tuple[BacktestIntent, ...]:
        bundle = self._feed.composition.input_bundle
        if context.symbol != bundle.symbol:
            msg = "engine symbol does not match input bundle symbol"
            raise StrategyBacktestValidationError(msg)
        if context.timeframe is not bundle.execution_timeframe:
            msg = "engine timeframe does not match execution timeframe"
            raise StrategyBacktestValidationError(msg)
        if context.candles_processed != context.bar_index + 1:
            msg = "candles_processed must equal bar_index + 1"
            raise StrategyBacktestValidationError(msg)

        view = self._feed.view_at(context.bar_index)
        if context.bar_index != view.base_view.execution_bar_index:
            msg = "engine bar_index does not match composed decision feed view"
            raise StrategyBacktestValidationError(msg)
        if context.candle != view.base_view.current_execution_candle:
            msg = "engine candle does not match composed decision feed view"
            raise StrategyBacktestValidationError(msg)

        if not view.overall_ready:
            self.warmup_skipped_decision_count += 1
            return ()

        enhanced = MultiTimeframeIndicatorBacktestDecisionContext(
            base=context,
            strategy_instance_hash=self._strategy_instance_hash,
            input_bundle_hash=self._input_bundle_hash,
            view=view,
        )
        self.provider_invocation_count += 1
        intents = self._provider.on_bar_close(enhanced)
        if type(intents) is not tuple:
            msg = "Indicator-aware multi-timeframe provider must return an exact tuple"
            raise BacktestValidationError(msg)
        for intent in intents:
            if isinstance(intent, EnterIntent):
                allowed: tuple[PositionDirection, ...] = self._definition.supported_directions
                if intent.direction not in allowed:
                    msg = (
                        "EnterIntent direction is not supported by the strategy definition: "
                        f"{intent.direction.value}"
                    )
                    raise BacktestValidationError(msg)
        return intents
