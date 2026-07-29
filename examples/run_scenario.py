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


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "src"
)


# The project currently uses standalone modules inside src rather than an
# installed Python package.
if str(
    SOURCE_DIRECTORY
) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from design_optimizer import (
    AirKermaMaterialDesignCandidate,
    MaterialDesignCandidate,
)
from fixed_shield_models import (
    FixedShieldDeterministicResult,
)
from optimization_models import (
    OptimizedDesignResult,
)
from scenario_io import (
    load_scenario,
)
from scenario_models import (
    ShieldingScenario,
    TargetSpec,
)
from scenario_runner import (
    run_scenario,
)
from target_models import (
    AirKermaRateTarget,
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
)


DEFAULT_SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_air_kerma_reference.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load and run a reproducible shielding scenario."
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
            "collision-air-kerma optimization case."
        ),
    )

    return parser.parse_args()


def require_result_value(
    value: float | None,
    description: str,
) -> float:
    # Convert an optional result field into a required value for a selected
    # optimization design.

    if value is None:
        raise ValueError(
            "Selected scenario design is missing "
            f"{description}."
        )

    return value


def describe_target(
    target: TargetSpec | None,
) -> str:
    # Create a readable description for an optional fixed-shield target.

    if target is None:
        return (
            "None "
            "(response calculation only)"
        )

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        return (
            "Collision air-kerma rate <= "
            f"{target.target_air_kerma_rate_microgy_per_h:.6g} "
            "µGy/h"
        )

    if isinstance(
        target,
        FluxTarget,
    ):
        return (
            "Photon fluence rate <= "
            f"{target.target_flux:.6g} "
            "photons/cm^2/s"
        )

    if isinstance(
        target,
        ReductionFactorTarget,
    ):
        return (
            "Reduction factor >= "
            f"{target.reduction_factor:.6g}"
        )

    if isinstance(
        target,
        TransmissionTarget,
    ):
        return (
            "Transmission <= "
            f"{target.target_transmission:.6g}"
        )

    raise ValueError(
        "Unsupported scenario target type."
    )


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

    if len(
        failed_candidates
    ) == 0:
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


def print_optimization_result_summary(
    scenario_path: Path,
    scenario: ShieldingScenario,
    result: OptimizedDesignResult,
) -> None:
    print()
    print("=" * 72)
    print("SHIELDING OPTIMIZATION SCENARIO RESULT")
    print("=" * 72)

    print(
        "Scenario file: "
        f"{scenario_path.resolve()}"
    )

    print(
        "Scenario ID:   "
        f"{scenario.scenario_id}"
    )

    print(
        "Description:   "
        f"{scenario.description}"
    )

    print(
        "Mode:          "
        f"{scenario.calculation_mode}"
    )

    print(
        "Objective:     "
        f"{scenario.optimization_mode}"
    )

    print(
        "Target:        "
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

    if len(
        result.warnings
    ) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    print("=" * 72)
    print()


def print_fixed_shield_result_summary(
    scenario_path: Path,
    scenario: ShieldingScenario,
    result: FixedShieldDeterministicResult,
) -> None:
    # Print a traceable deterministic response for one completed shield.
    #
    # The current result is evaluated at the point radius stored in the
    # scenario. The matched shell-volume-average result is added by the next
    # V1.13 benchmark layer.

    geometry = result.geometry

    print()
    print("=" * 72)
    print("FIXED-SHIELD DETERMINISTIC SCENARIO RESULT")
    print("=" * 72)

    print(
        "Scenario file: "
        f"{scenario_path.resolve()}"
    )

    print(
        "Scenario ID:   "
        f"{scenario.scenario_id}"
    )

    print(
        "Description:   "
        f"{scenario.description}"
    )

    print(
        "Mode:          "
        f"{scenario.calculation_mode}"
    )

    print(
        "Target:        "
        f"{describe_target(scenario.target)}"
    )

    print(
        "Source:        "
        f"{result.source_name}"
    )

    if result.activity_bq is None:
        print(
            "Activity:      "
            "Not applicable"
        )

    else:
        print(
            "Activity:      "
            f"{result.activity_bq:.6e} Bq"
        )

    print("-" * 72)
    print("Geometry:")

    print(
        "Source cavity radius: "
        f"{geometry.source_cavity_radius_cm:.6f} cm"
    )

    print(
        "Outer shield radius:  "
        f"{geometry.outer_shield_radius_cm:.6f} cm"
    )

    print(
        "Evaluation radius:    "
        f"{geometry.evaluation_radius_cm:.6f} cm"
    )

    print(
        "Total shield thickness: "
        f"{geometry.total_shield_thickness_cm:.6f} cm"
    )

    shells = geometry.create_shells()

    for shell, layer in zip(
        shells,
        result.layers,
        strict=True,
    ):
        print(
            f"Layer {shell.layer_index + 1}: "
            f"{layer.material.name} | "
            f"{shell.inner_radius_cm:.6f} to "
            f"{shell.outer_radius_cm:.6f} cm | "
            f"thickness {layer.thickness:.6f} cm"
        )

    print("-" * 72)
    print("Photon-line results:")

    for line_index, line_result in enumerate(
        result.line_results,
        start=1,
    ):
        shielding_result = (
            line_result.shielding_result
        )

        air_kerma_result = (
            line_result.air_kerma_result
        )

        uncollided_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                air_kerma_result
                .uncollided_collision_air_kerma_rate_gy_per_s
            )
        )

        print(
            f"Line {line_index}:"
        )

        print(
            "  Energy: "
            f"{line_result.photon_line.energy:.6f} MeV"
        )

        print(
            "  Emission intensity: "
            f"{line_result.photon_line.intensity:.6f} "
            "photons/decay"
        )

        print(
            "  Photon rate: "
            f"{line_result.photon_rate_per_s:.6e} photons/s"
        )

        print(
            "  Optical thickness: "
            f"{shielding_result.total_mfp:.6f} MFP"
        )

        print(
            "  Narrow-beam transmission: "
            f"{shielding_result.total_transmission:.6e}"
        )

        print(
            "  Point uncollided fluence rate: "
            f"{shielding_result.uncollided_flux:.6e} "
            "photons/cm^2/s"
        )

        print(
            "  Point uncollided collision air kerma: "
            f"{air_kerma_result.uncollided_collision_air_kerma_rate_gy_per_s:.6e} "
            "Gy/s"
        )

        print(
            "  Point uncollided collision air kerma: "
            f"{uncollided_microgy_per_h:.6e} µGy/h"
        )

        print(
            "  Buildup status: "
            f"{air_kerma_result.buildup_status}"
        )

        if (
            air_kerma_result.buildup_factor
            is not None
        ):
            print(
                "  G-P exposure buildup factor: "
                f"{air_kerma_result.buildup_factor:.6f}"
            )

        adjusted_response = (
            air_kerma_result
            .buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_response is not None:
            adjusted_microgy_per_h = (
                convert_gy_per_s_to_microgy_per_h(
                    adjusted_response
                )
            )

            print(
                "  Point G-P-adjusted collision air kerma: "
                f"{adjusted_response:.6e} Gy/s"
            )

            print(
                "  Point G-P-adjusted collision air kerma: "
                f"{adjusted_microgy_per_h:.6e} µGy/h"
            )

    total_uncollided_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        )
    )

    print("-" * 72)
    print("Source totals:")

    print(
        "Total point uncollided photon fluence rate: "
        f"{result.total_uncollided_photon_fluence_rate_per_cm2_s:.6e} "
        "photons/cm^2/s"
    )

    print(
        "Total point uncollided collision air kerma: "
        f"{result.total_uncollided_collision_air_kerma_rate_gy_per_s:.6e} "
        "Gy/s"
    )

    print(
        "Total point uncollided collision air kerma: "
        f"{total_uncollided_microgy_per_h:.6e} µGy/h"
    )

    print(
        "G-P exposure buildup requested: "
        f"{'Yes' if result.buildup_requested else 'No'}"
    )

    print(
        "Source buildup status: "
        f"{result.buildup_status}"
    )

    adjusted_total = (
        result
        .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    if adjusted_total is not None:
        adjusted_total_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                adjusted_total
            )
        )

        print(
            "Total point G-P-adjusted collision air kerma: "
            f"{adjusted_total:.6e} Gy/s"
        )

        print(
            "Total point G-P-adjusted collision air kerma: "
            f"{adjusted_total_microgy_per_h:.6e} µGy/h"
        )

    if len(
        result.warnings
    ) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    print("-" * 72)

    print(
        "Spatial response basis: "
        "Point response at the scenario evaluation radius."
    )

    print(
        "Matched OpenMC comparison basis: "
        "A shell-volume-average response will be added "
        "by the V1.13 benchmark comparison layer."
    )

    print("=" * 72)
    print()


def print_result_summary(
    scenario_path: Path,
    scenario: ShieldingScenario,
    result,
) -> None:
    # Route each result type into its compatible output formatter.

    if isinstance(
        result,
        OptimizedDesignResult,
    ):
        print_optimization_result_summary(
            scenario_path=scenario_path,
            scenario=scenario,
            result=result,
        )

        return

    if isinstance(
        result,
        FixedShieldDeterministicResult,
    ):
        print_fixed_shield_result_summary(
            scenario_path=scenario_path,
            scenario=scenario,
            result=result,
        )

        return

    raise ValueError(
        "Unsupported scenario result type."
    )


def main() -> int:
    arguments = parse_arguments()

    scenario_path = (
        arguments.scenario_path
    )

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