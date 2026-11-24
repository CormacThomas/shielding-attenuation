"""Verification cases migrated from the original validation runner."""

from shielding.data.isotopes import create_isotope_source
from shielding.data.materials import get_material_library
from shielding.data.relative_costs import get_material_cost_library
from shielding.design.comparison import (
    AirKermaMaterialDesignCandidate,
    compare_materials_for_air_kerma_target,
)
from shielding.design.models import (
    DesignConstraints,
    OptimizationWeights,
)
from shielding.design.optimization import (
    calculate_mass_per_area,
    calculate_relative_cost_index_per_area,
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
)
from shielding.physics.units import convert_activity_to_bq
from shielding.reporting.optimization_data import (
    create_optimization_plot_data,
    create_pareto_points,
)
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_less_than_or_equal,
    assert_not_none,
    assert_raises,
    get_air_kerma_candidate_by_material_key,
    get_optimized_candidate_by_material_key,
)


def test_constrained_material_selection() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    cs137_source = create_isotope_source("cs137", one_ci_bq)
    comparison_materials = [
        materials["lead"],
        materials["tungsten"],
        materials["concrete_ordinary"],
        materials["concrete_barite"],
        materials["water"],
        materials["polyethylene"],
    ]

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
    lead_relative_cost_index = material_cost_library["lead"].relative_cost_index

    lead_relative_cost_per_area = calculate_relative_cost_index_per_area(
        lead_mass_per_area,
        lead_relative_cost_index,
    )

    assert_close(
        "V1.09 relative cost per area calculation",
        lead_relative_cost_per_area,
        79.38 * lead_relative_cost_index,
        1e-10,
    )

    minimum_thickness_optimization_result = optimize_material_selection(
        source=cs137_source,
        materials=comparison_materials,
        detector_distance=detector_distance,
        target=FluxTarget(100.0),
        constraints=DesignConstraints(),
        optimization_mode="minimum_thickness",
        calculation_max_thickness=detector_distance,
        apply_buildup=False,
    )

    if minimum_thickness_optimization_result.best_candidate is None:
        raise AssertionError(
            "Minimum-thickness optimization did not select a candidate."
        )

    eligible_thicknesses = []

    for candidate in minimum_thickness_optimization_result.eligible_candidates():
        thickness = assert_not_none(
            "Eligible V1.09 candidate thickness",
            candidate.base_candidate.required_thickness,
        )

        eligible_thicknesses.append(thickness)

    best_thickness = assert_not_none(
        "Best V1.09 minimum-thickness candidate thickness",
        minimum_thickness_optimization_result.best_candidate.base_candidate.required_thickness,
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
        apply_buildup=False,
    )

    water_optimized_candidate = get_optimized_candidate_by_material_key(
        thickness_constraint_result,
        "water",
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

    multiple_rejection_candidate = get_optimized_candidate_by_material_key(
        multiple_constraint_result,
        "water",
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
        apply_buildup=False,
    )

    if minimum_mass_result.best_candidate is None:
        raise AssertionError("Minimum-mass optimization did not select a candidate.")

    eligible_mass_values = []

    for candidate in minimum_mass_result.eligible_candidates():
        candidate_mass = assert_not_none(
            "Eligible V1.09 candidate mass per area",
            candidate.mass_per_area_g_per_cm2,
        )

        eligible_mass_values.append(candidate_mass)

    best_mass = assert_not_none(
        "Best V1.09 mass candidate mass per area",
        minimum_mass_result.best_candidate.mass_per_area_g_per_cm2,
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
        apply_buildup=False,
    )

    if minimum_cost_result.best_candidate is None:
        raise AssertionError("Minimum-cost optimization did not select a candidate.")

    eligible_cost_values = []

    for candidate in minimum_cost_result.eligible_candidates():
        candidate_cost = assert_not_none(
            "Eligible V1.09 candidate relative cost",
            candidate.relative_cost_index_per_area,
        )

        eligible_cost_values.append(candidate_cost)

    best_cost = assert_not_none(
        "Best V1.09 cost candidate relative cost",
        minimum_cost_result.best_candidate.relative_cost_index_per_area,
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
        apply_buildup=False,
    )

    if balanced_result.best_candidate is None:
        raise AssertionError("Balanced optimization did not select a candidate.")

    eligible_balanced_scores = []

    for candidate in balanced_result.eligible_candidates():
        candidate_score = assert_not_none(
            "Eligible balanced candidate score",
            candidate.optimization_score,
        )

        assert_greater_than(
            f"{candidate.base_candidate.material.key} balanced score is not below zero",
            candidate_score + 1.0e-12,
            0.0,
        )

        assert_less_than_or_equal(
            f"{candidate.base_candidate.material.key} balanced score is not above one",
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

    failed_optimized_lead = get_optimized_candidate_by_material_key(
        failed_optimization_result,
        "lead",
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
        raise AssertionError("Negative design constraint should have failed.")
    except ValueError:
        print("PASS: Negative V1.09 design constraint rejected")

    try:
        OptimizationWeights(0.0, 0.0, 0.0)
        raise AssertionError("Zero optimization weights should have failed.")
    except ValueError:
        print("PASS: Zero V1.09 optimization weights rejected")


def test_thickness_mass_pareto() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    cs137_source = create_isotope_source("cs137", one_ci_bq)
    comparison_materials = [
        materials["lead"],
        materials["tungsten"],
        materials["concrete_ordinary"],
        materials["concrete_barite"],
        materials["water"],
        materials["polyethylene"],
    ]
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
        apply_buildup=False,
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

    unconstrained_plot_data = create_optimization_plot_data(balanced_result)

    pareto_points = create_pareto_points(
        unconstrained_plot_data,
        eligible_only=True,
    )

    pareto_material_keys = {
        point.material_key for point in pareto_points if point.is_pareto_optimal
    }

    assert_equal(
        "V1.10 Cs-137 Pareto front contains lead and tungsten",
        pareto_material_keys,
        {"lead", "tungsten"},
    )

    pareto_thickness_values = [point.thickness_cm for point in pareto_points]

    assert_equal(
        "V1.10 Pareto points are sorted by thickness",
        pareto_thickness_values,
        sorted(pareto_thickness_values),
    )


def test_air_kerma_material_comparison() -> None:
    solver_materials = get_material_library()
    solver_lead = solver_materials["lead"]
    solver_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)
    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
    )

    air_kerma_comparison = compare_materials_for_air_kerma_target(
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

    assert_equal(
        "V1.12 air-kerma comparison preserves candidate count",
        len(air_kerma_comparison.candidates),
        3,
    )

    assert_equal(
        "V1.12 air-kerma comparison preserves target description",
        air_kerma_comparison.target_description,
        ("G-P exposure-buildup-adjusted collision air-kerma rate <= 1 µGy/h"),
    )

    assert_equal(
        "V1.12 air-kerma comparison preserves buildup setting",
        air_kerma_comparison.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma comparison has two passing candidates",
        len(air_kerma_comparison.passing_candidates()),
        2,
    )

    assert_equal(
        "V1.12 air-kerma comparison has one failed candidate",
        len(air_kerma_comparison.failed_candidates()),
        1,
    )

    lead_air_kerma_candidate = get_air_kerma_candidate_by_material_key(
        air_kerma_comparison,
        "lead",
    )

    tungsten_air_kerma_candidate = get_air_kerma_candidate_by_material_key(
        air_kerma_comparison,
        "tungsten",
    )

    polyethylene_air_kerma_candidate = get_air_kerma_candidate_by_material_key(
        air_kerma_comparison,
        "polyethylene",
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

    for candidate in air_kerma_comparison.passing_candidates():
        required_thickness = candidate.required_thickness

        if required_thickness is None:
            raise AssertionError(
                "Passing air-kerma candidate did not preserve required thickness."
            )

        final_rate_microgy_per_h = candidate.final_air_kerma_rate_microgy_per_h

        if final_rate_microgy_per_h is None:
            raise AssertionError(
                "Passing air-kerma candidate did not preserve final air-kerma rate."
            )

        if candidate.design_result is None:
            raise AssertionError(
                "Passing air-kerma candidate did not "
                "preserve its complete design result."
            )

        passing_air_kerma_thicknesses.append(required_thickness)

        assert_greater_than(
            f"V1.12 {candidate.material.key} air-kerma "
            "candidate has positive thickness",
            required_thickness,
            0.0,
        )

        assert_less_than_or_equal(
            f"V1.12 {candidate.material.key} air-kerma candidate satisfies target",
            final_rate_microgy_per_h,
            (solver_target.target_air_kerma_rate_microgy_per_h + 1.0e-8),
        )

        assert_equal(
            f"V1.12 {candidate.material.key} air-kerma candidate uses buildup",
            candidate.buildup_used,
            True,
        )

        assert_equal(
            f"V1.12 {candidate.material.key} candidate material matches design result",
            candidate.design_result.material.key,
            candidate.material.key,
        )

        assert_greater_than(
            f"V1.12 {candidate.material.key} candidate "
            "preserves photon-line response data",
            len(candidate.design_result.final_source_response.line_results),
            0,
        )

    assert_equal(
        "V1.12 passing air-kerma candidates are sorted by thickness",
        passing_air_kerma_thicknesses,
        sorted(passing_air_kerma_thicknesses),
    )

    assert_equal(
        "V1.12 failed air-kerma candidate has no thickness",
        polyethylene_air_kerma_candidate.required_thickness,
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma candidate has no final response",
        (polyethylene_air_kerma_candidate.final_air_kerma_rate_microgy_per_h),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma candidate does not claim buildup",
        polyethylene_air_kerma_candidate.buildup_used,
        False,
    )

    if polyethylene_air_kerma_candidate.failure_reason is None or (
        polyethylene_air_kerma_candidate.failure_reason.strip() == ""
    ):
        raise AssertionError(
            "Failed air-kerma candidate did not preserve its failure reason."
        )

    polyethylene_uncollided_comparison = compare_materials_for_air_kerma_target(
        source=cs137_solver_source,
        materials=[
            solver_materials["polyethylene"],
        ],
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=100.0,
        apply_buildup=False,
    )

    polyethylene_uncollided_candidate = polyethylene_uncollided_comparison.candidates[0]

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
        polyethylene_uncollided_candidate.final_air_kerma_rate_microgy_per_h
    )

    if polyethylene_uncollided_rate is None:
        raise AssertionError(
            "Passing uncollided Polyethylene candidate "
            "did not preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 uncollided Polyethylene candidate satisfies target",
        polyethylene_uncollided_rate,
        (solver_target.target_air_kerma_rate_microgy_per_h + 1.0e-8),
    )

    impossible_air_kerma_comparison = compare_materials_for_air_kerma_target(
        source=cs137_solver_source,
        materials=[
            solver_lead,
        ],
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=0.1,
        apply_buildup=False,
    )

    impossible_air_kerma_candidate = impossible_air_kerma_comparison.candidates[0]

    assert_equal(
        "V1.12 impossible air-kerma candidate remains visible",
        impossible_air_kerma_candidate.status,
        "FAILED",
    )

    if impossible_air_kerma_candidate.failure_reason is None or (
        impossible_air_kerma_candidate.failure_reason.strip() == ""
    ):
        raise AssertionError(
            "Impossible air-kerma candidate did not preserve its failure reason."
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


def test_air_kerma_material_selection() -> None:
    solver_materials = get_material_library()
    solver_lead = solver_materials["lead"]
    solver_target = AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0)
    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
    )

    air_kerma_optimization_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    air_kerma_minimum_mass_result = optimize_air_kerma_material_selection(
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

    assert_equal(
        "V1.12 air-kerma optimization preserves target description",
        air_kerma_minimum_mass_result.target_description,
        ("G-P exposure-buildup-adjusted collision air-kerma rate <= 1 µGy/h"),
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves buildup setting",
        air_kerma_minimum_mass_result.apply_buildup,
        True,
    )

    assert_equal(
        "V1.12 air-kerma optimization preserves candidate count",
        len(air_kerma_minimum_mass_result.all_candidates),
        3,
    )

    assert_equal(
        "V1.12 air-kerma optimization has two eligible candidates",
        len(air_kerma_minimum_mass_result.eligible_candidates()),
        2,
    )

    assert_equal(
        "V1.12 air-kerma optimization has one failed candidate",
        len(air_kerma_minimum_mass_result.failed_candidates()),
        1,
    )

    minimum_mass_best_candidate = air_kerma_minimum_mass_result.best_candidate

    if minimum_mass_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-mass air-kerma optimization did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-mass air-kerma optimization selects Lead",
        (minimum_mass_best_candidate.base_candidate.material.key),
        "lead",
    )

    selected_air_kerma_base_candidate = minimum_mass_best_candidate.base_candidate

    if not isinstance(
        selected_air_kerma_base_candidate,
        AirKermaMaterialDesignCandidate,
    ):
        raise AssertionError(
            "V1.12 selected optimization candidate "
            "did not preserve the air-kerma candidate type."
        )

    selected_air_kerma_rate = (
        selected_air_kerma_base_candidate.final_air_kerma_rate_microgy_per_h
    )

    if selected_air_kerma_rate is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve its final response."
        )

    assert_less_than_or_equal(
        "V1.12 selected optimization candidate satisfies air-kerma target",
        selected_air_kerma_rate,
        (solver_target.target_air_kerma_rate_microgy_per_h + 1.0e-8),
    )

    assert_equal(
        "V1.12 selected optimization candidate used buildup",
        selected_air_kerma_base_candidate.buildup_used,
        True,
    )

    selected_air_kerma_design_result = selected_air_kerma_base_candidate.design_result

    if selected_air_kerma_design_result is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve its design result."
        )

    assert_equal(
        "V1.12 selected optimization candidate preserves applied source buildup",
        (selected_air_kerma_design_result.final_source_response.buildup_status),
        "applied",
    )

    selected_required_thickness = selected_air_kerma_base_candidate.required_thickness

    if selected_required_thickness is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate "
            "did not preserve required thickness."
        )

    selected_mass_per_area = minimum_mass_best_candidate.mass_per_area_g_per_cm2

    if selected_mass_per_area is None:
        raise AssertionError(
            "Selected air-kerma optimization candidate did not preserve mass per area."
        )

    assert_close(
        "V1.12 optimized air-kerma mass equals density times thickness",
        selected_mass_per_area,
        (
            selected_air_kerma_base_candidate.material.density
            * selected_required_thickness
        ),
        1.0e-10,
    )

    polyethylene_optimized_air_kerma = get_optimized_candidate_by_material_key(
        air_kerma_minimum_mass_result,
        "polyethylene",
    )

    assert_equal(
        "V1.12 unsupported buildup material remains FAILED in optimization",
        (polyethylene_optimized_air_kerma.optimization_status),
        "FAILED",
    )

    assert_equal(
        "V1.12 failed air-kerma optimization candidate has no mass",
        (polyethylene_optimized_air_kerma.mass_per_area_g_per_cm2),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma optimization candidate has no cost",
        (polyethylene_optimized_air_kerma.relative_cost_index_per_area),
        None,
    )

    polyethylene_failure_reason = (
        polyethylene_optimized_air_kerma.base_candidate.failure_reason
    )

    if polyethylene_failure_reason is None or polyethylene_failure_reason.strip() == "":
        raise AssertionError(
            "Failed air-kerma optimization candidate "
            "did not preserve its failure reason."
        )

    air_kerma_minimum_thickness_result = optimize_air_kerma_material_selection(
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

    minimum_thickness_best_candidate = air_kerma_minimum_thickness_result.best_candidate

    if minimum_thickness_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-thickness air-kerma optimization did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-thickness air-kerma optimization selects Tungsten",
        (minimum_thickness_best_candidate.base_candidate.material.key),
        "tungsten",
    )

    tungsten_air_kerma_mass = assert_not_none(
        "V1.12 Tungsten optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "tungsten",
            ).mass_per_area_g_per_cm2
        ),
    )

    lead_air_kerma_mass = assert_not_none(
        "V1.12 Lead optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "lead",
            ).mass_per_area_g_per_cm2
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
            ).mass_per_area_g_per_cm2
        ),
    )

    lead_air_kerma_mass = assert_not_none(
        "V1.12 Lead optimized air-kerma mass exists",
        (
            get_optimized_candidate_by_material_key(
                air_kerma_minimum_thickness_result,
                "lead",
            ).mass_per_area_g_per_cm2
        ),
    )

    assert_greater_than(
        "V1.12 Lead air-kerma design has lower mass than Tungsten",
        tungsten_air_kerma_mass,
        lead_air_kerma_mass,
    )

    air_kerma_thickness_constraint_result = optimize_air_kerma_material_selection(
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

    constrained_lead_candidate = get_optimized_candidate_by_material_key(
        air_kerma_thickness_constraint_result,
        "lead",
    )

    assert_equal(
        "V1.12 Lead is rejected by air-kerma thickness constraint",
        constrained_lead_candidate.optimization_status,
        "REJECTED",
    )

    assert_greater_than(
        "V1.12 rejected Lead preserves thickness rejection reason",
        len(constrained_lead_candidate.rejection_reasons),
        0,
    )

    constrained_thickness_best_candidate = (
        air_kerma_thickness_constraint_result.best_candidate
    )

    if constrained_thickness_best_candidate is None:
        raise AssertionError(
            "V1.12 thickness-constrained air-kerma optimization "
            "did not select a candidate."
        )

    assert_equal(
        "V1.12 thickness constraint leaves Tungsten selected",
        (constrained_thickness_best_candidate.base_candidate.material.key),
        "tungsten",
    )

    air_kerma_mass_constraint_result = optimize_air_kerma_material_selection(
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

    constrained_tungsten_candidate = get_optimized_candidate_by_material_key(
        air_kerma_mass_constraint_result,
        "tungsten",
    )

    assert_equal(
        "V1.12 Tungsten is rejected by air-kerma mass constraint",
        constrained_tungsten_candidate.optimization_status,
        "REJECTED",
    )

    constrained_mass_best_candidate = air_kerma_mass_constraint_result.best_candidate

    if constrained_mass_best_candidate is None:
        raise AssertionError(
            "V1.12 mass-constrained air-kerma optimization did not select a candidate."
        )

    assert_equal(
        "V1.12 mass constraint leaves Lead selected",
        (constrained_mass_best_candidate.base_candidate.material.key),
        "lead",
    )

    air_kerma_minimum_cost_result = optimize_air_kerma_material_selection(
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

    minimum_cost_best_candidate = air_kerma_minimum_cost_result.best_candidate

    if minimum_cost_best_candidate is None:
        raise AssertionError(
            "V1.12 minimum-cost air-kerma optimization did not select a candidate."
        )

    assert_equal(
        "V1.12 minimum-cost air-kerma optimization selects Lead",
        (minimum_cost_best_candidate.base_candidate.material.key),
        "lead",
    )

    assert_greater_than(
        "V1.12 relative-cost air-kerma optimization preserves warning",
        len(air_kerma_minimum_cost_result.warnings),
        0,
    )

    air_kerma_balanced_result = optimize_air_kerma_material_selection(
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

    balanced_best_candidate = air_kerma_balanced_result.best_candidate

    if balanced_best_candidate is None:
        raise AssertionError(
            "V1.12 balanced air-kerma optimization did not select a candidate."
        )

    assert_equal(
        "V1.12 balanced air-kerma optimization selects Lead",
        (balanced_best_candidate.base_candidate.material.key),
        "lead",
    )

    for candidate in air_kerma_balanced_result.eligible_candidates():
        candidate_score = assert_not_none(
            "V1.12 balanced air-kerma score exists",
            candidate.optimization_score,
        )

        assert_equal(
            f"V1.12 {candidate.base_candidate.material.key} "
            "balanced air-kerma score is bounded",
            (0.0 <= candidate_score <= 1.0),
            True,
        )

    no_eligible_air_kerma_result = optimize_air_kerma_material_selection(
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

    assert_equal(
        "V1.12 air-kerma optimization returns no best candidate when all rejected",
        no_eligible_air_kerma_result.best_candidate,
        None,
    )

    assert_equal(
        "V1.12 all calculated air-kerma candidates can be rejected",
        len(no_eligible_air_kerma_result.rejected_candidates()),
        2,
    )

    assert_greater_than(
        "V1.12 no-eligible air-kerma result preserves warning",
        len(no_eligible_air_kerma_result.warnings),
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
