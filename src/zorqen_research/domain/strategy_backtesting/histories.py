"""Bounded no-lookahead candle history views."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError


@dataclass(frozen=True, slots=True, init=False)
class VisibleCandleHistory:
    """
    Read-only view over ``candles[0:end_exclusive]`` without exposing the full tuple.

    Multiple views may share the same underlying immutable candle tuple.
    """

    _source: tuple[Candle, ...]
    _end_exclusive: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "VisibleCandleHistory must be created via from_prefix"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_prefix(
        cls,
        candles: tuple[Candle, ...],
        *,
        end_exclusive: int,
    ) -> VisibleCandleHistory:
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
        self = object.__new__(cls)
        object.__setattr__(self, "_source", candles)
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
