# Output formatting utilities.
#
# This module keeps printing/reporting logic separate from physics calculations.
# The calculation modules should return result objects. This file decides how
# those results are displayed to the user in the command-line interface.
#
# Keeping output separate makes the code easier to upgrade later when adding
# plotting, saved reports, scenario files, or a graphical interface.


from target_models import MinimumThicknessResult
from models import ShieldingResult
from source_models import SourceCalculationResult
from design_optimizer import MaterialComparisonResult, MaterialDesignCandidate
from optimization_models import (
    OptimizedDesignResult,
    OptimizedMaterialCandidate,
)

def print_results(result: ShieldingResult) -> None:
    if result.buildup_factor is not None and result.buildup_corrected_flux is not None:
        print("Calculation mode: Narrow-beam uncollided flux + G-P buildup correction\n")
    else:
        print("Calculation mode: Narrow-beam uncollided flux\n")

    print(f"Photon energy: {result.photon_energy} MeV")
    print(f"Source strength: {result.source_strength:.3e} photons/s")
    print(f"Detector distance: {result.detector_distance} cm")
    print(f"Number of layers: {len(result.layers)}")
    print(f"Total thickness: {result.total_thickness} cm")
    print(f"Total MFP: {result.total_mfp}")
    print(f"Total transmission: {result.total_transmission}")
    print(f"Uncollided flux at detector: {result.uncollided_flux:.6e} photons/cm^2/s")

    if result.buildup_factor is not None and result.buildup_corrected_flux is not None:
        print("\nG-P buildup correction:")
        print(f"Buildup mode: Single-layer {result.layers[0].material.name} exposure buildup")
        print(f"Buildup factor: {result.buildup_factor}")
        print(
            f"Buildup-corrected flux: "
            f"{result.buildup_corrected_flux:.6e} photons/cm^2/s"
        )

    print("\nLayers:")

    for layer_result in result.layer_results:
        print(f"\nMaterial: {layer_result.layer.material.name}")
        print(f"Thickness: {layer_result.layer.thickness} cm")
        print(f"Density: {layer_result.layer.material.density} g/cm^3")
        print(f"mu/rho: {layer_result.mu_over_p} cm^2/g")
        print(f"mu: {layer_result.mu} 1/cm")
        print(f"Layer MFP: {layer_result.mfp}")
        print(f"Layer transmission: {layer_result.transmission}")


def print_source_results(result: SourceCalculationResult) -> None:
    print("\nSource calculation results")
    print(f"Source: {result.source_name}")

    if result.activity_bq is not None:
        print(f"Activity: {result.activity_bq:.6e} Bq")

    print(f"Number of photon lines: {len(result.line_results)}")
    print(f"Total uncollided flux: {result.total_uncollided_flux:.6e} photons/cm^2/s")

    if result.total_buildup_corrected_flux is not None:
        print(
            f"Total buildup-corrected flux: "
            f"{result.total_buildup_corrected_flux:.6e} photons/cm^2/s"
        )

    if len(result.warnings) > 0:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning}")

    print("\nPhoton line results:")

    for i, line_result in enumerate(result.line_results):
        shielding_result = line_result.shielding_result

        print(f"\nLine {i + 1}")
        print(f"Photon energy: {line_result.photon_line.energy} MeV")
        print(f"Emission intensity: {line_result.photon_line.intensity} photons/decay")
        print(f"Photon emission rate: {line_result.photon_rate:.6e} photons/s")
        print(f"Transmission: {shielding_result.total_transmission}")
        print(f"Total MFP: {shielding_result.total_mfp}")
        print(
            f"Uncollided flux: "
            f"{shielding_result.uncollided_flux:.6e} photons/cm^2/s"
        )

        if shielding_result.buildup_factor is not None:
            print(f"Buildup factor: {shielding_result.buildup_factor}")

        if shielding_result.buildup_corrected_flux is not None:
            print(
                f"Buildup-corrected flux: "
                f"{shielding_result.buildup_corrected_flux:.6e} photons/cm^2/s"
            )


def print_minimum_thickness_result(result: MinimumThicknessResult) -> None:
    print("\nMinimum shielding thickness result")
    print(f"Calculation mode: {result.calculation_mode}")
    print(f"Material: {result.material.name}")
    print(f"Target: {result.target_description}")
    print(f"Required thickness: {result.required_thickness:.6g} cm")
    print(f"Final effective transmission: {result.final_transmission:.6e}")
    print(
        f"Final target-comparison flux: "
        f"{result.final_flux:.6e} photons/cm^2/s"
    )

    if result.final_uncollided_flux is not None:
        print(
            f"Final narrow-beam uncollided flux: "
            f"{result.final_uncollided_flux:.6e} photons/cm^2/s"
        )

    if result.final_buildup_corrected_flux is not None:
        print(
            f"Final buildup-corrected flux: "
            f"{result.final_buildup_corrected_flux:.6e} photons/cm^2/s"
        )

    if len(result.warnings) > 0:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning}")      


def get_buildup_display_for_candidate(candidate: MaterialDesignCandidate) -> str:
    # Convert internal buildup/fallback state into a short table label.
    #
    # "Yes" means buildup was successfully used.
    # "Fallback" means buildup was requested, but the candidate used narrow-beam
    # design instead and stored a warning.
    # "No" means buildup was not requested or not used without warning.
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


def print_material_comparison_result(result: MaterialComparisonResult) -> None:
    # Print the V1.08 material comparison table.
    #
    # The table is intentionally compact so it can be pasted into the README,
    # validation report, or internship/recruiter materials.
    #
    # Passing candidates show thickness and final flux.
    # Failed candidates show "--" in numerical columns and explain the failure below.
    print("\nMaterial comparison result")
    print("Calculation mode: Single-material design comparison")
    print(f"Target: {result.target_description}")
    buildup_requested_text = "Yes" if result.apply_buildup else "No"
    print(f"Buildup requested: {buildup_requested_text}")

    print("\nCandidates:")
    print(
        f"{'Material':<28}"
        f"{'Thickness (cm)':<18}"
        f"{'Final Flux':<18}"
        f"{'Buildup':<14}"
        f"{'Status':<10}"
    )
    print("-" * 88)

    for candidate in result.candidates:
        if candidate.status == "PASS":
            thickness_text = (
                f"{format_optional_float(candidate.required_thickness)}"
            )
            flux_text = (
                f"{format_optional_float(candidate.final_flux, '.6e')}"
            )
            buildup_text = get_buildup_display_for_candidate(candidate)

        else:
            thickness_text = "--"
            flux_text = "--"
            buildup_text = "--"

        print(
            f"{candidate.material.name:<28}"
            f"{thickness_text:<18}"
            f"{flux_text:<18}"
            f"{buildup_text:<14}"
            f"{candidate.status:<10}"
        )

    has_messages = False

    for candidate in result.candidates:
        if candidate.status == "FAILED":
            if not has_messages:
                print("\nFallbacks, failures, and warnings:")
                has_messages = True

            print(f"- {candidate.material.name}: {candidate.failure_reason}")

        if candidate.status == "PASS" and len(candidate.warnings) > 0:
            if not has_messages:
                print("\nFallbacks, failures, and warnings:")
                has_messages = True

            for warning in candidate.warnings:
                print(f"- {candidate.material.name}: {warning}")


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
        print(
            f"\nBest material: "
            f"{result.best_candidate.base_candidate.material.name}"
        )

        print(f"Selection reason: {result.selection_reason}")

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

            buildup_display = get_buildup_display_for_candidate(
                base_candidate
            )

        else:
            thickness_text = "--"
            mass_text = "--"
            cost_text = "--"
            score_text = "--"
            buildup_display = "--"

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