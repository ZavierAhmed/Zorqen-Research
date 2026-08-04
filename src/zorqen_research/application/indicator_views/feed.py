"""Standalone no-lookahead indicator decision feed."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.application.indicator_views.prefix_hashes import compute_prefix_hash_chain
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.histories import _VerifiedIndicatorSource
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicator_views.views import IndicatorDecisionView


def _defined_prefix_counts(values: tuple[Decimal | None, ...]) -> tuple[int, ...]:
    counts = [0]
    running = 0
    for value in values:
        if value is not None:
            running += 1
        counts.append(running)
    return tuple(counts)


@dataclass(frozen=True, slots=True, init=False)
class IndicatorDecisionFeed:
    """Standalone single-timeframe bounded indicator decision feed."""

    bundle: IndicatorSeriesBundle
    _sources: tuple[_VerifiedIndicatorSource, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorDecisionFeed must be created via from_bundle"
        raise IndicatorViewValidationError(msg)

    @classmethod
    def from_bundle(cls, bundle: object) -> IndicatorDecisionFeed:
        if type(bundle) is not IndicatorSeriesBundle:
            msg = "bundle must be an exact IndicatorSeriesBundle"
            raise IndicatorViewValidationError(msg)
        try:
            _ = (
                bundle.series,
                bundle.series_keys,
                bundle.symbol,
                bundle.timeframe,
                bundle.input_candle_count,
                bundle.bundle_hash,
            )
        except AttributeError as exc:
            msg = "bundle must be an exact IndicatorSeriesBundle"
            raise IndicatorViewValidationError(msg) from exc

        sources: list[_VerifiedIndicatorSource] = []
        for series, series_key in zip(bundle.series, bundle.series_keys, strict=True):
            rebuilt = IndicatorSeriesKey.from_series_parameters(
                indicator_code=series.indicator_code,
                parameters=series.parameters,
            )
            if rebuilt.key_hash != series_key.key_hash:
                msg = "bundle series key identity mismatch"
                raise IndicatorViewValidationError(msg)
            if series_key.indicator_code is not series.indicator_code:
                msg = "bundle series key code identity mismatch"
                raise IndicatorViewValidationError(msg)
            if series_key.parameters != series.parameters:
                msg = "bundle series key parameters identity mismatch"
                raise IndicatorViewValidationError(msg)
            prefix_hashes = compute_prefix_hash_chain(
                symbol=bundle.symbol,
                timeframe=bundle.timeframe,
                series_key=series_key,
                math_policy=series.math_policy,
                values=series.values,
            )
            defined_counts = _defined_prefix_counts(series.values)
            sources.append(
                _VerifiedIndicatorSource._bind_trusted(
                    series=series,
                    series_key=series_key,
                    prefix_hashes=prefix_hashes,
                    defined_prefix_counts=defined_counts,
                )
            )

        self = object.__new__(cls)
        object.__setattr__(self, "bundle", bundle)
        object.__setattr__(self, "_sources", tuple(sources))
        return self

    def view_at(self, bar_index: object) -> IndicatorDecisionView:
        if type(bar_index) is not int or isinstance(bar_index, bool):
            msg = "bar_index must be a real int"
            raise IndicatorViewValidationError(msg)
        count = self.bundle.input_candle_count
        if bar_index < 0 or bar_index >= count:
            msg = "bar_index must be within the input candle range"
            raise IndicatorViewValidationError(msg)
        return IndicatorDecisionView._from_feed(
            symbol=self.bundle.symbol,
            timeframe=self.bundle.timeframe,
            bar_index=bar_index,
            sources=self._sources,
        )
