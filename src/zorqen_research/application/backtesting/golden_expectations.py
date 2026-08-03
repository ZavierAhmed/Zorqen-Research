"""Committed golden expected economics (literal constants; not engine-derived)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.backtesting.enums import FillReason, FillSide
from zorqen_research.domain.backtesting.results import BacktestResult


@dataclass(frozen=True, slots=True)
class GoldenExpectation:
    input_candle_count: int
    fill_count: int
    closed_trade_count: int
    unfilled_intent_count: int
    final_equity: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fees: Decimal
    max_realized_equity_drawdown: Decimal
    expected_fill_reasons: tuple[FillReason, ...]
    expected_fill_sides: tuple[FillSide, ...]
    expected_fill_bar_indexes: tuple[int, ...]
    expected_reference_prices: tuple[Decimal, ...]
    expected_fill_prices: tuple[Decimal, ...]
    expected_fill_fees: tuple[Decimal, ...]
    expected_exit_reason: FillReason | None
    same_bar_ambiguity_used: bool
    result_hash: str


# Exact hashes frozen by Milestone 0.6 / 0.6A. Do not auto-update.
GOLDEN_EXPECTATIONS: dict[str, GoldenExpectation] = {
    "end-of-data": GoldenExpectation(
        input_candle_count=3,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("10000.48921"),
        gross_pnl=Decimal("0.69000"),
        net_pnl=Decimal("0.48921"),
        total_fees=Decimal("0.20079"),
        max_realized_equity_drawdown=Decimal("0.10005"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.END_OF_DATA),
        expected_fill_sides=(FillSide.BUY, FillSide.SELL),
        expected_fill_bar_indexes=(1, 2),
        expected_reference_prices=(Decimal("100"), Decimal("100.8")),
        expected_fill_prices=(Decimal("100.05"), Decimal("100.74")),
        expected_fill_fees=(Decimal("0.10005"), Decimal("0.10074")),
        expected_exit_reason=FillReason.END_OF_DATA,
        same_bar_ambiguity_used=False,
        result_hash="28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3",
    ),
    "explicit-exit": GoldenExpectation(
        input_candle_count=4,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("10000.18951"),
        gross_pnl=Decimal("0.39000"),
        net_pnl=Decimal("0.18951"),
        total_fees=Decimal("0.20049"),
        max_realized_equity_drawdown=Decimal("0.10005"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.EXPLICIT_EXIT),
        expected_fill_sides=(FillSide.BUY, FillSide.SELL),
        expected_fill_bar_indexes=(1, 2),
        expected_reference_prices=(Decimal("100"), Decimal("100.5")),
        expected_fill_prices=(Decimal("100.05"), Decimal("100.44")),
        expected_fill_fees=(Decimal("0.10005"), Decimal("0.10044")),
        expected_exit_reason=FillReason.EXPLICIT_EXIT,
        same_bar_ambiguity_used=False,
        result_hash="3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c",
    ),
    "long-stop": GoldenExpectation(
        input_candle_count=3,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("9994.70500"),
        gross_pnl=Decimal("-5.10000"),
        net_pnl=Decimal("-5.29500"),
        total_fees=Decimal("0.19500"),
        max_realized_equity_drawdown=Decimal("5.29500"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.STOP_LOSS),
        expected_fill_sides=(FillSide.BUY, FillSide.SELL),
        expected_fill_bar_indexes=(1, 2),
        expected_reference_prices=(Decimal("100"), Decimal("95")),
        expected_fill_prices=(Decimal("100.05"), Decimal("94.95")),
        expected_fill_fees=(Decimal("0.10005"), Decimal("0.09495")),
        expected_exit_reason=FillReason.STOP_LOSS,
        same_bar_ambiguity_used=False,
        result_hash="4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02",
    ),
    "long-target": GoldenExpectation(
        input_candle_count=4,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("10007.17150"),
        gross_pnl=Decimal("7.38000"),
        net_pnl=Decimal("7.17150"),
        total_fees=Decimal("0.20850"),
        max_realized_equity_drawdown=Decimal("0.10056"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.TAKE_PROFIT),
        expected_fill_sides=(FillSide.BUY, FillSide.SELL),
        expected_fill_bar_indexes=(1, 2),
        expected_reference_prices=(Decimal("100.5"), Decimal("108")),
        expected_fill_prices=(Decimal("100.56"), Decimal("107.94")),
        expected_fill_fees=(Decimal("0.10056"), Decimal("0.10794")),
        expected_exit_reason=FillReason.TAKE_PROFIT,
        same_bar_ambiguity_used=False,
        result_hash="964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38",
    ),
    "pending-final-entry": GoldenExpectation(
        input_candle_count=2,
        fill_count=0,
        closed_trade_count=0,
        unfilled_intent_count=1,
        final_equity=Decimal("10000"),
        gross_pnl=Decimal("0"),
        net_pnl=Decimal("0"),
        total_fees=Decimal("0"),
        max_realized_equity_drawdown=Decimal("0"),
        expected_fill_reasons=(),
        expected_fill_sides=(),
        expected_fill_bar_indexes=(),
        expected_reference_prices=(),
        expected_fill_prices=(),
        expected_fill_fees=(),
        expected_exit_reason=None,
        same_bar_ambiguity_used=False,
        result_hash="e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766",
    ),
    "same-bar-stop-first": GoldenExpectation(
        input_candle_count=2,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("9994.70500"),
        gross_pnl=Decimal("-5.10000"),
        net_pnl=Decimal("-5.29500"),
        total_fees=Decimal("0.19500"),
        max_realized_equity_drawdown=Decimal("5.29500"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.STOP_LOSS),
        expected_fill_sides=(FillSide.BUY, FillSide.SELL),
        expected_fill_bar_indexes=(1, 1),
        expected_reference_prices=(Decimal("100"), Decimal("95")),
        expected_fill_prices=(Decimal("100.05"), Decimal("94.95")),
        expected_fill_fees=(Decimal("0.10005"), Decimal("0.09495")),
        expected_exit_reason=FillReason.STOP_LOSS,
        same_bar_ambiguity_used=True,
        result_hash="a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6",
    ),
    "short-target": GoldenExpectation(
        input_candle_count=3,
        fill_count=2,
        closed_trade_count=1,
        unfilled_intent_count=0,
        final_equity=Decimal("10007.70800"),
        gross_pnl=Decimal("7.90000"),
        net_pnl=Decimal("7.70800"),
        total_fees=Decimal("0.19200"),
        max_realized_equity_drawdown=Decimal("0.09995"),
        expected_fill_reasons=(FillReason.MARKET_ENTRY, FillReason.TAKE_PROFIT),
        expected_fill_sides=(FillSide.SELL, FillSide.BUY),
        expected_fill_bar_indexes=(1, 2),
        expected_reference_prices=(Decimal("100"), Decimal("92")),
        expected_fill_prices=(Decimal("99.95"), Decimal("92.05")),
        expected_fill_fees=(Decimal("0.09995"), Decimal("0.09205")),
        expected_exit_reason=FillReason.TAKE_PROFIT,
        same_bar_ambiguity_used=False,
        result_hash="b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d",
    ),
}


class GoldenMismatchError(AssertionError):
    """Golden scenario result does not match committed expectation."""


def assert_matches_expectation(result: BacktestResult, expected: GoldenExpectation) -> None:
    """Compare a backtest result against committed golden economics."""
    errors: list[str] = []

    def check(label: str, actual: object, wanted: object) -> None:
        if actual != wanted:
            errors.append(f"{label}: expected {wanted!r}, got {actual!r}")

    check("input_candle_count", result.summary.input_candle_count, expected.input_candle_count)
    check("fill_count", len(result.fills), expected.fill_count)
    check("closed_trade_count", result.summary.closed_trade_count, expected.closed_trade_count)
    check(
        "unfilled_intent_count",
        result.summary.unfilled_intent_count,
        expected.unfilled_intent_count,
    )
    check("final_equity", result.summary.final_equity, expected.final_equity)
    check("gross_pnl", result.summary.gross_pnl, expected.gross_pnl)
    check("net_pnl", result.summary.net_pnl, expected.net_pnl)
    check("total_fees", result.summary.total_fees, expected.total_fees)
    check(
        "max_realized_equity_drawdown",
        result.summary.max_realized_equity_drawdown,
        expected.max_realized_equity_drawdown,
    )
    check("result_hash", result.summary.result_hash, expected.result_hash)

    reasons = tuple(f.reason for f in result.fills)
    sides = tuple(f.side for f in result.fills)
    bars = tuple(f.bar_index for f in result.fills)
    refs = tuple(f.reference_price for f in result.fills)
    prices = tuple(f.fill_price for f in result.fills)
    fees = tuple(f.fee for f in result.fills)
    check("fill_reasons", reasons, expected.expected_fill_reasons)
    check("fill_sides", sides, expected.expected_fill_sides)
    check("fill_bar_indexes", bars, expected.expected_fill_bar_indexes)
    check("reference_prices", refs, expected.expected_reference_prices)
    check("fill_prices", prices, expected.expected_fill_prices)
    check("fill_fees", fees, expected.expected_fill_fees)

    if expected.expected_exit_reason is None:
        if result.trades:
            errors.append("expected no trades, but trades were present")
    else:
        if not result.trades:
            errors.append("expected a closed trade, but none were present")
        else:
            check("exit_reason", result.trades[0].exit_reason, expected.expected_exit_reason)
            check(
                "same_bar_ambiguity_used",
                result.trades[0].same_bar_ambiguity_used,
                expected.same_bar_ambiguity_used,
            )

    if result.summary.final_equity != result.summary.initial_equity + result.summary.net_pnl:
        errors.append("equity does not reconcile with net_pnl")
    fee_sum = sum((f.fee for f in result.fills), Decimal("0"))
    if result.summary.total_fees != fee_sum:
        errors.append("total_fees does not equal fill fee sum")

    if errors:
        raise GoldenMismatchError("; ".join(errors))
