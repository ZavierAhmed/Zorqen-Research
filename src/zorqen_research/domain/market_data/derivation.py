"""Immutable timeframe derivation plans."""

from __future__ import annotations

from dataclasses import dataclass

from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.timeframes import Timeframe, duration_milliseconds, timeframe_duration

MAX_DERIVATION_RATIO = 10_080  # 1m → 1w


def _exact_ratio(source: Timeframe, target: Timeframe) -> int:
    source_ms = duration_milliseconds(timeframe_duration(source))
    target_ms = duration_milliseconds(timeframe_duration(target))
    if source_ms == target_ms:
        msg = "target timeframe must be strictly coarser than source timeframe"
        raise ResamplingValidationError(msg)
    if source_ms > target_ms:
        msg = "target timeframe must be coarser than source timeframe"
        raise ResamplingValidationError(msg)
    if target_ms % source_ms != 0:
        msg = (
            f"target duration is not an exact integer multiple of source duration: "
            f"{source.value} → {target.value}"
        )
        raise ResamplingValidationError(msg)
    ratio = target_ms // source_ms
    if ratio < 1 or ratio > MAX_DERIVATION_RATIO:
        msg = f"derivation ratio {ratio} is outside the supported range"
        raise ResamplingValidationError(msg)
    return ratio


@dataclass(frozen=True, slots=True)
class TimeframeDerivationPlan:
    """Exact integer-ratio derivation from a finer source to a coarser target."""

    source_timeframe: Timeframe
    target_timeframe: Timeframe
    ratio: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_timeframe, Timeframe):
            msg = "source_timeframe must be a Timeframe"
            raise ResamplingValidationError(msg)
        if not isinstance(self.target_timeframe, Timeframe):
            msg = "target_timeframe must be a Timeframe"
            raise ResamplingValidationError(msg)
        if type(self.ratio) is not int or isinstance(self.ratio, bool):
            msg = "ratio must be a real int"
            raise ResamplingValidationError(msg)
        expected = _exact_ratio(self.source_timeframe, self.target_timeframe)
        if self.ratio != expected:
            msg = "ratio does not match exact duration arithmetic"
            raise ResamplingValidationError(msg)


def derive_timeframe_plan(
    source_timeframe: Timeframe,
    target_timeframe: Timeframe,
) -> TimeframeDerivationPlan:
    """
    Build a validated derivation plan.

    Requires ``source duration < target duration`` and an exact integer multiple.
    """
    if not isinstance(source_timeframe, Timeframe):
        msg = "source_timeframe must be a Timeframe"
        raise ResamplingValidationError(msg)
    if not isinstance(target_timeframe, Timeframe):
        msg = "target_timeframe must be a Timeframe"
        raise ResamplingValidationError(msg)
    ratio = _exact_ratio(source_timeframe, target_timeframe)
    return TimeframeDerivationPlan(
        source_timeframe=source_timeframe,
        target_timeframe=target_timeframe,
        ratio=ratio,
    )
