"""CLI for immutable strategy-definition validation (no network/database/execution)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zorqen_research.application.baselines.verification import (
    assert_no_strategy_provider_registered,
    verify_baseline_family,
)
from zorqen_research.application.strategy_definitions.validation import (
    bind_parameters_files,
    validate_definition_file,
)
from zorqen_research.domain.baselines.errors import (
    BaselineError,
    BaselineParseError,
    BaselineValidationError,
    BaselineVerificationError,
)
from zorqen_research.domain.strategy_definitions.errors import (
    StrategyDefinitionError,
    StrategyDefinitionParseError,
    StrategyDefinitionValidationError,
)


def _emit_ok(payload: dict[str, object]) -> int:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


def _emit_err(payload: dict[str, object]) -> int:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True), file=sys.stderr)
    return 1


def _validate_definition(path: Path) -> int:
    try:
        definition, definition_hash = validate_definition_file(path)
    except FileNotFoundError:
        return _emit_err({"ok": False, "error": "file_not_found"})
    except (StrategyDefinitionParseError, StrategyDefinitionValidationError) as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except StrategyDefinitionError as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except OSError:
        return _emit_err({"ok": False, "error": "unable_to_read_file"})
    return _emit_ok(
        {
            "ok": True,
            "schema_version": definition.schema_version,
            "definition_id": str(definition.definition_id),
            "family_code": definition.family_code,
            "definition_code": definition.definition_code,
            "version": definition.version,
            "status": definition.status.value,
            "parameter_count": len(definition.parameters),
            "definition_hash": definition_hash,
            "executable_code_present": False,
            "approved_means_executable": False,
        }
    )


def _bind_parameters(definition_path: Path, parameters_path: Path) -> int:
    try:
        instance = bind_parameters_files(
            definition_path=definition_path,
            parameters_path=parameters_path,
        )
    except FileNotFoundError:
        return _emit_err({"ok": False, "error": "file_not_found"})
    except (StrategyDefinitionParseError, StrategyDefinitionValidationError) as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except StrategyDefinitionError as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except OSError:
        return _emit_err({"ok": False, "error": "unable_to_read_file"})
    return _emit_ok(
        {
            "ok": True,
            "definition_hash": instance.definition_hash,
            "parameter_set_hash": instance.parameter_set_hash,
            "instance_hash": instance.instance_hash,
            "parameter_count": len(instance.parameter_set.values),
            "executable_code_present": False,
        }
    )


def _verify_baseline(family: str) -> int:
    try:
        assert_no_strategy_provider_registered()
        result = verify_baseline_family(family)
    except BaselineVerificationError as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except (BaselineParseError, BaselineValidationError) as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except BaselineError as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except (StrategyDefinitionParseError, StrategyDefinitionValidationError) as exc:
        return _emit_err({"ok": False, "error": str(exc)})
    except OSError:
        return _emit_err({"ok": False, "error": "unable_to_read_baseline_files"})
    return _emit_ok(result.to_document())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zorqen-strategy",
        description=(
            "Validate immutable strategy definitions, bind parameters, and verify "
            "authoritative baselines (no network, database, or strategy execution)"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-definition", help="Validate a definition JSON file")
    validate.add_argument("--file", required=True, type=Path)

    bind = sub.add_parser("bind-parameters", help="Bind parameter values to a definition")
    bind.add_argument("--definition", required=True, type=Path)
    bind.add_argument("--parameters", required=True, type=Path)

    verify = sub.add_parser(
        "verify-baseline",
        help="Verify checked-in authoritative baseline contract and evidence",
    )
    verify.add_argument("--family", required=True, type=str)

    args = parser.parse_args(argv)
    if args.command == "validate-definition":
        return _validate_definition(args.file)
    if args.command == "bind-parameters":
        return _bind_parameters(args.definition, args.parameters)
    if args.command == "verify-baseline":
        return _verify_baseline(args.family)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
