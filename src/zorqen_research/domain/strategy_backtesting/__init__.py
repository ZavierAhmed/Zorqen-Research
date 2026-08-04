"""Domain package for multi-timeframe strategy backtest bridging."""

from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
    required_visible_count,
)
from zorqen_research.domain.strategy_backtesting.errors import (
    StrategyBacktestError,
    StrategyBacktestValidationError,
)
from zorqen_research.domain.strategy_backtesting.histories import (
    VerifiedHistorySource,
    VisibleCandleHistory,
)
from zorqen_research.domain.strategy_backtesting.inputs import (
    ContextSeriesInput,
    MultiTimeframeBacktestInput,
)
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope

__all__ = [
    "ContextDecisionView",
    "ContextSeriesInput",
    "MultiTimeframeBacktestInput",
    "MultiTimeframeDecisionView",
    "StrategyBacktestEnvelope",
    "StrategyBacktestError",
    "StrategyBacktestValidationError",
    "VerifiedHistorySource",
    "VisibleCandleHistory",
    "required_visible_count",
]
