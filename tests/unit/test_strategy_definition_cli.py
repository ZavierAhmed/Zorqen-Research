"""CLI tests for zorqen-strategy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.strategy_definition_helpers import EXAMPLE_DEFINITION, EXAMPLE_PARAMETERS
from zorqen_research.strategies.cli import main


def test_validate_definition_success(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["validate-definition", "--file", str(EXAMPLE_DEFINITION)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["definition_code"] == "example_test_definition"
    assert payload["parameter_count"] == 4
    assert len(payload["definition_hash"]) == 64
    assert payload["executable_code_present"] is False
    assert payload["approved_means_executable"] is False


def test_bind_parameters_success(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "bind-parameters",
            "--definition",
            str(EXAMPLE_DEFINITION),
            "--parameters",
            str(EXAMPLE_PARAMETERS),
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert len(payload["definition_hash"]) == 64
    assert len(payload["parameter_set_hash"]) == 64
    assert len(payload["instance_hash"]) == 64


def test_invalid_definition_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version":"1"}', encoding="utf-8")
    code = main(["validate-definition", "--file", str(bad)])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert err["ok"] is False
    assert "error" in err
    assert "Traceback" not in err["error"]


def test_missing_file_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["validate-definition", "--file", "missing-does-not-exist.json"])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert err["ok"] is False
