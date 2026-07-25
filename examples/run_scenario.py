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

# The project currently uses standalone modules inside src rather
# than an installed Python package.
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from design_optimizer import (
    AirKermaMaterialDesignCandidate,
    MaterialDesignCandidate,
)
from optimization_models import (
    OptimizedDesignResult,
)
from scenario_io import load_scenario
from scenario_models import ShieldingScenario
from scenario_runner import run_scenario


DEFAULT_SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_air_kerma_reference.json"
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
            "Defaults to the official V1.12 "
            "collision-air-kerma reference case."
        ),
    )

    return parser.parse_args()


def require_result_value(
    value: float | None,
    description: str,
) -> float:
    # Convert an optional result field into a required value for
    # a selected design.

    if value is None:
        raise ValueError(
            "Selected scenario design is missing "
            f"{description}."
        )

    return value


def print_air_kerma_selected_response(
    candidate: AirKermaMaterialDesignCandidate,
    result: OptimizedDesignResult,
) -> None:
    final_rate = require_result_value(
        candidate
        .final_air_kerma_rate_microgy_per_h,
        "its final collision air-kerma rate",
    )

    response_ratio = require_result_value(
        candidate.final_response_ratio,
        "its final response ratio",
    )

    if result.apply_buildup:
        response_label = (
            "Selected final G-P exposure-buildup-adjusted "
            "collision air-kerma rate"
        )

    else:
        response_label = (
            "Selected final uncollided collision "
            "air-kerma rate"
        )

    print(
        f"{response_label}: "
        f"{final_rate:.6e} µGy/h"
    )

    print(
        "Selected response ratio: "
        f"{response_ratio:.6e}"
    )

    print(
        "Selected buildup used: "
        f"{'Yes' if candidate.buildup_used else 'No'}"
    )


def print_photon_selected_response(
    candidate: MaterialDesignCandidate,
) -> None:
    final_value = require_result_value(
        candidate.final_flux,
        "its final photon-response value",
    )

    response_ratio = require_result_value(
        candidate.final_transmission,
        "its final response ratio",
    )

    if candidate.buildup_used:
        print(
            "Selected final legacy G-P "
            "exposure-buildup-adjusted "
            "photon-response proxy: "
            f"{final_value:.6e}"
        )

        print(
            "Selected response basis: "
            "Historical exposure-buildup proxy"
        )

    else:
        print(
            "Selected final uncollided photon "
            "fluence rate: "
            f"{final_value:.6e} photons/cm^2/s"
        )

        print(
            "Selected response basis: "
            "Uncollided photon fluence rate"
        )

    print(
        "Selected response ratio: "
        f"{response_ratio:.6e}"
    )


def print_failed_candidates(
    result: OptimizedDesignResult,
) -> None:
    failed_candidates = (
        result.failed_candidates()
    )

    if len(failed_candidates) == 0:
        return

    print("-" * 72)
    print("Failed candidates:")

    for candidate in failed_candidates:
        base_candidate = (
            candidate.base_candidate
        )

        failure_reason = (
            base_candidate.failure_reason
        )

        if (
            failure_reason is None
            or failure_reason.strip() == ""
        ):
            failure_reason = (
                "No failure reason was recorded."
            )

        print(
            f"- {base_candidate.material.name}: "
            f"{failure_reason}"
        )


def print_result_summary(
    scenario_path: Path,
    scenario: ShieldingScenario,
    result: OptimizedDesignResult,
) -> None:
    print()
    print("=" * 72)
    print("SHIELDING SCENARIO RESULT")
    print("=" * 72)

    print(
        f"Scenario file: "
        f"{scenario_path.resolve()}"
    )

    print(
        f"Scenario ID:   "
        f"{scenario.scenario_id}"
    )

    print(
        f"Description:   "
        f"{scenario.description}"
    )

    print(
        f"Mode:          "
        f"{scenario.calculation_mode}"
    )

    print(
        f"Objective:     "
        f"{scenario.optimization_mode}"
    )

    print(
        f"Target:        "
        f"{result.target_description}"
    )

    print(
        "G-P exposure buildup requested: "
        f"{'Yes' if result.apply_buildup else 'No'}"
    )

    print(
        "Candidates:    "
        f"{len(result.all_candidates)}"
    )

    print(
        "Eligible:      "
        f"{len(result.eligible_candidates())}"
    )

    print(
        "Rejected:      "
        f"{len(result.rejected_candidates())}"
    )

    print(
        "Failed:        "
        f"{len(result.failed_candidates())}"
    )

    print("-" * 72)

    best_candidate = result.best_candidate

    if best_candidate is None:
        print(
            "Selected design: None"
        )

        print(
            "No candidate satisfied all active "
            "engineering constraints."
        )

    else:
        base_candidate = (
            best_candidate.base_candidate
        )

        material = (
            base_candidate.material
        )

        required_thickness = (
            require_result_value(
                base_candidate
                .required_thickness,
                "its required thickness",
            )
        )

        mass_per_area = (
            require_result_value(
                best_candidate
                .mass_per_area_g_per_cm2,
                "its mass per area",
            )
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
            f"{required_thickness:.6f} cm"
        )

        print(
            "Mass per area:      "
            f"{mass_per_area:.6f} g/cm^2"
        )

        if isinstance(
            base_candidate,
            AirKermaMaterialDesignCandidate,
        ):
            print_air_kerma_selected_response(
                candidate=base_candidate,
                result=result,
            )

        elif isinstance(
            base_candidate,
            MaterialDesignCandidate,
        ):
            print_photon_selected_response(
                base_candidate
            )

        else:
            raise ValueError(
                "Unsupported selected scenario "
                "candidate type."
            )

        print(
            "Selection reason:   "
            f"{result.selection_reason}"
        )

    print_failed_candidates(
        result
    )

    if len(result.warnings) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

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
    raise SystemExit(
        main()
    )