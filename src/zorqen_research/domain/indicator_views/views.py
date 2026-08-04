"""Per-bar bounded indicator decision items and views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.histories import (
    VisibleIndicatorHistory,
    _VerifiedIndicatorSource,
)
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.math_policy import require_period
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_VIEW_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False, repr=False)
class IndicatorDecisionItem:
    """Provider-visible bounded indicator state at one decision bar."""

    series_key: IndicatorSeriesKey
    indicator_code: IndicatorCode
    parameters: tuple[tuple[str, int], ...]
    symbol: Symbol
    timeframe: Timeframe
    history: VisibleIndicatorHistory
    visible_count: int
    defined_visible_count: int
    latest: Decimal | None
    ready: bool
    visible_prefix_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorDecisionItem must be created by IndicatorDecisionFeed"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        source: _VerifiedIndicatorSource,
        end_exclusive: int,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> IndicatorDecisionItem:
        history = VisibleIndicatorHistory._from_verified_source(
            source,
            end_exclusive=end_exclusive,
        )
        latest = history.latest
        ready = latest is not None and type(latest) is Decimal
        self = object.__new__(cls)
        object.__setattr__(self, "series_key", source._series_key)
        object.__setattr__(self, "indicator_code", source._series_key.indicator_code)
        object.__setattr__(self, "parameters", source._series_key.parameters)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "history", history)
        object.__setattr__(self, "visible_count", history.visible_count)
        object.__setattr__(self, "defined_visible_count", history.defined_visible_count)
        object.__setattr__(self, "latest", latest)
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "visible_prefix_hash", history.visible_prefix_hash)
        return self

    def __repr__(self) -> str:
        return (
            f"IndicatorDecisionItem(key={self.series_key!r}, "
            f"visible_count={self.visible_count}, ready={self.ready})"
        )

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(frozen=True, slots=True, init=False, repr=False)
class IndicatorDecisionView:
    """All requested bounded indicator values at one candle index."""

    schema_version: str
    symbol: Symbol
    timeframe: Timeframe
    bar_index: int
    visible_count: int
    items: tuple[IndicatorDecisionItem, ...]
    item_count: int
    overall_ready: bool
    decision_view_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorDecisionView must be created via IndicatorDecisionFeed.view_at"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def _from_feed(
        cls,
        *,
        symbol: Symbol,
        timeframe: Timeframe,
        bar_index: int,
        sources: tuple[_VerifiedIndicatorSource, ...],
    ) -> IndicatorDecisionView:
        end_exclusive = bar_index + 1
        items = tuple(
            IndicatorDecisionItem._from_feed(
                source=source,
                end_exclusive=end_exclusive,
                symbol=symbol,
                timeframe=timeframe,
            )
            for source in sources
        )
        overall_ready = all(item.ready for item in items)
        digest = sha256_hex(
            json.dumps(
                {
                    "bar_index": bar_index,
                    "item_count": len(items),
                    "items": [
                        {
                            "indicator_code": item.indicator_code.value,
                            "key_hash": item.series_key.key_hash,
                            "parameters": {k: v for k, v in item.parameters},
                            "ready": item.ready,
                            "visible_prefix_hash": item.visible_prefix_hash,
                        }
                        for item in items
                    ],
                    "overall_ready": overall_ready,
                    "schema_version": _VIEW_SCHEMA,
                    "symbol": symbol.value,
                    "timeframe": timeframe.value,
                    "visible_count": end_exclusive,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _VIEW_SCHEMA)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "bar_index", bar_index)
        object.__setattr__(self, "visible_count", end_exclusive)
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "item_count", len(items))
        object.__setattr__(self, "overall_ready", overall_ready)
        object.__setattr__(self, "decision_view_hash", digest)
        return self

    def require(
        self,
        indicator_code: object,
        period: object | None = None,
    ) -> IndicatorDecisionItem:
        if not isinstance(indicator_code, IndicatorCode):
            msg = "indicator_code must be an IndicatorCode"
            raise IndicatorViewValidationError(msg)
        if indicator_code is IndicatorCode.TRUE_RANGE:
            if period is not None:
                msg = "true_range requires no period"
                raise IndicatorViewValidationError(msg)
            wanted = IndicatorSeriesKey.from_verified(
                indicator_code=indicator_code,
                parameters={},
            )
        else:
            if period is None:
                msg = "period is required for this indicator"
                raise IndicatorViewValidationError(msg)
            try:
                period_value = require_period(period)
            except IndicatorValidationError as exc:
                raise IndicatorViewValidationError(str(exc)) from exc
            wanted = IndicatorSeriesKey.from_verified(
                indicator_code=indicator_code,
                parameters={"period": period_value},
            )
        for item in self.items:
            if item.series_key.key_hash == wanted.key_hash:
                return item
        msg = "requested indicator series key is not present in this view"
        raise IndicatorViewValidationError(msg)

    def __repr__(self) -> str:
        return (
            f"IndicatorDecisionView(bar_index={self.bar_index}, "
            f"visible_count={self.visible_count}, "
            f"item_count={self.item_count}, overall_ready={self.overall_ready})"
        )

    def __str__(self) -> str:
        return self.__repr__()
