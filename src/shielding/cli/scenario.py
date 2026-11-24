"""Run deterministic shielding scenarios from JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shielding.cli.scenario_output import print_result_summary
from shielding.scenarios.json_io import load_scenario
from shielding.scenarios.runner import run_scenario


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "scenario_path", type=Path, help="Path to a scenario JSON file."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a deterministic shielding scenario."
    )
    configure_parser(parser)
    return run(parser.parse_args(argv))


def run(arguments: argparse.Namespace) -> int:

    scenario_path = arguments.scenario_path

    try:
        scenario = load_scenario(scenario_path)

        result = run_scenario(scenario)

        print_result_summary(
            scenario_path=scenario_path,
            scenario=scenario,
            result=result,
        )

    except (
        FileNotFoundError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        print(
            f"Scenario execution failed: {error}",
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
