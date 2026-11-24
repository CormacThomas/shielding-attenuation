"""Verification cases migrated from the original validation runner."""

from pathlib import Path

from shielding.data.isotopes import (
    create_isotope_source,
)
from shielding.data.materials import get_material_library
from shielding.design.comparison import (
    AirKermaMaterialDesignCandidate,
)
from shielding.design.kerma_thickness import (
    calculate_air_kerma_minimum_thickness,
    calculate_air_kerma_response_at_thickness,
    calculate_maximum_gp_valid_thickness_cm,
    get_source_photon_energies_mev,
)
from shielding.design.models import DesignConstraints
from shielding.design.targets import (
    AirKermaMinimumThicknessResult,
    AirKermaRateTarget,
)
from shielding.physics.air_kerma import calculate_source_air_kerma_result
from shielding.physics.models import Layer
from shielding.physics.source_models import ManualPhotonSource
from shielding.physics.units import (
    convert_gy_per_s_to_microgy_per_h,
)
from shielding.scenarios.geometry import ConcentricSphericalGeometry
from shielding.scenarios.json_io import load_scenario
from shielding.scenarios.models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ShieldingScenario,
)
from shielding.scenarios.runner import run_scenario
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_less_than_or_equal,
    assert_not_none,
    assert_raises,
    get_optimized_candidate_by_material_key,
)


def test_shielding_and_gp_integration() -> None:
    # Real shielding and G-P integration

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

    manual_result = calculate_source_air_kerma_result(
        source=manual_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=False,
    )

    assert_equal(
        "V1.12 manual source produces one response line",
        len(manual_result.line_results),
        1,
    )

    assert_greater_than(
        "V1.12 shielded manual source produces positive air kerma",
        (manual_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        0.0,
    )

    manual_buildup_result = calculate_source_air_kerma_result(
        source=manual_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=True,
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
                manual_buildup_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        (manual_buildup_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
    )

    one_ci_bq = 3.7e10

    cs137_source = create_isotope_source(
        "cs137",
        one_ci_bq,
    )

    cs137_source_result = calculate_source_air_kerma_result(
        source=cs137_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=True,
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

    co60_source_result = calculate_source_air_kerma_result(
        source=co60_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=True,
    )

    assert_equal(
        "V1.12 Co-60 response contains two photon lines",
        len(co60_source_result.line_results),
        2,
    )

    assert_close(
        "V1.12 Co-60 uncollided total equals line sum",
        (co60_source_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        sum(
            line_result.uncollided_collision_air_kerma_rate_gy_per_s
            for line_result in co60_source_result.line_results
        ),
        1.0e-20,
    )

    assert_close(
        "V1.12 Co-60 buildup-adjusted total equals line sum",
        assert_not_none(
            "V1.12 Co-60 buildup total exists",
            (
                co60_source_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        sum(
            assert_not_none(
                "V1.12 Co-60 adjusted line exists",
                (line_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s),
            )
            for line_result in co60_source_result.line_results
        ),
        1.0e-20,
    )

    am241_source = create_isotope_source(
        "am241",
        one_ci_bq,
    )

    am241_result = calculate_source_air_kerma_result(
        source=am241_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=True,
    )

    assert_equal(
        "V1.12 Am-241 buildup is unavailable beyond valid MFP range",
        am241_result.buildup_status,
        "unavailable",
    )

    assert_equal(
        "V1.12 unavailable Am-241 buildup has no adjusted total",
        (am241_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s),
        None,
    )

    assert_greater_than(
        "V1.12 unavailable Am-241 buildup preserves warning",
        len(am241_result.warnings),
        0,
    )

    zero_thickness_result = calculate_source_air_kerma_result(
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

    zero_thickness_line = zero_thickness_result.line_results[0]

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
            (zero_thickness_line.buildup_adjusted_collision_air_kerma_rate_gy_per_s),
        ),
        (zero_thickness_line.uncollided_collision_air_kerma_rate_gy_per_s),
        1.0e-20,
    )


def test_air_kerma_minimum_thickness() -> None:
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
    manual_result = calculate_source_air_kerma_result(
        source=manual_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=False,
    )
    one_ci_bq = 3.7e10
    cs137_source = create_isotope_source(
        "cs137",
        one_ci_bq,
    )
    cs137_source_result = calculate_source_air_kerma_result(
        source=cs137_source,
        layers=lead_layers,
        detector_distance_cm=100.0,
        apply_buildup=True,
    )

    # Air-kerma target and minimum-thickness result models

    air_kerma_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)

    assert_close(
        "V1.12 air-kerma target converts microGy per hour to Gy per second",
        air_kerma_target.target_air_kerma_rate_gy_per_s,
        1.0 / 3.6e9,
        1.0e-20,
    )

    assert_raises(
        "V1.12 nonpositive air-kerma target rejected",
        ValueError,
        lambda: AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=0.0),
        "must be greater than zero",
    )

    uncollided_design_result = AirKermaMinimumThicknessResult(
        material=materials["lead"],
        required_thickness=5.0,
        final_source_response=manual_result,
        final_response_ratio=0.5,
        target_description=("Collision air-kerma-rate target <= 1 µGy/h"),
        warnings=[],
        calculation_mode=("Uncollided collision air-kerma minimum thickness design"),
        buildup_used=False,
    )

    assert_close(
        "V1.12 uncollided design selects uncollided air-kerma response",
        uncollided_design_result.final_air_kerma_rate_gy_per_s,
        (manual_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        1.0e-20,
    )

    assert_close(
        "V1.12 design result converts selected response to microGy per hour",
        uncollided_design_result.final_air_kerma_rate_microgy_per_h,
        convert_gy_per_s_to_microgy_per_h(
            manual_result.total_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-12,
    )

    buildup_design_result = AirKermaMinimumThicknessResult(
        material=materials["lead"],
        required_thickness=5.0,
        final_source_response=cs137_source_result,
        final_response_ratio=0.5,
        target_description=(
            "G-P buildup-adjusted collision air-kerma-rate target <= 1 µGy/h"
        ),
        warnings=[],
        calculation_mode=(
            "G-P buildup-adjusted collision air-kerma minimum thickness design"
        ),
        buildup_used=True,
    )

    assert_close(
        "V1.12 buildup design selects buildup-adjusted air-kerma response",
        buildup_design_result.final_air_kerma_rate_gy_per_s,
        assert_not_none(
            "V1.12 buildup design adjusted response exists",
            (
                cs137_source_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        1.0e-20,
    )

    assert_close(
        "V1.12 buildup design preserves uncollided source response",
        (buildup_design_result.final_uncollided_collision_air_kerma_rate_gy_per_s),
        (cs137_source_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
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

    solver_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)

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
        get_source_photon_energies_mev(manual_solver_source),
        [0.661657],
    )

    assert_equal(
        "V1.12 Co-60 source energy extraction",
        get_source_photon_energies_mev(co60_solver_source),
        [
            1.173228,
            1.332492,
        ],
    )

    maximum_gp_thickness_cm = calculate_maximum_gp_valid_thickness_cm(
        source=cs137_solver_source,
        material=solver_lead,
    )

    assert_greater_than(
        "V1.12 G-P-valid thickness limit is positive",
        maximum_gp_thickness_cm,
        0.0,
    )

    near_gp_limit_response, _ = calculate_air_kerma_response_at_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        thickness_cm=(maximum_gp_thickness_cm * 0.999999),
        apply_buildup=True,
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
            thickness_cm=(maximum_gp_thickness_cm * 1.000001),
            apply_buildup=True,
        ),
        "requires valid G-P exposure buildup",
    )

    mn54_solver_source = create_isotope_source(
        "mn54",
        3.7e10,
    )

    copper_gp_limit_cm = calculate_maximum_gp_valid_thickness_cm(
        source=mn54_solver_source,
        material=solver_materials["copper"],
    )

    copper_limit_response, _ = calculate_air_kerma_response_at_thickness(
        source=mn54_solver_source,
        material=solver_materials["copper"],
        detector_distance_cm=100.0,
        thickness_cm=copper_gp_limit_cm,
        apply_buildup=True,
    )

    assert_equal(
        "V1.12 floating-point 40-MFP boundary remains valid",
        copper_limit_response.buildup_status,
        "applied",
    )

    uncollided_solver_result = calculate_air_kerma_minimum_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=20.0,
        apply_buildup=False,
    )

    assert_greater_than(
        "V1.12 uncollided air-kerma design requires shielding",
        uncollided_solver_result.required_thickness,
        0.0,
    )

    assert_equal(
        "V1.12 uncollided air-kerma design satisfies target",
        (
            uncollided_solver_result.final_air_kerma_rate_gy_per_s
            <= solver_target.target_air_kerma_rate_gy_per_s
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
        ("Uncollided collision air-kerma rate <= 1 µGy/h"),
    )

    buildup_solver_result = calculate_air_kerma_minimum_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=20.0,
        apply_buildup=True,
    )

    assert_greater_than(
        "V1.12 buildup-aware design requires more Lead than uncollided design",
        buildup_solver_result.required_thickness,
        uncollided_solver_result.required_thickness,
    )

    assert_equal(
        "V1.12 buildup-aware air-kerma design satisfies target",
        (
            buildup_solver_result.final_air_kerma_rate_gy_per_s
            <= solver_target.target_air_kerma_rate_gy_per_s
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
        (buildup_solver_result.final_source_response.buildup_status),
        "applied",
    )

    assert_equal(
        "V1.12 buildup-aware design response ratio is physical",
        (0.0 < buildup_solver_result.final_response_ratio <= 1.0),
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

    no_shielding_result = calculate_air_kerma_minimum_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0e6),
        max_thickness_cm=20.0,
        apply_buildup=True,
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


def test_nonmonotonic_buildup_bracketing() -> None:
    solver_materials = get_material_library()
    solver_lead = solver_materials["lead"]
    solver_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)
    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
    )

    water_buildup_source = ManualPhotonSource(
        energy=0.1,
        photon_rate=3.7e10,
    )

    _, water_unshielded_rate = calculate_air_kerma_response_at_thickness(
        source=water_buildup_source,
        material=solver_materials["water"],
        detector_distance_cm=100.0,
        thickness_cm=0.0,
        apply_buildup=True,
    )

    _, water_one_cm_rate = calculate_air_kerma_response_at_thickness(
        source=water_buildup_source,
        material=solver_materials["water"],
        detector_distance_cm=100.0,
        thickness_cm=1.0,
        apply_buildup=True,
    )

    assert_greater_than(
        "V1.12 buildup response can initially increase with shielding",
        water_one_cm_rate,
        water_unshielded_rate,
    )

    water_buildup_target = AirKermaRateTarget(
        target_air_kerma_rate_microgy_per_h=(
            convert_gy_per_s_to_microgy_per_h(0.5 * water_unshielded_rate)
        )
    )

    water_buildup_design = calculate_air_kerma_minimum_thickness(
        source=water_buildup_source,
        material=solver_materials["water"],
        detector_distance_cm=100.0,
        target=water_buildup_target,
        max_thickness_cm=100.0,
        apply_buildup=True,
        bracket_scan_intervals=200,
    )

    assert_greater_than(
        "V1.12 bracketed buildup design passes beyond initial response rise",
        water_buildup_design.required_thickness,
        1.0,
    )

    assert_equal(
        "V1.12 bracketed buildup design satisfies target",
        (
            water_buildup_design.final_air_kerma_rate_gy_per_s
            <= water_buildup_target.target_air_kerma_rate_gy_per_s
        ),
        True,
    )

    slightly_thinner_water_cm = water_buildup_design.required_thickness - 1.0e-5

    _, slightly_thinner_water_rate = calculate_air_kerma_response_at_thickness(
        source=water_buildup_source,
        material=solver_materials["water"],
        detector_distance_cm=100.0,
        thickness_cm=slightly_thinner_water_cm,
        apply_buildup=True,
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


def test_reproducible_air_kerma_scenario() -> None:
    solver_materials = get_material_library()
    solver_lead = solver_materials["lead"]
    solver_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)
    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
    )
    buildup_solver_result = calculate_air_kerma_minimum_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=20.0,
        apply_buildup=True,
    )
    air_kerma_scenario = ShieldingScenario(
        scenario_id="cs137_air_kerma_serialization_test",
        description=(
            "V1.12 reproducible Cs-137 collision air-kerma scenario serialization test."
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
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0),
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

    # Reproducible air-kerma scenario execution

    air_kerma_scenario_result = run_scenario(air_kerma_scenario)

    assert_equal(
        "V1.12 air-kerma scenario preserves target description",
        air_kerma_scenario_result.target_description,
        ("G-P exposure-buildup-adjusted collision air-kerma rate <= 1 µGy/h"),
    )

    assert_equal(
        "V1.12 air-kerma scenario preserves buildup setting",
        air_kerma_scenario_result.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma scenario preserves candidate count",
        len(air_kerma_scenario_result.all_candidates),
        2,
    )

    assert_equal(
        "V1.12 air-kerma scenario has two eligible candidates",
        len(air_kerma_scenario_result.eligible_candidates()),
        2,
    )

    air_kerma_scenario_best_candidate = air_kerma_scenario_result.best_candidate

    if air_kerma_scenario_best_candidate is None:
        raise AssertionError("V1.12 air-kerma scenario did not select a candidate.")

    assert_equal(
        "V1.12 minimum-mass air-kerma scenario selects Lead",
        (air_kerma_scenario_best_candidate.base_candidate.material.key),
        "lead",
    )

    air_kerma_scenario_base_candidate = air_kerma_scenario_best_candidate.base_candidate

    if not isinstance(
        air_kerma_scenario_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "V1.12 scenario runner did not preserve the air-kerma candidate type."
        )

    air_kerma_scenario_final_rate = (
        air_kerma_scenario_base_candidate.final_air_kerma_rate_microgy_per_h
    )

    if air_kerma_scenario_final_rate is None:
        raise AssertionError(
            "V1.12 air-kerma scenario did not preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 air-kerma scenario satisfies target",
        air_kerma_scenario_final_rate,
        (solver_target.target_air_kerma_rate_microgy_per_h + 1.0e-8),
    )

    air_kerma_scenario_design_result = air_kerma_scenario_base_candidate.design_result

    if air_kerma_scenario_design_result is None:
        raise AssertionError(
            "V1.12 air-kerma scenario did not preserve its design result."
        )

    assert_equal(
        "V1.12 air-kerma scenario applies source buildup",
        (air_kerma_scenario_design_result.final_source_response.buildup_status),
        "applied",
    )

    assert_close(
        "V1.12 scenario and direct solver reproduce Lead thickness",
        (air_kerma_scenario_design_result.required_thickness),
        buildup_solver_result.required_thickness,
        1.0e-8,
    )

    scenario_lead_mass = assert_not_none(
        "V1.12 scenario-selected Lead mass exists",
        (air_kerma_scenario_best_candidate.mass_per_area_g_per_cm2),
    )

    assert_close(
        "V1.12 scenario-selected Lead mass equals density times thickness",
        scenario_lead_mass,
        (
            air_kerma_scenario_base_candidate.material.density
            * air_kerma_scenario_design_result.required_thickness
        ),
        1.0e-10,
    )

    assert_equal(
        "V1.12 air-kerma scenario provides selection reason",
        (air_kerma_scenario_result.selection_reason is not None),
        True,
    )

    strict_air_kerma_failure_scenario = ShieldingScenario(
        scenario_id=("air_kerma_strict_buildup_failure"),
        description=(
            "Confirm that air-kerma scenarios do not "
            "silently fall back when requested G-P "
            "buildup is unavailable."
        ),
        calculation_mode=("material_optimization"),
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
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0),
        constraints=DesignConstraints(),
        optimization_mode="minimum_mass",
        deterministic_settings=(
            DeterministicSettings(
                apply_buildup=True,
                calculation_max_thickness_cm=20.0,
            )
        ),
    )

    strict_air_kerma_failure_result = run_scenario(strict_air_kerma_failure_scenario)

    assert_equal(
        "V1.12 strict air-kerma scenario has no selected design",
        strict_air_kerma_failure_result.best_candidate,
        None,
    )

    assert_equal(
        "V1.12 strict air-kerma scenario preserves failed candidate",
        len(strict_air_kerma_failure_result.failed_candidates()),
        1,
    )

    strict_failed_candidate = strict_air_kerma_failure_result.failed_candidates()[0]

    assert_equal(
        "V1.12 strict scenario marks unsupported buildup as FAILED",
        strict_failed_candidate.optimization_status,
        "FAILED",
    )

    strict_failure_reason = strict_failed_candidate.base_candidate.failure_reason

    if strict_failure_reason is None or strict_failure_reason.strip() == "":
        raise AssertionError(
            "V1.12 strict air-kerma scenario did not preserve its failure reason."
        )

    assert_equal(
        "V1.12 strict scenario reports G-P requirement",
        ("requires valid G-P exposure buildup" in strict_failure_reason),
        True,
    )


def test_air_kerma_reference_scenario() -> None:
    # Official V1.12 air-kerma reference scenario

    air_kerma_reference_scenario_path = (
        Path(__file__).resolve().parents[2]
        / "scenarios"
        / "cs137_air_kerma_reference.json"
    )

    assert_equal(
        "V1.12 official air-kerma reference scenario file exists",
        air_kerma_reference_scenario_path.is_file(),
        True,
    )

    official_air_kerma_scenario = load_scenario(air_kerma_reference_scenario_path)

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
        len(official_air_kerma_scenario.candidate_material_keys),
        9,
    )

    official_air_kerma_target = official_air_kerma_scenario.target

    if not isinstance(
        official_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError(
            "Official V1.12 scenario did not reconstruct an AirKermaRateTarget."
        )

    assert_close(
        "V1.12 official scenario preserves air-kerma target",
        (official_air_kerma_target.target_air_kerma_rate_microgy_per_h),
        1.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 official scenario requires buildup",
        (official_air_kerma_scenario.deterministic_settings.apply_buildup),
        True,
    )

    assert_equal(
        "V1.12 official scenario uses minimum-mass objective",
        official_air_kerma_scenario.optimization_mode,
        "minimum_mass",
    )

    official_air_kerma_result = run_scenario(official_air_kerma_scenario)

    assert_equal(
        "V1.12 official scenario returns nine candidates",
        len(official_air_kerma_result.all_candidates),
        9,
    )

    assert_equal(
        "V1.12 official scenario preserves target description",
        official_air_kerma_result.target_description,
        ("G-P exposure-buildup-adjusted collision air-kerma rate <= 1 µGy/h"),
    )

    official_air_kerma_best_candidate = official_air_kerma_result.best_candidate

    if official_air_kerma_best_candidate is None:
        raise AssertionError(
            "Official V1.12 air-kerma scenario did not select a design."
        )

    assert_equal(
        "V1.12 official minimum-mass scenario selects Lead",
        (official_air_kerma_best_candidate.base_candidate.material.key),
        "lead",
    )

    official_air_kerma_base_candidate = official_air_kerma_best_candidate.base_candidate

    if not isinstance(
        official_air_kerma_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "Official V1.12 scenario did not preserve the air-kerma candidate type."
        )

    official_air_kerma_design_result = official_air_kerma_base_candidate.design_result

    if official_air_kerma_design_result is None:
        raise AssertionError(
            "Official V1.12 selected candidate did not preserve its design result."
        )

    assert_close(
        "V1.12 official Lead reference thickness",
        (official_air_kerma_design_result.required_thickness),
        7.180648660287261,
        1.0e-8,
    )

    official_air_kerma_mass = assert_not_none(
        "V1.12 official Lead reference mass exists",
        (official_air_kerma_best_candidate.mass_per_area_g_per_cm2),
    )

    assert_close(
        "V1.12 official Lead reference mass per area",
        official_air_kerma_mass,
        81.42855580765755,
        1.0e-7,
    )

    official_air_kerma_final_rate = (
        official_air_kerma_base_candidate.final_air_kerma_rate_microgy_per_h
    )

    if official_air_kerma_final_rate is None:
        raise AssertionError(
            "Official V1.12 selected design did not preserve its final air-kerma rate."
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
        (official_air_kerma_design_result.final_source_response.buildup_status),
        "applied",
    )

    official_barite_candidate = get_optimized_candidate_by_material_key(
        official_air_kerma_result,
        "concrete_barite",
    )

    official_polyethylene_candidate = get_optimized_candidate_by_material_key(
        official_air_kerma_result,
        "polyethylene",
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
        failure_reason = unsupported_candidate.base_candidate.failure_reason

        if failure_reason is None or failure_reason.strip() == "":
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
