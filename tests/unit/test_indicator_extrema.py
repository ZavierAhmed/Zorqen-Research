"""Rolling and prior-window extrema tests."""

from __future__ import annotations

from decimal import Decimal

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicators.extrema import (
    CountingSequence,
    prior_rolling_highest,
    prior_rolling_highest_counted,
    prior_rolling_lowest,
    rolling_highest,
    rolling_highest_counted,
    rolling_lowest,
)

EXTREMA_SPECS = (
    ("3", "5", "1", "4"),
    ("4", "7", "3", "5"),
    ("5", "7", "2", "6"),
    ("4", "6", "2", "5"),
    ("6", "8", "4", "7"),
)


def test_rolling_period_one_equals_current() -> None:
    indicator_input = indicator_input_from_specs(EXTREMA_SPECS)
    assert rolling_highest(indicator_input, 1).values == tuple(
        c.high for c in indicator_input.candles
    )
    assert rolling_lowest(indicator_input, 1).values == tuple(
        c.low for c in indicator_input.candles
    )


def test_prior_period_one_equals_previous() -> None:
    indicator_input = indicator_input_from_specs(EXTREMA_SPECS)
    highs = prior_rolling_highest(indicator_input, 1).values
    lows = prior_rolling_lowest(indicator_input, 1).values
    assert highs[0] is None
    assert lows[0] is None
    for index in range(1, len(indicator_input.candles)):
        assert highs[index] == indicator_input.candles[index - 1].high
        assert lows[index] == indicator_input.candles[index - 1].low


def test_rolling_warmup_and_duplicates() -> None:
    indicator_input = indicator_input_from_specs(EXTREMA_SPECS)
    highest = rolling_highest(indicator_input, 3)
    lowest = rolling_lowest(indicator_input, 3)
    assert highest.values[:2] == (None, None)
    assert lowest.values[:2] == (None, None)
    assert highest.values[2:] == (Decimal("7"), Decimal("7"), Decimal("8"))
    assert lowest.values[2:] == (Decimal("1"), Decimal("2"), Decimal("2"))


def test_prior_excludes_current_candle() -> None:
    indicator_input = indicator_input_from_specs(EXTREMA_SPECS)
    highest = prior_rolling_highest(indicator_input, 3)
    lowest = prior_rolling_lowest(indicator_input, 3)
    assert highest.values[:3] == (None, None, None)
    assert lowest.values[:3] == (None, None, None)
    # At index 3, current high is 6 / low is 2; prior window uses 5,7,7 / 1,3,2
    assert highest.values[3] == Decimal("7")
    assert lowest.values[3] == Decimal("1")
    assert highest.values[3] != indicator_input.candles[3].high
    assert lowest.values[4] == Decimal("2")


def test_rolling_strictly_increasing_and_decreasing() -> None:
    increasing = indicator_input_from_specs(
        (
            ("1", "1", "1", "1"),
            ("2", "2", "2", "2"),
            ("3", "3", "3", "3"),
            ("4", "4", "4", "4"),
        )
    )
    decreasing = indicator_input_from_specs(
        (
            ("4", "4", "4", "4"),
            ("3", "3", "3", "3"),
            ("2", "2", "2", "2"),
            ("1", "1", "1", "1"),
        )
    )
    assert rolling_highest(increasing, 3).values[2:] == (
        Decimal("3"),
        Decimal("4"),
    )
    assert rolling_lowest(decreasing, 3).values[2:] == (
        Decimal("2"),
        Decimal("1"),
    )


def test_extrema_prefix_equivalence() -> None:
    full = indicator_input_from_specs(EXTREMA_SPECS)
    prefix = indicator_input_from_specs(EXTREMA_SPECS[:4])
    assert rolling_highest(prefix, 3).values == rolling_highest(full, 3).values[:4]
    assert prior_rolling_highest(prefix, 3).values == (prior_rolling_highest(full, 3).values[:4])


def test_rolling_linear_operation_bound() -> None:
    values = tuple(Decimal(index % 17) for index in range(500))
    period = 25
    counted = CountingSequence(values)
    result = rolling_highest_counted(counted, period)
    assert len(result) == 500
    # Each index is read when entered; deque comparisons add O(1) amortized reads.
    # Bound well below quadratic n*period.
    assert counted.reads < 500 * 4


def test_prior_linear_operation_bound() -> None:
    values = tuple(Decimal(index % 13) for index in range(500))
    period = 40
    counted = CountingSequence(values)
    result = prior_rolling_highest_counted(counted, period)
    assert result[period - 1] is None
    assert result[period] is not None
    assert counted.reads < 500 * 4


def test_current_candle_mutation_does_not_affect_prior_at_same_index() -> None:
    """Changing the current candle must not alter the prior-window level at that index."""
    base = indicator_input_from_specs(EXTREMA_SPECS)
    prior = prior_rolling_highest(base, 3)
    mutated_specs = (
        EXTREMA_SPECS[0],
        EXTREMA_SPECS[1],
        EXTREMA_SPECS[2],
        ("4", "99", "2", "5"),  # mutate current high at index 3
        EXTREMA_SPECS[4],
    )
    mutated = indicator_input_from_specs(mutated_specs)
    mutated_prior = prior_rolling_highest(mutated, 3)
    assert mutated_prior.values[3] == prior.values[3] == Decimal("7")
