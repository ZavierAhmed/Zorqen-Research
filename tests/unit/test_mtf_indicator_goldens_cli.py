"""CLI tests for Milestone 1.2 MTF indicator goldens."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from zorqen_research.application.strategy_backtesting.indicator_goldens import (
    ALL_MTF_INDICATOR_SCENARIO_NAMES,
    run_mtf_indicator_scenario,
)
from zorqen_research.backtesting.cli import main


def test_all_mtf_indicator_golden_scenarios_pass() -> None:
    for name in ALL_MTF_INDICATOR_SCENARIO_NAMES:
        payload = run_mtf_indicator_scenario(name)
        assert payload["ok"] is True
        assert payload["scenario"] == name


def test_mtf_indicator_cli_all_emits_json_and_exits_zero() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["run-mtf-indicator-golden", "--scenario", "all"])
    assert code == 0
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == len(ALL_MTF_INDICATOR_SCENARIO_NAMES)
    for line in lines:
        payload = json.loads(line)
        assert payload["ok"] is True


def test_mtf_indicator_cli_unknown_and_mismatch_nonzero() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["run-mtf-indicator-golden", "--scenario", "nope"])
    assert code == 1
    payload = json.loads(stderr.getvalue())
    assert payload["ok"] is False
    assert payload["error"] == "unknown_scenario"

    from dataclasses import replace

    from zorqen_research.application.strategy_backtesting import indicator_goldens as mod

    original = mod.GOLDENS["execution-indicator-warmup"]
    mod.GOLDENS["execution-indicator-warmup"] = replace(
        original,
        composition_hash="ff" * 32,
    )
    try:
        stderr = StringIO()
        with patch("sys.stderr", stderr):
            code = main(["run-mtf-indicator-golden", "--scenario", "execution-indicator-warmup"])
        assert code == 1
        payload = json.loads(stderr.getvalue())
        assert payload["ok"] is False
        assert payload["error"] == "golden_mismatch"
    finally:
        mod.GOLDENS["execution-indicator-warmup"] = original
