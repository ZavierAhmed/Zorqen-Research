"""Factory-bound indicator input identity."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.market_data.series import require_canonical_series
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_INPUT_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False)
class IndicatorInput:
    """Canonical candle series identity for offline indicator calculation."""

    symbol: Symbol
    timeframe: Timeframe
    candles: tuple[Candle, ...]
    candle_count: int
    minimum_open_time: datetime
    maximum_open_time: datetime
    candle_sha256: str
    input_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorInput must be created via from_verified"
        raise IndicatorValidationError(msg)

    @classmethod
    def from_verified(
        cls,
        *,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: tuple[Candle, ...],
    ) -> IndicatorInput:
        if not isinstance(symbol, Symbol):
            msg = "symbol must be a Symbol"
            raise IndicatorValidationError(msg)
        if not isinstance(timeframe, Timeframe):
            msg = "timeframe must be a Timeframe"
            raise IndicatorValidationError(msg)
        # Exact runtime types before any iteration, hashing, or retention.
        if type(candles) is not tuple:
            msg = "candles must be an exact tuple"
            raise IndicatorValidationError(msg)
        for index, candle in enumerate(candles):
            if type(candle) is not Candle:
                msg = f"candles[{index}] must be an exact Candle"
                raise IndicatorValidationError(msg)
        try:
            verified = require_canonical_series(
                candles,
                timeframe=timeframe,
                label="indicator",
            )
        except ResamplingValidationError as exc:
            raise IndicatorValidationError(str(exc)) from exc
        if verified is not candles:
            msg = "verified candle tuple identity must match the caller-supplied tuple"
            raise IndicatorValidationError(msg)

        candle_sha256 = hash_candle_tuple(verified)
        digest = sha256_hex(
            json.dumps(
                {
                    "candle_count": len(verified),
                    "candle_sha256": candle_sha256,
                    "maximum_open_time": verified[-1].open_time.isoformat(),
                    "minimum_open_time": verified[0].open_time.isoformat(),
                    "schema_version": _INPUT_SCHEMA,
                    "symbol": symbol.value,
                    "timeframe": timeframe.value,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "candles", verified)
        object.__setattr__(self, "candle_count", len(verified))
        object.__setattr__(self, "minimum_open_time", verified[0].open_time)
        object.__setattr__(self, "maximum_open_time", verified[-1].open_time)
        object.__setattr__(self, "candle_sha256", candle_sha256)
        object.__setattr__(self, "input_hash", digest)
        return self
