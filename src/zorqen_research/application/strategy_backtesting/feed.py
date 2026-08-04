"""Deterministic multi-timeframe decision feed."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeDecisionFeed:
    """Factory-controlled feed producing no-lookahead views per execution bar."""

    _bundle: MultiTimeframeBacktestInput
    _execution_source: VerifiedHistorySource
    _context_sources: tuple[VerifiedHistorySource, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeDecisionFeed must be created via from_input"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_input(cls, bundle: MultiTimeframeBacktestInput) -> MultiTimeframeDecisionFeed:
        if not isinstance(bundle, MultiTimeframeBacktestInput):
            msg = "bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        execution_source = VerifiedHistorySource.bind_trusted(bundle.execution_candles)
        context_sources = tuple(
            VerifiedHistorySource.bind_trusted(context.candles) for context in bundle.contexts
        )
        self = object.__new__(cls)
        object.__setattr__(self, "_bundle", bundle)
        object.__setattr__(self, "_execution_source", execution_source)
        object.__setattr__(self, "_context_sources", context_sources)
        return self

    @property
    def bundle(self) -> MultiTimeframeBacktestInput:
        return self._bundle

    def view_at(self, bar_index: object) -> MultiTimeframeDecisionView:
        if type(bar_index) is not int or isinstance(bar_index, bool):
            msg = "bar_index must be a real int"
            raise StrategyBacktestValidationError(msg)
        bundle = self._bundle
        if bar_index < 0 or bar_index >= bundle.execution_candle_count:
            msg = "bar_index is outside the execution candle tuple"
            raise StrategyBacktestValidationError(msg)

        execution_history = VisibleCandleHistory.from_verified_source(
            self._execution_source,
            end_exclusive=bar_index + 1,
        )
        context_views: list[ContextDecisionView] = []
        for context, source in zip(bundle.contexts, self._context_sources, strict=True):
            mapped = context.alignment.mapping[bar_index]
            if mapped is None:
                history = VisibleCandleHistory.from_verified_source(source, end_exclusive=0)
            else:
                history = VisibleCandleHistory.from_verified_source(
                    source,
                    end_exclusive=mapped + 1,
                )
            context_views.append(
                ContextDecisionView.from_context_series(
                    context=context,
                    history=history,
                    latest_closed_index=mapped,
                )
            )
        return MultiTimeframeDecisionView.from_bundle(
            bundle=bundle,
            execution_bar_index=bar_index,
            execution_history=execution_history,
            contexts=tuple(context_views),
        )
