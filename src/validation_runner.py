# Validation runner for benchmark and regression tests.
#
# This script is intended to be run after major code changes.
# It validates the physics helpers, source calculations, minimum-thickness
# design logic, buildup-aware behavior, material comparison behavior, and
# important error-handling cases.
#
# It is intentionally separate from main.py so validation can run without
# interactive user input.

from target_models import (
    AirKermaMinimumThicknessResult,
    AirKermaRateTarget,
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from thickness_calculator import (
    calculate_air_kerma_minimum_thickness,
    calculate_air_kerma_response_at_thickness,
    calculate_isotope_minimum_thickness,
    calculate_manual_minimum_thickness,
    calculate_maximum_gp_valid_thickness_cm,
    calculate_unshielded_isotope_flux,
    calculate_unshielded_manual_flux,
    get_source_photon_energies_mev,
    get_target_description,
)
from buildup import calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from buildup_library import get_gp_coefficients_library
from material_library import get_material_library
from models import Layer
from source_calculator import calculate_isotope_source_result, calculate_manual_source_result
from source_library import create_isotope_source, get_available_isotopes
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
    PhotonLine,
)
from design_optimizer import (
    AirKermaMaterialDesignCandidate,
    compare_materials_for_air_kerma_target,
    compare_materials_for_target,
)
from constraint_optimizer import (
    calculate_mass_per_area,
    calculate_relative_cost_index_per_area,
    optimize_air_kerma_material_selection,
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
from plotting_utils import format_plot_text
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from geometry_models import (
    ConcentricSphericalGeometry,
    ShieldLayerSpec,
)
from scenario_io import (
    load_scenario,
    save_scenario,
    scenario_from_dict,
    scenario_to_dict,
)
from scenario_models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ShieldingScenario,
)
from scenario_runner import (
    create_runtime_source,
    resolve_candidate_materials,
    run_scenario,
)
from air_response import (
    aggregate_source_air_kerma_results,
    calculate_collision_air_kerma_rate_gy_per_s,
    calculate_collision_air_kerma_rate_microgy_per_h,
    calculate_energy_fluence_rate_mev_per_cm2_s,
    calculate_photon_line_air_kerma_result,
    calculate_source_air_kerma_result,
    get_air_kerma_coefficient_at_energy,
    get_exact_air_kerma_coefficient,
    log_log_interpolate_positive_value,
)

from air_response_library import (
    NIST_DRY_AIR_COEFFICIENT_SOURCE,
    get_dry_air_mu_en_over_rho_library,
)

from unit_conversions import (
    convert_activity_to_bq,
    convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s,
    convert_gy_per_s_to_microgy_per_h,
    convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg,
    convert_mev_to_joules,
    convert_microgy_per_h_to_gy_per_s,
)
from collections.abc import Callable
from output import (
    print_air_kerma_material_comparison_result,
    print_air_kerma_minimum_thickness_result,
    print_material_comparison_result,
    print_minimum_thickness_result,
    print_optimized_design_result,
    print_source_air_kerma_result,
    print_source_results,
)
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from input_handler import (
    get_response_quantity_from_user,
    get_target_from_user,
)
from main import (
    run_fixed_thickness_mode,
    run_material_comparison_mode,
    run_material_optimization_mode,
    run_minimum_thickness_mode,
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


def assert_raises(
    name: str,
    expected_exception: type[Exception],
    function: Callable[[], object],
    expected_message: str | None = None,
) -> None:
    # Confirm that a callable rejects invalid input using the expected
    # exception type and, optionally, a recognizable error message.

    try:
        function()

    except expected_exception as error:
        if (
            expected_message is not None
            and expected_message not in str(error)
        ):
            raise AssertionError(
                f"{name} failed: expected message containing "
                f"{expected_message!r}, got {str(error)!r}"
            ) from error

        print(f"PASS: {name}")
        return

    except Exception as error:
        raise AssertionError(
            f"{name} failed: expected "
            f"{expected_exception.__name__}, got "
            f"{type(error).__name__}: {error}"
        ) from error

    raise AssertionError(
        f"{name} failed: expected "
        f"{expected_exception.__name__}, but no exception was raised"
    )


def get_candidate_by_material_key(comparison_result, material_key: str):
    for candidate in comparison_result.candidates:
        if candidate.material.key == material_key:
            return candidate

    raise AssertionError(f"Candidate not found for material key: {material_key}")


def get_air_kerma_candidate_by_material_key(
    comparison_result,
    material_key: str,
):
    for candidate in comparison_result.candidates:
        if candidate.material.key == material_key:
            return candidate

    raise AssertionError(
        "Air-kerma candidate not found for material key: "
        f"{material_key}"
    )


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

    assert_equal(
        "V1.10 plot typography formats comparison symbols and units",
        format_plot_text(
            "Flux target <= 100 photons/cm^2/s; "
            "density >= 1 g/cm^3"
        ),
        (
            "Flux target ≤ 100 photons/cm²/s; "
            "density ≥ 1 g/cm³"
        ),
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

    run_v111_validation_tests()
    run_v112_validation_tests()
    print("\nAll validation tests passed.")


def run_v111_validation_tests() -> None:
    # Validate V1.11 reproducible scenario and spherical geometry behavior.
    #
    # These tests focus on:
    #   - geometry derivation and rejection
    #   - serializable source specifications
    #   - runtime source conversion
    #   - scenario JSON serialization and loading
    #   - scenario-level combination validation
    #   - material resolution
    #   - reproduction of the official V1.10 optimization result

    # ------------------------------------------------------------
    # Concentric spherical geometry
    # ------------------------------------------------------------

    lead_layer_spec = ShieldLayerSpec(
        material_key="  LEAD  ",
        thickness_cm=5.0,
    )

    copper_layer_spec = ShieldLayerSpec(
        material_key="copper",
        thickness_cm=1.0,
    )

    assert_equal(
        "V1.11 shield layer normalizes material key",
        lead_layer_spec.material_key,
        "lead",
    )

    layered_geometry = ConcentricSphericalGeometry(
        source_cavity_radius_cm=2.0,
        evaluation_radius_cm=100.0,
        layers=[
            lead_layer_spec,
            copper_layer_spec,
        ],
    )

    assert_close(
        "V1.11 spherical geometry total shield thickness",
        layered_geometry.total_shield_thickness_cm,
        6.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 spherical geometry outer shield radius",
        layered_geometry.outer_shield_radius_cm,
        8.0,
        1.0e-12,
    )

    derived_shells = layered_geometry.create_shells()

    assert_equal(
        "V1.11 spherical geometry creates two shells",
        len(derived_shells),
        2,
    )

    assert_close(
        "V1.11 first shell inner radius",
        derived_shells[0].inner_radius_cm,
        2.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 first shell outer radius",
        derived_shells[0].outer_radius_cm,
        7.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 second shell inner radius",
        derived_shells[1].inner_radius_cm,
        7.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 second shell outer radius",
        derived_shells[1].outer_radius_cm,
        8.0,
        1.0e-12,
    )

    assert_raises(
        "V1.11 nonpositive layer thickness rejected",
        ValueError,
        lambda: ShieldLayerSpec(
            material_key="lead",
            thickness_cm=0.0,
        ),
        "greater than zero",
    )

    assert_raises(
        "V1.11 evaluation radius inside shield rejected",
        ValueError,
        lambda: ConcentricSphericalGeometry(
            source_cavity_radius_cm=2.0,
            evaluation_radius_cm=7.0,
            layers=[
                ShieldLayerSpec(
                    material_key="lead",
                    thickness_cm=5.0,
                )
            ],
        ),
        "beyond the outer shield radius",
    )

    # ------------------------------------------------------------
    # Source specifications and runtime conversion
    # ------------------------------------------------------------

    isotope_source_spec = IsotopeSourceSpec(
        isotope_key="  CS137  ",
        activity_bq=3.7e10,
    )

    assert_equal(
        "V1.11 isotope source normalizes isotope key",
        isotope_source_spec.isotope_key,
        "cs137",
    )

    manual_source_spec = ManualPhotonSourceSpec(
        photon_energy_mev=0.661657,
        photon_rate_per_s=3.7e10,
    )

    runtime_manual_source = create_runtime_source(
        manual_source_spec
    )

    if not isinstance(
        runtime_manual_source,
        ManualPhotonSource,
    ):
        raise AssertionError(
            "V1.11 manual source adapter returned "
            "the wrong runtime source type."
        )


    assert_close(
        "V1.11 manual source adapter preserves energy",
        runtime_manual_source.energy,
        0.661657,
        1.0e-12,
    )

    assert_close(
        "V1.11 manual source adapter preserves photon rate",
        runtime_manual_source.photon_rate,
        3.7e10,
        1.0e-6,
    )

    runtime_isotope_source = create_runtime_source(
        isotope_source_spec
    )

    if not isinstance(
        runtime_isotope_source,
        IsotopeSource,
    ):
        raise AssertionError(
            "V1.11 isotope source adapter returned "
            "the wrong runtime source type."
        )


    assert_equal(
        "V1.11 isotope source adapter creates Cs-137 source",
        runtime_isotope_source.name,
        "Cs-137",
    )

    assert_close(
        "V1.11 isotope source adapter preserves activity",
        runtime_isotope_source.activity_bq,
        3.7e10,
        1.0e-6,
    )

    assert_raises(
        "V1.11 nonpositive calculation search limit rejected",
        ValueError,
        lambda: DeterministicSettings(
            calculation_max_thickness_cm=0.0
        ),
        "greater than zero",
    )

    # ------------------------------------------------------------
    # Official JSON scenario
    # ------------------------------------------------------------

    repository_root = Path(__file__).resolve().parents[1]

    reference_scenario_path = (
        repository_root
        / "scenarios"
        / "cs137_v110_reference.json"
    )

    assert_equal(
        "V1.11 official reference scenario file exists",
        reference_scenario_path.is_file(),
        True,
    )

    reference_scenario = load_scenario(
        reference_scenario_path
    )

    assert_equal(
        "V1.11 loaded scenario preserves scenario ID",
        reference_scenario.scenario_id,
        "cs137_v110_reference",
    )

    assert_equal(
        "V1.11 loaded scenario preserves schema version",
        reference_scenario.schema_version,
        "1.0",
    )

    assert_equal(
        "V1.11 loaded scenario preserves nine candidates",
        len(reference_scenario.candidate_material_keys),
        9,
    )

    assert_equal(
        "V1.11 loaded scenario reconstructs spherical geometry",
        isinstance(
            reference_scenario.geometry,
            ConcentricSphericalGeometry,
        ),
        True,
    )

    loaded_target = reference_scenario.target

    if not isinstance(loaded_target, FluxTarget):
        raise AssertionError(
            "V1.11 reference scenario did not reconstruct "
            "a FluxTarget."
        )

    assert_close(
        "V1.11 loaded scenario preserves flux target",
        loaded_target.target_flux,
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.11 loaded scenario preserves buildup setting",
        (
            reference_scenario
            .deterministic_settings
            .apply_buildup
        ),
        True,
    )

    # ------------------------------------------------------------
    # Dictionary serialization and reconstruction
    # ------------------------------------------------------------

    reference_scenario_data = scenario_to_dict(
        reference_scenario
    )

    assert_equal(
        "V1.11 serialized source contains explicit type",
        reference_scenario_data["source"]["type"],
        "isotope",
    )

    assert_equal(
        "V1.11 serialized geometry contains explicit type",
        reference_scenario_data["geometry"]["type"],
        "concentric_spherical",
    )

    assert_equal(
        "V1.11 serialized target contains explicit type",
        reference_scenario_data["target"]["type"],
        "flux",
    )

    assert_equal(
        "V1.11 serialized optimization preserves mode",
        reference_scenario_data["optimization"]["mode"],
        "minimum_mass",
    )

    reconstructed_scenario = scenario_from_dict(
        reference_scenario_data
    )

    assert_equal(
        "V1.11 dictionary reconstruction preserves scenario",
        reconstructed_scenario,
        reference_scenario,
    )

    # ------------------------------------------------------------
    # File round-trip and malformed-file behavior
    # ------------------------------------------------------------

    with TemporaryDirectory() as temporary_directory:
        temporary_path = Path(
            temporary_directory
        )

        roundtrip_path = (
            temporary_path
            / "roundtrip_scenario.json"
        )

        saved_path = save_scenario(
            reference_scenario,
            roundtrip_path,
        )

        assert_equal(
            "V1.11 scenario save creates JSON file",
            saved_path.is_file(),
            True,
        )

        roundtrip_scenario = load_scenario(
            roundtrip_path
        )

        assert_equal(
            "V1.11 scenario JSON round trip preserves object",
            roundtrip_scenario,
            reference_scenario,
        )

        unsupported_schema_data = json.loads(
            json.dumps(reference_scenario_data)
        )

        unsupported_schema_data[
            "schema_version"
        ] = "99.0"

        assert_raises(
            "V1.11 unsupported schema version rejected",
            ValueError,
            lambda: scenario_from_dict(
                unsupported_schema_data
            ),
            "Unsupported scenario schema version",
        )

        invalid_json_path = (
            temporary_path
            / "invalid.json"
        )

        invalid_json_path.write_text(
            '{"scenario_id": ',
            encoding="utf-8",
        )

        assert_raises(
            "V1.11 malformed JSON rejected",
            ValueError,
            lambda: load_scenario(
                invalid_json_path
            ),
            "invalid JSON",
        )

        missing_field_data = json.loads(
            json.dumps(reference_scenario_data)
        )

        missing_field_data.pop(
            "source"
        )

        missing_field_path = (
            temporary_path
            / "missing_source.json"
        )

        with missing_field_path.open(
            mode="w",
            encoding="utf-8",
        ) as missing_field_file:
            json.dump(
                missing_field_data,
                missing_field_file,
                indent=2,
            )

        assert_raises(
            "V1.11 missing required JSON field rejected",
            ValueError,
            lambda: load_scenario(
                missing_field_path
            ),
            "missing required field",
        )

    # ------------------------------------------------------------
    # Complete scenario validation
    # ------------------------------------------------------------

    assert_raises(
        "V1.11 duplicate candidate materials rejected",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="duplicate_material_test",
            description=(
                "Scenario duplicate-material validation test."
            ),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=0.0,
                evaluation_radius_cm=100.0,
            ),
            candidate_material_keys=[
                "lead",
                "  LEAD  ",
            ],
            target=FluxTarget(
                target_flux=100.0
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
        ),
        "must be unique",
    )

    assert_raises(
        "V1.11 optimization scenario rejects fixed layers",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="fixed_layer_test",
            description=(
                "Scenario fixed-layer validation test."
            ),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=2.0,
                evaluation_radius_cm=100.0,
                layers=[
                    ShieldLayerSpec(
                        material_key="lead",
                        thickness_cm=1.0,
                    )
                ],
            ),
            candidate_material_keys=[
                "lead",
            ],
            target=FluxTarget(
                target_flux=100.0
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
        ),
        "cannot contain fixed shield layers",
    )

    assert_raises(
        "V1.11 calculation limit beyond radial space rejected",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="radial_limit_test",
            description=(
                "Scenario radial-space validation test."
            ),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=10.0,
                evaluation_radius_cm=100.0,
            ),
            candidate_material_keys=[
                "lead",
            ],
            target=FluxTarget(
                target_flux=100.0
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
            deterministic_settings=DeterministicSettings(
                calculation_max_thickness_cm=90.1
            ),
        ),
        "cannot exceed the radial space",
    )

    # ------------------------------------------------------------
    # Material resolution
    # ------------------------------------------------------------

    resolved_materials = resolve_candidate_materials(
        [
            "lead",
            "water",
        ]
    )

    assert_equal(
        "V1.11 material resolver preserves candidate count",
        len(resolved_materials),
        2,
    )

    assert_equal(
        "V1.11 material resolver preserves first material order",
        resolved_materials[0].key,
        "lead",
    )

    assert_equal(
        "V1.11 material resolver preserves second material order",
        resolved_materials[1].key,
        "water",
    )

    assert_raises(
        "V1.11 unknown material key rejected",
        ValueError,
        lambda: resolve_candidate_materials(
            [
                "lead",
                "unobtainium",
            ]
        ),
        "unknown material keys",
    )

    # ------------------------------------------------------------
    # Complete deterministic execution
    # ------------------------------------------------------------

    scenario_result = run_scenario(
        reference_scenario
    )

    assert_equal(
        "V1.11 reference scenario returns nine candidates",
        len(scenario_result.all_candidates),
        9,
    )

    best_candidate = scenario_result.best_candidate

    assert_equal(
        "V1.11 reference scenario selects a candidate",
        best_candidate is not None,
        True,
    )

    if best_candidate is None:
        raise AssertionError(
            "V1.11 reference scenario requires a selected candidate."
        )

    assert_equal(
        "V1.11 reference scenario selects lead",
        best_candidate.base_candidate.material.key,
        "lead",
    )

    lead_required_thickness = assert_not_none(
        "V1.11 selected Lead required thickness",
        best_candidate.base_candidate.required_thickness,
    )

    lead_mass_per_area = assert_not_none(
        "V1.11 selected Lead mass per area",
        best_candidate.mass_per_area_g_per_cm2,
    )

    assert_close(
        "V1.11 reference scenario reproduces lead thickness",
        lead_required_thickness,
        7.088213,
        1.0e-5,
    )

    assert_close(
        "V1.11 reference scenario reproduces lead mass per area",
        lead_mass_per_area,
        80.3803,
        1.0e-3,
    )

    assert_equal(
        "V1.11 reference scenario provides selection reason",
        scenario_result.selection_reason is not None,
        True,
    )


def run_v112_validation_tests() -> None:
    # Validate the V1.12 radiation-response quantity foundation.
    #
    # These tests cover:
    #   - dry-air coefficient data and provenance
    #   - exact lookup and log-log interpolation
    #   - absorption-edge behavior
    #   - unit conversions
    #   - energy-fluence and collision-air-kerma calculations
    #   - line-level response construction
    #   - source-level response aggregation
    #   - real shielding and G-P exposure-buildup integration
    #   - Cs-137, Co-60, and Am-241 behavior

    # ------------------------------------------------------------
    # Dry-air response-coefficient library
    # ------------------------------------------------------------

    air_library = (
        get_dry_air_mu_en_over_rho_library()
    )

    assert_equal(
        "V1.12 dry-air coefficient library contains 38 entries",
        len(air_library),
        38,
    )

    assert_equal(
        "V1.12 dry-air coefficient energies are nondecreasing",
        all(
            air_library[index].photon_energy_mev
            <= air_library[index + 1].photon_energy_mev
            for index in range(len(air_library) - 1)
        ),
        True,
    )

    exact_006_coefficient = (
        get_exact_air_kerma_coefficient(
            0.06
        )
    )

    assert_close(
        "V1.12 exact dry-air coefficient lookup",
        exact_006_coefficient.mu_en_over_rho_cm2_per_g,
        0.03041,
        1.0e-12,
    )

    assert_equal(
        "V1.12 dry-air coefficient preserves source metadata",
        exact_006_coefficient.source,
        NIST_DRY_AIR_COEFFICIENT_SOURCE,
    )

    cs137_coefficient = (
        get_air_kerma_coefficient_at_energy(
            0.661657
        )
    )

    assert_close(
        "V1.12 Cs-137 dry-air coefficient interpolation",
        cs137_coefficient.mu_en_over_rho_cm2_per_g,
        0.02928664455391956,
        1.0e-12,
    )

    below_edge = (
        get_exact_air_kerma_coefficient(
            0.0032029,
            edge_side="below",
        )
    )

    above_edge = (
        get_exact_air_kerma_coefficient(
            0.0032029,
            edge_side="above",
        )
    )

    assert_close(
        "V1.12 argon edge below-edge coefficient",
        below_edge.mu_en_over_rho_cm2_per_g,
        133.0,
        1.0e-12,
    )

    assert_close(
        "V1.12 argon edge above-edge coefficient",
        above_edge.mu_en_over_rho_cm2_per_g,
        146.0,
        1.0e-12,
    )

    assert_raises(
        "V1.12 ambiguous absorption-edge lookup rejected",
        ValueError,
        lambda: get_exact_air_kerma_coefficient(
            0.0032029
        ),
        "absorption edge",
    )

    assert_raises(
        "V1.12 out-of-range dry-air coefficient rejected",
        ValueError,
        lambda: get_air_kerma_coefficient_at_energy(
            25.0
        ),
        "outside the dry-air coefficient range",
    )

    logarithmic_midpoint = (
        log_log_interpolate_positive_value(
            x=(0.1 * 0.2) ** 0.5,
            x1=0.1,
            y1=0.02325,
            x2=0.2,
            y2=0.02672,
        )
    )

    assert_close(
        "V1.12 log-log interpolation geometric midpoint",
        logarithmic_midpoint,
        (0.02325 * 0.02672) ** 0.5,
        1.0e-12,
    )

    # ------------------------------------------------------------
    # Unit-conversion foundation
    # ------------------------------------------------------------

    assert_close(
        "V1.12 one MeV converts to joules",
        convert_mev_to_joules(
            1.0
        ),
        1.602176634e-13,
        1.0e-25,
    )

    assert_close(
        "V1.12 energy-fluence SI conversion",
        convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s(
            1.0
        ),
        1.602176634e-9,
        1.0e-21,
    )

    assert_close(
        "V1.12 mass energy-absorption coefficient SI conversion",
        convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg(
            1.0
        ),
        0.1,
        1.0e-12,
    )

    assert_close(
        "V1.12 Gy per second converts to microGy per hour",
        convert_gy_per_s_to_microgy_per_h(
            1.0
        ),
        3.6e9,
        1.0e-3,
    )

    assert_close(
        "V1.12 microGy per hour converts to Gy per second",
        convert_microgy_per_h_to_gy_per_s(
            3.6e9
        ),
        1.0,
        1.0e-12,
    )

    # ------------------------------------------------------------
    # Energy fluence and collision air kerma
    # ------------------------------------------------------------

    cs137_energy_fluence = (
        calculate_energy_fluence_rate_mev_per_cm2_s(
            photon_energy_mev=0.661657,
            photon_fluence_rate_per_cm2_s=100.0,
        )
    )

    assert_close(
        "V1.12 Cs-137 energy-fluence calculation",
        cs137_energy_fluence,
        66.1657,
        1.0e-12,
    )

    cs137_air_kerma_gy_per_s = (
        calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=(
                cs137_energy_fluence
            ),
            mu_en_over_rho_cm2_per_g=(
                cs137_coefficient
                .mu_en_over_rho_cm2_per_g
            ),
        )
    )

    assert_close(
        "V1.12 Cs-137 collision air-kerma rate in Gy per second",
        cs137_air_kerma_gy_per_s,
        3.1046519590756025e-10,
        1.0e-20,
    )

    assert_close(
        "V1.12 Cs-137 collision air-kerma rate in microGy per hour",
        calculate_collision_air_kerma_rate_microgy_per_h(
            cs137_energy_fluence,
            cs137_coefficient.mu_en_over_rho_cm2_per_g,
        ),
        1.117674705267217,
        1.0e-10,
    )

    assert_close(
        "V1.12 zero energy fluence produces zero air kerma",
        calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=0.0,
            mu_en_over_rho_cm2_per_g=(
                cs137_coefficient
                .mu_en_over_rho_cm2_per_g
            ),
        ),
        0.0,
        1.0e-20,
    )

    assert_raises(
        "V1.12 nonpositive response coefficient rejected",
        ValueError,
        lambda: calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=1.0,
            mu_en_over_rho_cm2_per_g=0.0,
        ),
        "must be greater than zero",
    )

    # ------------------------------------------------------------
    # Photon-line response model
    # ------------------------------------------------------------

    cs137_line = PhotonLine(
        energy=0.661657,
        intensity=0.851,
    )

    cs137_line_result = (
        calculate_photon_line_air_kerma_result(
            photon_line=cs137_line,
            photon_rate_per_s=3.1487e10,
            uncollided_photon_fluence_rate_per_cm2_s=100.0,
        )
    )

    assert_equal(
        "V1.12 photon line defaults to no buildup requested",
        cs137_line_result.buildup_status,
        "not_requested",
    )

    assert_close(
        "V1.12 photon line stores interpolated response coefficient",
        cs137_line_result.air_mu_en_over_rho_cm2_per_g,
        0.02928664455391956,
        1.0e-12,
    )

    assert_close(
        "V1.12 photon line stores uncollided air-kerma response",
        (
            cs137_line_result
            .uncollided_collision_air_kerma_rate_gy_per_s
        ),
        3.1046519590756025e-10,
        1.0e-20,
    )

    assert_equal(
        "V1.12 unrequested line buildup has no adjusted response",
        (
            cs137_line_result
            .buildup_adjusted_collision_air_kerma_rate_gy_per_s
        ),
        None,
    )

    cs137_buildup_line_result = (
        calculate_photon_line_air_kerma_result(
            photon_line=cs137_line,
            photon_rate_per_s=3.1487e10,
            uncollided_photon_fluence_rate_per_cm2_s=100.0,
            buildup_status="applied",
            buildup_factor=2.5,
        )
    )

    assert_equal(
        "V1.12 photon line stores applied buildup status",
        cs137_buildup_line_result.buildup_status,
        "applied",
    )

    assert_close(
        "V1.12 photon line stores buildup factor",
        assert_not_none(
            "V1.12 buildup factor exists",
            cs137_buildup_line_result.buildup_factor,
        ),
        2.5,
        1.0e-12,
    )

    assert_close(
        "V1.12 buildup-adjusted line response uses supplied factor",
        assert_not_none(
            "V1.12 adjusted line response exists",
            (
                cs137_buildup_line_result
                .buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        (
            cs137_buildup_line_result
            .uncollided_collision_air_kerma_rate_gy_per_s
            * 2.5
        ),
        1.0e-20,
    )

    assert_raises(
        "V1.12 buildup factor rejected when buildup not requested",
        ValueError,
        lambda: calculate_photon_line_air_kerma_result(
            photon_line=cs137_line,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=1.0,
            buildup_status="not_requested",
            buildup_factor=2.0,
        ),
        "may only be supplied",
    )

    # ------------------------------------------------------------
    # Source-level aggregation
    # ------------------------------------------------------------

    co60_line_1 = PhotonLine(
        energy=1.173228,
        intensity=0.9985,
    )

    co60_line_2 = PhotonLine(
        energy=1.332492,
        intensity=0.9998,
    )

    co60_line_result_1 = (
        calculate_photon_line_air_kerma_result(
            photon_line=co60_line_1,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=100.0,
        )
    )

    co60_line_result_2 = (
        calculate_photon_line_air_kerma_result(
            photon_line=co60_line_2,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=80.0,
        )
    )

    co60_aggregate = (
        aggregate_source_air_kerma_results(
            source_name="Co-60",
            activity_bq=3.7e10,
            line_results=[
                co60_line_result_1,
                co60_line_result_2,
            ],
        )
    )

    assert_close(
        "V1.12 source aggregation sums photon fluence",
        (
            co60_aggregate
            .total_uncollided_photon_fluence_rate_per_cm2_s
        ),
        180.0,
        1.0e-12,
    )

    assert_close(
        "V1.12 source aggregation sums uncollided air kerma",
        (
            co60_aggregate
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        (
            co60_line_result_1
            .uncollided_collision_air_kerma_rate_gy_per_s
            + co60_line_result_2
            .uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    assert_equal(
        "V1.12 uncollided source aggregation preserves buildup status",
        co60_aggregate.buildup_status,
        "not_requested",
    )

    co60_buildup_line_1 = (
        calculate_photon_line_air_kerma_result(
            photon_line=co60_line_1,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=100.0,
            buildup_status="applied",
            buildup_factor=2.0,
        )
    )

    co60_buildup_line_2 = (
        calculate_photon_line_air_kerma_result(
            photon_line=co60_line_2,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=80.0,
            buildup_status="applied",
            buildup_factor=2.5,
        )
    )

    co60_buildup_aggregate = (
        aggregate_source_air_kerma_results(
            source_name="Co-60",
            activity_bq=3.7e10,
            line_results=[
                co60_buildup_line_1,
                co60_buildup_line_2,
            ],
        )
    )

    assert_equal(
        "V1.12 buildup source aggregation stores applied status",
        co60_buildup_aggregate.buildup_status,
        "applied",
    )

    expected_co60_adjusted_total = (
        assert_not_none(
            "V1.12 first Co-60 adjusted response exists",
            (
                co60_buildup_line_1
                .buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        )
        + assert_not_none(
            "V1.12 second Co-60 adjusted response exists",
            (
                co60_buildup_line_2
                .buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        )
    )

    assert_close(
        "V1.12 source aggregation sums buildup-adjusted air kerma",
        assert_not_none(
            "V1.12 Co-60 adjusted source total exists",
            (
                co60_buildup_aggregate
                .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        expected_co60_adjusted_total,
        1.0e-20,
    )

    assert_raises(
        "V1.12 mixed source buildup settings rejected",
        ValueError,
        lambda: aggregate_source_air_kerma_results(
            source_name="Co-60",
            activity_bq=3.7e10,
            line_results=[
                co60_line_result_1,
                co60_buildup_line_2,
            ],
        ),
        "cannot mix",
    )

    # ------------------------------------------------------------
    # Real shielding and G-P integration
    # ------------------------------------------------------------

    materials = get_material_library()

    lead_layers = [
        Layer(
            thickness=5.0,
            material=materials["lead"],
        )
    ]

    manual_source = ManualPhotonSource(
        energy=0.661657,
        photon_rate=3.7e10,
    )

    manual_result = (
        calculate_source_air_kerma_result(
            source=manual_source,
            layers=lead_layers,
            detector_distance_cm=100.0,
            apply_buildup=False,
        )
    )

    assert_equal(
        "V1.12 manual source produces one response line",
        len(manual_result.line_results),
        1,
    )

    assert_greater_than(
        "V1.12 shielded manual source produces positive air kerma",
        (
            manual_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        0.0,
    )

    manual_buildup_result = (
        calculate_source_air_kerma_result(
            source=manual_source,
            layers=lead_layers,
            detector_distance_cm=100.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 shielded manual source applies real G-P buildup",
        manual_buildup_result.buildup_status,
        "applied",
    )

    assert_greater_than(
        "V1.12 manual buildup-adjusted response exceeds uncollided response",
        assert_not_none(
            "V1.12 manual buildup-adjusted response exists",
            (
                manual_buildup_result
                .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        (
            manual_buildup_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
    )

    one_ci_bq = 3.7e10

    cs137_source = create_isotope_source(
        "cs137",
        one_ci_bq,
    )

    cs137_source_result = (
        calculate_source_air_kerma_result(
            source=cs137_source,
            layers=lead_layers,
            detector_distance_cm=100.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 Cs-137 response contains one selected photon line",
        len(cs137_source_result.line_results),
        1,
    )

    assert_equal(
        "V1.12 Cs-137 applies G-P exposure buildup",
        cs137_source_result.buildup_status,
        "applied",
    )

    co60_source = create_isotope_source(
        "co60",
        one_ci_bq,
    )

    co60_source_result = (
        calculate_source_air_kerma_result(
            source=co60_source,
            layers=lead_layers,
            detector_distance_cm=100.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 Co-60 response contains two photon lines",
        len(co60_source_result.line_results),
        2,
    )

    assert_close(
        "V1.12 Co-60 uncollided total equals line sum",
        (
            co60_source_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        sum(
            line_result
            .uncollided_collision_air_kerma_rate_gy_per_s
            for line_result
            in co60_source_result.line_results
        ),
        1.0e-20,
    )

    assert_close(
        "V1.12 Co-60 buildup-adjusted total equals line sum",
        assert_not_none(
            "V1.12 Co-60 buildup total exists",
            (
                co60_source_result
                .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        sum(
            assert_not_none(
                "V1.12 Co-60 adjusted line exists",
                (
                    line_result
                    .buildup_adjusted_collision_air_kerma_rate_gy_per_s
                ),
            )
            for line_result
            in co60_source_result.line_results
        ),
        1.0e-20,
    )

    am241_source = create_isotope_source(
        "am241",
        one_ci_bq,
    )

    am241_result = (
        calculate_source_air_kerma_result(
            source=am241_source,
            layers=lead_layers,
            detector_distance_cm=100.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 Am-241 buildup is unavailable beyond valid MFP range",
        am241_result.buildup_status,
        "unavailable",
    )

    assert_equal(
        "V1.12 unavailable Am-241 buildup has no adjusted total",
        (
            am241_result
            .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        ),
        None,
    )

    assert_greater_than(
        "V1.12 unavailable Am-241 buildup preserves warning",
        len(am241_result.warnings),
        0,
    )

    zero_thickness_result = (
        calculate_source_air_kerma_result(
            source=cs137_source,
            layers=[
                Layer(
                    thickness=0.0,
                    material=materials["lead"],
                )
            ],
            detector_distance_cm=100.0,
            apply_buildup=True,
        )
    )

    zero_thickness_line = (
        zero_thickness_result.line_results[0]
    )

    assert_close(
        "V1.12 zero-thickness G-P buildup factor equals one",
        assert_not_none(
            "V1.12 zero-thickness buildup factor exists",
            zero_thickness_line.buildup_factor,
        ),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.12 zero-thickness adjusted and uncollided responses match",
        assert_not_none(
            "V1.12 zero-thickness adjusted response exists",
            (
                zero_thickness_line
                .buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        (
            zero_thickness_line
            .uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    # ------------------------------------------------------------
    # Air-kerma target and minimum-thickness result models
    # ------------------------------------------------------------

    air_kerma_target = AirKermaRateTarget(
        target_air_kerma_rate_microgy_per_h=1.0
    )

    assert_close(
        "V1.12 air-kerma target converts microGy per hour to Gy per second",
        air_kerma_target.target_air_kerma_rate_gy_per_s,
        1.0 / 3.6e9,
        1.0e-20,
    )

    assert_raises(
        "V1.12 nonpositive air-kerma target rejected",
        ValueError,
        lambda: AirKermaRateTarget(
            target_air_kerma_rate_microgy_per_h=0.0
        ),
        "must be greater than zero",
    )

    uncollided_design_result = (
        AirKermaMinimumThicknessResult(
            material=materials["lead"],
            required_thickness=5.0,
            final_source_response=manual_result,
            final_response_ratio=0.5,
            target_description=(
                "Collision air-kerma-rate target <= 1 µGy/h"
            ),
            warnings=[],
            calculation_mode=(
                "Uncollided collision air-kerma "
                "minimum thickness design"
            ),
            buildup_used=False,
        )
    )

    assert_close(
        "V1.12 uncollided design selects uncollided air-kerma response",
        uncollided_design_result.final_air_kerma_rate_gy_per_s,
        (
            manual_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    assert_close(
        "V1.12 design result converts selected response to microGy per hour",
        uncollided_design_result.final_air_kerma_rate_microgy_per_h,
        convert_gy_per_s_to_microgy_per_h(
            manual_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-12,
    )

    buildup_design_result = (
        AirKermaMinimumThicknessResult(
            material=materials["lead"],
            required_thickness=5.0,
            final_source_response=cs137_source_result,
            final_response_ratio=0.5,
            target_description=(
                "G-P buildup-adjusted collision "
                "air-kerma-rate target <= 1 µGy/h"
            ),
            warnings=[],
            calculation_mode=(
                "G-P buildup-adjusted collision air-kerma "
                "minimum thickness design"
            ),
            buildup_used=True,
        )
    )

    assert_close(
        "V1.12 buildup design selects buildup-adjusted air-kerma response",
        buildup_design_result.final_air_kerma_rate_gy_per_s,
        assert_not_none(
            "V1.12 buildup design adjusted response exists",
            (
                cs137_source_result
                .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        1.0e-20,
    )

    assert_close(
        "V1.12 buildup design preserves uncollided source response",
        (
            buildup_design_result
            .final_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        (
            cs137_source_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    assert_raises(
        "V1.12 inconsistent buildup design result rejected",
        ValueError,
        lambda: AirKermaMinimumThicknessResult(
            material=materials["lead"],
            required_thickness=5.0,
            final_source_response=manual_result,
            final_response_ratio=0.5,
            target_description="Test target",
            warnings=[],
            buildup_used=True,
        ),
        "requires an applied source buildup result",
    )

    assert_raises(
        "V1.12 negative air-kerma response ratio rejected",
        ValueError,
        lambda: AirKermaMinimumThicknessResult(
            material=materials["lead"],
            required_thickness=5.0,
            final_source_response=manual_result,
            final_response_ratio=-0.1,
            target_description="Test target",
            warnings=[],
            buildup_used=False,
        ),
        "response ratio cannot be negative",
    )

    solver_materials = get_material_library()

    solver_lead = solver_materials["lead"]

    solver_target = AirKermaRateTarget(
        target_air_kerma_rate_microgy_per_h=1.0
    )

    manual_solver_source = ManualPhotonSource(
        energy=0.661657,
        photon_rate=3.7e10,
    )

    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
    )

    co60_solver_source = create_isotope_source(
        "co60",
        3.7e10,
    )

    assert_equal(
        "V1.12 manual source energy extraction",
        get_source_photon_energies_mev(
            manual_solver_source
        ),
        [
            0.661657
        ],
    )

    assert_equal(
        "V1.12 Co-60 source energy extraction",
        get_source_photon_energies_mev(
            co60_solver_source
        ),
        [
            1.173228,
            1.332492,
        ],
    )

    maximum_gp_thickness_cm = (
        calculate_maximum_gp_valid_thickness_cm(
            source=cs137_solver_source,
            material=solver_lead,
        )
    )

    assert_greater_than(
        "V1.12 G-P-valid thickness limit is positive",
        maximum_gp_thickness_cm,
        0.0,
    )

    near_gp_limit_response, _ = (
        calculate_air_kerma_response_at_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            thickness_cm=(
                maximum_gp_thickness_cm
                * 0.999999
            ),
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 response immediately below G-P limit applies buildup",
        near_gp_limit_response.buildup_status,
        "applied",
    )

    assert_raises(
        "V1.12 response beyond G-P validity limit rejected",
        ValueError,
        lambda: calculate_air_kerma_response_at_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            thickness_cm=(
                maximum_gp_thickness_cm
                * 1.000001
            ),
            apply_buildup=True,
        ),
        "requires valid G-P exposure buildup",
    )

    mn54_solver_source = create_isotope_source(
        "mn54",
        3.7e10,
    )

    copper_gp_limit_cm = (
        calculate_maximum_gp_valid_thickness_cm(
            source=mn54_solver_source,
            material=solver_materials["copper"],
        )
    )

    copper_limit_response, _ = (
        calculate_air_kerma_response_at_thickness(
            source=mn54_solver_source,
            material=solver_materials["copper"],
            detector_distance_cm=100.0,
            thickness_cm=copper_gp_limit_cm,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 floating-point 40-MFP boundary remains valid",
        copper_limit_response.buildup_status,
        "applied",
    )

    uncollided_solver_result = (
        calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=False,
        )
    )

    assert_greater_than(
        "V1.12 uncollided air-kerma design requires shielding",
        uncollided_solver_result.required_thickness,
        0.0,
    )

    assert_equal(
        "V1.12 uncollided air-kerma design satisfies target",
        (
            uncollided_solver_result
            .final_air_kerma_rate_gy_per_s
            <= solver_target
            .target_air_kerma_rate_gy_per_s
        ),
        True,
    )

    assert_equal(
        "V1.12 uncollided air-kerma design does not mark buildup used",
        uncollided_solver_result.buildup_used,
        False,
    )

    assert_equal(
        "V1.12 uncollided solver describes constrained quantity",
        uncollided_solver_result.target_description,
        (
            "Uncollided collision air-kerma rate "
            "<= 1 µGy/h"
        ),
    )

    buildup_solver_result = (
        calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=True,
        )
    )

    assert_greater_than(
        "V1.12 buildup-aware design requires more Lead than uncollided design",
        buildup_solver_result.required_thickness,
        uncollided_solver_result.required_thickness,
    )

    assert_equal(
        "V1.12 buildup-aware air-kerma design satisfies target",
        (
            buildup_solver_result
            .final_air_kerma_rate_gy_per_s
            <= solver_target
            .target_air_kerma_rate_gy_per_s
        ),
        True,
    )

    assert_equal(
        "V1.12 buildup-aware air-kerma design marks buildup used",
        buildup_solver_result.buildup_used,
        True,
    )

    assert_equal(
        "V1.12 buildup-aware design preserves applied source status",
        (
            buildup_solver_result
            .final_source_response
            .buildup_status
        ),
        "applied",
    )

    assert_equal(
        "V1.12 buildup-aware design response ratio is physical",
        (
            0.0
            < buildup_solver_result.final_response_ratio
            <= 1.0
        ),
        True,
    )

    assert_raises(
        "V1.12 unsupported buildup material is strictly rejected",
        ValueError,
        lambda: calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_materials["polyethylene"],
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=True,
        ),
        "requires valid G-P exposure buildup",
    )

    assert_raises(
        "V1.12 insufficient air-kerma search thickness rejected",
        ValueError,
        lambda: calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=0.1,
            apply_buildup=True,
        ),
        "cannot reach the requested air-kerma-rate target",
    )

    no_shielding_result = (
        calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=AirKermaRateTarget(
                target_air_kerma_rate_microgy_per_h=1.0e6
            ),
            max_thickness_cm=20.0,
            apply_buildup=True,
        )
    )

    assert_close(
        "V1.12 satisfied unshielded target returns zero thickness",
        no_shielding_result.required_thickness,
        0.0,
        1.0e-12,
    )

    assert_greater_than(
        "V1.12 unshielded target result preserves warning",
        len(no_shielding_result.warnings),
        0,
    )

    assert_raises(
        "V1.12 air-kerma search limit beyond detector rejected",
        ValueError,
        lambda: calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=101.0,
            apply_buildup=False,
        ),
        "cannot exceed the source-to-detector distance",
    )

    assert_raises(
        "V1.12 nonpositive air-kerma solver tolerance rejected",
        ValueError,
        lambda: calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=False,
            thickness_tolerance_cm=0.0,
        ),
        "tolerance must be greater than zero",
    )

        # ------------------------------------------------------------
    # Nonmonotonic buildup-response bracketing
    # ------------------------------------------------------------

    water_buildup_source = ManualPhotonSource(
        energy=0.1,
        photon_rate=3.7e10,
    )

    _, water_unshielded_rate = (
        calculate_air_kerma_response_at_thickness(
            source=water_buildup_source,
            material=solver_materials["water"],
            detector_distance_cm=100.0,
            thickness_cm=0.0,
            apply_buildup=True,
        )
    )

    _, water_one_cm_rate = (
        calculate_air_kerma_response_at_thickness(
            source=water_buildup_source,
            material=solver_materials["water"],
            detector_distance_cm=100.0,
            thickness_cm=1.0,
            apply_buildup=True,
        )
    )

    assert_greater_than(
        "V1.12 buildup response can initially increase with shielding",
        water_one_cm_rate,
        water_unshielded_rate,
    )

    water_buildup_target = AirKermaRateTarget(
        target_air_kerma_rate_microgy_per_h=(
            convert_gy_per_s_to_microgy_per_h(
                0.5
                * water_unshielded_rate
            )
        )
    )

    water_buildup_design = (
        calculate_air_kerma_minimum_thickness(
            source=water_buildup_source,
            material=solver_materials["water"],
            detector_distance_cm=100.0,
            target=water_buildup_target,
            max_thickness_cm=100.0,
            apply_buildup=True,
            bracket_scan_intervals=200,
        )
    )

    assert_greater_than(
        "V1.12 bracketed buildup design passes beyond initial response rise",
        water_buildup_design.required_thickness,
        1.0,
    )

    assert_equal(
        "V1.12 bracketed buildup design satisfies target",
        (
            water_buildup_design
            .final_air_kerma_rate_gy_per_s
            <= water_buildup_target
            .target_air_kerma_rate_gy_per_s
        ),
        True,
    )

    slightly_thinner_water_cm = (
        water_buildup_design.required_thickness
        - 1.0e-5
    )

    _, slightly_thinner_water_rate = (
        calculate_air_kerma_response_at_thickness(
            source=water_buildup_source,
            material=solver_materials["water"],
            detector_distance_cm=100.0,
            thickness_cm=slightly_thinner_water_cm,
            apply_buildup=True,
        )
    )

    assert_greater_than(
        "V1.12 slightly thinner bracketed design fails target",
        slightly_thinner_water_rate,
        water_buildup_target.target_air_kerma_rate_gy_per_s,
    )

    assert_raises(
        "V1.12 nonpositive bracket scan interval count rejected",
        ValueError,
        lambda: calculate_air_kerma_minimum_thickness(
            source=cs137_solver_source,
            material=solver_lead,
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=True,
            bracket_scan_intervals=0,
        ),
        "scan interval count must be greater than zero",
    )

        # ------------------------------------------------------------
    # Air-kerma material comparison
    # ------------------------------------------------------------

    air_kerma_comparison = (
        compare_materials_for_air_kerma_target(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
                solver_materials["polyethylene"],
            ],
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 air-kerma comparison preserves candidate count",
        len(air_kerma_comparison.candidates),
        3,
    )

    assert_equal(
        "V1.12 air-kerma comparison preserves target description",
        air_kerma_comparison.target_description,
        (
            "G-P exposure-buildup-adjusted collision "
            "air-kerma rate <= 1 µGy/h"
        ),
    )

    assert_equal(
        "V1.12 air-kerma comparison preserves buildup setting",
        air_kerma_comparison.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma comparison has two passing candidates",
        len(
            air_kerma_comparison
            .passing_candidates()
        ),
        2,
    )

    assert_equal(
        "V1.12 air-kerma comparison has one failed candidate",
        len(
            air_kerma_comparison
            .failed_candidates()
        ),
        1,
    )

    lead_air_kerma_candidate = (
        get_air_kerma_candidate_by_material_key(
            air_kerma_comparison,
            "lead",
        )
    )

    tungsten_air_kerma_candidate = (
        get_air_kerma_candidate_by_material_key(
            air_kerma_comparison,
            "tungsten",
        )
    )

    polyethylene_air_kerma_candidate = (
        get_air_kerma_candidate_by_material_key(
            air_kerma_comparison,
            "polyethylene",
        )
    )

    assert_equal(
        "V1.12 Lead air-kerma comparison candidate passes",
        lead_air_kerma_candidate.status,
        "PASS",
    )

    assert_equal(
        "V1.12 Tungsten air-kerma comparison candidate passes",
        tungsten_air_kerma_candidate.status,
        "PASS",
    )

    assert_equal(
        "V1.12 unsupported buildup candidate fails strictly",
        polyethylene_air_kerma_candidate.status,
        "FAILED",
    )

    passing_air_kerma_thicknesses = []

    for candidate in (
        air_kerma_comparison
        .passing_candidates()
    ):
        required_thickness = (
            candidate.required_thickness
        )

        if required_thickness is None:
            raise AssertionError(
                "Passing air-kerma candidate did not "
                "preserve required thickness."
            )

        final_rate_microgy_per_h = (
            candidate
            .final_air_kerma_rate_microgy_per_h
        )

        if final_rate_microgy_per_h is None:
            raise AssertionError(
                "Passing air-kerma candidate did not "
                "preserve final air-kerma rate."
            )

        if candidate.design_result is None:
            raise AssertionError(
                "Passing air-kerma candidate did not "
                "preserve its complete design result."
            )

        passing_air_kerma_thicknesses.append(
            required_thickness
        )

        assert_greater_than(
            f"V1.12 {candidate.material.key} air-kerma "
            "candidate has positive thickness",
            required_thickness,
            0.0,
        )

        assert_less_than_or_equal(
            f"V1.12 {candidate.material.key} air-kerma "
            "candidate satisfies target",
            final_rate_microgy_per_h,
            (
                solver_target
                .target_air_kerma_rate_microgy_per_h
                + 1.0e-8
            ),
        )

        assert_equal(
            f"V1.12 {candidate.material.key} air-kerma "
            "candidate uses buildup",
            candidate.buildup_used,
            True,
        )

        assert_equal(
            f"V1.12 {candidate.material.key} candidate "
            "material matches design result",
            candidate.design_result.material.key,
            candidate.material.key,
        )

        assert_greater_than(
            f"V1.12 {candidate.material.key} candidate "
            "preserves photon-line response data",
            len(
                candidate
                .design_result
                .final_source_response
                .line_results
            ),
            0,
        )

    assert_equal(
        "V1.12 passing air-kerma candidates are sorted by thickness",
        passing_air_kerma_thicknesses,
        sorted(
            passing_air_kerma_thicknesses
        ),
    )

    assert_equal(
        "V1.12 failed air-kerma candidate has no thickness",
        polyethylene_air_kerma_candidate.required_thickness,
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma candidate has no final response",
        (
            polyethylene_air_kerma_candidate
            .final_air_kerma_rate_microgy_per_h
        ),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma candidate does not claim buildup",
        polyethylene_air_kerma_candidate.buildup_used,
        False,
    )

    if (
        polyethylene_air_kerma_candidate
        .failure_reason
        is None
        or (
            polyethylene_air_kerma_candidate
            .failure_reason
            .strip()
            == ""
        )
    ):
        raise AssertionError(
            "Failed air-kerma candidate did not "
            "preserve its failure reason."
        )

    print(
        "PASS: V1.12 failed air-kerma candidate "
        "preserves failure reason"
    )

    polyethylene_uncollided_comparison = (
        compare_materials_for_air_kerma_target(
            source=cs137_solver_source,
            materials=[
                solver_materials["polyethylene"],
            ],
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=100.0,
            apply_buildup=False,
        )
    )

    polyethylene_uncollided_candidate = (
        polyethylene_uncollided_comparison
        .candidates[0]
    )

    assert_equal(
        "V1.12 unsupported G-P material can pass uncollided design",
        polyethylene_uncollided_candidate.status,
        "PASS",
    )

    assert_equal(
        "V1.12 uncollided Polyethylene candidate does not use buildup",
        polyethylene_uncollided_candidate.buildup_used,
        False,
    )

    polyethylene_uncollided_rate = (
        polyethylene_uncollided_candidate
        .final_air_kerma_rate_microgy_per_h
    )

    if polyethylene_uncollided_rate is None:
        raise AssertionError(
            "Passing uncollided Polyethylene candidate "
            "did not preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 uncollided Polyethylene candidate satisfies target",
        polyethylene_uncollided_rate,
        (
            solver_target
            .target_air_kerma_rate_microgy_per_h
            + 1.0e-8
        ),
    )

    impossible_air_kerma_comparison = (
        compare_materials_for_air_kerma_target(
            source=cs137_solver_source,
            materials=[
                solver_lead,
            ],
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=0.1,
            apply_buildup=False,
        )
    )

    impossible_air_kerma_candidate = (
        impossible_air_kerma_comparison
        .candidates[0]
    )

    assert_equal(
        "V1.12 impossible air-kerma candidate remains visible",
        impossible_air_kerma_candidate.status,
        "FAILED",
    )

    if (
        impossible_air_kerma_candidate
        .failure_reason
        is None
        or (
            impossible_air_kerma_candidate
            .failure_reason
            .strip()
            == ""
        )
    ):
        raise AssertionError(
            "Impossible air-kerma candidate did not "
            "preserve its failure reason."
        )

    print(
        "PASS: V1.12 impossible air-kerma candidate "
        "preserves failure reason"
    )

    assert_raises(
        "V1.12 empty air-kerma material comparison rejected",
        ValueError,
        lambda: compare_materials_for_air_kerma_target(
            source=cs137_solver_source,
            materials=[],
            detector_distance_cm=100.0,
            target=solver_target,
            max_thickness_cm=20.0,
            apply_buildup=False,
        ),
        "At least one material",
    )

    assert_raises(
        "V1.12 passing air-kerma candidate without result rejected",
        ValueError,
        lambda: AirKermaMaterialDesignCandidate(
            material=solver_lead,
            status="PASS",
        ),
        "must store a design result",
    )

    assert_raises(
        "V1.12 failed air-kerma candidate without reason rejected",
        ValueError,
        lambda: AirKermaMaterialDesignCandidate(
            material=solver_lead,
            status="FAILED",
        ),
        "must store a failure reason",
    )

        # ------------------------------------------------------------
    # Air-kerma engineering optimization
    # ------------------------------------------------------------

    air_kerma_optimization_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    air_kerma_minimum_mass_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=air_kerma_optimization_materials,
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(
                max_thickness_cm=20.0,
                max_mass_per_area_g_per_cm2=120.0,
            ),
            optimization_mode="minimum_mass",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves target description",
        air_kerma_minimum_mass_result.target_description,
        (
            "G-P exposure-buildup-adjusted collision "
            "air-kerma rate <= 1 µGy/h"
        ),
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves buildup setting",
        air_kerma_minimum_mass_result.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves candidate count",
        len(
            air_kerma_minimum_mass_result
            .all_candidates
        ),
        3,
    )

    assert_equal(
        "V1.12 air-kerma optimization has two eligible candidates",
        len(
            air_kerma_minimum_mass_result
            .eligible_candidates()
        ),
        2,
    )

    assert_equal(
        "V1.12 air-kerma optimization has one failed candidate",
        len(
            air_kerma_minimum_mass_result
            .failed_candidates()
        ),
        1,
    )

    minimum_mass_best_candidate = (
        air_kerma_minimum_mass_result
        .best_candidate
    )

    if minimum_mass_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-mass air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-mass air-kerma optimization selects Lead",
        (
            minimum_mass_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    selected_air_kerma_base_candidate = (
        minimum_mass_best_candidate
        .base_candidate
    )

    if not isinstance(
        selected_air_kerma_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "V1.12 selected optimization candidate "
            "did not preserve the air-kerma candidate type."
        )

    print(
        "PASS: V1.12 selected optimization candidate "
        "preserves air-kerma type"
    )

    selected_air_kerma_rate = (
        selected_air_kerma_base_candidate
        .final_air_kerma_rate_microgy_per_h
    )

    if selected_air_kerma_rate is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 selected optimization candidate satisfies air-kerma target",
        selected_air_kerma_rate,
        (
            solver_target
            .target_air_kerma_rate_microgy_per_h
            + 1.0e-8
        ),
    )

    assert_equal(
        "V1.12 selected optimization candidate used buildup",
        selected_air_kerma_base_candidate.buildup_used,
        True,
    )

    selected_air_kerma_design_result = (
        selected_air_kerma_base_candidate
        .design_result
    )

    if selected_air_kerma_design_result is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve its design result."
        )

    assert_equal(
        "V1.12 selected optimization candidate preserves applied source buildup",
        (
            selected_air_kerma_design_result
            .final_source_response
            .buildup_status
        ),
        "applied",
    )

    selected_required_thickness = (
        selected_air_kerma_base_candidate
        .required_thickness
    )

    if selected_required_thickness is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve required thickness."
        )

    selected_mass_per_area = (
        minimum_mass_best_candidate
        .mass_per_area_g_per_cm2
    )

    if selected_mass_per_area is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve mass per area."
        )

    assert_close(
        "V1.12 optimized air-kerma mass equals density times thickness",
        selected_mass_per_area,
        (
            selected_air_kerma_base_candidate
            .material
            .density
            * selected_required_thickness
        ),
        1.0e-10,
    )

    polyethylene_optimized_air_kerma = (
        get_optimized_candidate_by_material_key(
            air_kerma_minimum_mass_result,
            "polyethylene",
        )
    )

    assert_equal(
        "V1.12 unsupported buildup material remains FAILED in optimization",
        (
            polyethylene_optimized_air_kerma
            .optimization_status
        ),
        "FAILED",
    )

    assert_equal(
        "V1.12 failed air-kerma optimization candidate has no mass",
        (
            polyethylene_optimized_air_kerma
            .mass_per_area_g_per_cm2
        ),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma optimization candidate has no cost",
        (
            polyethylene_optimized_air_kerma
            .relative_cost_index_per_area
        ),
        None,
    )

    polyethylene_failure_reason = (
        polyethylene_optimized_air_kerma
        .base_candidate
        .failure_reason
    )

    if (
        polyethylene_failure_reason is None
        or polyethylene_failure_reason.strip() == ""
    ):
        raise AssertionError(
            "Failed air-kerma optimization candidate "
            "did not preserve its failure reason."
        )

    print(
        "PASS: V1.12 failed air-kerma optimization "
        "candidate preserves failure reason"
    )

    air_kerma_minimum_thickness_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    minimum_thickness_best_candidate = (
        air_kerma_minimum_thickness_result
        .best_candidate
    )

    if minimum_thickness_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-thickness air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-thickness air-kerma optimization selects Tungsten",
        (
            minimum_thickness_best_candidate
            .base_candidate
            .material
            .key
        ),
        "tungsten",
    )

    tungsten_air_kerma_mass = assert_not_none(
        "V1.12 Tungsten optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "tungsten",
            )
            .mass_per_area_g_per_cm2
        ),
    )

    lead_air_kerma_mass = assert_not_none(
        "V1.12 Lead optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "lead",
            )
            .mass_per_area_g_per_cm2
        ),
    )

    assert_greater_than(
        "V1.12 Lead air-kerma design has lower mass than Tungsten",
        tungsten_air_kerma_mass,
        lead_air_kerma_mass,
    )

    tungsten_air_kerma_mass = assert_not_none(
        "V1.12 Tungsten optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "tungsten",
            )
            .mass_per_area_g_per_cm2
        ),
    )

    lead_air_kerma_mass = assert_not_none(
        "V1.12 Lead optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "lead",
            )
            .mass_per_area_g_per_cm2
        ),
    )

    assert_greater_than(
        "V1.12 Lead air-kerma design has lower mass than Tungsten",
        tungsten_air_kerma_mass,
        lead_air_kerma_mass,
    )

    air_kerma_thickness_constraint_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(
                max_thickness_cm=6.0,
            ),
            optimization_mode="minimum_mass",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    constrained_lead_candidate = (
        get_optimized_candidate_by_material_key(
            air_kerma_thickness_constraint_result,
            "lead",
        )
    )

    assert_equal(
        "V1.12 Lead is rejected by air-kerma thickness constraint",
        constrained_lead_candidate.optimization_status,
        "REJECTED",
    )

    assert_greater_than(
        "V1.12 rejected Lead preserves thickness rejection reason",
        len(
            constrained_lead_candidate
            .rejection_reasons
        ),
        0,
    )

    constrained_thickness_best_candidate = (
        air_kerma_thickness_constraint_result
        .best_candidate
    )

    if constrained_thickness_best_candidate is None:
        raise AssertionError(
            "V1.12 thickness-constrained air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 thickness constraint leaves Tungsten selected",
        (
            constrained_thickness_best_candidate
            .base_candidate
            .material
            .key
        ),
        "tungsten",
    )

    air_kerma_mass_constraint_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(
                max_mass_per_area_g_per_cm2=90.0,
            ),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    constrained_tungsten_candidate = (
        get_optimized_candidate_by_material_key(
            air_kerma_mass_constraint_result,
            "tungsten",
        )
    )

    assert_equal(
        "V1.12 Tungsten is rejected by air-kerma mass constraint",
        constrained_tungsten_candidate.optimization_status,
        "REJECTED",
    )

    constrained_mass_best_candidate = (
        air_kerma_mass_constraint_result
        .best_candidate
    )

    if constrained_mass_best_candidate is None:
        raise AssertionError(
            "V1.12 mass-constrained air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 mass constraint leaves Lead selected",
        (
            constrained_mass_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    air_kerma_minimum_cost_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(),
            optimization_mode="minimum_cost",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    minimum_cost_best_candidate = (
        air_kerma_minimum_cost_result
        .best_candidate
    )

    if minimum_cost_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-cost air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-cost air-kerma optimization selects Lead",
        (
            minimum_cost_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    assert_greater_than(
        "V1.12 relative-cost air-kerma optimization preserves warning",
        len(
            air_kerma_minimum_cost_result
            .warnings
        ),
        0,
    )

    air_kerma_balanced_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(),
            optimization_mode="balanced",
            weights=OptimizationWeights(
                thickness_weight=1.0,
                mass_weight=1.0,
                cost_weight=1.0,
            ),
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    balanced_best_candidate = (
        air_kerma_balanced_result
        .best_candidate
    )

    if balanced_best_candidate is None:
        raise AssertionError(
            "V1.12 balanced air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 balanced air-kerma optimization selects Lead",
        (
            balanced_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    for candidate in (
        air_kerma_balanced_result
        .eligible_candidates()
    ):
        candidate_score = assert_not_none(
            "V1.12 balanced air-kerma score exists",
            candidate.optimization_score,
        )

        assert_equal(
            f"V1.12 {candidate.base_candidate.material.key} "
            "balanced air-kerma score is bounded",
            (
                0.0
                <= candidate_score
                <= 1.0
            ),
            True,
        )

    no_eligible_air_kerma_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["lead"],
                solver_materials["tungsten"],
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(
                max_thickness_cm=1.0,
            ),
            optimization_mode="minimum_mass",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        )
    )

    assert_equal(
        "V1.12 air-kerma optimization returns no best candidate when all rejected",
        no_eligible_air_kerma_result.best_candidate,
        None,
    )

    assert_equal(
        "V1.12 all calculated air-kerma candidates can be rejected",
        len(
            no_eligible_air_kerma_result
            .rejected_candidates()
        ),
        2,
    )

    assert_greater_than(
        "V1.12 no-eligible air-kerma result preserves warning",
        len(
            no_eligible_air_kerma_result
            .warnings
        ),
        0,
    )

    assert_raises(
        "V1.12 balanced air-kerma optimization requires weights",
        ValueError,
        lambda: optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_lead,
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(),
            optimization_mode="balanced",
            calculation_max_thickness=20.0,
            apply_buildup=True,
        ),
        "requires optimization weights",
    )

    assert_raises(
        "V1.12 non-balanced air-kerma optimization rejects weights",
        ValueError,
        lambda: optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_lead,
            ],
            detector_distance=100.0,
            target=solver_target,
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
            weights=OptimizationWeights(
                thickness_weight=1.0,
                mass_weight=1.0,
                cost_weight=1.0,
            ),
            calculation_max_thickness=20.0,
            apply_buildup=True,
        ),
        "only be supplied for balanced mode",
    )

        # ------------------------------------------------------------
    # Air-kerma optimization plot-data compatibility
    # ------------------------------------------------------------

    air_kerma_plot_data = (
        create_optimization_plot_data(
            air_kerma_minimum_mass_result
        )
    )

    assert_equal(
        "V1.12 air-kerma plot data preserves candidate count",
        len(air_kerma_plot_data.candidates),
        len(
            air_kerma_minimum_mass_result
            .all_candidates
        ),
    )

    assert_equal(
        "V1.12 air-kerma plot data preserves selected material",
        air_kerma_plot_data.selected_material_key,
        "lead",
    )

    plotted_air_kerma_lead = (
        get_material_plot_point_by_key(
            air_kerma_plot_data,
            "lead",
        )
    )

    assert_equal(
        "V1.12 plotted air-kerma Lead candidate is eligible",
        plotted_air_kerma_lead.optimization_status,
        "ELIGIBLE",
    )

    assert_equal(
        "V1.12 plotted air-kerma Lead candidate is selected",
        plotted_air_kerma_lead.is_selected,
        True,
    )

    assert_equal(
        "V1.12 plotted air-kerma Lead candidate shows buildup",
        plotted_air_kerma_lead.buildup_display,
        "YES",
    )

    plotted_lead_thickness = assert_not_none(
        "V1.12 plotted air-kerma Lead thickness exists",
        plotted_air_kerma_lead.required_thickness_cm,
    )

    optimized_lead_candidate = (
        get_optimized_candidate_by_material_key(
            air_kerma_minimum_mass_result,
            "lead",
        )
    )

    optimized_lead_thickness = assert_not_none(
        "V1.12 optimized air-kerma Lead thickness exists",
        (
            optimized_lead_candidate
            .base_candidate
            .required_thickness
        ),
    )

    assert_close(
        "V1.12 air-kerma plot data preserves Lead thickness",
        plotted_lead_thickness,
        optimized_lead_thickness,
        1.0e-12,
    )

    plotted_lead_mass = assert_not_none(
        "V1.12 plotted air-kerma Lead mass exists",
        (
            plotted_air_kerma_lead
            .mass_per_area_g_per_cm2
        ),
    )

    optimized_lead_mass = assert_not_none(
        "V1.12 optimized air-kerma Lead mass exists",
        (
            optimized_lead_candidate
            .mass_per_area_g_per_cm2
        ),
    )

    assert_close(
        "V1.12 air-kerma plot data preserves Lead mass",
        plotted_lead_mass,
        optimized_lead_mass,
        1.0e-12,
    )

    plotted_air_kerma_polyethylene = (
        get_material_plot_point_by_key(
            air_kerma_plot_data,
            "polyethylene",
        )
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate remains visible",
        (
            plotted_air_kerma_polyethylene
            .optimization_status
        ),
        "FAILED",
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has unavailable buildup",
        (
            plotted_air_kerma_polyethylene
            .buildup_display
        ),
        "UNAVAILABLE",
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has no thickness",
        (
            plotted_air_kerma_polyethylene
            .required_thickness_cm
        ),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has no mass",
        (
            plotted_air_kerma_polyethylene
            .mass_per_area_g_per_cm2
        ),
        None,
    )

    if (
        plotted_air_kerma_polyethylene
        .failure_reason
        is None
        or (
            plotted_air_kerma_polyethylene
            .failure_reason
            .strip()
            == ""
        )
    ):
        raise AssertionError(
            "Failed plotted air-kerma candidate did not "
            "preserve its failure reason."
        )

    print(
        "PASS: V1.12 failed plotted air-kerma candidate "
        "preserves failure reason"
    )

    air_kerma_constraint_plot_data = (
        create_optimization_plot_data(
            air_kerma_thickness_constraint_result
        )
    )

    air_kerma_feasibility_rows = (
        create_constraint_feasibility_rows(
            air_kerma_constraint_plot_data
        )
    )

    air_kerma_lead_feasibility = (
        get_feasibility_row_by_material_key(
            air_kerma_feasibility_rows,
            "lead",
        )
    )

    air_kerma_tungsten_feasibility = (
        get_feasibility_row_by_material_key(
            air_kerma_feasibility_rows,
            "tungsten",
        )
    )

    assert_equal(
        "V1.12 air-kerma Lead fails thickness feasibility check",
        air_kerma_lead_feasibility.thickness_status,
        "FAIL",
    )

    assert_equal(
        "V1.12 air-kerma Lead remains rejected in feasibility data",
        (
            air_kerma_lead_feasibility
            .optimization_status
        ),
        "REJECTED",
    )

    assert_equal(
        "V1.12 air-kerma Tungsten passes thickness feasibility check",
        air_kerma_tungsten_feasibility.thickness_status,
        "PASS",
    )

    assert_equal(
        "V1.12 air-kerma Tungsten is selected in feasibility data",
        air_kerma_tungsten_feasibility.is_selected,
        True,
    )

    assert_equal(
        "V1.12 inactive air-kerma mass constraint remains inactive",
        air_kerma_tungsten_feasibility.mass_status,
        "INACTIVE",
    )

    assert_equal(
        "V1.12 inactive air-kerma cost constraint remains inactive",
        air_kerma_tungsten_feasibility.cost_status,
        "INACTIVE",
    )

    air_kerma_pareto_plot_data = (
        create_optimization_plot_data(
            air_kerma_minimum_thickness_result
        )
    )

    air_kerma_pareto_points = (
        create_pareto_points(
            air_kerma_pareto_plot_data,
            eligible_only=True,
        )
    )

    air_kerma_pareto_material_keys = {
        point.material_key
        for point in air_kerma_pareto_points
        if point.is_pareto_optimal
    }

    assert_equal(
        "V1.12 air-kerma Pareto front contains Lead and Tungsten",
        air_kerma_pareto_material_keys,
        {
            "lead",
            "tungsten",
        },
    )

    air_kerma_pareto_thicknesses = [
        point.thickness_cm
        for point in air_kerma_pareto_points
    ]

    assert_equal(
        "V1.12 air-kerma Pareto points are sorted by thickness",
        air_kerma_pareto_thicknesses,
        sorted(
            air_kerma_pareto_thicknesses
        ),
    )

        # ------------------------------------------------------------
    # Explicit air-kerma console output
    # ------------------------------------------------------------

    source_output_buffer = StringIO()

    with redirect_stdout(
        source_output_buffer
    ):
        print_source_air_kerma_result(
            buildup_solver_result
            .final_source_response
        )

    source_output_text = (
        source_output_buffer.getvalue()
    )

    source_output_requirements = [
        "Collision air-kerma response result",
        "Total uncollided photon fluence rate:",
        "Total uncollided collision air-kerma rate:",
        (
            "Total G-P buildup-adjusted collision "
            "air-kerma rate:"
        ),
        "Photon-line contributions:",
        "Energy fluence rate:",
        "Dry-air mu_en/rho:",
        "G-P exposure buildup factor:",
        "Coefficient source:",
        "µGy/h",
        "Gy/s",
    ]

    for required_text in (
        source_output_requirements
    ):
        assert_equal(
            "V1.12 source air-kerma output contains "
            f"{required_text}",
            required_text in source_output_text,
            True,
        )

    minimum_output_buffer = StringIO()

    with redirect_stdout(
        minimum_output_buffer
    ):
        print_air_kerma_minimum_thickness_result(
            buildup_solver_result
        )

    minimum_output_text = (
        minimum_output_buffer.getvalue()
    )

    minimum_output_requirements = [
        (
            "Air-kerma minimum shielding "
            "thickness result"
        ),
        "Required thickness:",
        (
            "Final target-comparison collision "
            "air-kerma rate:"
        ),
        (
            "Final uncollided collision "
            "air-kerma rate:"
        ),
        (
            "Final G-P buildup-adjusted collision "
            "air-kerma rate:"
        ),
        "Final selected-response ratio:",
        "Buildup used: Yes",
        "Final detailed source response:",
        "Photon-line contributions:",
    ]

    for required_text in (
        minimum_output_requirements
    ):
        assert_equal(
            "V1.12 minimum-thickness output contains "
            f"{required_text}",
            required_text in minimum_output_text,
            True,
        )

    # ------------------------------------------------------------
    # Air-kerma scenario target serialization
    # ------------------------------------------------------------

    air_kerma_scenario = ShieldingScenario(
        scenario_id="cs137_air_kerma_serialization_test",
        description=(
            "V1.12 reproducible Cs-137 collision "
            "air-kerma scenario serialization test."
        ),
        calculation_mode="material_optimization",
        source=IsotopeSourceSpec(
            isotope_key="cs137",
            activity_bq=3.7e10,
        ),
        geometry=ConcentricSphericalGeometry(
            source_cavity_radius_cm=0.0,
            evaluation_radius_cm=100.0,
        ),
        candidate_material_keys=[
            "lead",
            "tungsten",
        ],
        target=AirKermaRateTarget(
            target_air_kerma_rate_microgy_per_h=1.0
        ),
        constraints=DesignConstraints(
            max_thickness_cm=20.0,
            max_mass_per_area_g_per_cm2=120.0,
        ),
        optimization_mode="minimum_mass",
        deterministic_settings=(
            DeterministicSettings(
                apply_buildup=True,
                calculation_max_thickness_cm=20.0,
            )
        ),
    )

    assert_equal(
        "V1.12 scenario model accepts air-kerma target",
        isinstance(
            air_kerma_scenario.target,
            AirKermaRateTarget,
        ),
        True,
    )

    air_kerma_scenario_data = (
        scenario_to_dict(
            air_kerma_scenario
        )
    )

    assert_equal(
        "V1.12 scenario serializes explicit air-kerma target type",
        air_kerma_scenario_data[
            "target"
        ][
            "type"
        ],
        "air_kerma_rate",
    )

    assert_close(
        "V1.12 scenario serializes air-kerma target in microGy per hour",
        air_kerma_scenario_data[
            "target"
        ][
            "target_air_kerma_rate_microgy_per_h"
        ],
        1.0,
        1.0e-12,
    )

    reconstructed_air_kerma_scenario = (
        scenario_from_dict(
            air_kerma_scenario_data
        )
    )

    reconstructed_air_kerma_target = (
        reconstructed_air_kerma_scenario
        .target
    )

    if not isinstance(
        reconstructed_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError(
            "V1.12 scenario reconstruction did not "
            "preserve the air-kerma target type."
        )

    print(
        "PASS: V1.12 scenario reconstruction "
        "preserves air-kerma target type"
    )

    assert_close(
        "V1.12 reconstructed scenario preserves air-kerma target value",
        (
            reconstructed_air_kerma_target
            .target_air_kerma_rate_microgy_per_h
        ),
        1.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma scenario dictionary round trip preserves object",
        reconstructed_air_kerma_scenario,
        air_kerma_scenario,
    )

    with TemporaryDirectory() as (
        air_kerma_temporary_directory
    ):
        air_kerma_scenario_path = (
            Path(
                air_kerma_temporary_directory
            )
            / "air_kerma_scenario.json"
        )

        saved_air_kerma_path = (
            save_scenario(
                air_kerma_scenario,
                air_kerma_scenario_path,
            )
        )

        assert_equal(
            "V1.12 air-kerma scenario save creates JSON file",
            saved_air_kerma_path.is_file(),
            True,
        )

        loaded_air_kerma_scenario = (
            load_scenario(
                saved_air_kerma_path
            )
        )

        assert_equal(
            "V1.12 air-kerma scenario JSON round trip preserves object",
            loaded_air_kerma_scenario,
            air_kerma_scenario,
        )

    invalid_air_kerma_target_data = (
        json.loads(
            json.dumps(
                air_kerma_scenario_data
            )
        )
    )

    invalid_air_kerma_target_data[
        "target"
    ][
        "target_air_kerma_rate_microgy_per_h"
    ] = 0.0

    assert_raises(
        "V1.12 scenario rejects nonpositive air-kerma target",
        ValueError,
        lambda: scenario_from_dict(
            invalid_air_kerma_target_data
        ),
        "must be greater than zero",
    )

    # ------------------------------------------------------------
    # Reproducible air-kerma scenario execution
    # ------------------------------------------------------------

    air_kerma_scenario_result = (
        run_scenario(
            air_kerma_scenario
        )
    )

    assert_equal(
        "V1.12 air-kerma scenario preserves target description",
        air_kerma_scenario_result.target_description,
        (
            "G-P exposure-buildup-adjusted collision "
            "air-kerma rate <= 1 µGy/h"
        ),
    )

    assert_equal(
        "V1.12 air-kerma scenario preserves buildup setting",
        air_kerma_scenario_result.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma scenario preserves candidate count",
        len(
            air_kerma_scenario_result
            .all_candidates
        ),
        2,
    )

    assert_equal(
        "V1.12 air-kerma scenario has two eligible candidates",
        len(
            air_kerma_scenario_result
            .eligible_candidates()
        ),
        2,
    )

    air_kerma_scenario_best_candidate = (
        air_kerma_scenario_result
        .best_candidate
    )

    if air_kerma_scenario_best_candidate is None:
        raise AssertionError(
            "V1.12 air-kerma scenario did not "
            "select a candidate."
        )

    assert_equal(
        "V1.12 minimum-mass air-kerma scenario selects Lead",
        (
            air_kerma_scenario_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    air_kerma_scenario_base_candidate = (
        air_kerma_scenario_best_candidate
        .base_candidate
    )

    if not isinstance(
        air_kerma_scenario_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "V1.12 scenario runner did not preserve "
            "the air-kerma candidate type."
        )

    print(
        "PASS: V1.12 scenario runner preserves "
        "air-kerma candidate type"
    )

    air_kerma_scenario_final_rate = (
        air_kerma_scenario_base_candidate
        .final_air_kerma_rate_microgy_per_h
    )

    if air_kerma_scenario_final_rate is None:
        raise AssertionError(
            "V1.12 air-kerma scenario did not "
            "preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 air-kerma scenario satisfies target",
        air_kerma_scenario_final_rate,
        (
            solver_target
            .target_air_kerma_rate_microgy_per_h
            + 1.0e-8
        ),
    )

    air_kerma_scenario_design_result = (
        air_kerma_scenario_base_candidate
        .design_result
    )

    if air_kerma_scenario_design_result is None:
        raise AssertionError(
            "V1.12 air-kerma scenario did not "
            "preserve its design result."
        )

    assert_equal(
        "V1.12 air-kerma scenario applies source buildup",
        (
            air_kerma_scenario_design_result
            .final_source_response
            .buildup_status
        ),
        "applied",
    )

    assert_close(
        "V1.12 scenario and direct solver reproduce Lead thickness",
        (
            air_kerma_scenario_design_result
            .required_thickness
        ),
        buildup_solver_result.required_thickness,
        1.0e-8,
    )

    scenario_lead_mass = assert_not_none(
        "V1.12 scenario-selected Lead mass exists",
        (
            air_kerma_scenario_best_candidate
            .mass_per_area_g_per_cm2
        ),
    )

    assert_close(
        "V1.12 scenario-selected Lead mass equals density times thickness",
        scenario_lead_mass,
        (
            air_kerma_scenario_base_candidate
            .material
            .density
            * air_kerma_scenario_design_result
            .required_thickness
        ),
        1.0e-10,
    )

    assert_equal(
        "V1.12 air-kerma scenario provides selection reason",
        (
            air_kerma_scenario_result
            .selection_reason
            is not None
        ),
        True,
    )       

    strict_air_kerma_failure_scenario = (
        ShieldingScenario(
            scenario_id=(
                "air_kerma_strict_buildup_failure"
            ),
            description=(
                "Confirm that air-kerma scenarios do not "
                "silently fall back when requested G-P "
                "buildup is unavailable."
            ),
            calculation_mode=(
                "material_optimization"
            ),
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=(
                ConcentricSphericalGeometry(
                    source_cavity_radius_cm=0.0,
                    evaluation_radius_cm=100.0,
                )
            ),
            candidate_material_keys=[
                "polyethylene",
            ],
            target=AirKermaRateTarget(
                target_air_kerma_rate_microgy_per_h=1.0
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
            deterministic_settings=(
                DeterministicSettings(
                    apply_buildup=True,
                    calculation_max_thickness_cm=20.0,
                )
            ),
        )
    )

    strict_air_kerma_failure_result = (
        run_scenario(
            strict_air_kerma_failure_scenario
        )
    )

    assert_equal(
        "V1.12 strict air-kerma scenario has no selected design",
        strict_air_kerma_failure_result.best_candidate,
        None,
    )

    assert_equal(
        "V1.12 strict air-kerma scenario preserves failed candidate",
        len(
            strict_air_kerma_failure_result
            .failed_candidates()
        ),
        1,
    )

    strict_failed_candidate = (
        strict_air_kerma_failure_result
        .failed_candidates()[0]
    )

    assert_equal(
        "V1.12 strict scenario marks unsupported buildup as FAILED",
        strict_failed_candidate.optimization_status,
        "FAILED",
    )

    strict_failure_reason = (
        strict_failed_candidate
        .base_candidate
        .failure_reason
    )

    if (
        strict_failure_reason is None
        or strict_failure_reason.strip() == ""
    ):
        raise AssertionError(
            "V1.12 strict air-kerma scenario "
            "did not preserve its failure reason."
        )

    assert_equal(
        "V1.12 strict scenario reports G-P requirement",
        (
            "requires valid G-P exposure buildup"
            in strict_failure_reason
        ),
        True,
    )  

    # ------------------------------------------------------------
    # Official V1.12 air-kerma reference scenario
    # ------------------------------------------------------------

    air_kerma_reference_scenario_path = (
        Path(__file__)
        .resolve()
        .parents[1]
        / "scenarios"
        / "cs137_air_kerma_reference.json"
    )

    assert_equal(
        "V1.12 official air-kerma reference scenario file exists",
        air_kerma_reference_scenario_path.is_file(),
        True,
    )

    official_air_kerma_scenario = (
        load_scenario(
            air_kerma_reference_scenario_path
        )
    )

    assert_equal(
        "V1.12 official scenario preserves scenario ID",
        official_air_kerma_scenario.scenario_id,
        "cs137_air_kerma_reference",
    )

    assert_equal(
        "V1.12 official scenario preserves schema version",
        official_air_kerma_scenario.schema_version,
        "1.0",
    )

    assert_equal(
        "V1.12 official scenario preserves nine materials",
        len(
            official_air_kerma_scenario
            .candidate_material_keys
        ),
        9,
    )

    official_air_kerma_target = (
        official_air_kerma_scenario.target
    )

    if not isinstance(
        official_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError(
            "Official V1.12 scenario did not "
            "reconstruct an AirKermaRateTarget."
        )

    print(
        "PASS: V1.12 official scenario reconstructs "
        "air-kerma target type"
    )

    assert_close(
        "V1.12 official scenario preserves air-kerma target",
        (
            official_air_kerma_target
            .target_air_kerma_rate_microgy_per_h
        ),
        1.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 official scenario requires buildup",
        (
            official_air_kerma_scenario
            .deterministic_settings
            .apply_buildup
        ),
        True,
    )

    assert_equal(
        "V1.12 official scenario uses minimum-mass objective",
        official_air_kerma_scenario.optimization_mode,
        "minimum_mass",
    )

    official_air_kerma_result = (
        run_scenario(
            official_air_kerma_scenario
        )
    )

    assert_equal(
        "V1.12 official scenario returns nine candidates",
        len(
            official_air_kerma_result
            .all_candidates
        ),
        9,
    )

    assert_equal(
        "V1.12 official scenario preserves target description",
        official_air_kerma_result.target_description,
        (
            "G-P exposure-buildup-adjusted collision "
            "air-kerma rate <= 1 µGy/h"
        ),
    )

    official_air_kerma_best_candidate = (
        official_air_kerma_result
        .best_candidate
    )

    if official_air_kerma_best_candidate is None:
        raise AssertionError(
            "Official V1.12 air-kerma scenario "
            "did not select a design."
        )

    assert_equal(
        "V1.12 official minimum-mass scenario selects Lead",
        (
            official_air_kerma_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    official_air_kerma_base_candidate = (
        official_air_kerma_best_candidate
        .base_candidate
    )

    if not isinstance(
        official_air_kerma_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "Official V1.12 scenario did not preserve "
            "the air-kerma candidate type."
        )

    print(
        "PASS: V1.12 official scenario preserves "
        "air-kerma candidate type"
    )

    official_air_kerma_design_result = (
        official_air_kerma_base_candidate
        .design_result
    )

    if official_air_kerma_design_result is None:
        raise AssertionError(
            "Official V1.12 selected candidate did not "
            "preserve its design result."
        )       

    assert_close(
        "V1.12 official Lead reference thickness",
        (
            official_air_kerma_design_result
            .required_thickness
        ),
        7.180648660287261,
        1.0e-8,
    )

    official_air_kerma_mass = assert_not_none(
        "V1.12 official Lead reference mass exists",
        (
            official_air_kerma_best_candidate
            .mass_per_area_g_per_cm2
        ),
    )

    assert_close(
        "V1.12 official Lead reference mass per area",
        official_air_kerma_mass,
        81.42855580765755,
        1.0e-7,
    )

    official_air_kerma_final_rate = (
        official_air_kerma_base_candidate
        .final_air_kerma_rate_microgy_per_h
    )

    if official_air_kerma_final_rate is None:
        raise AssertionError(
            "Official V1.12 selected design did not "
            "preserve its final air-kerma rate."
        )

    assert_less_than_or_equal(
        "V1.12 official Lead design satisfies target",
        official_air_kerma_final_rate,
        1.0 + 1.0e-8,
    )

    assert_equal(
        "V1.12 official Lead design uses buildup",
        official_air_kerma_design_result.buildup_used,
        True,
    )

    assert_equal(
        "V1.12 official Lead source response applies buildup",
        (
            official_air_kerma_design_result
            .final_source_response
            .buildup_status
        ),
        "applied",
    )

    official_barite_candidate = (
        get_optimized_candidate_by_material_key(
            official_air_kerma_result,
            "concrete_barite",
        )
    )

    official_polyethylene_candidate = (
        get_optimized_candidate_by_material_key(
            official_air_kerma_result,
            "polyethylene",
        )
    )

    assert_equal(
        "V1.12 official Barite Concrete candidate remains FAILED",
        official_barite_candidate.optimization_status,
        "FAILED",
    )

    assert_equal(
        "V1.12 official Polyethylene candidate remains FAILED",
        official_polyethylene_candidate.optimization_status,
        "FAILED",
    )

    for unsupported_candidate in [
        official_barite_candidate,
        official_polyethylene_candidate,
    ]:
        failure_reason = (
            unsupported_candidate
            .base_candidate
            .failure_reason
        )

        if (
            failure_reason is None
            or failure_reason.strip() == ""
        ):
            raise AssertionError(
                "Official V1.12 unsupported material "
                "did not preserve its failure reason."
            )

        assert_equal(
            "V1.12 official "
            f"{unsupported_candidate.base_candidate.material.key} "
            "reports G-P limitation",
            "G-P" in failure_reason,
            True,
        )

    # ------------------------------------------------------------
    # Explicit CLI response-quantity input
    # ------------------------------------------------------------

    with patch(
        "builtins.input",
        return_value="1",
    ):
        cli_photon_response_quantity = (
            get_response_quantity_from_user()
        )

    assert_equal(
        "V1.12 CLI selects photon fluence-rate response",
        cli_photon_response_quantity,
        "photon_fluence_rate",
    )

    with patch(
        "builtins.input",
        return_value="2",
    ):
        cli_air_kerma_response_quantity = (
            get_response_quantity_from_user()
        )

    assert_equal(
        "V1.12 CLI selects collision air-kerma response",
        cli_air_kerma_response_quantity,
        "collision_air_kerma_rate",
    )

    with patch(
        "builtins.input",
        return_value="1.0",
    ):
        cli_air_kerma_target = (
            get_target_from_user(
                "collision_air_kerma_rate"
            )
        )

    if not isinstance(
        cli_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError(
            "V1.12 CLI did not construct an "
            "AirKermaRateTarget."
        )

    print(
        "PASS: V1.12 CLI constructs "
        "air-kerma target type"
    )

    assert_close(
        "V1.12 CLI preserves air-kerma target value",
        (
            cli_air_kerma_target
            .target_air_kerma_rate_microgy_per_h
        ),
        1.0,
        1.0e-12,
    )

    with patch(
        "builtins.input",
        side_effect=[
            "3",
            "100.0",
        ],
    ):
        cli_photon_target = (
            get_target_from_user(
                "photon_fluence_rate"
            )
        )

    if not isinstance(
        cli_photon_target,
        FluxTarget,
    ):
        raise AssertionError(
            "V1.12 CLI did not preserve the "
            "legacy photon target type."
        )

    print(
        "PASS: V1.12 CLI preserves "
        "photon target type"
    )

    assert_close(
        "V1.12 CLI preserves photon fluence-rate target value",
        cli_photon_target.target_flux,
        100.0,
        1.0e-12,
    )

    with patch(
        "builtins.input",
        return_value="9",
    ):
        assert_raises(
            "V1.12 CLI rejects unsupported response choice",
            ValueError,
            get_response_quantity_from_user,
            "Please enter 1 or 2",
        )

    # ------------------------------------------------------------
    # Fixed-thickness and minimum-thickness CLI routing
    # ------------------------------------------------------------

    cli_fixed_air_kerma_layers = [
        Layer(
            thickness=5.0,
            material=solver_lead,
        )
    ]

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value=(
                "collision_air_kerma_rate"
            ),
        ),
        patch(
            "main.get_layers_from_user",
            return_value=(
                cli_fixed_air_kerma_layers
            ),
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as fixed_air_buildup_prompt,
        patch(
            "main.print_source_air_kerma_result",
        ) as fixed_air_output,
        patch(
            "main.print_source_results",
        ) as fixed_photon_output,
    ):
        run_fixed_thickness_mode()

    assert_equal(
        "V1.12 fixed-thickness CLI requests buildup for air kerma",
        fixed_air_buildup_prompt.call_count,
        1,
    )

    assert_equal(
        "V1.12 fixed-thickness CLI uses air-kerma output",
        fixed_air_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 fixed-thickness air-kerma CLI skips photon output",
        fixed_photon_output.call_count,
        0,
    )

    fixed_air_kerma_result = (
        fixed_air_output
        .call_args
        .args[0]
    )

    assert_equal(
        "V1.12 fixed-thickness CLI applies air-kerma buildup",
        fixed_air_kerma_result.buildup_status,
        "applied",
    )

    assert_greater_than(
        "V1.12 fixed-thickness CLI produces positive air kerma",
        (
            fixed_air_kerma_result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        0.0,
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=manual_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "main.get_layers_from_user",
            return_value=(
                cli_fixed_air_kerma_layers
            ),
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as fixed_photon_buildup_prompt,
        patch(
            "main.print_source_air_kerma_result",
        ) as photon_mode_air_output,
        patch(
            "main.print_source_results",
        ) as photon_mode_output,
    ):
        run_fixed_thickness_mode()

    assert_equal(
        "V1.12 photon fixed-thickness CLI does not request exposure buildup",
        fixed_photon_buildup_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon fixed-thickness CLI uses photon output",
        photon_mode_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon fixed-thickness CLI skips air-kerma output",
        photon_mode_air_output.call_count,
        0,
    )

    fixed_photon_result = (
        photon_mode_output
        .call_args
        .args[0]
    )

    assert_equal(
        "V1.12 photon fixed-thickness CLI stores no buildup total",
        (
            fixed_photon_result
            .total_buildup_corrected_flux
        ),
        None,
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value=(
                "collision_air_kerma_rate"
            ),
        ),
        patch(
            "main.get_single_material_from_user",
            return_value=solver_lead,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=solver_target,
        ) as minimum_air_target_prompt,
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as minimum_air_buildup_prompt,
        patch(
            "main.print_air_kerma_minimum_thickness_result",
        ) as minimum_air_output,
        patch(
            "main.print_minimum_thickness_result",
        ) as minimum_photon_output,
    ):
        run_minimum_thickness_mode()

    assert_equal(
        "V1.12 minimum-thickness CLI passes response to target prompt",
        (
            minimum_air_target_prompt
            .call_args
            .args[0]
        ),
        "collision_air_kerma_rate",
    )

    assert_equal(
        "V1.12 minimum-thickness CLI requests air-kerma buildup",
        minimum_air_buildup_prompt.call_count,
        1,
    )

    assert_equal(
        "V1.12 minimum-thickness CLI uses air-kerma output",
        minimum_air_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma minimum-thickness CLI skips photon output",
        minimum_photon_output.call_count,
        0,
    )

    cli_air_kerma_design = (
        minimum_air_output
        .call_args
        .args[0]
    )

    assert_equal(
        "V1.12 minimum-thickness CLI preserves buildup use",
        cli_air_kerma_design.buildup_used,
        True,
    )

    assert_less_than_or_equal(
        "V1.12 minimum-thickness CLI satisfies air-kerma target",
        (
            cli_air_kerma_design
            .final_air_kerma_rate_microgy_per_h
        ),
        1.0 + 1.0e-8,
    )

    assert_close(
        "V1.12 minimum-thickness CLI reproduces Lead design",
        cli_air_kerma_design.required_thickness,
        buildup_solver_result.required_thickness,
        1.0e-8,
    )

    cli_photon_target = FluxTarget(
        target_flux=100.0
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "main.get_single_material_from_user",
            return_value=solver_lead,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=cli_photon_target,
        ),
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as minimum_photon_buildup_prompt,
        patch(
            "main.print_air_kerma_minimum_thickness_result",
        ) as photon_minimum_air_output,
        patch(
            "main.print_minimum_thickness_result",
        ) as photon_minimum_output,
    ):
        run_minimum_thickness_mode()

    assert_equal(
        "V1.12 photon minimum-thickness CLI does not request exposure buildup",
        minimum_photon_buildup_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon minimum-thickness CLI uses photon output",
        photon_minimum_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon minimum-thickness CLI skips air-kerma output",
        photon_minimum_air_output.call_count,
        0,
    )

    cli_photon_design = (
        photon_minimum_output
        .call_args
        .args[0]
    )

    assert_equal(
        "V1.12 photon minimum-thickness CLI does not use buildup",
        cli_photon_design.buildup_used,
        False,
    )

    assert_less_than_or_equal(
        "V1.12 photon minimum-thickness CLI satisfies fluence target",
        cli_photon_design.final_flux,
        100.0 + 1.0e-6,
    )


    # ------------------------------------------------------------
    # Air-kerma material-comparison console output
    # ------------------------------------------------------------

    air_kerma_comparison_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        air_kerma_comparison_output_buffer
    ):
        print_air_kerma_material_comparison_result(
            air_kerma_comparison
        )

    air_kerma_comparison_output_text = (
        air_kerma_comparison_output_buffer
        .getvalue()
    )

    air_kerma_comparison_output_requirements = [
        (
            "Collision air-kerma material "
            "comparison result"
        ),
        (
            "Single-material collision air-kerma "
            "design comparison"
        ),
        (
            "G-P exposure buildup requested: Yes"
        ),
        "Thickness (cm)",
        "Final Air Kerma",
        "Response Ratio",
        "Final Air Kerma units: µGy/h",
        "Lead",
        "Tungsten",
        "Polyethylene",
        "PASS",
        "FAILED",
        "G-P",
    ]

    for required_text in (
        air_kerma_comparison_output_requirements
    ):
        assert_equal(
            "V1.12 air-kerma comparison output "
            f"contains {required_text}",
            (
                required_text
                in air_kerma_comparison_output_text
            ),
            True,
        )

    assert_equal(
        "V1.12 air-kerma comparison output does not use Final Flux column",
        (
            "Final Flux"
            in air_kerma_comparison_output_text
        ),
        False,
    )

    assert_equal(
        "V1.12 air-kerma comparison output displays microGy per hour units",
        (
            "µGy/h"
            in air_kerma_comparison_output_text
        ),
        True,
    )

    assert_equal(
        "V1.12 air-kerma comparison output preserves strict failure",
        (
            polyethylene_air_kerma_candidate
            .failure_reason
            in air_kerma_comparison_output_text
        ),
        True,
    )

    # ------------------------------------------------------------
    # Material-comparison CLI routing
    # ------------------------------------------------------------

    cli_comparison_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value=(
                "collision_air_kerma_rate"
            ),
        ),
        patch(
            "main.get_materials_for_comparison_from_user",
            return_value=cli_comparison_materials,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=solver_target,
        ) as comparison_air_target_prompt,
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as comparison_air_buildup_prompt,
        patch(
            "main.compare_materials_for_air_kerma_target",
            return_value=air_kerma_comparison,
        ) as air_kerma_comparison_function,
        patch(
            "main.compare_materials_for_target",
        ) as photon_comparison_function,
        patch(
            "main.print_air_kerma_material_comparison_result",
        ) as air_kerma_comparison_output,
        patch(
            "main.print_material_comparison_result",
        ) as photon_comparison_output,
    ):
        run_material_comparison_mode()

    assert_equal(
        "V1.12 comparison CLI passes air-kerma response to target prompt",
        (
            comparison_air_target_prompt
            .call_args
            .args[0]
        ),
        "collision_air_kerma_rate",
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI requests buildup setting",
        comparison_air_buildup_prompt.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI calls response-specific solver",
        air_kerma_comparison_function.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI skips photon solver",
        photon_comparison_function.call_count,
        0,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI uses dedicated output",
        air_kerma_comparison_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI skips photon output",
        photon_comparison_output.call_count,
        0,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI preserves comparison result",
        (
            air_kerma_comparison_output
            .call_args
            .args[0]
        ),
        air_kerma_comparison,
    )

    air_kerma_comparison_call = (
        air_kerma_comparison_function
        .call_args
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI passes source",
        air_kerma_comparison_call.kwargs[
            "source"
        ],
        cs137_solver_source,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI passes selected materials",
        air_kerma_comparison_call.kwargs[
            "materials"
        ],
        cli_comparison_materials,
    )

    assert_close(
        "V1.12 air-kerma comparison CLI passes detector distance",
        air_kerma_comparison_call.kwargs[
            "detector_distance_cm"
        ],
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI passes strict buildup request",
        air_kerma_comparison_call.kwargs[
            "apply_buildup"
        ],
        True,
    )

    assert_close(
        "V1.12 air-kerma comparison CLI passes calculation limit",
        air_kerma_comparison_call.kwargs[
            "max_thickness_cm"
        ],
        20.0,
        1.0e-12,
    )

    cli_photon_comparison_target = (
        FluxTarget(
            target_flux=100.0
        )
    )

    cli_photon_comparison_result = (
        compare_materials_for_target(
            source=cs137_solver_source,
            materials=cli_comparison_materials,
            detector_distance=100.0,
            target=cli_photon_comparison_target,
            max_thickness=20.0,
            apply_buildup=False,
        )
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "main.get_materials_for_comparison_from_user",
            return_value=cli_comparison_materials,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=(
                cli_photon_comparison_target
            ),
        ) as comparison_photon_target_prompt,
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as comparison_photon_buildup_prompt,
        patch(
            "main.compare_materials_for_air_kerma_target",
        ) as photon_mode_air_comparison,
        patch(
            "main.compare_materials_for_target",
            return_value=cli_photon_comparison_result,
        ) as photon_mode_comparison,
        patch(
            "main.print_air_kerma_material_comparison_result",
        ) as photon_mode_air_output,
        patch(
            "main.print_material_comparison_result",
        ) as photon_mode_output,
    ):
        run_material_comparison_mode()

    assert_equal(
        "V1.12 photon comparison CLI passes response to target prompt",
        (
            comparison_photon_target_prompt
            .call_args
            .args[0]
        ),
        "photon_fluence_rate",
    )

    assert_equal(
        "V1.12 photon comparison CLI does not request exposure buildup",
        comparison_photon_buildup_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon comparison CLI calls photon solver",
        photon_mode_comparison.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon comparison CLI skips air-kerma solver",
        photon_mode_air_comparison.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon comparison CLI uses photon output",
        photon_mode_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon comparison CLI skips air-kerma output",
        photon_mode_air_output.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon comparison CLI disables exposure buildup",
        (
            photon_mode_comparison
            .call_args
            .kwargs[
                "apply_buildup"
            ]
        ),
        False,
    )

    # ------------------------------------------------------------
    # Material-optimization CLI routing
    # ------------------------------------------------------------

    cli_optimization_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    cli_optimization_constraints = (
        DesignConstraints(
            max_thickness_cm=20.0,
            max_mass_per_area_g_per_cm2=120.0,
        )
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value=(
                "collision_air_kerma_rate"
            ),
        ),
        patch(
            "main.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=solver_target,
        ) as optimization_air_target_prompt,
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_design_constraints_from_user",
            return_value=(
                cli_optimization_constraints
            ),
        ),
        patch(
            "main.get_optimization_mode_from_user",
            return_value="minimum_mass",
        ),
        patch(
            "main.get_optimization_weights_from_user",
        ) as air_optimization_weight_prompt,
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as air_optimization_buildup_prompt,
        patch(
            "main.optimize_air_kerma_material_selection",
            return_value=(
                air_kerma_minimum_mass_result
            ),
        ) as air_kerma_optimizer,
        patch(
            "main.optimize_material_selection",
        ) as photon_optimizer,
        patch(
            "main.print_optimized_design_result",
        ) as air_optimization_output,
    ):
        run_material_optimization_mode()

    assert_equal(
        "V1.12 optimization CLI passes air-kerma response to target prompt",
        (
            optimization_air_target_prompt
            .call_args
            .args[0]
        ),
        "collision_air_kerma_rate",
    )

    assert_equal(
        "V1.12 minimum-mass air-kerma optimization does not request weights",
        air_optimization_weight_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 air-kerma optimization requests buildup setting",
        air_optimization_buildup_prompt.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma optimization calls response-specific optimizer",
        air_kerma_optimizer.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma optimization skips photon optimizer",
        photon_optimizer.call_count,
        0,
    )

    assert_equal(
        "V1.12 air-kerma optimization uses engineering output",
        air_optimization_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves result",
        (
            air_optimization_output
            .call_args
            .args[0]
        ),
        air_kerma_minimum_mass_result,
    )

    air_kerma_optimizer_call = (
        air_kerma_optimizer.call_args
    )

    assert_equal(
        "V1.12 air-kerma optimization passes source",
        air_kerma_optimizer_call.kwargs[
            "source"
        ],
        cs137_solver_source,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes selected materials",
        air_kerma_optimizer_call.kwargs[
            "materials"
        ],
        cli_optimization_materials,
    )

    assert_close(
        "V1.12 air-kerma optimization passes detector distance",
        air_kerma_optimizer_call.kwargs[
            "detector_distance"
        ],
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes target",
        air_kerma_optimizer_call.kwargs[
            "target"
        ],
        solver_target,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes constraints",
        air_kerma_optimizer_call.kwargs[
            "constraints"
        ],
        cli_optimization_constraints,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes minimum-mass objective",
        air_kerma_optimizer_call.kwargs[
            "optimization_mode"
        ],
        "minimum_mass",
    )

    assert_equal(
        "V1.12 air-kerma optimization passes no weights",
        air_kerma_optimizer_call.kwargs[
            "weights"
        ],
        None,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes strict buildup request",
        air_kerma_optimizer_call.kwargs[
            "apply_buildup"
        ],
        True,
    )

    assert_close(
        "V1.12 air-kerma optimization passes calculation limit",
        air_kerma_optimizer_call.kwargs[
            "calculation_max_thickness"
        ],
        20.0,
        1.0e-12,
    )

    cli_air_optimization_best_candidate = (
        air_optimization_output
        .call_args
        .args[0]
        .best_candidate
    )

    if cli_air_optimization_best_candidate is None:
        raise AssertionError(
            "V1.12 CLI air-kerma optimization "
            "did not preserve a selected design."
        )

    assert_equal(
        "V1.12 CLI minimum-mass air-kerma optimization selects Lead",
        (
            cli_air_optimization_best_candidate
            .base_candidate
            .material
            .key
        ),
        "lead",
    )

    cli_photon_optimization_target = (
        FluxTarget(
            target_flux=100.0
        )
    )

    cli_photon_optimization_result = (
        optimize_material_selection(
            source=cs137_solver_source,
            materials=cli_optimization_materials,
            detector_distance=100.0,
            target=cli_photon_optimization_target,
            constraints=(
                cli_optimization_constraints
            ),
            optimization_mode="minimum_mass",
            calculation_max_thickness=20.0,
            apply_buildup=False,
        )
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "main.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=(
                cli_photon_optimization_target
            ),
        ) as photon_optimization_target_prompt,
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_design_constraints_from_user",
            return_value=(
                cli_optimization_constraints
            ),
        ),
        patch(
            "main.get_optimization_mode_from_user",
            return_value="minimum_mass",
        ),
        patch(
            "main.get_optimization_weights_from_user",
        ) as photon_optimization_weight_prompt,
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ) as photon_optimization_buildup_prompt,
        patch(
            "main.optimize_air_kerma_material_selection",
        ) as photon_mode_air_optimizer,
        patch(
            "main.optimize_material_selection",
            return_value=(
                cli_photon_optimization_result
            ),
        ) as photon_mode_optimizer,
        patch(
            "main.print_optimized_design_result",
        ) as photon_optimization_output,
    ):
        run_material_optimization_mode()

    assert_equal(
        "V1.12 photon optimization passes response to target prompt",
        (
            photon_optimization_target_prompt
            .call_args
            .args[0]
        ),
        "photon_fluence_rate",
    )

    assert_equal(
        "V1.12 minimum-mass photon optimization does not request weights",
        photon_optimization_weight_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon optimization does not request exposure buildup",
        photon_optimization_buildup_prompt.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon optimization calls photon optimizer",
        photon_mode_optimizer.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon optimization skips air-kerma optimizer",
        photon_mode_air_optimizer.call_count,
        0,
    )

    assert_equal(
        "V1.12 photon optimization uses engineering output",
        photon_optimization_output.call_count,
        1,
    )

    assert_equal(
        "V1.12 photon optimization disables exposure buildup",
        (
            photon_mode_optimizer
            .call_args
            .kwargs[
                "apply_buildup"
            ]
        ),
        False,
    )

    cli_balanced_weights = (
        OptimizationWeights(
            thickness_weight=1.0,
            mass_weight=2.0,
            cost_weight=3.0,
        )
    )

    with (
        patch(
            "main.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "main.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "main.get_response_quantity_from_user",
            return_value=(
                "collision_air_kerma_rate"
            ),
        ),
        patch(
            "main.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "main.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "main.get_target_from_user",
            return_value=solver_target,
        ),
        patch(
            "main.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "main.get_design_constraints_from_user",
            return_value=(
                cli_optimization_constraints
            ),
        ),
        patch(
            "main.get_optimization_mode_from_user",
            return_value="balanced",
        ),
        patch(
            "main.get_optimization_weights_from_user",
            return_value=cli_balanced_weights,
        ) as balanced_weight_prompt,
        patch(
            "main.get_apply_buildup_from_user",
            return_value=True,
        ),
        patch(
            "main.optimize_air_kerma_material_selection",
            return_value=air_kerma_balanced_result,
        ) as balanced_air_optimizer,
        patch(
            "main.print_optimized_design_result",
        ),
    ):
        run_material_optimization_mode()

    assert_equal(
        "V1.12 balanced air-kerma optimization requests weights",
        balanced_weight_prompt.call_count,
        1,
    )

    assert_equal(
        "V1.12 balanced air-kerma optimization passes weights",
        (
            balanced_air_optimizer
            .call_args
            .kwargs[
                "weights"
            ]
        ),
        cli_balanced_weights,
    )

    assert_equal(
        "V1.12 balanced air-kerma optimization passes objective",
        (
            balanced_air_optimizer
            .call_args
            .kwargs[
                "optimization_mode"
            ]
        ),
        "balanced",
    )

    # ------------------------------------------------------------
    # Response-aware engineering optimization output
    # ------------------------------------------------------------

    air_kerma_optimization_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        air_kerma_optimization_output_buffer
    ):
        print_optimized_design_result(
            air_kerma_minimum_mass_result
        )

    air_kerma_optimization_output_text = (
        air_kerma_optimization_output_buffer
        .getvalue()
    )

    air_kerma_optimization_output_requirements = [
        "Optimized material selection",
        "Best material: Lead",
        (
            "Selected final G-P exposure-buildup-"
            "adjusted collision air-kerma rate:"
        ),
        "Selected final response ratio:",
        "µGy/h",
        "Lead",
        "Tungsten",
        "Polyethylene",
        "Unavailable",
        "FAILED",
    ]

    for required_text in (
        air_kerma_optimization_output_requirements
    ):
        assert_equal(
            "V1.12 air-kerma optimization output "
            f"contains {required_text}",
            (
                required_text
                in air_kerma_optimization_output_text
            ),
            True,
        )

    # ------------------------------------------------------------
    # Response-aware engineering optimization output
    # ------------------------------------------------------------

    air_kerma_optimization_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        air_kerma_optimization_output_buffer
    ):
        print_optimized_design_result(
            air_kerma_minimum_mass_result
        )

    air_kerma_optimization_output_text = (
        air_kerma_optimization_output_buffer
        .getvalue()
    )

    air_kerma_optimization_output_requirements = [
        "Optimized material selection",
        "Best material: Lead",
        (
            "Selected final G-P exposure-buildup-"
            "adjusted collision air-kerma rate:"
        ),
        "Selected final response ratio:",
        "µGy/h",
        "Lead",
        "Tungsten",
        "Polyethylene",
        "Unavailable",
        "FAILED",
    ]

    for required_text in (
        air_kerma_optimization_output_requirements
    ):
        assert_equal(
            "V1.12 air-kerma optimization output "
            f"contains {required_text}",
            (
                required_text
                in air_kerma_optimization_output_text
            ),
            True,
        )

    strict_optimization_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        strict_optimization_output_buffer
    ):
        print_optimized_design_result(
            strict_air_kerma_failure_result
        )

    strict_optimization_output_text = (
        strict_optimization_output_buffer
        .getvalue()
    )

    strict_output_requirements = [
        "Best material: None",
        "Polyethylene",
        "Unavailable",
        "FAILED",
        "requires valid G-P exposure buildup",
    ]

    for required_text in strict_output_requirements:
        assert_equal(
            "V1.12 strict optimization output "
            f"contains {required_text}",
            (
                required_text
                in strict_optimization_output_text
            ),
            True,
        )

    assert_equal(
        "V1.12 strict failed candidate is not displayed as fallback",
        (
            "Fallback"
            in strict_optimization_output_text
        ),
        False,
    )

    uncollided_warning_optimization_result = (
        optimize_air_kerma_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_lead,
            ],
            detector_distance=100.0,
            target=AirKermaRateTarget(
                target_air_kerma_rate_microgy_per_h=(
                    1.0e6
                )
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
            calculation_max_thickness=20.0,
            apply_buildup=False,
        )
    )

    uncollided_warning_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        uncollided_warning_output_buffer
    ):
        print_optimized_design_result(
            uncollided_warning_optimization_result
        )

    uncollided_warning_output_text = (
        uncollided_warning_output_buffer
        .getvalue()
    )

    assert_equal(
        "V1.12 uncollided optimization output identifies response",
        (
            "Selected final uncollided collision "
            "air-kerma rate:"
            in uncollided_warning_output_text
        ),
        True,
    )

    assert_equal(
        "V1.12 uncollided air-kerma warning is not labeled fallback",
        (
            "Fallback"
            in uncollided_warning_output_text
        ),
        False,
    )

    assert_equal(
        "V1.12 uncollided air-kerma output reports buildup not requested",
        (
            "Buildup requested: No"
            in uncollided_warning_output_text
        ),
        True,
    )

    legacy_fallback_optimization_result = (
        optimize_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials[
                    "concrete_barite"
                ],
            ],
            detector_distance=100.0,
            target=FluxTarget(
                target_flux=100.0
            ),
            constraints=DesignConstraints(),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=100.0,
            apply_buildup=True,
        )
    )

    legacy_fallback_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        legacy_fallback_output_buffer
    ):
        print_optimized_design_result(
            legacy_fallback_optimization_result
        )

    legacy_fallback_output_text = (
        legacy_fallback_output_buffer
        .getvalue()
    )

    assert_equal(
        "V1.12 output preserves legacy photon fallback display",
        (
            "Fallback"
            in legacy_fallback_output_text
        ),
        True,
    )

    # ------------------------------------------------------------
    # Remaining photon-response terminology
    # ------------------------------------------------------------

    assert_equal(
        "V1.12 photon target description identifies uncollided fluence rate",
        get_target_description(
            FluxTarget(
                target_flux=100.0
            ),
            apply_buildup=False,
        ),
        (
            "Uncollided photon fluence-rate target "
            "<= 100 photons/cm^2/s"
        ),
    )

    assert_equal(
        "V1.12 historical buildup target description identifies proxy",
        get_target_description(
            FluxTarget(
                target_flux=100.0
            ),
            apply_buildup=True,
        ),
        (
            "Legacy G-P exposure-buildup-adjusted "
            "photon-response proxy target <= 100"
        ),
    )

    photon_minimum_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        photon_minimum_output_buffer
    ):
        print_minimum_thickness_result(
            cli_photon_design
        )

    photon_minimum_output_text = (
        photon_minimum_output_buffer
        .getvalue()
    )

    photon_minimum_requirements = [
        (
            "Photon-response minimum shielding "
            "thickness result"
        ),
        (
            "Final selected-response ratio:"
        ),
        (
            "Final target-comparison uncollided "
            "photon fluence rate:"
        ),
        (
            "Final uncollided photon "
            "fluence rate:"
        ),
        "photons/cm^2/s",
    ]

    for required_text in (
        photon_minimum_requirements
    ):
        assert_equal(
            "V1.12 photon minimum output "
            f"contains {required_text}",
            (
                required_text
                in photon_minimum_output_text
            ),
            True,
        )

    assert_equal(
        "V1.12 photon minimum output removes generic flux label",
        (
            "Final target-comparison flux:"
            in photon_minimum_output_text
        ),
        False,
    )

    photon_comparison_output_buffer = (
        StringIO()
    )

    with redirect_stdout(
        photon_comparison_output_buffer
    ):
        print_material_comparison_result(
            cli_photon_comparison_result
        )

    photon_comparison_output_text = (
        photon_comparison_output_buffer
        .getvalue()
    )

    photon_comparison_requirements = [
        (
            "Photon-response material "
            "comparison result"
        ),
        "Final Fluence Rate",
        "Response Basis",
        "Uncollided fluence",
        "photons/cm^2/s",
    ]

    for required_text in (
        photon_comparison_requirements
    ):
        assert_equal(
            "V1.12 photon comparison output "
            f"contains {required_text}",
            (
                required_text
                in photon_comparison_output_text
            ),
            True,
        )

    assert_equal(
        "V1.12 photon comparison output removes Final Flux column",
        (
            "Final Flux"
            in photon_comparison_output_text
        ),
        False,
    )


if __name__ == "__main__":
    run_validation_tests()