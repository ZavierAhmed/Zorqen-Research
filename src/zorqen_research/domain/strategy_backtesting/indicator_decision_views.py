"""Provider-visible multi-timeframe indicator decision views."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicator_views.views import IndicatorDecisionView
from zorqen_research.domain.strategy_backtesting.decision_views import MultiTimeframeDecisionView
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.timeframes import Timeframe

_COMPOSED_VIEW_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False, repr=False)
class ContextIndicatorDecisionView:
    """Bounded indicator state for one context slot at an execution decision."""

    timeframe: Timeframe
    latest_closed_index: int | None
    indicator_view: IndicatorDecisionView | None
    configured: bool
    ready: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "ContextIndicatorDecisionView must be created by MultiTimeframeIndicatorDecisionFeed"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        timeframe: Timeframe,
        latest_closed_index: int | None,
        indicator_view: IndicatorDecisionView | None,
        configured: bool,
    ) -> ContextIndicatorDecisionView:
        if configured:
            if latest_closed_index is None:
                if indicator_view is not None:
                    msg = "context indicators require None view when no closed context candle"
                    raise StrategyBacktestValidationError(msg)
                ready = False
            else:
                if indicator_view is None:
                    msg = "configured context indicators require a view when a candle is closed"
                    raise StrategyBacktestValidationError(msg)
                if indicator_view.bar_index != latest_closed_index:
                    msg = "context indicator bar_index must equal latest_closed_index"
                    raise StrategyBacktestValidationError(msg)
                if indicator_view.visible_count != latest_closed_index + 1:
                    msg = "context indicator visible_count must match context candle visibility"
                    raise StrategyBacktestValidationError(msg)
                if indicator_view.timeframe is not timeframe:
                    msg = "context indicator timeframe must match the context slot"
                    raise StrategyBacktestValidationError(msg)
                ready = indicator_view.overall_ready
        else:
            if indicator_view is not None:
                msg = "unconfigured context indicator slot must not expose a view"
                raise StrategyBacktestValidationError(msg)
            ready = True

        self = object.__new__(cls)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "latest_closed_index", latest_closed_index)
        object.__setattr__(self, "indicator_view", indicator_view)
        object.__setattr__(self, "configured", configured)
        object.__setattr__(self, "ready", ready)
        return self

    def __repr__(self) -> str:
        return (
            f"ContextIndicatorDecisionView(timeframe={self.timeframe.value}, "
            f"configured={self.configured}, ready={self.ready})"
        )

    def __str__(self) -> str:
        return self.__repr__()


def build_provider_visible_indicator_hash_document(
    *,
    execution_bar_index: int,
    execution_indicator_view: IndicatorDecisionView | None,
    execution_indicators_configured: bool,
    execution_indicators_ready: bool,
    context_slots: tuple[ContextIndicatorDecisionView, ...],
    overall_ready: bool,
) -> dict[str, object]:
    return {
        "context_slots": [
            {
                "configured": slot.configured,
                "decision_view_hash": (
                    None if slot.indicator_view is None else slot.indicator_view.decision_view_hash
                ),
                "latest_closed_index": slot.latest_closed_index,
                "ready": slot.ready,
                "timeframe": slot.timeframe.value,
            }
            for slot in context_slots
        ],
        "execution_bar_index": execution_bar_index,
        "execution_decision_view_hash": (
            None
            if execution_indicator_view is None
            else execution_indicator_view.decision_view_hash
        ),
        "execution_indicators_configured": execution_indicators_configured,
        "execution_indicators_ready": execution_indicators_ready,
        "overall_ready": overall_ready,
        "schema_version": _COMPOSED_VIEW_SCHEMA,
    }


@dataclass(frozen=True, slots=True, init=False, repr=False)
class MultiTimeframeIndicatorDecisionView:
    """Composed candle + indicator decision snapshot at one execution bar."""

    schema_version: str
    base_view: MultiTimeframeDecisionView
    execution_indicator_view: IndicatorDecisionView | None
    context_indicator_views: tuple[ContextIndicatorDecisionView, ...]
    execution_indicators_configured: bool
    execution_indicators_ready: bool
    overall_ready: bool
    provider_visible_indicator_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = (
            "MultiTimeframeIndicatorDecisionView must be created via "
            "MultiTimeframeIndicatorDecisionFeed.view_at"
        )
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        base_view: MultiTimeframeDecisionView,
        execution_indicator_view: IndicatorDecisionView | None,
        execution_indicators_configured: bool,
        context_indicator_views: tuple[ContextIndicatorDecisionView, ...],
    ) -> MultiTimeframeIndicatorDecisionView:
        if not isinstance(base_view, MultiTimeframeDecisionView):
            msg = "base_view must be a MultiTimeframeDecisionView"
            raise StrategyBacktestValidationError(msg)
        if len(context_indicator_views) != len(base_view.contexts):
            msg = "context indicator views must align with base context slots"
            raise StrategyBacktestValidationError(msg)

        if execution_indicators_configured:
            if execution_indicator_view is None:
                msg = "configured execution indicators require a view"
                raise StrategyBacktestValidationError(msg)
            if execution_indicator_view.bar_index != base_view.execution_bar_index:
                msg = "execution indicator bar_index must equal execution bar index"
                raise StrategyBacktestValidationError(msg)
            if execution_indicator_view.visible_count != len(base_view.execution_history):
                msg = "execution indicator visible_count must match execution candle visibility"
                raise StrategyBacktestValidationError(msg)
            execution_ready = execution_indicator_view.overall_ready
        else:
            if execution_indicator_view is not None:
                msg = "unconfigured execution indicators must not expose a view"
                raise StrategyBacktestValidationError(msg)
            execution_ready = True

        # Configured context slots must be ready; unconfigured already ready=True.
        contexts_ready = all(slot.ready for slot in context_indicator_views)
        overall_ready = base_view.overall_ready and execution_ready and contexts_ready

        document = build_provider_visible_indicator_hash_document(
            execution_bar_index=base_view.execution_bar_index,
            execution_indicator_view=execution_indicator_view,
            execution_indicators_configured=execution_indicators_configured,
            execution_indicators_ready=execution_ready,
            context_slots=context_indicator_views,
            overall_ready=overall_ready,
        )
        digest = sha256_hex(
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )

        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _COMPOSED_VIEW_SCHEMA)
        object.__setattr__(self, "base_view", base_view)
        object.__setattr__(self, "execution_indicator_view", execution_indicator_view)
        object.__setattr__(self, "context_indicator_views", context_indicator_views)
        object.__setattr__(self, "execution_indicators_configured", execution_indicators_configured)
        object.__setattr__(self, "execution_indicators_ready", execution_ready)
        object.__setattr__(self, "overall_ready", overall_ready)
        object.__setattr__(self, "provider_visible_indicator_hash", digest)
        return self

    def __repr__(self) -> str:
        return (
            f"MultiTimeframeIndicatorDecisionView("
            f"bar_index={self.base_view.execution_bar_index}, "
            f"overall_ready={self.overall_ready})"
        )

    def __str__(self) -> str:
        return self.__repr__()
