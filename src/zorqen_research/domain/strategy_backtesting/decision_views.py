"""Per-bar multi-timeframe decision views."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import (
    VisibleCandleHistory,
    _VerifiedHistorySource,
)
from zorqen_research.domain.strategy_backtesting.inputs import (
    ContextSeriesInput,
    MultiTimeframeBacktestInput,
)
from zorqen_research.domain.timeframes import Timeframe

_VIEW_SCHEMA = "1"


def required_visible_count(warmup_bars: int) -> int:
    """Declared warmups still require at least one closed candle."""
    if type(warmup_bars) is not int or isinstance(warmup_bars, bool):
        msg = "warmup_bars must be a real int"
        raise StrategyBacktestValidationError(msg)
    if warmup_bars < 0:
        msg = "warmup_bars must be non-negative"
        raise StrategyBacktestValidationError(msg)
    return max(1, warmup_bars)


@dataclass(frozen=True, slots=True, init=False)
class ContextDecisionView:
    """No-lookahead view of one context series at an execution decision."""

    timeframe: Timeframe
    warmup_bars: int
    history: VisibleCandleHistory
    latest_closed_index: int | None
    visible_count: int
    ready: bool
    context_candle_sha256: str
    alignment_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "ContextDecisionView must be created via MultiTimeframeDecisionFeed.view_at"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        context: ContextSeriesInput,
        source: _VerifiedHistorySource,
        latest_closed_index: int | None,
    ) -> ContextDecisionView:
        if not isinstance(context, ContextSeriesInput):
            msg = "context must be a ContextSeriesInput"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(source, _VerifiedHistorySource):
            msg = "source must be a feed-owned _VerifiedHistorySource"
            raise StrategyBacktestValidationError(msg)
        if source._candles is not context.candles:
            msg = "context history source must be the exact ContextSeriesInput candle series"
            raise StrategyBacktestValidationError(msg)
        if latest_closed_index is None:
            history = VisibleCandleHistory._from_verified_source(source, end_exclusive=0)
        else:
            if type(latest_closed_index) is not int or isinstance(latest_closed_index, bool):
                msg = "latest_closed_index must be None or a real int"
                raise StrategyBacktestValidationError(msg)
            if latest_closed_index < 0:
                msg = "latest_closed_index must be non-negative"
                raise StrategyBacktestValidationError(msg)
            history = VisibleCandleHistory._from_verified_source(
                source,
                end_exclusive=latest_closed_index + 1,
            )
            if history.latest is None:
                msg = "aligned context history must expose a latest candle"
                raise StrategyBacktestValidationError(msg)
        visible_count = len(history)
        if latest_closed_index is None:
            if visible_count != 0:
                msg = "latest_closed_index=None requires zero visible candles"
                raise StrategyBacktestValidationError(msg)
        elif visible_count != latest_closed_index + 1:
            msg = "visible count must equal latest_closed_index + 1"
            raise StrategyBacktestValidationError(msg)
        ready = visible_count >= required_visible_count(context.warmup_bars)
        self = object.__new__(cls)
        object.__setattr__(self, "timeframe", context.timeframe)
        object.__setattr__(self, "warmup_bars", context.warmup_bars)
        object.__setattr__(self, "history", history)
        object.__setattr__(self, "latest_closed_index", latest_closed_index)
        object.__setattr__(self, "visible_count", visible_count)
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "context_candle_sha256", context.candle_sha256)
        object.__setattr__(self, "alignment_hash", context.alignment.alignment_hash)
        return self


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeDecisionView:
    """Immutable per-execution-bar multi-timeframe decision snapshot."""

    input_bundle_hash: str
    execution_bar_index: int
    current_execution_candle: Candle
    execution_history: VisibleCandleHistory
    execution_warmup_bars: int
    execution_ready: bool
    contexts: tuple[ContextDecisionView, ...]
    overall_ready: bool
    decision_view_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeDecisionView must be created via MultiTimeframeDecisionFeed.view_at"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        bundle: MultiTimeframeBacktestInput,
        execution_source: _VerifiedHistorySource,
        context_sources: tuple[_VerifiedHistorySource, ...],
        execution_bar_index: int,
    ) -> MultiTimeframeDecisionView:
        if not isinstance(bundle, MultiTimeframeBacktestInput):
            msg = "bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(execution_source, _VerifiedHistorySource):
            msg = "execution_source must be a feed-owned _VerifiedHistorySource"
            raise StrategyBacktestValidationError(msg)
        if execution_source._candles is not bundle.execution_candles:
            msg = "execution history source must be the exact input-bundle execution series"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(context_sources, tuple):
            msg = "context_sources must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)
        if len(context_sources) != len(bundle.contexts):
            msg = "context source count must match bundle contexts"
            raise StrategyBacktestValidationError(msg)
        if type(execution_bar_index) is not int or isinstance(execution_bar_index, bool):
            msg = "execution_bar_index must be a real int"
            raise StrategyBacktestValidationError(msg)
        if execution_bar_index < 0 or execution_bar_index >= bundle.execution_candle_count:
            msg = "execution_bar_index is outside the execution candle tuple"
            raise StrategyBacktestValidationError(msg)

        execution_history = VisibleCandleHistory._from_verified_source(
            execution_source,
            end_exclusive=execution_bar_index + 1,
        )
        current = bundle.execution_candles[execution_bar_index]
        if execution_history.latest != current:
            msg = "current execution candle must be the latest visible execution candle"
            raise StrategyBacktestValidationError(msg)

        contexts = tuple(
            ContextDecisionView._from_feed(
                context=context,
                source=source,
                latest_closed_index=context.alignment.mapping[execution_bar_index],
            )
            for context, source in zip(bundle.contexts, context_sources, strict=True)
        )
        execution_ready = len(execution_history) >= required_visible_count(
            bundle.execution_warmup_bars
        )
        overall_ready = execution_ready and all(item.ready for item in contexts)
        digest = sha256_hex(
            json.dumps(
                {
                    "contexts": [
                        {
                            "latest_closed_index": item.latest_closed_index,
                            "ready": item.ready,
                            "timeframe": item.timeframe.value,
                            "visible_count": item.visible_count,
                        }
                        for item in contexts
                    ],
                    "execution_bar_index": execution_bar_index,
                    "execution_ready": execution_ready,
                    "execution_visible_count": len(execution_history),
                    "input_bundle_hash": bundle.input_bundle_hash,
                    "overall_ready": overall_ready,
                    "schema_version": _VIEW_SCHEMA,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "input_bundle_hash", bundle.input_bundle_hash)
        object.__setattr__(self, "execution_bar_index", execution_bar_index)
        object.__setattr__(self, "current_execution_candle", current)
        object.__setattr__(self, "execution_history", execution_history)
        object.__setattr__(self, "execution_warmup_bars", bundle.execution_warmup_bars)
        object.__setattr__(self, "execution_ready", execution_ready)
        object.__setattr__(self, "contexts", contexts)
        object.__setattr__(self, "overall_ready", overall_ready)
        object.__setattr__(self, "decision_view_hash", digest)
        return self
