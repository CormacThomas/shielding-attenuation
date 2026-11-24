"""Verification cases migrated from the original validation runner."""

from pathlib import Path

from shielding.data.isotopes import (
    create_isotope_source,
    get_available_isotopes,
)
from shielding.data.materials import get_material_library
from shielding.design.comparison import (
    compare_materials_for_target,
)
from shielding.design.response_curves import create_response_curve
from shielding.design.targets import (
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from shielding.design.thickness import (
    calculate_isotope_minimum_thickness,
    calculate_manual_minimum_thickness,
    calculate_unshielded_isotope_flux,
    calculate_unshielded_manual_flux,
)
from shielding.physics.models import Layer
from shielding.physics.source_models import ManualPhotonSource
from shielding.physics.source_transport import (
    calculate_isotope_source_result,
    calculate_manual_source_result,
)
from shielding.physics.units import (
    convert_activity_to_bq,
)
from shielding.reporting.optimization_data import evaluate_maximum_constraint
from shielding.reporting.style import format_plot_text
from shielding.scenarios.json_io import load_scenario
from shielding.scenarios.runner import run_scenario
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_less_than_or_equal,
    assert_not_none,
    assert_raises,
    get_candidate_by_material_key,
    get_response_curve_point_by_thickness,
)


def test_isotope_source_library() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")

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
                expected_photon_rate_sum + source.activity_bq * photon_line.intensity
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


def test_manual_cs137_lead_reference() -> None:
    materials = get_material_library()
    lead_layer = Layer(5.0, materials["lead"])
    layers = [lead_layer]
    detector_distance = 100.0

    # Regression test: manual source mode should reproduce the V1.05 Cs-137 lead case.

    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )

    manual_result = calculate_manual_source_result(
        manual_source,
        layers,
        detector_distance,
    )

    assert_close(
        "Manual source V1.05 uncollided flux regression",
        manual_result.total_uncollided_flux,
        5.40662e2,
        1e-2,
    )


def test_minimum_thickness() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
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


def test_material_comparison() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )
    cs137_source = create_isotope_source("cs137", one_ci_bq)

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
        apply_buildup=False,
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
        "Barite Concrete can use uncollided photon comparison",
        barite_candidate.status,
        "PASS",
    )

    assert_raises(
        ("V1.08 photon material comparison rejects G-P exposure buildup"),
        ValueError,
        lambda: compare_materials_for_target(
            source=cs137_source,
            materials=[
                materials["lead"],
            ],
            detector_distance=detector_distance,
            target=FluxTarget(100.0),
            max_thickness=detector_distance,
            apply_buildup=True,
        ),
        "not supported for photon fluence",
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
        raise AssertionError(
            "Failed material candidate did not preserve failure reason."
        )

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


def test_manual_response_curve() -> None:
    materials = get_material_library()
    detector_distance = 100.0
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )
    manual_flux_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
    )
    manual_unshielded_flux = calculate_unshielded_manual_flux(
        manual_source,
        detector_distance,
    )

    # Validate a supported manual-source response curve.

    manual_response_curve = create_response_curve(
        source=manual_source,
        material=materials["lead"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=21,
        apply_buildup=False,
        target=FluxTarget(100.0),
        required_thickness_cm=(manual_flux_target_result.required_thickness),
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

    manual_required_curve_point = get_response_curve_point_by_thickness(
        manual_response_curve,
        manual_flux_target_result.required_thickness,
    )

    assert_less_than_or_equal(
        ("V1.10 manual uncollided curve reaches target at required thickness"),
        manual_required_curve_point.uncollided_flux,
        100.000001,
    )

    assert_equal(
        ("V1.10 manual curve identifies uncollided photon fluence"),
        manual_response_curve.quantity_name,
        "Uncollided photon fluence rate",
    )


def test_isotope_response_curve() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    cs137_source = create_isotope_source("cs137", one_ci_bq)
    cs137_flux_target_result = calculate_isotope_minimum_thickness(
        cs137_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
        max_thickness=detector_distance,
    )

    # Validate isotope-source response-curve generation.

    isotope_response_curve = create_response_curve(
        source=cs137_source,
        material=materials["lead"],
        detector_distance_cm=detector_distance,
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=21,
        apply_buildup=False,
        target=FluxTarget(100.0),
        required_thickness_cm=(cs137_flux_target_result.required_thickness),
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

    isotope_required_curve_point = get_response_curve_point_by_thickness(
        isotope_response_curve,
        cs137_flux_target_result.required_thickness,
    )

    assert_less_than_or_equal(
        ("V1.10 isotope uncollided curve reaches target at required thickness"),
        isotope_required_curve_point.uncollided_flux,
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
        format_plot_text("Flux target <= 100 photons/cm^2/s; density >= 1 g/cm^3"),
        ("Flux target ≤ 100 photons/cm²/s; density ≥ 1 g/cm³"),
    )


def test_uncollided_reference_scenario() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    reference_scenario_path = (
        repository_root / "scenarios" / "cs137_v110_reference.json"
    )
    reference_scenario = load_scenario(reference_scenario_path)

    # Complete deterministic execution

    scenario_result = run_scenario(reference_scenario)

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
        raise AssertionError("V1.11 reference scenario requires a selected candidate.")

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
        ("V1.11 uncollided reference scenario reproduces Lead thickness"),
        lead_required_thickness,
        6.210850924253464,
        1.0e-5,
    )

    expected_lead_mass_per_area = (
        best_candidate.base_candidate.material.density * lead_required_thickness
    )

    assert_close(
        ("V1.11 Lead mass per area equals density times thickness"),
        lead_mass_per_area,
        expected_lead_mass_per_area,
        1.0e-10,
    )

    assert_equal(
        "V1.11 reference scenario provides selection reason",
        scenario_result.selection_reason is not None,
        True,
    )
