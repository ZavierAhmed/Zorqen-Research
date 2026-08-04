"""Per-bar multi-timeframe decision views."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
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
        msg = "ContextDecisionView must be created via from_alignment"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_alignment(
        cls,
        *,
        timeframe: Timeframe,
        warmup_bars: int,
        history: VisibleCandleHistory,
        latest_closed_index: int | None,
        context_candle_sha256: str,
        alignment_hash: str,
    ) -> ContextDecisionView:
        if not isinstance(timeframe, Timeframe):
            msg = "timeframe must be a Timeframe"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(history, VisibleCandleHistory):
            msg = "history must be a VisibleCandleHistory"
            raise StrategyBacktestValidationError(msg)
        if latest_closed_index is None:
            if len(history) != 0:
                msg = "latest_closed_index=None requires zero visible candles"
                raise StrategyBacktestValidationError(msg)
        else:
            if type(latest_closed_index) is not int or isinstance(latest_closed_index, bool):
                msg = "latest_closed_index must be None or a real int"
                raise StrategyBacktestValidationError(msg)
            if latest_closed_index < 0:
                msg = "latest_closed_index must be non-negative"
                raise StrategyBacktestValidationError(msg)
            if len(history) != latest_closed_index + 1:
                msg = "visible count must equal latest_closed_index + 1"
                raise StrategyBacktestValidationError(msg)
            latest = history.latest
            if latest is None:
                msg = "aligned context history must expose a latest candle"
                raise StrategyBacktestValidationError(msg)
        visible_count = len(history)
        ready = visible_count >= required_visible_count(warmup_bars)
        self = object.__new__(cls)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "warmup_bars", warmup_bars)
        object.__setattr__(self, "history", history)
        object.__setattr__(self, "latest_closed_index", latest_closed_index)
        object.__setattr__(self, "visible_count", visible_count)
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "context_candle_sha256", context_candle_sha256)
        object.__setattr__(self, "alignment_hash", alignment_hash)
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
        msg = "MultiTimeframeDecisionView must be created via from_parts"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_parts(
        cls,
        *,
        input_bundle_hash: str,
        execution_bar_index: int,
        current_execution_candle: Candle,
        execution_history: VisibleCandleHistory,
        execution_warmup_bars: int,
        contexts: tuple[ContextDecisionView, ...],
    ) -> MultiTimeframeDecisionView:
        if not isinstance(current_execution_candle, Candle):
            msg = "current_execution_candle must be a Candle"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(execution_history, VisibleCandleHistory):
            msg = "execution_history must be a VisibleCandleHistory"
            raise StrategyBacktestValidationError(msg)
        if type(execution_bar_index) is not int or isinstance(execution_bar_index, bool):
            msg = "execution_bar_index must be a real int"
            raise StrategyBacktestValidationError(msg)
        if len(execution_history) != execution_bar_index + 1:
            msg = "execution history must end at bar_index + 1"
            raise StrategyBacktestValidationError(msg)
        if execution_history.latest != current_execution_candle:
            msg = "current execution candle must be the latest visible execution candle"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(contexts, tuple):
            msg = "contexts must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)
        for item in contexts:
            if not isinstance(item, ContextDecisionView):
                msg = "contexts must contain ContextDecisionView values"
                raise StrategyBacktestValidationError(msg)
        execution_ready = len(execution_history) >= required_visible_count(execution_warmup_bars)
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
                    "input_bundle_hash": input_bundle_hash,
                    "overall_ready": overall_ready,
                    "schema_version": _VIEW_SCHEMA,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "input_bundle_hash", input_bundle_hash)
        object.__setattr__(self, "execution_bar_index", execution_bar_index)
        object.__setattr__(self, "current_execution_candle", current_execution_candle)
        object.__setattr__(self, "execution_history", execution_history)
        object.__setattr__(self, "execution_warmup_bars", execution_warmup_bars)
        object.__setattr__(self, "execution_ready", execution_ready)
        object.__setattr__(self, "contexts", contexts)
        object.__setattr__(self, "overall_ready", overall_ready)
        object.__setattr__(self, "decision_view_hash", digest)
        return self
