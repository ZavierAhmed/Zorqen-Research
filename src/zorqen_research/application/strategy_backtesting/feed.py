"""Deterministic multi-timeframe decision feed."""

from __future__ import annotations

from dataclasses import dataclass

from zorqen_research.domain.strategy_backtesting.decision_views import MultiTimeframeDecisionView
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import _VerifiedHistorySource
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeDecisionFeed:
    """Factory-controlled feed producing no-lookahead views per execution bar."""

    _bundle: MultiTimeframeBacktestInput
    _execution_source: _VerifiedHistorySource
    _context_sources: tuple[_VerifiedHistorySource, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeDecisionFeed must be created via from_input"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_input(cls, bundle: MultiTimeframeBacktestInput) -> MultiTimeframeDecisionFeed:
        if not isinstance(bundle, MultiTimeframeBacktestInput):
            msg = "bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        execution_source = _VerifiedHistorySource._bind_trusted(bundle.execution_candles)
        context_sources = tuple(
            _VerifiedHistorySource._bind_trusted(context.candles) for context in bundle.contexts
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
        return MultiTimeframeDecisionView._from_feed(
            bundle=bundle,
            execution_source=self._execution_source,
            context_sources=self._context_sources,
            execution_bar_index=bar_index,
        )
