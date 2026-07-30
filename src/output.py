# Output formatting utilities.
#
# This module keeps printing/reporting logic separate from physics calculations.
# The calculation modules should return result objects. This file decides how
# those results are displayed to the user in the command-line interface.
#
# Keeping output separate makes the code easier to upgrade later when adding
# plotting, saved reports, scenario files, or a graphical interface.


from target_models import (
    AirKermaMinimumThicknessResult,
    MinimumThicknessResult,
)
from models import ShieldingResult
from source_models import SourceCalculationResult
from design_optimizer import (
    AirKermaMaterialComparisonResult,
    MaterialComparisonResult,
    AirKermaMaterialDesignCandidate,
)
from optimization_models import (
    OptimizationBaseCandidate,
    OptimizedDesignResult,
    OptimizedMaterialCandidate,
)
from air_response_models import (
    SourceAirKermaResult,
)

from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
)


def print_results(
    result: ShieldingResult,
) -> None:
    # Print one low-level uncollided photon attenuation
    # result.

    print(
        "Calculation mode: Narrow-beam uncollided "
        "photon fluence rate\n"
    )

    print(
        f"Photon energy: "
        f"{result.photon_energy} MeV"
    )

    print(
        f"Source strength: "
        f"{result.source_strength:.3e} photons/s"
    )

    print(
        f"Detector distance: "
        f"{result.detector_distance} cm"
    )

    print(
        f"Number of layers: "
        f"{len(result.layers)}"
    )

    print(
        f"Total thickness: "
        f"{result.total_thickness} cm"
    )

    print(
        f"Total MFP: "
        f"{result.total_mfp}"
    )

    print(
        f"Total transmission: "
        f"{result.total_transmission}"
    )

    print(
        "Uncollided photon fluence rate at detector: "
        f"{result.uncollided_flux:.6e} "
        "photons/cm^2/s"
    )

    print("\nLayers:")

    for layer_result in result.layer_results:
        print(
            f"\nMaterial: "
            f"{layer_result.layer.material.name}"
        )

        print(
            f"Thickness: "
            f"{layer_result.layer.thickness} cm"
        )

        print(
            f"Density: "
            f"{layer_result.layer.material.density} "
            "g/cm^3"
        )

        print(
            f"mu/rho: "
            f"{layer_result.mu_over_p} cm^2/g"
        )

        print(
            f"mu: "
            f"{layer_result.mu} 1/cm"
        )

        print(
            f"Layer MFP: "
            f"{layer_result.mfp}"
        )

        print(
            f"Layer transmission: "
            f"{layer_result.transmission}"
        )


def print_source_results(
    result: SourceCalculationResult,
) -> None:
    # Print an uncollided manual or isotope
    # photon-fluence result.

    print(
        "\nUncollided photon fluence-rate result"
    )

    print(
        f"Source: "
        f"{result.source_name}"
    )

    if result.activity_bq is not None:
        print(
            f"Activity: "
            f"{result.activity_bq:.6e} Bq"
        )

    print(
        f"Number of photon lines: "
        f"{len(result.line_results)}"
    )

    print(
        "Total uncollided photon fluence rate: "
        f"{result.total_uncollided_flux:.6e} "
        "photons/cm^2/s"
    )

    print("\nPhoton-line results:")

    for line_index, line_result in enumerate(
        result.line_results,
        start=1,
    ):
        shielding_result = (
            line_result.shielding_result
        )

        print(
            f"\nLine {line_index}"
        )

        print(
            f"Photon energy: "
            f"{line_result.photon_line.energy} MeV"
        )

        if result.activity_bq is not None:
            print(
                "Emission intensity: "
                f"{line_result.photon_line.intensity} "
                "photons/decay"
            )

        print(
            f"Photon emission rate: "
            f"{line_result.photon_rate:.6e} "
            "photons/s"
        )

        print(
            f"Transmission: "
            f"{shielding_result.total_transmission}"
        )

        print(
            f"Total MFP: "
            f"{shielding_result.total_mfp}"
        )

        print(
            "Uncollided photon fluence rate: "
            f"{shielding_result.uncollided_flux:.6e} "
            "photons/cm^2/s"
        )


def print_source_air_kerma_result(
    result: SourceAirKermaResult,
) -> None:
    # Print an explicit collision-air-kerma response result.
    #
    # This output intentionally distinguishes:
    #   - photon fluence rate
    #   - energy fluence rate
    #   - uncollided collision air-kerma rate
    #   - G-P buildup-adjusted collision air-kerma rate
    #
    # No air-kerma quantity is labeled as a generic photon flux.

    print("\nCollision air-kerma response result")
    print(f"Source: {result.source_name}")

    if result.activity_bq is not None:
        print(
            f"Activity: "
            f"{result.activity_bq:.6e} Bq"
        )

    print(
        f"Number of photon lines: "
        f"{len(result.line_results)}"
    )

    print(
        "Total uncollided photon fluence rate: "
        f"{result.total_uncollided_photon_fluence_rate_per_cm2_s:.6e} "
        "photons/cm^2/s"
    )

    total_uncollided_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        )
    )

    print(
        "Total uncollided collision air-kerma rate: "
        f"{total_uncollided_microgy_per_h:.6e} µGy/h"
    )

    print(
        "Total uncollided collision air-kerma rate "
        f"(internal): "
        f"{result.total_uncollided_collision_air_kerma_rate_gy_per_s:.6e} "
        "Gy/s"
    )

    print(
        f"Buildup status: "
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
            "Total G-P buildup-adjusted collision "
            "air-kerma rate: "
            f"{adjusted_total_microgy_per_h:.6e} µGy/h"
        )

        print(
            "Total G-P buildup-adjusted collision "
            "air-kerma rate (internal): "
            f"{adjusted_total:.6e} Gy/s"
        )

    if len(result.warnings) > 0:
        print("\nWarnings:")

        for warning in result.warnings:
            print(f"- {warning}")

    print("\nPhoton-line contributions:")

    for line_index, line_result in enumerate(
        result.line_results,
        start=1,
    ):
        line_uncollided_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                line_result
                .uncollided_collision_air_kerma_rate_gy_per_s
            )
        )

        print(f"\nLine {line_index}")
        print(
            f"Photon energy: "
            f"{line_result.photon_energy_mev:.8g} MeV"
        )

        print(
            f"Emission intensity: "
            f"{line_result.emission_intensity:.8g}"
        )

        print(
            f"Photon emission rate: "
            f"{line_result.photon_rate_per_s:.6e} photons/s"
        )

        print(
            "Uncollided photon fluence rate: "
            f"{line_result.uncollided_photon_fluence_rate_per_cm2_s:.6e} "
            "photons/cm^2/s"
        )

        print(
            "Energy fluence rate: "
            f"{line_result.energy_fluence_rate_mev_per_cm2_s:.6e} "
            "MeV/cm^2/s"
        )

        print(
            "Dry-air mu_en/rho: "
            f"{line_result.air_mu_en_over_rho_cm2_per_g:.6e} "
            "cm^2/g"
        )

        print(
            "Uncollided collision air-kerma rate: "
            f"{line_uncollided_microgy_per_h:.6e} µGy/h"
        )

        print(
            f"Buildup status: "
            f"{line_result.buildup_status}"
        )

        if line_result.buildup_factor is not None:
            print(
                f"G-P exposure buildup factor: "
                f"{line_result.buildup_factor:.6g}"
            )

        line_adjusted_rate = (
            line_result
            .buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if line_adjusted_rate is not None:
            line_adjusted_microgy_per_h = (
                convert_gy_per_s_to_microgy_per_h(
                    line_adjusted_rate
                )
            )

            print(
                "G-P buildup-adjusted collision "
                "air-kerma rate: "
                f"{line_adjusted_microgy_per_h:.6e} µGy/h"
            )

        print(
            f"Calculation method: "
            f"{line_result.calculation_method}"
        )

        print(
            f"Coefficient source: "
            f"{line_result.coefficient_source}"
        )

        if len(line_result.warnings) > 0:
            print("Line warnings:")

            for warning in line_result.warnings:
                print(f"- {warning}")


def print_minimum_thickness_result(
    result: MinimumThicknessResult,
) -> None:
    # Print an uncollided photon-fluence
    # minimum-thickness result.

    print(
        "\nPhoton-fluence minimum shielding "
        "thickness result"
    )

    print(
        f"Calculation mode: "
        f"{result.calculation_mode}"
    )

    print(
        f"Material: "
        f"{result.material.name}"
    )

    print(
        f"Target: "
        f"{result.target_description}"
    )

    print(
        f"Required thickness: "
        f"{result.required_thickness:.6g} cm"
    )

    print(
        "Final uncollided response ratio: "
        f"{result.final_transmission:.6e}"
    )

    print(
        "Final target-comparison uncollided "
        "photon fluence rate: "
        f"{result.final_flux:.6e} "
        "photons/cm^2/s"
    )

    if len(result.warnings) > 0:
        print("\nWarnings:")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )


def print_air_kerma_minimum_thickness_result(
    result: AirKermaMinimumThicknessResult,
) -> None:
    # Print the complete result of an explicit collision-air-kerma
    # minimum-thickness design.

    print(
        "\nAir-kerma minimum shielding thickness result"
    )

    print(
        f"Calculation mode: "
        f"{result.calculation_mode}"
    )

    print(
        f"Material: "
        f"{result.material.name}"
    )

    print(
        f"Target: "
        f"{result.target_description}"
    )

    print(
        f"Required thickness: "
        f"{result.required_thickness:.6g} cm"
    )

    print(
        "Final target-comparison collision "
        "air-kerma rate: "
        f"{result.final_air_kerma_rate_microgy_per_h:.6e} "
        "µGy/h"
    )

    uncollided_rate_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .final_uncollided_collision_air_kerma_rate_gy_per_s
        )
    )

    print(
        "Final uncollided collision air-kerma rate: "
        f"{uncollided_rate_microgy_per_h:.6e} µGy/h"
    )

    adjusted_rate = (
        result
        .final_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    if adjusted_rate is not None:
        adjusted_rate_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                adjusted_rate
            )
        )

        print(
            "Final G-P buildup-adjusted collision "
            "air-kerma rate: "
            f"{adjusted_rate_microgy_per_h:.6e} µGy/h"
        )

    print(
        f"Final selected-response ratio: "
        f"{result.final_response_ratio:.6e}"
    )

    buildup_text = (
        "Yes"
        if result.buildup_used
        else "No"
    )

    print(
        f"Buildup used: "
        f"{buildup_text}"
    )

    if len(result.warnings) > 0:
        print("\nDesign warnings:")

        for warning in result.warnings:
            print(f"- {warning}")

    print("\nFinal detailed source response:")

    print_source_air_kerma_result(
        result.final_source_response
    )


def get_buildup_display_for_candidate(
    candidate: OptimizationBaseCandidate,
) -> str:
    # Air-kerma candidates use strict, response-specific buildup
    # semantics.
    #
    # PASS air-kerma candidate:
    #   Yes -> G-P exposure buildup was applied.
    #   No  -> an explicitly uncollided response was requested.
    #
    # FAILED air-kerma candidate:
    #   Unavailable -> the requested response could not be calculated.
    #
    # Legacy photon candidates retain their historical fallback
    # display for regression compatibility.

    if candidate.status == "FAILED":
        if isinstance(
            candidate,
            AirKermaMaterialDesignCandidate,
        ):
            return "Unavailable"

        return "--"

    if isinstance(
        candidate,
        AirKermaMaterialDesignCandidate,
    ):
        if candidate.buildup_used:
            return "Yes"

        return "No"

    if candidate.buildup_used:
        return "Yes"

    if len(candidate.warnings) > 0:
        return "Fallback"

    return "No"



def format_optional_float(value: float | None, precision: str = ".6g") -> str:
    # Format optional numerical values for tables.
    # Failed candidates may not have thickness or flux values, so None becomes "--".
    if value is None:
        return "--"

    return format(value, precision)


def print_material_comparison_result(
    result: MaterialComparisonResult,
) -> None:
    # Print a legacy-compatible photon-response material comparison.
    #
    # Uncollided candidates are reported as photon fluence rates.
    # Historical buildup-adjusted candidates are identified as
    # response proxies through the Response Basis column.

    print(
        "\nPhoton-response material comparison result"
    )

    print(
        "Calculation mode: Single-material "
        "photon-response design comparison"
    )

    print(
        f"Target: "
        f"{result.target_description}"
    )

    buildup_requested_text = (
        "Yes"
        if result.apply_buildup
        else "No"
    )

    print(
        "Legacy G-P exposure buildup requested: "
        f"{buildup_requested_text}"
    )

    final_value_header = (
        "Final Value"
        if result.apply_buildup
        else "Final Fluence Rate"
    )

    print("\nCandidates:")

    print(
        f"{'Material':<28}"
        f"{'Thickness (cm)':<18}"
        f"{final_value_header:<22}"
        f"{'Response Basis':<22}"
        f"{'Status':<10}"
    )

    print("-" * 100)

    any_legacy_proxy = False

    for candidate in result.candidates:
        if candidate.status == "PASS":
            thickness_text = (
                format_optional_float(
                    candidate.required_thickness
                )
            )

            final_value_text = (
                format_optional_float(
                    candidate.final_flux,
                    ".6e",
                )
            )

            if candidate.buildup_used:
                response_basis = (
                    "Legacy G-P proxy"
                )

                any_legacy_proxy = True

            else:
                response_basis = (
                    "Uncollided fluence"
                )

        else:
            thickness_text = "--"
            final_value_text = "--"
            response_basis = "--"

        print(
            f"{candidate.material.name:<28}"
            f"{thickness_text:<18}"
            f"{final_value_text:<22}"
            f"{response_basis:<22}"
            f"{candidate.status:<10}"
        )

    print(
        "\nUncollided fluence units: photons/cm^2/s"
    )

    if any_legacy_proxy:
        print(
            "Legacy G-P proxy values are historical "
            "exposure-buildup-scaled response values and "
            "are not interpreted as photon fluence rates."
        )

    has_messages = False

    for candidate in result.candidates:
        if candidate.status == "FAILED":
            if not has_messages:
                print(
                    "\nFallbacks, failures, and warnings:"
                )

                has_messages = True

            print(
                f"- {candidate.material.name}: "
                f"{candidate.failure_reason}"
            )

        if (
            candidate.status == "PASS"
            and len(candidate.warnings) > 0
        ):
            if not has_messages:
                print(
                    "\nFallbacks, failures, and warnings:"
                )

                has_messages = True

            for warning in candidate.warnings:
                print(
                    f"- {candidate.material.name}: "
                    f"{warning}"
                )


def print_air_kerma_material_comparison_result(
    result: AirKermaMaterialComparisonResult,
) -> None:
    # Print a material comparison for an explicit collision-air-kerma
    # target.
    #
    # This remains separate from the legacy photon comparison output:
    #
    #   photon comparison
    #       -> final photon fluence-rate field
    #
    #   air-kerma comparison
    #       -> final collision air-kerma rate in microGy/h
    #
    # Air-kerma values are never placed in fields or columns named flux.

    print(
        "\nCollision air-kerma material comparison result"
    )

    print(
        "Calculation mode: Single-material collision "
        "air-kerma design comparison"
    )

    print(
        f"Target: "
        f"{result.target_description}"
    )

    buildup_requested_text = (
        "Yes"
        if result.apply_buildup
        else "No"
    )

    print(
        "G-P exposure buildup requested: "
        f"{buildup_requested_text}"
    )

    print("\nCandidates:")

    print(
        f"{'Material':<28}"
        f"{'Thickness (cm)':<18}"
        f"{'Final Air Kerma':<19}"
        f"{'Response Ratio':<17}"
        f"{'Buildup':<12}"
        f"{'Status':<10}"
    )

    print("-" * 104)

    for candidate in result.candidates:
        if candidate.status == "PASS":
            thickness_text = (
                format_optional_float(
                    candidate.required_thickness
                )
            )

            air_kerma_text = (
                format_optional_float(
                    candidate
                    .final_air_kerma_rate_microgy_per_h,
                    ".6e",
                )
            )

            response_ratio_text = (
                format_optional_float(
                    candidate.final_response_ratio,
                    ".6e",
                )
            )

            buildup_text = (
                "Yes"
                if candidate.buildup_used
                else "No"
            )

        else:
            thickness_text = "--"
            air_kerma_text = "--"
            response_ratio_text = "--"
            buildup_text = "--"

        print(
            f"{candidate.material.name:<28}"
            f"{thickness_text:<18}"
            f"{air_kerma_text:<19}"
            f"{response_ratio_text:<17}"
            f"{buildup_text:<12}"
            f"{candidate.status:<10}"
        )

    print(
        "\nFinal Air Kerma units: µGy/h"
    )

    has_messages = False

    for candidate in result.candidates:
        if candidate.status == "FAILED":
            if not has_messages:
                print(
                    "\nFailures and warnings:"
                )

                has_messages = True

            print(
                f"- {candidate.material.name}: "
                f"{candidate.failure_reason}"
            )

        if (
            candidate.status == "PASS"
            and len(candidate.warnings) > 0
        ):
            if not has_messages:
                print(
                    "\nFailures and warnings:"
                )

                has_messages = True

            for warning in candidate.warnings:
                print(
                    f"- {candidate.material.name}: "
                    f"{warning}"
                )


def get_optimized_candidate_thickness(
    candidate: OptimizedMaterialCandidate,
) -> float | None:
    return candidate.base_candidate.required_thickness


def print_design_constraints(result: OptimizedDesignResult) -> None:
    constraints = result.constraints

    print("\nActive design constraints:")

    if constraints.max_thickness_cm is None:
        print("- Maximum design thickness: None")
    else:
        print(
            f"- Maximum design thickness: "
            f"{constraints.max_thickness_cm:.6g} cm"
        )

    if constraints.max_mass_per_area_g_per_cm2 is None:
        print("- Maximum mass per area: None")
    else:
        print(
            f"- Maximum mass per area: "
            f"{constraints.max_mass_per_area_g_per_cm2:.6g} g/cm^2"
        )

    if constraints.max_relative_cost_index_per_area is None:
        print("- Maximum relative cost index per area: None")
    else:
        print(
            f"- Maximum relative cost index per area: "
            f"{constraints.max_relative_cost_index_per_area:.6g}"
        )


def print_optimized_design_result(
    result: OptimizedDesignResult,
) -> None:
    print("\nOptimized material selection")
    print("Calculation mode: Constraint-based material optimization")
    print(f"Target: {result.target_description}")
    print(f"Optimization objective: {result.optimization_mode}")

    buildup_text = "Yes" if result.apply_buildup else "No"
    print(f"Buildup requested: {buildup_text}")

    if result.weights is not None:
        print(
            "Balanced weights: "
            f"thickness={result.weights.thickness_weight:.6g}, "
            f"mass={result.weights.mass_weight:.6g}, "
            f"cost={result.weights.cost_weight:.6g}"
        )

    print_design_constraints(result)

    if result.best_candidate is None:
        print("\nBest material: None")
        print(
            "Selection result: No candidate satisfied all active constraints."
        )
    else:
        best_base_candidate = (
            result
            .best_candidate
            .base_candidate
        )

        print(
            f"\nBest material: "
            f"{best_base_candidate.material.name}"
        )

        print(
            f"Selection reason: "
            f"{result.selection_reason}"
        )

        if isinstance(
            best_base_candidate,
            AirKermaMaterialDesignCandidate,
        ):
            final_air_kerma_rate = (
                best_base_candidate
                .final_air_kerma_rate_microgy_per_h
            )

            final_response_ratio = (
                best_base_candidate
                .final_response_ratio
            )

            if final_air_kerma_rate is None:
                raise ValueError(
                    "Selected air-kerma candidate is "
                    "missing its final response."
                )

            if final_response_ratio is None:
                raise ValueError(
                    "Selected air-kerma candidate is "
                    "missing its final response ratio."
                )

            if result.apply_buildup:
                response_label = (
                    "Selected final G-P exposure-buildup-"
                    "adjusted collision air-kerma rate"
                )

            else:
                response_label = (
                    "Selected final uncollided collision "
                    "air-kerma rate"
                )

            print(
                f"{response_label}: "
                f"{final_air_kerma_rate:.6e} µGy/h"
            )

            print(
                "Selected final response ratio: "
                f"{final_response_ratio:.6e}"
            )

    print("\nCandidates:")

    print(
        f"{'Material':<28}"
        f"{'Thickness':<13}"
        f"{'Mass/Area':<15}"
        f"{'Rel Cost/Area':<16}"
        f"{'Score':<13}"
        f"{'Buildup':<12}"
        f"{'Status':<10}"
    )

    print("-" * 107)

    for candidate in result.all_candidates:
        base_candidate = candidate.base_candidate

        if base_candidate.status == "PASS":
            thickness_text = format_optional_float(
                base_candidate.required_thickness
            )

            mass_text = format_optional_float(
                candidate.mass_per_area_g_per_cm2
            )

            cost_text = format_optional_float(
                candidate.relative_cost_index_per_area
            )

            score_text = format_optional_float(
                candidate.optimization_score
            )

        else:
            thickness_text = "--"
            mass_text = "--"
            cost_text = "--"
            score_text = "--"

        buildup_display = (
            get_buildup_display_for_candidate(
                base_candidate
            )
        )

        print(
            f"{base_candidate.material.name:<28}"
            f"{thickness_text:<13}"
            f"{mass_text:<15}"
            f"{cost_text:<16}"
            f"{score_text:<13}"
            f"{buildup_display:<12}"
            f"{candidate.optimization_status:<10}"
        )

    has_messages = False

    for candidate in result.all_candidates:
        base_candidate = candidate.base_candidate

        if candidate.optimization_status == "REJECTED":
            if not has_messages:
                print("\nRejections, failures, and warnings:")
                has_messages = True

            for reason in candidate.rejection_reasons:
                print(
                    f"- {base_candidate.material.name}: {reason}"
                )

        if candidate.optimization_status == "FAILED":
            if not has_messages:
                print("\nRejections, failures, and warnings:")
                has_messages = True

            print(
                f"- {base_candidate.material.name}: "
                f"{base_candidate.failure_reason}"
            )

        if (
            base_candidate.status == "PASS"
            and len(base_candidate.warnings) > 0
        ):
            if not has_messages:
                print("\nRejections, failures, and warnings:")
                has_messages = True

            for warning in base_candidate.warnings:
                print(
                    f"- {base_candidate.material.name}: {warning}"
                )

    if len(result.warnings) > 0:
        if not has_messages:
            print("\nWarnings:")
        else:
            print("\nOptimization warnings:")

        for warning in result.warnings:
            print(f"- {warning}")