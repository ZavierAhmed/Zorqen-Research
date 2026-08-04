"""Multi-timeframe decision provider protocol and engine adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from zorqen_research.application.backtesting.provider import (
    BacktestDecisionContext,
)
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.intents import BacktestIntent, EnterIntent
from zorqen_research.domain.strategy_backtesting.decision_views import MultiTimeframeDecisionView
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition


@dataclass(frozen=True, slots=True)
class MultiTimeframeBacktestDecisionContext:
    """Enhanced decision context wrapping the existing single-timeframe context."""

    base: BacktestDecisionContext
    strategy_instance_hash: str
    input_bundle_hash: str
    view: MultiTimeframeDecisionView


class MultiTimeframeDecisionProvider(Protocol):
    def on_bar_close(
        self,
        context: MultiTimeframeBacktestDecisionContext,
    ) -> tuple[BacktestIntent, ...]:
        """Return intents eligible only on the next candle open."""


class MultiTimeframeProviderAdapter:
    """
    Adapts a multi-timeframe provider to the existing BacktestDecisionProvider protocol.

    Tracks warmup skips and real invocations for the result envelope.
    """

    def __init__(
        self,
        *,
        feed: MultiTimeframeDecisionFeed,
        provider: MultiTimeframeDecisionProvider,
        definition: StrategyDefinition,
        strategy_instance_hash: str,
    ) -> None:
        if not isinstance(feed, MultiTimeframeDecisionFeed):
            msg = "feed must be a MultiTimeframeDecisionFeed"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(definition, StrategyDefinition):
            msg = "definition must be a StrategyDefinition"
            raise StrategyBacktestValidationError(msg)
        self._feed = feed
        self._provider = provider
        self._definition = definition
        self._strategy_instance_hash = strategy_instance_hash
        self.provider_invocation_count = 0
        self.warmup_skipped_decision_count = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> tuple[BacktestIntent, ...]:
        view = self._feed.view_at(context.bar_index)
        if context.bar_index != view.execution_bar_index:
            msg = "engine bar_index does not match decision feed view"
            raise StrategyBacktestValidationError(msg)
        if context.candle != view.current_execution_candle:
            msg = "engine candle does not match decision feed view"
            raise StrategyBacktestValidationError(msg)
        if context.timeframe is not self._feed.bundle.execution_timeframe:
            msg = "engine timeframe does not match execution timeframe"
            raise StrategyBacktestValidationError(msg)

        if not view.overall_ready:
            self.warmup_skipped_decision_count += 1
            return ()

        enhanced = MultiTimeframeBacktestDecisionContext(
            base=context,
            strategy_instance_hash=self._strategy_instance_hash,
            input_bundle_hash=self._feed.bundle.input_bundle_hash,
            view=view,
        )
        self.provider_invocation_count += 1
        intents = self._provider.on_bar_close(enhanced)
        if not isinstance(intents, tuple):
            msg = "Multi-timeframe provider must return an exact tuple"
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
