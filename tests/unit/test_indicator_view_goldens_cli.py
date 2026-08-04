"""Indicator decision-view golden CLI tests."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from zorqen_research.application.indicator_views.goldens import ALL_SCENARIO_NAMES, run_scenario
from zorqen_research.indicators.cli import main


def test_all_indicator_view_golden_scenarios_pass() -> None:
    for name in ALL_SCENARIO_NAMES:
        payload = run_scenario(name)
        assert payload["ok"] is True
        assert payload["scenario"] == name
        assert "bundle_hash" in payload
        assert "decision_view_hash" in payload


def test_indicator_view_cli_all_emits_json_and_exits_zero() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["verify-view-golden", "--scenario", "all"])
    assert code == 0
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == len(ALL_SCENARIO_NAMES)
    for line in lines:
        payload = json.loads(line)
        assert payload["ok"] is True
        assert "item_prefix_hashes" in payload


def test_indicator_view_cli_unknown_and_mismatch_nonzero() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["verify-view-golden", "--scenario", "nope"])
    assert code == 1
    payload = json.loads(stderr.getvalue())
    assert payload["ok"] is False
    assert payload["error"] == "unknown_scenario"

    with patch(
        "zorqen_research.application.indicator_views.goldens.MULTI_EMA_BUNDLE_HASH",
        "ff" * 32,
    ):
        stderr = StringIO()
        with patch("sys.stderr", stderr):
            code = main(["verify-view-golden", "--scenario", "multiple-ema-keys"])
        assert code == 1
        payload = json.loads(stderr.getvalue())
        assert payload["ok"] is False
        assert payload["error"] == "golden_mismatch"


def test_existing_verify_golden_unchanged() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["verify-golden", "--scenario", "ema-close"])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["result_hash"] == (
        "982dcb739655d2eb018e74911c8d53a66a9f86555ffa74aa8111c7134482d303"
    )
