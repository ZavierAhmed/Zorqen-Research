"""Immutable indicator-series results (calculator-owned construction only)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.math_policy import IndicatorMathPolicy
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


@dataclass(frozen=True, slots=True, init=False)
class IndicatorSeries:
    """Complete offline indicator value series — not provider-safe."""

    schema_version: str
    indicator_code: IndicatorCode
    symbol: Symbol
    timeframe: Timeframe
    input_candle_sha256: str
    input_candle_count: int
    parameters: tuple[tuple[str, int], ...]
    value_count: int
    values: tuple[Decimal | None, ...]
    first_defined_index: int | None
    defined_value_count: int
    math_policy: IndicatorMathPolicy
    result_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorSeries must be created by indicator calculators"
        raise IndicatorValidationError(msg)
