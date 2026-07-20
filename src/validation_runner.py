# Validation runner for benchmark and regression tests.
#
# This script is intended to be run after major code changes.
# It validates the physics helpers, source calculations, minimum-thickness
# design logic, buildup-aware behavior, material comparison behavior, and
# important error-handling cases.
#
# It is intentionally separate from main.py so validation can run without
# interactive user input.

from target_models import FluxTarget, ReductionFactorTarget, TransmissionTarget
from thickness_calculator import (
    calculate_isotope_minimum_thickness,
    calculate_manual_minimum_thickness,
    calculate_unshielded_isotope_flux,
    calculate_unshielded_manual_flux,
)
from buildup import calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from buildup_library import get_gp_coefficients_library
from material_library import get_material_library
from models import Layer
from source_calculator import calculate_isotope_source_result, calculate_manual_source_result
from source_library import create_isotope_source, get_available_isotopes
from source_models import ManualPhotonSource
from unit_conversions import convert_activity_to_bq
from design_optimizer import compare_materials_for_target
from constraint_optimizer import (
    calculate_mass_per_area,
    calculate_relative_cost_index_per_area,
    optimize_material_selection,
)
from material_cost_library import get_material_cost_library
from optimization_models import (
    DesignConstraints,
    OptimizationWeights,
)
from plot_data import (
    create_constraint_feasibility_rows,
    create_optimization_plot_data,
    create_pareto_points,
    evaluate_maximum_constraint,
)

from response_curve import (
    calculate_response_curve_target_flux,
    create_response_curve,
    create_thickness_samples,
)

def assert_close(
    name: str,
    actual: float,
    expected: float,
    tolerance: float = 1e-6,
) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")


def get_candidate_by_material_key(comparison_result, material_key: str):
    for candidate in comparison_result.candidates:
        if candidate.material.key == material_key:
            return candidate

    raise AssertionError(f"Candidate not found for material key: {material_key}")


def get_optimized_candidate_by_material_key(
    optimization_result,
    material_key: str,
):
    for candidate in optimization_result.all_candidates:
        if candidate.base_candidate.material.key == material_key:
            return candidate

    raise AssertionError(
        f"Optimized candidate not found for material key: {material_key}"
    )


def get_material_plot_point_by_key(
    plot_data,
    material_key: str,
):
    for candidate in plot_data.candidates:
        if candidate.material_key == material_key:
            return candidate

    raise AssertionError(
        f"Material plot point not found for key: {material_key}"
    )


def get_feasibility_row_by_material_key(
    feasibility_rows,
    material_key: str,
):
    for row in feasibility_rows:
        if row.material_key == material_key:
            return row

    raise AssertionError(
        f"Feasibility row not found for material key: {material_key}"
    )


def get_response_curve_point_by_thickness(
    curve_result,
    thickness_cm: float,
    tolerance: float = 1.0e-12,
):
    for point in curve_result.points:
        if abs(point.thickness_cm - thickness_cm) <= tolerance:
            return point

    raise AssertionError(
        f"Response curve does not contain thickness: {thickness_cm}"
    )


def assert_greater_than(name: str, actual: float, minimum: float) -> None:
    if actual <= minimum:
        raise AssertionError(
            f"{name} failed: expected greater than {minimum}, got {actual}"
        )

    print(f"PASS: {name}")


def assert_less_than_or_equal(name: str, actual: float, maximum: float) -> None:
    if actual > maximum:
        raise AssertionError(
            f"{name} failed: expected less than or equal to {maximum}, got {actual}"
        )

    print(f"PASS: {name}")


def assert_equal(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")


def assert_not_none(name: str, value: float | None) -> float:
    if value is None:
        raise AssertionError(f"{name} failed: expected a value, got None")

    return value


def run_validation_tests() -> None:
    
    gp_library = get_gp_coefficients_library()

    # Validate G-P buildup behavior for every material with coefficient data.

    for material_key in gp_library:
        coefficients = get_gp_coefficients_at_energy(
            material_key,
            1.0,
            gp_library,
        )

        assert_close(
            f"{material_key} GP buildup at 0 MFP",
            calculate_gp_buildup_factor(coefficients, 0.0),
            1.0,
            1e-12,
        )

        assert_close(
            f"{material_key} GP buildup at 1 MFP",
            calculate_gp_buildup_factor(coefficients, 1.0),
            coefficients.b,
            1e-8,
        )

        buildup_at_5_mfp = calculate_gp_buildup_factor(coefficients, 5.0)

        assert_greater_than(
            f"{material_key} GP buildup at 5 MFP greater than 1",
            buildup_at_5_mfp,
            1.0,
        )

    # Validate activity-unit conversions used by isotope sources.

    one_ci_bq = convert_activity_to_bq(1.0, "ci")

    assert_close(
        "1 Ci activity conversion",
        one_ci_bq,
        3.7e10,
        1e-6,
    )

    assert_close(
        "1 mCi activity conversion",
        convert_activity_to_bq(1.0, "mci"),
        3.7e7,
        1e-6,
    )

    assert_close(
        "1 uCi activity conversion",
        convert_activity_to_bq(1.0, "uci"),
        3.7e4,
        1e-9,
    )

    # Validate source-library structure and source-line bookkeeping.

    isotope_keys = get_available_isotopes()

    assert_equal(
        "Source library contains 10 isotope keys",
        len(isotope_keys),
        10,
    )

    expected_line_counts = {
        "cs137": 1,
        "co60": 2,
        "am241": 1,
        "ba133": 7,
        "na22": 2,
        "mn54": 1,
        "co57": 2,
        "zn65": 2,
        "eu152": 9,
        "ir192": 10,
    }

    materials = get_material_library()
    lead_layer = Layer(5.0, materials["lead"])
    layers = [lead_layer]
    detector_distance = 100.0

    # Validate that every isotope source can run through the narrow-beam calculator.

    for isotope_key in isotope_keys:
        source = create_isotope_source(isotope_key, one_ci_bq)

        assert_equal(
            f"{isotope_key} source line count",
            len(source.photon_lines),
            expected_line_counts[isotope_key],
        )

        assert_close(
            f"{isotope_key} activity stored in Bq",
            source.activity_bq,
            one_ci_bq,
            1e-6,
        )

        for i, photon_line in enumerate(source.photon_lines):
            assert_greater_than(
                f"{isotope_key} line {i + 1} energy greater than 0",
                photon_line.energy,
                0.0,
            )

            assert_greater_than(
                f"{isotope_key} line {i + 1} intensity greater than 0",
                photon_line.intensity,
                0.0,
            )

        source_result = calculate_isotope_source_result(
            source,
            layers,
            detector_distance,
            apply_buildup=False,
        )

        assert_equal(
            f"{isotope_key} calculation line result count",
            len(source_result.line_results),
            len(source.photon_lines),
        )

        line_flux_sum = 0.0
        photon_rate_sum = 0.0

        for line_result in source_result.line_results:
            line_flux_sum = line_flux_sum + line_result.shielding_result.uncollided_flux
            photon_rate_sum = photon_rate_sum + line_result.photon_rate

        expected_photon_rate_sum = 0.0

        for photon_line in source.photon_lines:
            expected_photon_rate_sum = (
                expected_photon_rate_sum
                + source.activity_bq * photon_line.intensity
            )

        assert_close(
            f"{isotope_key} photon rates equal activity times intensities",
            photon_rate_sum,
            expected_photon_rate_sum,
            1e-3,
        )

        assert_close(
            f"{isotope_key} total uncollided flux equals sum of line fluxes",
            source_result.total_uncollided_flux,
            line_flux_sum,
            1e-6,
        )

    # Regression test: manual source mode should reproduce the V1.05 Cs-137 lead case.

    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )

    manual_result = calculate_manual_source_result(
        manual_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    assert_close(
        "Manual source V1.05 uncollided flux regression",
        manual_result.total_uncollided_flux,
        5.40662e2,
        1e-2,
    )

    manual_buildup_flux = assert_not_none(
        "Manual source V1.05 buildup-corrected flux regression",
        manual_result.total_buildup_corrected_flux,
    )

    assert_close(
        "Manual source V1.05 buildup-corrected flux regression",
        manual_buildup_flux,
        1.42612e3,
        1e-2,
    )

    # Validate that multi-line buildup totals equal the sum of valid line-by-line results.

    co60_source = create_isotope_source("co60", one_ci_bq)

    co60_result = calculate_isotope_source_result(
        co60_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    co60_buildup_flux_sum = 0.0

    for line_result in co60_result.line_results:
        line_buildup_flux = assert_not_none(
            "Co-60 line buildup-corrected flux",
            line_result.shielding_result.buildup_corrected_flux,
        )

        co60_buildup_flux_sum = co60_buildup_flux_sum + line_buildup_flux

    co60_total_buildup_flux = assert_not_none(
        "Co-60 total buildup-corrected flux",
        co60_result.total_buildup_corrected_flux,
    )

    assert_close(
        "Co-60 total buildup-corrected flux equals sum of line fluxes",
        co60_total_buildup_flux,
        co60_buildup_flux_sum,
        1e-6,
    )

    # Validate warning behavior when buildup is requested outside the valid G-P MFP range.

    am241_source = create_isotope_source("am241", one_ci_bq)

    am241_result = calculate_isotope_source_result(
        am241_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    assert_equal(
        "Am-241 total buildup-corrected flux is unavailable above G-P MFP range",
        am241_result.total_buildup_corrected_flux,
        None,
    )

    assert_greater_than(
        "Am-241 buildup warning generated",
        len(am241_result.warnings),
        0,
    )


    # Validate V1.07 minimum shielding thickness calculations.

    manual_transmission_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        TransmissionTarget(0.1),
    )

    assert_close(
        "Manual minimum thickness transmission target",
        manual_transmission_target_result.final_transmission,
        0.1,
        1e-8,
    )

    manual_reduction_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        ReductionFactorTarget(1000.0),
    )

    assert_close(
        "Manual minimum thickness reduction factor target",
        manual_reduction_target_result.final_transmission,
        0.001,
        1e-8,
    )

    manual_flux_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
    )

    assert_less_than_or_equal(
        "Manual minimum thickness flux target",
        manual_flux_target_result.final_flux,
        100.000001,
    )

    cs137_source = create_isotope_source("cs137", one_ci_bq)

    cs137_flux_target_result = calculate_isotope_minimum_thickness(
        cs137_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
        max_thickness=detector_distance,
    )

    assert_less_than_or_equal(
        "Cs-137 isotope minimum thickness flux target",
        cs137_flux_target_result.final_flux,
        100.000001,
    )

    assert_greater_than(
        "Cs-137 isotope required thickness greater than zero",
        cs137_flux_target_result.required_thickness,
        0.0,
    )

    no_shielding_required_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(1.0e12),
    )

    assert_close(
        "No shielding required returns zero thickness",
        no_shielding_required_result.required_thickness,
        0.0,
        1e-12,
    )

    assert_greater_than(
        "No shielding required warning generated",
        len(no_shielding_required_result.warnings),
        0,
    )


    # Validate buildup-aware V1.07 minimum shielding thickness calculations.

    manual_buildup_flux_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
        apply_buildup=True,
    )

    assert_less_than_or_equal(
        "Manual buildup-aware minimum thickness flux target",
        manual_buildup_flux_target_result.final_flux,
        100.000001,
    )

    assert_equal(
        "Manual buildup-aware minimum thickness used buildup",
        manual_buildup_flux_target_result.buildup_used,
        True,
    )

    assert_greater_than(
        "Manual buildup-aware thickness greater than narrow-beam thickness",
        manual_buildup_flux_target_result.required_thickness,
        manual_flux_target_result.required_thickness,
    )

    cs137_buildup_flux_target_result = calculate_isotope_minimum_thickness(
        cs137_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
        max_thickness=detector_distance,
        apply_buildup=True,
    )

    assert_less_than_or_equal(
        "Cs-137 buildup-aware isotope minimum thickness flux target",
        cs137_buildup_flux_target_result.final_flux,
        100.000001,
    )

    assert_equal(
        "Cs-137 buildup-aware isotope minimum thickness used buildup",
        cs137_buildup_flux_target_result.buildup_used,
        True,
    )

    am241_manual_source = ManualPhotonSource(
        0.059541,
        3.7e10,
    )

    am241_buildup_fallback_result = calculate_manual_minimum_thickness(
        am241_manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(1.0e-121),
        apply_buildup=True,
    )

    assert_less_than_or_equal(
        "Am-241 fallback minimum thickness reaches flux target",
        am241_buildup_fallback_result.final_flux,
        1.000001e-121,
    )

    assert_equal(
        "Am-241 fallback minimum thickness did not use buildup",
        am241_buildup_fallback_result.buildup_used,
        False,
    )

    assert_greater_than(
        "Am-241 fallback minimum thickness warning generated",
        len(am241_buildup_fallback_result.warnings),
        0,
    )


    # Validate V1.08 single-material design comparison.

    comparison_materials = [
        materials["lead"],
        materials["tungsten"],
        materials["concrete_ordinary"],
        materials["concrete_barite"],
        materials["water"],
        materials["polyethylene"],
    ]

    material_comparison_result = compare_materials_for_target(
        cs137_source,
        comparison_materials,
        detector_distance,
        FluxTarget(100.0),
        max_thickness=detector_distance,
        apply_buildup=True,
    )

    assert_equal(
        "Material comparison returns one candidate per selected material",
        len(material_comparison_result.candidates),
        len(comparison_materials),
    )

    lead_candidate = get_candidate_by_material_key(
        material_comparison_result,
        "lead",
    )

    assert_equal(
        "Lead material comparison candidate passes",
        lead_candidate.status,
        "PASS",
    )

    lead_final_flux = assert_not_none(
        "Lead material comparison final flux",
        lead_candidate.final_flux,
    )

    assert_less_than_or_equal(
        "Lead material comparison reaches flux target",
        lead_final_flux,
        100.000001,
    )

    assert_equal(
        "Lead material comparison uses buildup when valid",
        lead_candidate.buildup_used,
        True,
    )

    for candidate in material_comparison_result.candidates:
        if candidate.status == "PASS":
            candidate_final_flux = assert_not_none(
                f"{candidate.material.key} material comparison final flux",
                candidate.final_flux,
            )

            assert_less_than_or_equal(
                f"{candidate.material.key} material comparison reaches flux target",
                candidate_final_flux,
                100.000001,
            )

    barite_candidate = get_candidate_by_material_key(
        material_comparison_result,
        "concrete_barite",
    )

    assert_equal(
        "Unsupported buildup material can fall back to narrow-beam",
        barite_candidate.status,
        "PASS",
    )

    assert_equal(
        "Unsupported buildup material does not use buildup",
        barite_candidate.buildup_used,
        False,
    )

    assert_greater_than(
        "Unsupported buildup material warning preserved",
        len(barite_candidate.warnings),
        0,
    )

    impossible_comparison_result = compare_materials_for_target(
        cs137_source,
        [materials["lead"], materials["water"]],
        detector_distance,
        FluxTarget(1.0e-30),
        max_thickness=0.1,
        apply_buildup=False,
    )

    failed_lead_candidate = get_candidate_by_material_key(
        impossible_comparison_result,
        "lead",
    )

    assert_equal(
        "Failed material comparison candidate preserved",
        failed_lead_candidate.status,
        "FAILED",
    )

    if (
        failed_lead_candidate.failure_reason is None
        or failed_lead_candidate.failure_reason.strip() == ""
    ):
        raise AssertionError("Failed material candidate did not preserve failure reason.")

    print("PASS: Failed material comparison candidate preserves failure reason")


    try:
        calculate_manual_minimum_thickness(
            manual_source,
            materials["lead"],
            detector_distance,
            FluxTarget(1.0e-30),
            max_thickness=0.1,
        )
        raise AssertionError("Impossible manual thickness target should have failed.")
    except ValueError:
        print("PASS: Impossible manual thickness target rejected")


    # Validate V1.09 constraint-based material optimization.

    lead_mass_per_area = calculate_mass_per_area(
        materials["lead"].density,
        7.0,
    )

    assert_close(
        "V1.09 mass per area equals density times thickness",
        lead_mass_per_area,
        79.38,
        1e-10,
    )

    material_cost_library = get_material_cost_library()
    lead_relative_cost_index = (
        material_cost_library["lead"].relative_cost_index
    )

    lead_relative_cost_per_area = (
        calculate_relative_cost_index_per_area(
            lead_mass_per_area,
            lead_relative_cost_index,
        )
    )

    assert_close(
        "V1.09 relative cost per area calculation",
        lead_relative_cost_per_area,
        79.38 * lead_relative_cost_index,
        1e-10,
    )

    minimum_thickness_optimization_result = (
        optimize_material_selection(
            source=cs137_source,
            materials=comparison_materials,
            detector_distance=detector_distance,
            target=FluxTarget(100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=detector_distance,
            apply_buildup=True,
        )
    )

    if minimum_thickness_optimization_result.best_candidate is None:
        raise AssertionError(
            "Minimum-thickness optimization did not select a candidate."
        )

    eligible_thicknesses = []

    for candidate in (
        minimum_thickness_optimization_result.eligible_candidates()
    ):
        thickness = assert_not_none(
            "Eligible V1.09 candidate thickness",
            candidate.base_candidate.required_thickness,
        )

        eligible_thicknesses.append(thickness)

    best_thickness = assert_not_none(
        "Best V1.09 minimum-thickness candidate thickness",
        minimum_thickness_optimization_result
        .best_candidate
        .base_candidate
        .required_thickness,
    )

    assert_close(
        "V1.09 minimum-thickness objective selects smallest thickness",
        best_thickness,
        min(eligible_thicknesses),
        1e-12,
    )

    thickness_constraint_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(
            max_thickness_cm=10.0,
        ),
        optimization_mode="minimum_thickness",
        calculation_max_thickness=detector_distance,
        apply_buildup=True,
    )

    water_optimized_candidate = (
        get_optimized_candidate_by_material_key(
            thickness_constraint_result,
            "water",
        )
    )

    assert_equal(
        "V1.09 candidate violating thickness constraint is rejected",
        water_optimized_candidate.optimization_status,
        "REJECTED",
    )

    assert_greater_than(
        "V1.09 rejected candidate preserves rejection reason",
        len(water_optimized_candidate.rejection_reasons),
        0,
    )

    multiple_constraint_result = optimize_material_selection(
        source=cs137_source,
        materials=[materials["water"]],
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(
            max_thickness_cm=10.0,
            max_mass_per_area_g_per_cm2=50.0,
        ),
        optimization_mode="minimum_mass",
        calculation_max_thickness=detector_distance,
        apply_buildup=False,
    )

    multiple_rejection_candidate = (
        get_optimized_candidate_by_material_key(
            multiple_constraint_result,
            "water",
        )
    )

    assert_equal(
        "V1.09 candidate can be rejected by multiple constraints",
        multiple_rejection_candidate.optimization_status,
        "REJECTED",
    )

    assert_greater_than(
        "V1.09 candidate preserves multiple rejection reasons",
        len(multiple_rejection_candidate.rejection_reasons),
        1,
    )

    minimum_mass_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(),
        optimization_mode="minimum_mass",
        calculation_max_thickness=detector_distance,
        apply_buildup=True,
    )

    if minimum_mass_result.best_candidate is None:
        raise AssertionError(
            "Minimum-mass optimization did not select a candidate."
        )

    eligible_mass_values = []

    for candidate in minimum_mass_result.eligible_candidates():
        candidate_mass = assert_not_none(
            "Eligible V1.09 candidate mass per area",
            candidate.mass_per_area_g_per_cm2,
        )

        eligible_mass_values.append(candidate_mass)

    best_mass = assert_not_none(
        "Best V1.09 mass candidate mass per area",
        minimum_mass_result
        .best_candidate
        .mass_per_area_g_per_cm2,
    )

    assert_close(
        "V1.09 minimum-mass objective selects smallest mass",
        best_mass,
        min(eligible_mass_values),
        1e-12,
    )

    minimum_cost_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(),
        optimization_mode="minimum_cost",
        calculation_max_thickness=detector_distance,
        apply_buildup=True,
    )

    if minimum_cost_result.best_candidate is None:
        raise AssertionError(
            "Minimum-cost optimization did not select a candidate."
        )

    eligible_cost_values = []

    for candidate in minimum_cost_result.eligible_candidates():
        candidate_cost = assert_not_none(
            "Eligible V1.09 candidate relative cost",
            candidate.relative_cost_index_per_area,
        )

        eligible_cost_values.append(candidate_cost)

    best_cost = assert_not_none(
        "Best V1.09 cost candidate relative cost",
        minimum_cost_result
        .best_candidate
        .relative_cost_index_per_area,
    )

    assert_close(
        "V1.09 minimum-cost objective selects smallest relative cost",
        best_cost,
        min(eligible_cost_values),
        1e-12,
    )

    balanced_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(),
        optimization_mode="balanced",
        weights=OptimizationWeights(
            thickness_weight=0.5,
            mass_weight=0.3,
            cost_weight=0.2,
        ),
        calculation_max_thickness=detector_distance,
        apply_buildup=True,
    )

    if balanced_result.best_candidate is None:
        raise AssertionError(
            "Balanced optimization did not select a candidate."
        )

    eligible_balanced_scores = []

    for candidate in balanced_result.eligible_candidates():
        candidate_score = assert_not_none(
            "Eligible balanced candidate score",
            candidate.optimization_score,
        )

        assert_greater_than(
            f"{candidate.base_candidate.material.key} balanced score "
            "is not below zero",
            candidate_score + 1.0e-12,
            0.0,
        )

        assert_less_than_or_equal(
            f"{candidate.base_candidate.material.key} balanced score "
            "is not above one",
            candidate_score,
            1.0,
        )

        eligible_balanced_scores.append(candidate_score)

    best_balanced_score = assert_not_none(
        "Best balanced candidate score",
        balanced_result.best_candidate.optimization_score,
    )

    assert_close(
        "V1.09 balanced objective selects smallest score",
        best_balanced_score,
        min(eligible_balanced_scores),
        1e-12,
    )

    failed_optimization_result = optimize_material_selection(
        source=cs137_source,
        materials=[materials["lead"], materials["water"]],
        detector_distance=detector_distance,
        target=FluxTarget(1.0e-30),
        constraints=DesignConstraints(),
        optimization_mode="minimum_thickness",
        calculation_max_thickness=0.1,
        apply_buildup=False,
    )

    failed_optimized_lead = (
        get_optimized_candidate_by_material_key(
            failed_optimization_result,
            "lead",
        )
    )

    assert_equal(
        "V1.09 preserves failed V1.08 candidates",
        failed_optimized_lead.optimization_status,
        "FAILED",
    )

    no_eligible_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(
            max_thickness_cm=0.1,
        ),
        optimization_mode="minimum_thickness",
        calculation_max_thickness=detector_distance,
        apply_buildup=False,
    )

    assert_equal(
        "V1.09 no eligible candidates returns no best candidate",
        no_eligible_result.best_candidate,
        None,
    )

    assert_greater_than(
        "V1.09 no eligible candidates generates warning",
        len(no_eligible_result.warnings),
        0,
    )

    try:
        DesignConstraints(max_thickness_cm=-1.0)
        raise AssertionError(
            "Negative design constraint should have failed."
        )
    except ValueError:
        print("PASS: Negative V1.09 design constraint rejected")

    try:
        OptimizationWeights(0.0, 0.0, 0.0)
        raise AssertionError(
            "Zero optimization weights should have failed."
        )
    except ValueError:
        print("PASS: Zero V1.09 optimization weights rejected")


    # Validate V1.10 optimization plot-data preparation.

    constrained_plot_data = create_optimization_plot_data(
        thickness_constraint_result
    )

    assert_equal(
        "V1.10 plot data preserves candidate count",
        len(constrained_plot_data.candidates),
        len(thickness_constraint_result.all_candidates),
    )

    if thickness_constraint_result.best_candidate is None:
        raise AssertionError(
            "V1.10 plot-data test requires a selected candidate."
        )

    expected_selected_material_key = (
        thickness_constraint_result
        .best_candidate
        .base_candidate
        .material
        .key
    )

    assert_equal(
        "V1.10 plot data preserves selected material",
        constrained_plot_data.selected_material_key,
        expected_selected_material_key,
    )

    plotted_water_candidate = get_material_plot_point_by_key(
        constrained_plot_data,
        "water",
    )

    assert_equal(
        "V1.10 plot data preserves rejected candidate status",
        plotted_water_candidate.optimization_status,
        "REJECTED",
    )

    assert_equal(
        "V1.10 plot data preserves rejection reasons",
        plotted_water_candidate.rejection_reasons,
        tuple(water_optimized_candidate.rejection_reasons),
    )

    assert_greater_than(
        "V1.10 rejected plot candidate has rejection reason",
        len(plotted_water_candidate.rejection_reasons),
        0,
    )

    multiple_constraint_plot_data = create_optimization_plot_data(
    multiple_constraint_result
)

    multiple_rejection_plot_point = get_material_plot_point_by_key(
        multiple_constraint_plot_data,
        "water",
    )

    assert_equal(
        "V1.10 plot data preserves multiple rejection reasons",
        multiple_rejection_plot_point.rejection_reasons,
        tuple(multiple_rejection_candidate.rejection_reasons),
    )

    assert_greater_than(
        "V1.10 rejected plot candidate can preserve multiple reasons",
        len(multiple_rejection_plot_point.rejection_reasons),
        1,
    )

    failed_plot_data = create_optimization_plot_data(
        failed_optimization_result
    )

    failed_feasibility_rows = create_constraint_feasibility_rows(
    failed_plot_data
    )

    failed_lead_feasibility = get_feasibility_row_by_material_key(
        failed_feasibility_rows,
        "lead",
    )

    assert_equal(
        "V1.10 failed candidate thickness check unavailable",
        failed_lead_feasibility.thickness_status,
        "UNAVAILABLE",
    )

    assert_equal(
        "V1.10 failed candidate mass check unavailable",
        failed_lead_feasibility.mass_status,
        "UNAVAILABLE",
    )

    assert_equal(
        "V1.10 failed candidate cost check unavailable",
        failed_lead_feasibility.cost_status,
        "UNAVAILABLE",
    )

    failed_lead_plot_point = get_material_plot_point_by_key(
        failed_plot_data,
        "lead",
    )

    assert_equal(
        "V1.10 plot data preserves failed candidate status",
        failed_lead_plot_point.optimization_status,
        "FAILED",
    )

    assert_equal(
        "V1.10 failed plot candidate has no thickness",
        failed_lead_plot_point.required_thickness_cm,
        None,
    )

    if failed_lead_plot_point.failure_reason is None:
        raise AssertionError(
            "V1.10 failed plot candidate did not preserve failure reason."
        )

    assert_greater_than(
        "V1.10 failed plot candidate preserves failure reason",
        len(failed_lead_plot_point.failure_reason),
        0,
    )


    visualization_constraint_result = optimize_material_selection(
        source=cs137_source,
        materials=list(materials.values()),
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(
            max_thickness_cm=20.0,
            max_mass_per_area_g_per_cm2=120.0,
        ),
        optimization_mode="minimum_mass",
        calculation_max_thickness=detector_distance,
        apply_buildup=True,
    )

    visualization_plot_data = create_optimization_plot_data(
        visualization_constraint_result
    )

    feasibility_rows = create_constraint_feasibility_rows(
        visualization_plot_data
    )


    # Validate V1.10 thickness-versus-mass Pareto classification.
    #
    # The unconstrained Cs-137 candidate set should have two Pareto-optimal
    # materials:
    #
    # Tungsten:
    #   smallest required thickness, but greater mass per area
    #
    # Lead:
    #   greater thickness than tungsten, but smallest mass per area
    #
    # Neither candidate dominates the other.

    unconstrained_plot_data = create_optimization_plot_data(
        balanced_result
    )

    pareto_points = create_pareto_points(
        unconstrained_plot_data,
        eligible_only=True,
    )

    pareto_material_keys = {
        point.material_key
        for point in pareto_points
        if point.is_pareto_optimal
    }

    assert_equal(
        "V1.10 Cs-137 Pareto front contains lead and tungsten",
        pareto_material_keys,
        {"lead", "tungsten"},
    )

    pareto_thickness_values = [
        point.thickness_cm
        for point in pareto_points
    ]

    assert_equal(
        "V1.10 Pareto points are sorted by thickness",
        pareto_thickness_values,
        sorted(pareto_thickness_values),
    )


    # Validate V1.10 thickness sampling.

    inserted_required_thickness = 7.08821

    thickness_samples = create_thickness_samples(
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=11,
        required_thickness_cm=inserted_required_thickness,
    )

    assert_equal(
        "V1.10 exact required thickness adds one sampling point",
        len(thickness_samples),
        12,
    )

    assert_close(
        "V1.10 thickness samples preserve lower endpoint",
        thickness_samples[0],
        0.0,
        1.0e-12,
    )

    assert_close(
        "V1.10 thickness samples preserve upper endpoint",
        thickness_samples[-1],
        10.0,
        1.0e-12,
    )

    exact_thickness_is_present = any(
        abs(value - inserted_required_thickness) <= 1.0e-12
        for value in thickness_samples
    )

    assert_equal(
        "V1.10 exact required thickness is included",
        exact_thickness_is_present,
        True,
    )

    samples_are_strictly_increasing = all(
        thickness_samples[index]
        < thickness_samples[index + 1]
        for index in range(len(thickness_samples) - 1)
    )

    assert_equal(
        "V1.10 thickness samples are strictly increasing",
        samples_are_strictly_increasing,
        True,
    )


    # Validate target conversion for response curves.

    manual_unshielded_flux = calculate_unshielded_manual_flux(
        manual_source,
        detector_distance,
    )

    transmission_curve_target = (
        calculate_response_curve_target_flux(
            source=manual_source,
            detector_distance_cm=detector_distance,
            target=TransmissionTarget(0.1),
        )
    )

    transmission_curve_target_value = assert_not_none(
        "V1.10 transmission curve target",
        transmission_curve_target,
    )

    assert_close(
        "V1.10 transmission target converts to target flux",
        transmission_curve_target_value,
        manual_unshielded_flux * 0.1,
        1.0e-8,
    )

    reduction_curve_target = (
        calculate_response_curve_target_flux(
            source=manual_source,
            detector_distance_cm=detector_distance,
            target=ReductionFactorTarget(1000.0),
        )
    )

    reduction_curve_target_value = assert_not_none(
        "V1.10 reduction curve target",
        reduction_curve_target,
    )

    assert_close(
        "V1.10 reduction factor converts to target flux",
        reduction_curve_target_value,
        manual_unshielded_flux / 1000.0,
        1.0e-8,
    )


    # Validate a supported manual-source response curve.

    manual_response_curve = create_response_curve(
        source=manual_source,
        material=materials["lead"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=21,
        apply_buildup=True,
        target=FluxTarget(100.0),
        required_thickness_cm=(
            manual_buildup_flux_target_result.required_thickness
        ),
    )

    assert_close(
        "V1.10 manual curve zero-thickness flux equals unshielded flux",
        manual_response_curve.points[0].uncollided_flux,
        manual_unshielded_flux,
        1.0e-6,
    )

    manual_uncollided_flux_is_monotonic = all(
        manual_response_curve.points[index + 1].uncollided_flux
        <= manual_response_curve.points[index].uncollided_flux
        for index in range(len(manual_response_curve.points) - 1)
    )

    assert_equal(
        "V1.10 manual uncollided curve decreases monotonically",
        manual_uncollided_flux_is_monotonic,
        True,
    )

    manual_curve_target_flux = assert_not_none(
        "V1.10 manual curve target flux",
        manual_response_curve.target_flux,
    )

    assert_close(
        "V1.10 manual response curve stores target flux",
        manual_curve_target_flux,
        100.0,
        1.0e-12,
    )

    manual_required_curve_point = (
        get_response_curve_point_by_thickness(
            manual_response_curve,
            manual_buildup_flux_target_result.required_thickness,
        )
    )

    manual_required_buildup_flux = assert_not_none(
        "V1.10 manual required-thickness buildup flux",
        manual_required_curve_point.buildup_corrected_flux,
    )

    assert_less_than_or_equal(
        "V1.10 manual curve reaches target at required thickness",
        manual_required_buildup_flux,
        100.000001,
    )

    all_manual_buildup_points_available = all(
        point.buildup_corrected_flux is not None
        for point in manual_response_curve.points
    )

    assert_equal(
        "V1.10 supported lead curve stores buildup values",
        all_manual_buildup_points_available,
        True,
    )

    lead_feasibility = get_feasibility_row_by_material_key(
    feasibility_rows,
    "lead",
    )

    assert_equal(
        "V1.10 lead passes thickness constraint",
        lead_feasibility.thickness_status,
        "PASS",
    )

    assert_equal(
        "V1.10 lead passes mass constraint",
        lead_feasibility.mass_status,
        "PASS",
    )

    assert_equal(
        "V1.10 lead cost constraint is inactive",
        lead_feasibility.cost_status,
        "INACTIVE",
    )

    assert_equal(
        "V1.10 lead is selected",
        lead_feasibility.is_selected,
        True,
    )

    copper_feasibility = get_feasibility_row_by_material_key(
        feasibility_rows,
        "copper",
    )

    assert_equal(
        "V1.10 copper passes thickness constraint",
        copper_feasibility.thickness_status,
        "PASS",
    )

    assert_equal(
        "V1.10 copper fails mass constraint",
        copper_feasibility.mass_status,
        "FAIL",
    )

    assert_equal(
        "V1.10 copper is rejected overall",
        copper_feasibility.optimization_status,
        "REJECTED",
    )

    tin_feasibility = get_feasibility_row_by_material_key(
        feasibility_rows,
        "tin",
    )

    assert_equal(
        "V1.10 tin passes thickness constraint",
        tin_feasibility.thickness_status,
        "PASS",
    )

    assert_equal(
        "V1.10 tin fails mass constraint",
        tin_feasibility.mass_status,
        "FAIL",
    )

    water_feasibility = get_feasibility_row_by_material_key(
        feasibility_rows,
        "water",
    )

    assert_equal(
        "V1.10 water fails thickness constraint",
        water_feasibility.thickness_status,
        "FAIL",
    )

    assert_equal(
        "V1.10 water passes mass constraint",
        water_feasibility.mass_status,
        "PASS",
    )

    concrete_feasibility = get_feasibility_row_by_material_key(
        feasibility_rows,
        "concrete_ordinary",
    )

    assert_equal(
        "V1.10 ordinary concrete fails thickness constraint",
        concrete_feasibility.thickness_status,
        "FAIL",
    )

    assert_equal(
        "V1.10 ordinary concrete fails mass constraint",
        concrete_feasibility.mass_status,
        "FAIL",
    )

    # Validate unsupported buildup behavior.
    #
    # Polyethylene does not have implemented G-P coefficient data.
    # Its uncollided curve should still be calculated, while every buildup
    # value remains unavailable.

    unsupported_buildup_curve = create_response_curve(
        source=manual_source,
        material=materials["polyethylene"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=5.0,
        number_of_points=6,
        apply_buildup=True,
    )

    unsupported_buildup_values_are_none = all(
        point.buildup_corrected_flux is None
        for point in unsupported_buildup_curve.points
    )

    assert_equal(
        "V1.10 unsupported material does not invent buildup curve values",
        unsupported_buildup_values_are_none,
        True,
    )

    assert_greater_than(
        "V1.10 unsupported buildup curve generates warning",
        len(unsupported_buildup_curve.warnings),
        0,
    )


    # Validate buildup termination at the 40-MFP limit.
    #
    # At 0.6617 MeV, lead reaches 40 MFP at approximately 31.75 cm.
    # The narrow-beam curve continues through 40 cm, while the buildup
    # series should contain valid early points and unavailable later points.

    limited_buildup_curve = create_response_curve(
        source=manual_source,
        material=materials["lead"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=40.0,
        number_of_points=7,
        apply_buildup=True,
    )

    valid_buildup_point_count = sum(
        point.buildup_corrected_flux is not None
        for point in limited_buildup_curve.points
    )

    unavailable_buildup_point_count = sum(
        point.buildup_corrected_flux is None
        for point in limited_buildup_curve.points
    )

    assert_greater_than(
        "V1.10 limited buildup curve contains valid early points",
        valid_buildup_point_count,
        0,
    )

    assert_greater_than(
        "V1.10 limited buildup curve stops outside valid range",
        unavailable_buildup_point_count,
        0,
    )

    first_unavailable_buildup_index = next(
        index
        for index, point in enumerate(limited_buildup_curve.points)
        if point.buildup_corrected_flux is None
    )

    buildup_remains_unavailable = all(
        point.buildup_corrected_flux is None
        for point in limited_buildup_curve.points[
            first_unavailable_buildup_index:
        ]
    )

    assert_equal(
        "V1.10 buildup remains unavailable after curve termination",
        buildup_remains_unavailable,
        True,
    )


    # Validate isotope-source response-curve generation.

    isotope_response_curve = create_response_curve(
        source=cs137_source,
        material=materials["lead"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=21,
        apply_buildup=True,
        target=FluxTarget(100.0),
        required_thickness_cm=(
            cs137_buildup_flux_target_result.required_thickness
        ),
    )

    assert_equal(
        "V1.10 isotope response curve preserves source name",
        isotope_response_curve.source_name,
        "Cs-137",
    )

    isotope_unshielded_flux = calculate_unshielded_isotope_flux(
        cs137_source,
        detector_distance,
    )

    assert_close(
        "V1.10 isotope curve zero-thickness flux equals unshielded flux",
        isotope_response_curve.points[0].uncollided_flux,
        isotope_unshielded_flux,
        1.0e-6,
    )

    assert_greater_than(
        "V1.10 isotope uncollided flux decreases with shielding",
        isotope_response_curve.points[0].uncollided_flux,
        isotope_response_curve.points[-1].uncollided_flux,
    )

    isotope_curve_target_flux = assert_not_none(
        "V1.10 isotope curve target flux",
        isotope_response_curve.target_flux,
    )

    assert_close(
        "V1.10 isotope response curve stores target flux",
        isotope_curve_target_flux,
        100.0,
        1.0e-12,
    )

    isotope_required_curve_point = (
        get_response_curve_point_by_thickness(
            isotope_response_curve,
            cs137_buildup_flux_target_result.required_thickness,
        )
    )

    isotope_required_buildup_flux = assert_not_none(
        "V1.10 isotope required-thickness buildup flux",
        isotope_required_curve_point.buildup_corrected_flux,
    )

    assert_less_than_or_equal(
        "V1.10 isotope curve reaches target at required thickness",
        isotope_required_buildup_flux,
        100.000001,
    )

    assert_equal(
        "V1.10 value below maximum passes constraint",
        evaluate_maximum_constraint(19.0, 20.0),
        "PASS",
    )

    assert_equal(
        "V1.10 value equal to maximum passes constraint",
        evaluate_maximum_constraint(20.0, 20.0),
        "PASS",
    )

    assert_equal(
        "V1.10 value above maximum fails constraint",
        evaluate_maximum_constraint(21.0, 20.0),
        "FAIL",
    )

    assert_equal(
        "V1.10 missing maximum produces inactive constraint",
        evaluate_maximum_constraint(20.0, None),
        "INACTIVE",
    )

    assert_equal(
        "V1.10 missing metric produces unavailable constraint",
        evaluate_maximum_constraint(None, 20.0),
        "UNAVAILABLE",
    )

    # Validate response-curve input rejection.

    try:
        create_response_curve(
            source=manual_source,
            material=materials["lead"],
            detector_distance_cm=100.0,
            minimum_thickness_cm=0.0,
            maximum_thickness_cm=101.0,
            number_of_points=10,
        )

        raise AssertionError(
            "Response curve beyond detector distance should have failed."
        )

    except ValueError:
        print(
            "PASS: V1.10 response curve beyond detector distance rejected"
        )

    try:
        create_thickness_samples(
            minimum_thickness_cm=0.0,
            maximum_thickness_cm=10.0,
            number_of_points=1,
        )

        raise AssertionError(
            "Response curve with one sample should have failed."
        )

    except ValueError:
        print(
            "PASS: V1.10 response curve with insufficient samples rejected"
        )


    # Validate expected error handling for invalid user inputs.

    try:
        convert_activity_to_bq(1.0, "banana")
        raise AssertionError("Unsupported activity unit should have failed.")
    except ValueError:
        print("PASS: Unsupported activity unit rejected")

    try:
        create_isotope_source("fake_isotope", one_ci_bq)
        raise AssertionError("Unsupported isotope source should have failed.")
    except ValueError:
        print("PASS: Unsupported isotope source rejected")

    try:
        convert_activity_to_bq(-1.0, "ci")
        raise AssertionError("Negative activity should have failed.")
    except ValueError:
        print("PASS: Negative activity rejected")

    print("\nAll validation tests passed.")


if __name__ == "__main__":
    run_validation_tests()