"""Indicator golden CLI and frozen vector tests."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from zorqen_research.application.indicators.goldens import ALL_SCENARIO_NAMES, run_scenario
from zorqen_research.indicators.cli import main


def test_all_indicator_golden_scenarios_pass() -> None:
    for name in ALL_SCENARIO_NAMES:
        payload = run_scenario(name)
        assert payload["ok"] is True
        assert payload["scenario"] == name


def test_indicator_cli_all_emits_json_and_exits_zero() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["verify-golden", "--scenario", "all"])
    assert code == 0
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == len(ALL_SCENARIO_NAMES)
    for line in lines:
        payload = json.loads(line)
        assert payload["ok"] is True
        assert "result_hash" in payload


def test_indicator_cli_unknown_scenario_nonzero() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["verify-golden", "--scenario", "nope"])
    assert code == 1
    payload = json.loads(stderr.getvalue())
    assert payload["ok"] is False
    assert payload["error"] == "unknown_scenario"
