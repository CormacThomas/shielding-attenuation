"""Render deterministic scenario results for the terminal."""

from pathlib import Path

from shielding.design.comparison import (
    AirKermaMaterialDesignCandidate,
    MaterialDesignCandidate,
)
from shielding.design.models import (
    OptimizedDesignResult,
)
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from shielding.physics.units import (
    convert_gy_per_s_to_microgy_per_h,
)
from shielding.scenarios.fixed_shield_models import (
    FixedShieldDeterministicResult,
)
from shielding.scenarios.models import (
    ShieldingScenario,
    TargetSpec,
)


def require_result_value(
    value: float | None,
    description: str,
) -> float:
    # Convert an optional result field into a required value for a selected
    # optimization design.

    if value is None:
        raise ValueError(f"Selected scenario design is missing {description}.")

    return value


def describe_target(
    target: TargetSpec | None,
) -> str:
    # Create a readable description for an optional fixed-shield target.

    if target is None:
        return "None (response calculation only)"

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
        return f"Photon fluence rate <= {target.target_flux:.6g} photons/cm^2/s"

    if isinstance(
        target,
        ReductionFactorTarget,
    ):
        return f"Reduction factor >= {target.reduction_factor:.6g}"

    if isinstance(
        target,
        TransmissionTarget,
    ):
        return f"Transmission <= {target.target_transmission:.6g}"

    raise ValueError("Unsupported scenario target type.")


def print_air_kerma_selected_response(
    candidate: AirKermaMaterialDesignCandidate,
    result: OptimizedDesignResult,
) -> None:
    final_rate = require_result_value(
        candidate.final_air_kerma_rate_microgy_per_h,
        "its final collision air-kerma rate",
    )

    response_ratio = require_result_value(
        candidate.final_response_ratio,
        "its final response ratio",
    )

    if result.apply_buildup:
        response_label = (
            "Selected final G-P exposure-buildup-adjusted collision air-kerma rate"
        )

    else:
        response_label = "Selected final uncollided collision air-kerma rate"

    print(f"{response_label}: {final_rate:.6e} µGy/h")

    print(f"Selected response ratio: {response_ratio:.6e}")

    print(f"Selected buildup used: {'Yes' if candidate.buildup_used else 'No'}")


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

    print(
        "Selected final uncollided photon fluence rate: "
        f"{final_value:.6e} photons/cm^2/s"
    )
    print("Selected response basis: Uncollided photon fluence rate")

    print(f"Selected response ratio: {response_ratio:.6e}")


def print_failed_candidates(
    result: OptimizedDesignResult,
) -> None:
    failed_candidates = result.failed_candidates()

    if len(failed_candidates) == 0:
        return

    print("-" * 72)
    print("Failed candidates:")

    for candidate in failed_candidates:
        base_candidate = candidate.base_candidate

        failure_reason = base_candidate.failure_reason

        if failure_reason is None or failure_reason.strip() == "":
            failure_reason = "No failure reason was recorded."

        print(f"- {base_candidate.material.name}: {failure_reason}")


def print_optimization_result_summary(
    scenario_path: Path,
    scenario: ShieldingScenario,
    result: OptimizedDesignResult,
) -> None:
    print()
    print("=" * 72)
    print("SHIELDING OPTIMIZATION SCENARIO RESULT")
    print("=" * 72)

    print(f"Scenario file: {scenario_path.resolve()}")

    print(f"Scenario ID:   {scenario.scenario_id}")

    print(f"Description:   {scenario.description}")

    print(f"Mode:          {scenario.calculation_mode}")

    print(f"Objective:     {scenario.optimization_mode}")

    print(f"Target:        {result.target_description}")

    print(f"G-P exposure buildup requested: {'Yes' if result.apply_buildup else 'No'}")

    print(f"Candidates:    {len(result.all_candidates)}")

    print(f"Eligible:      {len(result.eligible_candidates())}")

    print(f"Rejected:      {len(result.rejected_candidates())}")

    print(f"Failed:        {len(result.failed_candidates())}")

    print("-" * 72)

    best_candidate = result.best_candidate

    if best_candidate is None:
        print("Selected design: None")

        print("No candidate satisfied all active engineering constraints.")

    else:
        base_candidate = best_candidate.base_candidate

        material = base_candidate.material

        required_thickness = require_result_value(
            base_candidate.required_thickness,
            "its required thickness",
        )

        mass_per_area = require_result_value(
            best_candidate.mass_per_area_g_per_cm2,
            "its mass per area",
        )

        print(f"Selected material: {material.name}")

        print(f"Material key:      {material.key}")

        print(f"Required thickness: {required_thickness:.6f} cm")

        print(f"Mass per area:      {mass_per_area:.6f} g/cm^2")

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
            print_photon_selected_response(base_candidate)

        else:
            raise ValueError("Unsupported selected scenario candidate type.")

        print(f"Selection reason:   {result.selection_reason}")

    print_failed_candidates(result)

    if len(result.warnings) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(f"- {warning}")

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

    print(f"Scenario file: {scenario_path.resolve()}")

    print(f"Scenario ID:   {scenario.scenario_id}")

    print(f"Description:   {scenario.description}")

    print(f"Mode:          {scenario.calculation_mode}")

    print(f"Target:        {describe_target(scenario.target)}")

    print(f"Source:        {result.source_name}")

    if result.activity_bq is None:
        print("Activity:      Not applicable")

    else:
        print(f"Activity:      {result.activity_bq:.6e} Bq")

    print("-" * 72)
    print("Geometry:")

    print(f"Source cavity radius: {geometry.source_cavity_radius_cm:.6f} cm")

    print(f"Outer shield radius:  {geometry.outer_shield_radius_cm:.6f} cm")

    print(f"Evaluation radius:    {geometry.evaluation_radius_cm:.6f} cm")

    print(f"Total shield thickness: {geometry.total_shield_thickness_cm:.6f} cm")

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
        shielding_result = line_result.shielding_result

        air_kerma_result = line_result.air_kerma_result

        uncollided_microgy_per_h = convert_gy_per_s_to_microgy_per_h(
            air_kerma_result.uncollided_collision_air_kerma_rate_gy_per_s
        )

        print(f"Line {line_index}:")

        print(f"  Energy: {line_result.photon_line.energy:.6f} MeV")

        print(
            "  Emission intensity: "
            f"{line_result.photon_line.intensity:.6f} "
            "photons/decay"
        )

        print(f"  Photon rate: {line_result.photon_rate_per_s:.6e} photons/s")

        print(f"  Optical thickness: {shielding_result.total_mfp:.6f} MFP")

        print(f"  Narrow-beam transmission: {shielding_result.total_transmission:.6e}")

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

        print(f"  Buildup status: {air_kerma_result.buildup_status}")

        if air_kerma_result.buildup_factor is not None:
            print(
                f"  G-P exposure buildup factor: {air_kerma_result.buildup_factor:.6f}"
            )

        adjusted_response = (
            air_kerma_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_response is not None:
            adjusted_microgy_per_h = convert_gy_per_s_to_microgy_per_h(
                adjusted_response
            )

            print(
                "  Point G-P-adjusted collision air kerma: "
                f"{adjusted_response:.6e} Gy/s"
            )

            print(
                "  Point G-P-adjusted collision air kerma: "
                f"{adjusted_microgy_per_h:.6e} µGy/h"
            )

    total_uncollided_microgy_per_h = convert_gy_per_s_to_microgy_per_h(
        result.total_uncollided_collision_air_kerma_rate_gy_per_s
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
        f"G-P exposure buildup requested: {'Yes' if result.buildup_requested else 'No'}"
    )

    print(f"Source buildup status: {result.buildup_status}")

    adjusted_total = result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s

    if adjusted_total is not None:
        adjusted_total_microgy_per_h = convert_gy_per_s_to_microgy_per_h(adjusted_total)

        print(
            f"Total point G-P-adjusted collision air kerma: {adjusted_total:.6e} Gy/s"
        )

        print(
            "Total point G-P-adjusted collision air kerma: "
            f"{adjusted_total_microgy_per_h:.6e} µGy/h"
        )

    if len(result.warnings) > 0:
        print("-" * 72)
        print("Warnings:")

        for warning in result.warnings:
            print(f"- {warning}")

    print("-" * 72)

    print("Spatial response basis: Point response at the scenario evaluation radius.")

    print(
        "Matched OpenMC comparison basis: "
        "The benchmark command compares shell-volume-averaged responses."
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

    raise ValueError("Unsupported scenario result type.")
