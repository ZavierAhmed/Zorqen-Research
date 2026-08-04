"""Composed multi-timeframe candle + indicator decision feed."""

from __future__ import annotations

from dataclasses import dataclass

from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.indicator_decision_views import (
    ContextIndicatorDecisionView,
    MultiTimeframeIndicatorDecisionView,
)


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeIndicatorDecisionFeed:
    """Owns trusted MTF candle feed plus optional per-slot indicator feeds."""

    composition: MultiTimeframeIndicatorInput
    _mtf_feed: MultiTimeframeDecisionFeed
    _execution_indicator_feed: IndicatorDecisionFeed | None
    _context_indicator_feeds: tuple[IndicatorDecisionFeed | None, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeIndicatorDecisionFeed must be created via from_composition"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_composition(
        cls,
        composition: object,
    ) -> MultiTimeframeIndicatorDecisionFeed:
        if type(composition) is not MultiTimeframeIndicatorInput:
            msg = "composition must be an exact MultiTimeframeIndicatorInput"
            raise StrategyBacktestValidationError(msg)

        mtf_feed = MultiTimeframeDecisionFeed.from_input(composition.input_bundle)
        execution_feed = (
            None
            if composition.execution_indicators is None
            else IndicatorDecisionFeed.from_bundle(composition.execution_indicators)
        )
        context_feeds = tuple(
            None if bundle is None else IndicatorDecisionFeed.from_bundle(bundle)
            for bundle in composition.context_indicators
        )

        self = object.__new__(cls)
        object.__setattr__(self, "composition", composition)
        object.__setattr__(self, "_mtf_feed", mtf_feed)
        object.__setattr__(self, "_execution_indicator_feed", execution_feed)
        object.__setattr__(self, "_context_indicator_feeds", context_feeds)
        return self

    def view_at(self, bar_index: object) -> MultiTimeframeIndicatorDecisionView:
        base = self._mtf_feed.view_at(bar_index)
        execution_configured = self._execution_indicator_feed is not None
        execution_view = (
            None
            if self._execution_indicator_feed is None
            else self._execution_indicator_feed.view_at(base.execution_bar_index)
        )
        if execution_view is not None:
            if execution_view.symbol != self.composition.input_bundle.symbol:
                msg = "execution indicator symbol does not match MTF symbol"
                raise StrategyBacktestValidationError(msg)
            if execution_view.timeframe is not self.composition.input_bundle.execution_timeframe:
                msg = "execution indicator timeframe does not match execution timeframe"
                raise StrategyBacktestValidationError(msg)

        context_slots: list[ContextIndicatorDecisionView] = []
        for context_view, indicator_feed in zip(
            base.contexts,
            self._context_indicator_feeds,
            strict=True,
        ):
            configured = indicator_feed is not None
            if not configured:
                context_slots.append(
                    ContextIndicatorDecisionView._from_feed(
                        timeframe=context_view.timeframe,
                        latest_closed_index=context_view.latest_closed_index,
                        indicator_view=None,
                        configured=False,
                    )
                )
                continue
            assert indicator_feed is not None
            latest = context_view.latest_closed_index
            if latest is None:
                context_slots.append(
                    ContextIndicatorDecisionView._from_feed(
                        timeframe=context_view.timeframe,
                        latest_closed_index=None,
                        indicator_view=None,
                        configured=True,
                    )
                )
                continue
            indicator_view = indicator_feed.view_at(latest)
            if indicator_view.symbol != self.composition.input_bundle.symbol:
                msg = "context indicator symbol does not match MTF symbol"
                raise StrategyBacktestValidationError(msg)
            if indicator_view.visible_count != context_view.visible_count:
                msg = "context indicator visibility must match context candle visibility"
                raise StrategyBacktestValidationError(msg)
            context_slots.append(
                ContextIndicatorDecisionView._from_feed(
                    timeframe=context_view.timeframe,
                    latest_closed_index=latest,
                    indicator_view=indicator_view,
                    configured=True,
                )
            )

        return MultiTimeframeIndicatorDecisionView._from_feed(
            base_view=base,
            execution_indicator_view=execution_view,
            execution_indicators_configured=execution_configured,
            context_indicator_views=tuple(context_slots),
        )
