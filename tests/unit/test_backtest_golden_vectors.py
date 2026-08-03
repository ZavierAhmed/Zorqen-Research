"""Committed golden vector verification tests."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.golden import SCENARIOS, run_scenario
from zorqen_research.application.backtesting.golden_expectations import (
    GOLDEN_EXPECTATIONS,
    GoldenMismatchError,
    assert_matches_expectation,
)
from zorqen_research.backtesting.cli import main as backtest_main
from zorqen_research.domain.backtesting.enums import FillReason

FROZEN_HASHES = {
    "end-of-data": "28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3",
    "explicit-exit": "3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c",
    "long-stop": "4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02",
    "long-target": "964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38",
    "pending-final-entry": "e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766",
    "same-bar-stop-first": "a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6",
    "short-target": "b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d",
}


def test_every_scenario_matches_committed_expectation() -> None:
    assert set(SCENARIOS) == set(GOLDEN_EXPECTATIONS) == set(FROZEN_HASHES)
    for name in SCENARIOS:
        result = run_scenario(name)
        assert result.summary.result_hash == FROZEN_HASHES[name]
        assert GOLDEN_EXPECTATIONS[name].result_hash == FROZEN_HASHES[name]


def test_modified_fill_price_expectation_fails() -> None:
    result = run_scenario("long-target")
    expected = GOLDEN_EXPECTATIONS["long-target"]
    bad = replace(
        expected,
        expected_fill_prices=(Decimal("100.56"), Decimal("999.99")),
    )
    with pytest.raises(GoldenMismatchError, match="fill_prices"):
        assert_matches_expectation(result, bad)


def test_modified_fee_expectation_fails() -> None:
    result = run_scenario("long-target")
    expected = GOLDEN_EXPECTATIONS["long-target"]
    bad = replace(
        expected,
        expected_fill_fees=(Decimal("0.10056"), Decimal("9.99")),
        total_fees=Decimal("10.09056"),
    )
    with pytest.raises(GoldenMismatchError, match="fill_fees"):
        assert_matches_expectation(result, bad)


def test_modified_result_hash_expectation_fails() -> None:
    result = run_scenario("long-target")
    bad = replace(GOLDEN_EXPECTATIONS["long-target"], result_hash="0" * 64)
    with pytest.raises(GoldenMismatchError, match="result_hash"):
        assert_matches_expectation(result, bad)


def test_cli_exits_nonzero_on_golden_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    original = GOLDEN_EXPECTATIONS["long-target"]
    monkeypatch.setitem(
        GOLDEN_EXPECTATIONS,
        "long-target",
        replace(original, result_hash="0" * 64),
    )
    code = backtest_main(["run-golden", "--scenario", "long-target"])
    assert code == 1


def test_cli_all_repeated_output_identical() -> None:
    def capture() -> str:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "zorqen_research.backtesting.cli",
                "run-golden",
                "--scenario",
                "all",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    first = capture()
    second = capture()
    assert first == second
    lines = [json.loads(line) for line in first.strip().splitlines()]
    assert len(lines) == 7
    assert all(row["ok"] is True for row in lines)
    by_name = {row["scenario"]: row["result_hash"] for row in lines}
    assert by_name == FROZEN_HASHES


def test_exit_reasons_match_committed() -> None:
    assert GOLDEN_EXPECTATIONS["same-bar-stop-first"].same_bar_ambiguity_used is True
    assert GOLDEN_EXPECTATIONS["same-bar-stop-first"].expected_exit_reason is FillReason.STOP_LOSS
    assert GOLDEN_EXPECTATIONS["pending-final-entry"].expected_exit_reason is None
