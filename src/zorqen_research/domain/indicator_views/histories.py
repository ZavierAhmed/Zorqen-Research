"""Bounded no-lookahead indicator value histories."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.results import IndicatorSeries


@dataclass(frozen=True, slots=True, init=False, repr=False)
class _VerifiedIndicatorSource:
    """
    Internal immutable indicator-value source bound once at the feed boundary.

    Not part of the public domain contract.
    """

    _series: IndicatorSeries
    _values: tuple[Decimal | None, ...]
    _series_key: IndicatorSeriesKey
    _prefix_hashes: tuple[str, ...]
    _defined_prefix_counts: tuple[int, ...]
    _first_defined_index: int | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "_VerifiedIndicatorSource is internal to the indicator decision feed"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def _bind_trusted(
        cls,
        *,
        series: IndicatorSeries,
        series_key: IndicatorSeriesKey,
        prefix_hashes: tuple[str, ...],
        defined_prefix_counts: tuple[int, ...],
    ) -> _VerifiedIndicatorSource:
        if not isinstance(series, IndicatorSeries):
            msg = "series must be an IndicatorSeries"
            raise IndicatorViewValidationError(msg)
        if type(series) is not IndicatorSeries:
            msg = "series must be an exact IndicatorSeries"
            raise IndicatorViewValidationError(msg)
        if not isinstance(series_key, IndicatorSeriesKey):
            msg = "series_key must be an IndicatorSeriesKey"
            raise IndicatorViewValidationError(msg)
        if type(prefix_hashes) is not tuple or type(defined_prefix_counts) is not tuple:
            msg = "prefix hash/count chains must be exact tuples"
            raise IndicatorViewValidationError(msg)
        if len(prefix_hashes) != len(series.values) + 1:
            msg = "prefix_hashes length must equal value count + 1"
            raise IndicatorViewValidationError(msg)
        if len(defined_prefix_counts) != len(series.values) + 1:
            msg = "defined_prefix_counts length must equal value count + 1"
            raise IndicatorViewValidationError(msg)
        self = object.__new__(cls)
        object.__setattr__(self, "_series", series)
        object.__setattr__(self, "_values", series.values)
        object.__setattr__(self, "_series_key", series_key)
        object.__setattr__(self, "_prefix_hashes", prefix_hashes)
        object.__setattr__(self, "_defined_prefix_counts", defined_prefix_counts)
        object.__setattr__(self, "_first_defined_index", series.first_defined_index)
        return self

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return "_VerifiedIndicatorSource()"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(frozen=True, slots=True, init=False, repr=False)
class VisibleIndicatorHistory:
    """
    Read-only view over ``source.values[0:end_exclusive]``.

    Multiple views may share the same underlying verified source.
    """

    _source: _VerifiedIndicatorSource
    _end_exclusive: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "VisibleIndicatorHistory must be created by IndicatorDecisionFeed"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def _from_verified_source(
        cls,
        source: _VerifiedIndicatorSource,
        *,
        end_exclusive: int,
    ) -> VisibleIndicatorHistory:
        """Constant-time trusted construction for the per-bar feed path."""
        if not isinstance(source, _VerifiedIndicatorSource):
            msg = "source must be a _VerifiedIndicatorSource"
            raise IndicatorViewValidationError(msg)
        if type(end_exclusive) is not int or isinstance(end_exclusive, bool):
            msg = "end_exclusive must be a real int"
            raise IndicatorViewValidationError(msg)
        if end_exclusive < 0 or end_exclusive > len(source):
            msg = "end_exclusive must be between 0 and source length inclusive"
            raise IndicatorViewValidationError(msg)
        self = object.__new__(cls)
        object.__setattr__(self, "_source", source)
        object.__setattr__(self, "_end_exclusive", end_exclusive)
        return self

    def __len__(self) -> int:
        return self._end_exclusive

    @property
    def visible_count(self) -> int:
        return self._end_exclusive

    @property
    def defined_visible_count(self) -> int:
        return self._source._defined_prefix_counts[self._end_exclusive]

    @property
    def visible_prefix_hash(self) -> str:
        return self._source._prefix_hashes[self._end_exclusive]

    @property
    def latest(self) -> Decimal | None:
        if self._end_exclusive == 0:
            return None
        return self._source._values[self._end_exclusive - 1]

    @property
    def latest_defined(self) -> bool:
        latest = self.latest
        return latest is not None and type(latest) is Decimal

    def __iter__(self) -> Iterator[Decimal | None]:
        for index in range(self._end_exclusive):
            yield self._source._values[index]

    def __getitem__(self, key: int | slice) -> Decimal | None | tuple[Decimal | None, ...]:
        visible = self._end_exclusive
        if isinstance(key, slice):
            start, stop, step = key.indices(visible)
            return tuple(self._source._values[index] for index in range(start, stop, step))
        if isinstance(key, bool) or not isinstance(key, int):
            msg = "history index must be a real int or slice"
            raise IndicatorViewValidationError(msg)
        index = key
        if index < 0:
            index = visible + index
        if index < 0 or index >= visible:
            raise IndexError("VisibleIndicatorHistory index out of range")
        return self._source._values[index]

    def __repr__(self) -> str:
        latest_defined = "true" if self.latest_defined else "false"
        return (
            f"VisibleIndicatorHistory(visible_count={self._end_exclusive}, "
            f"latest_defined={latest_defined})"
        )

    def __str__(self) -> str:
        return self.__repr__()
