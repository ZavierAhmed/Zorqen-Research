"""Bounded no-lookahead candle history views."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError


@dataclass(frozen=True, slots=True, init=False)
class VerifiedHistorySource:
    """
    Immutable candle tuple validated once at the bundle/feed boundary.

    Per-bar views retain a reference to this source plus an end-exclusive index.
    """

    _candles: Sequence[Candle]

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "VerifiedHistorySource must be created via from_verified_tuple or bind_trusted"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_verified_tuple(cls, candles: object) -> VerifiedHistorySource:
        """Standalone constructor with full candle-tuple validation."""
        if not isinstance(candles, tuple):
            msg = "candles must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)
        if not candles:
            msg = "candles must be non-empty"
            raise StrategyBacktestValidationError(msg)
        for index, candle in enumerate(candles):
            if not isinstance(candle, Candle):
                msg = f"candles[{index}] must be a Candle"
                raise StrategyBacktestValidationError(msg)
        return cls._bind(candles)

    @classmethod
    def bind_trusted(cls, candles: tuple[Candle, ...]) -> VerifiedHistorySource:
        """
        Feed-boundary construction after the input bundle already validated candles.

        Does not re-scan or slice the series.
        """
        if type(candles) is not tuple:
            msg = "candles must be an exact tuple"
            raise StrategyBacktestValidationError(msg)
        if not candles:
            msg = "candles must be non-empty"
            raise StrategyBacktestValidationError(msg)
        return cls._bind(candles)

    @classmethod
    def _bind(cls, candles: Sequence[Candle]) -> VerifiedHistorySource:
        self = object.__new__(cls)
        object.__setattr__(self, "_candles", candles)
        return self

    def __len__(self) -> int:
        return len(self._candles)

    @property
    def candles(self) -> Sequence[Candle]:
        """Internal access for trusted feed/view construction only."""
        return self._candles


@dataclass(frozen=True, slots=True, init=False)
class VisibleCandleHistory:
    """
    Read-only view over ``source[0:end_exclusive]`` without exposing the full tuple.

    Multiple views may share the same underlying verified source.
    """

    _source: Sequence[Candle]
    _end_exclusive: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "VisibleCandleHistory must be created via from_prefix or from_verified_source"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_prefix(
        cls,
        candles: tuple[Candle, ...],
        *,
        end_exclusive: int,
    ) -> VisibleCandleHistory:
        """Public standalone constructor with full prefix validation."""
        if not isinstance(candles, tuple):
            msg = "candles must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)
        if type(end_exclusive) is not int or isinstance(end_exclusive, bool):
            msg = "end_exclusive must be a real int"
            raise StrategyBacktestValidationError(msg)
        if end_exclusive < 0 or end_exclusive > len(candles):
            msg = "end_exclusive must be between 0 and source length inclusive"
            raise StrategyBacktestValidationError(msg)
        for index, candle in enumerate(candles[:end_exclusive]):
            if not isinstance(candle, Candle):
                msg = f"candles[{index}] must be a Candle"
                raise StrategyBacktestValidationError(msg)
        return cls._bind(candles, end_exclusive=end_exclusive)

    @classmethod
    def from_verified_source(
        cls,
        source: VerifiedHistorySource,
        *,
        end_exclusive: int,
    ) -> VisibleCandleHistory:
        """
        Constant-time trusted construction for the per-bar feed path.

        Performs only bounds checks — no prefix loops and no slicing.
        """
        if not isinstance(source, VerifiedHistorySource):
            msg = "source must be a VerifiedHistorySource"
            raise StrategyBacktestValidationError(msg)
        if type(end_exclusive) is not int or isinstance(end_exclusive, bool):
            msg = "end_exclusive must be a real int"
            raise StrategyBacktestValidationError(msg)
        if end_exclusive < 0 or end_exclusive > len(source):
            msg = "end_exclusive must be between 0 and source length inclusive"
            raise StrategyBacktestValidationError(msg)
        return cls._bind(source.candles, end_exclusive=end_exclusive)

    @classmethod
    def _bind(cls, source: Sequence[Candle], *, end_exclusive: int) -> VisibleCandleHistory:
        self = object.__new__(cls)
        object.__setattr__(self, "_source", source)
        object.__setattr__(self, "_end_exclusive", end_exclusive)
        return self

    def __len__(self) -> int:
        return self._end_exclusive

    def __iter__(self) -> Iterator[Candle]:
        for index in range(self._end_exclusive):
            yield self._source[index]

    def __getitem__(self, key: int | slice) -> Candle | tuple[Candle, ...]:
        visible = self._end_exclusive
        if isinstance(key, slice):
            start, stop, step = key.indices(visible)
            return tuple(self._source[index] for index in range(start, stop, step))
        if isinstance(key, bool) or not isinstance(key, int):
            msg = "history index must be a real int or slice"
            raise StrategyBacktestValidationError(msg)
        index = key
        if index < 0:
            index = visible + index
        if index < 0 or index >= visible:
            raise IndexError("VisibleCandleHistory index out of range")
        return self._source[index]

    @property
    def latest(self) -> Candle | None:
        if self._end_exclusive == 0:
            return None
        return self._source[self._end_exclusive - 1]

    @property
    def source_object(self) -> Sequence[Candle]:
        """Identity of the shared backing sequence (for tests; not candle content)."""
        return self._source
