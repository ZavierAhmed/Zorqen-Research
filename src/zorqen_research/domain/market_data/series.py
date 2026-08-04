"""Immutable resampled candle series results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_SHA256_RE_LEN = 64


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != _SHA256_RE_LEN:
        msg = f"{field_name} must be a 64-character lowercase hex digest"
        raise ResamplingValidationError(msg)
    if any(ch not in "0123456789abcdef" for ch in value):
        msg = f"{field_name} must be a 64-character lowercase hex digest"
        raise ResamplingValidationError(msg)
    if value == "0" * 64:
        msg = f"{field_name} must not be a placeholder all-zero hash"
        raise ResamplingValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class ResampledCandleSeries:
    """Deterministic complete-bucket resampling result with computed target hash."""

    symbol: Symbol
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    ratio: int
    source_candle_count: int
    source_minimum_open_time: datetime
    source_maximum_open_time: datetime
    source_candle_sha256: str
    candles: tuple[Candle, ...]
    target_candle_count: int = field(init=False)
    target_minimum_open_time: datetime = field(init=False)
    target_maximum_open_time: datetime = field(init=False)
    target_candle_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, Symbol):
            msg = "symbol must be a Symbol"
            raise ResamplingValidationError(msg)
        if not isinstance(self.candles, tuple) or not self.candles:
            msg = "resampled candles must be a non-empty tuple"
            raise ResamplingValidationError(msg)
        for index, candle in enumerate(self.candles):
            if not isinstance(candle, Candle):
                msg = f"candles[{index}] must be a Candle"
                raise ResamplingValidationError(msg)
        plan = derive_timeframe_plan(self.source_timeframe, self.target_timeframe)
        if self.ratio != plan.ratio:
            msg = "ratio does not match source/target timeframes"
            raise ResamplingValidationError(msg)
        if type(self.source_candle_count) is not int or isinstance(self.source_candle_count, bool):
            msg = "source_candle_count must be a real int"
            raise ResamplingValidationError(msg)
        if self.source_candle_count != len(self.candles) * self.ratio:
            msg = "source_candle_count must equal target_candle_count * ratio"
            raise ResamplingValidationError(msg)
        _require_sha256(self.source_candle_sha256, field_name="source_candle_sha256")

        # Deferred import keeps candle CSV contract single-sourced.
        from zorqen_research.application.market_data.serialization import serialize_candles_csv

        target_count = len(self.candles)
        target_min = self.candles[0].open_time
        target_max = self.candles[-1].open_time
        target_digest = sha256_hex(serialize_candles_csv(self.candles))
        object.__setattr__(self, "target_candle_count", target_count)
        object.__setattr__(self, "target_minimum_open_time", target_min)
        object.__setattr__(self, "target_maximum_open_time", target_max)
        object.__setattr__(self, "target_candle_sha256", target_digest)
