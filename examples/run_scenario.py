# Run a reproducible shielding scenario from JSON.
#
# Usage from the repository root:
#
#   python examples/run_scenario.py
#
# A different scenario file can be supplied as an optional argument:
#
#   python examples/run_scenario.py scenarios/example.json


from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

# The current project uses standalone modules inside src rather than an
# installed Python package. Add src to the import path for this example.
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from scenario_io import load_scenario
from scenario_runner import run_scenario


DEFAULT_SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_v110_reference.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load and run a reproducible shielding "
            "optimization scenario."
        )
    )

    parser.add_argument(
        "scenario_path",
        nargs="?",
        type=Path,
        default=DEFAULT_SCENARIO_PATH,
        help=(
            "Path to a scenario JSON file. "
            "Defaults to the official V1.10 reference case."
        ),
    )

    return parser.parse_args()


def print_result_summary(
    scenario_path: Path,
    scenario,
    result,
) -> None:
    print()
    print("=" * 72)
    print("SHIELDING SCENARIO RESULT")
    print("=" * 72)

    print(f"Scenario file: {scenario_path.resolve()}")
    print(f"Scenario ID:   {scenario.scenario_id}")
    print(f"Description:   {scenario.description}")
    print(f"Mode:          {scenario.calculation_mode}")
    print(f"Objective:     {scenario.optimization_mode}")
    print(
        "Candidates:    "
        f"{len(result.all_candidates)}"
    )

    print("-" * 72)

    best_candidate = result.best_candidate

    if best_candidate is None:
        print("Selected design: None")
        print(
            "No candidate satisfied all active "
            "engineering constraints."
        )

    else:
        material = (
            best_candidate
            .base_candidate
            .material
        )

        print(
            "Selected material: "
            f"{material.name}"
        )

        print(
            "Material key:      "
            f"{material.key}"
        )

        print(
            "Required thickness: "
            f"{best_candidate.base_candidate.required_thickness:.6f} cm"
        )

        print(
            "Mass per area:      "
            f"{best_candidate.mass_per_area_g_per_cm2:.6f} g/cm²"
        )

        print(
            "Selection reason:   "
            f"{result.selection_reason}"
        )

    if len(result.warnings) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(f"- {warning}")

    print("=" * 72)
    print()


def main() -> int:
    arguments = parse_arguments()
    scenario_path = arguments.scenario_path

    try:
        scenario = load_scenario(
            scenario_path
        )

        result = run_scenario(
            scenario
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

    print_result_summary(
        scenario_path=scenario_path,
        scenario=scenario,
        result=result,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())