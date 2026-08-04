"""Domain package for deterministic candle resampling and alignment."""

from zorqen_research.domain.market_data.alignment import (
    ContextAlignment,
    MultiContextAlignment,
    align_context_to_execution,
    align_multi_context,
)
from zorqen_research.domain.market_data.derivation import (
    MAX_DERIVATION_RATIO,
    TimeframeDerivationPlan,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingError,
    ResamplingValidationError,
)
from zorqen_research.domain.market_data.resampling import resample_candles
from zorqen_research.domain.market_data.series import ResampledCandleSeries

__all__ = [
    "AlignmentValidationError",
    "ContextAlignment",
    "MAX_DERIVATION_RATIO",
    "MultiContextAlignment",
    "ResampledCandleSeries",
    "ResamplingError",
    "ResamplingValidationError",
    "TimeframeDerivationPlan",
    "align_context_to_execution",
    "align_multi_context",
    "derive_timeframe_plan",
    "resample_candles",
]
