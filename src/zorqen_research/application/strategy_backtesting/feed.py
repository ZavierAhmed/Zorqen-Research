"""Deterministic multi-timeframe decision feed."""

from __future__ import annotations

from dataclasses import dataclass

from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
)
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeDecisionFeed:
    """Factory-controlled feed producing no-lookahead views per execution bar."""

    _bundle: MultiTimeframeBacktestInput

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeDecisionFeed must be created via from_input"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_input(cls, bundle: MultiTimeframeBacktestInput) -> MultiTimeframeDecisionFeed:
        if not isinstance(bundle, MultiTimeframeBacktestInput):
            msg = "bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        self = object.__new__(cls)
        object.__setattr__(self, "_bundle", bundle)
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

        execution_history = VisibleCandleHistory.from_prefix(
            bundle.execution_candles,
            end_exclusive=bar_index + 1,
        )
        context_views: list[ContextDecisionView] = []
        for context in bundle.contexts:
            mapped = context.alignment.mapping[bar_index]
            if mapped is None:
                history = VisibleCandleHistory.from_prefix(context.candles, end_exclusive=0)
            else:
                history = VisibleCandleHistory.from_prefix(
                    context.candles,
                    end_exclusive=mapped + 1,
                )
            context_views.append(
                ContextDecisionView.from_alignment(
                    timeframe=context.timeframe,
                    warmup_bars=context.warmup_bars,
                    history=history,
                    latest_closed_index=mapped,
                    context_candle_sha256=context.candle_sha256,
                    alignment_hash=context.alignment.alignment_hash,
                )
            )
        return MultiTimeframeDecisionView.from_parts(
            input_bundle_hash=bundle.input_bundle_hash,
            execution_bar_index=bar_index,
            current_execution_candle=bundle.execution_candles[bar_index],
            execution_history=execution_history,
            execution_warmup_bars=bundle.execution_warmup_bars,
            contexts=tuple(context_views),
        )
