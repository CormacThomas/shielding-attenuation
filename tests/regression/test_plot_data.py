"""Verification cases migrated from the original validation runner."""

from shielding.data.isotopes import create_isotope_source
from shielding.data.materials import get_material_library
from shielding.design.models import (
    DesignConstraints,
)
from shielding.design.optimization import (
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from shielding.design.response_curves import create_response_curve
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
)
from shielding.physics.source_models import ManualPhotonSource
from shielding.physics.units import convert_activity_to_bq
from shielding.reporting.optimization_data import (
    create_constraint_feasibility_rows,
    create_optimization_plot_data,
    create_pareto_points,
)
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_not_none,
    assert_raises,
    get_feasibility_row_by_material_key,
    get_material_plot_point_by_key,
    get_optimized_candidate_by_material_key,
)


def test_optimization_plot_data() -> None:
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

    # Validate V1.10 optimization plot-data preparation.

    constrained_plot_data = create_optimization_plot_data(thickness_constraint_result)

    assert_equal(
        "V1.10 plot data preserves candidate count",
        len(constrained_plot_data.candidates),
        len(thickness_constraint_result.all_candidates),
    )

    if thickness_constraint_result.best_candidate is None:
        raise AssertionError("V1.10 plot-data test requires a selected candidate.")

    expected_selected_material_key = (
        thickness_constraint_result.best_candidate.base_candidate.material.key
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

    failed_plot_data = create_optimization_plot_data(failed_optimization_result)

    failed_feasibility_rows = create_constraint_feasibility_rows(failed_plot_data)

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
        apply_buildup=False,
    )

    assert_raises(
        ("V1.09 photon material optimization rejects G-P exposure buildup"),
        ValueError,
        lambda: optimize_material_selection(
            source=cs137_source,
            materials=[
                materials["lead"],
            ],
            detector_distance=detector_distance,
            target=FluxTarget(100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=detector_distance,
            apply_buildup=True,
        ),
        "not supported for photon fluence",
    )

    visualization_plot_data = create_optimization_plot_data(
        visualization_constraint_result
    )

    create_constraint_feasibility_rows(visualization_plot_data)


def test_constraint_feasibility_and_plotting() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")
    materials = get_material_library()
    detector_distance = 100.0
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )
    cs137_source = create_isotope_source("cs137", one_ci_bq)
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
        apply_buildup=False,
    )
    visualization_plot_data = create_optimization_plot_data(
        visualization_constraint_result
    )
    feasibility_rows = create_constraint_feasibility_rows(visualization_plot_data)

    # Validate every material's feasibility status against the
    # numerical constraints used to create this optimization result.
    #
    # These tests intentionally derive the expected state from each
    # candidate's current uncollided-photon design values rather than
    # preserving historical buildup-proxy classifications.

    feasibility_rows_by_key = {row.material_key: row for row in feasibility_rows}

    for candidate in visualization_plot_data.candidates:
        row = feasibility_rows_by_key[candidate.material_key]

        assert_equal(
            (
                "V1.10 feasibility row preserves material "
                f"key for {candidate.material_key}"
            ),
            row.material_key,
            candidate.material_key,
        )

        if candidate.optimization_status == "FAILED":
            assert_equal(
                (
                    "V1.10 failed candidate has unavailable "
                    f"thickness status for {candidate.material_key}"
                ),
                row.thickness_status,
                "UNAVAILABLE",
            )

            assert_equal(
                (
                    "V1.10 failed candidate has unavailable "
                    f"mass status for {candidate.material_key}"
                ),
                row.mass_status,
                "UNAVAILABLE",
            )

            assert_equal(
                (
                    "V1.10 failed candidate has unavailable "
                    f"cost status for {candidate.material_key}"
                ),
                row.cost_status,
                "UNAVAILABLE",
            )

            continue

        required_thickness_cm = assert_not_none(
            (
                "V1.10 successful candidate thickness exists "
                f"for {candidate.material_key}"
            ),
            candidate.required_thickness_cm,
        )

        mass_per_area_g_per_cm2 = assert_not_none(
            (f"V1.10 successful candidate mass exists for {candidate.material_key}"),
            candidate.mass_per_area_g_per_cm2,
        )

        expected_thickness_status = "PASS" if required_thickness_cm <= 20.0 else "FAIL"

        expected_mass_status = "PASS" if mass_per_area_g_per_cm2 <= 120.0 else "FAIL"

        assert_equal(
            (
                "V1.10 thickness feasibility matches "
                f"numerical value for {candidate.material_key}"
            ),
            row.thickness_status,
            expected_thickness_status,
        )

        assert_equal(
            (
                "V1.10 mass feasibility matches "
                f"numerical value for {candidate.material_key}"
            ),
            row.mass_status,
            expected_mass_status,
        )

        assert_equal(
            (
                "V1.10 inactive cost constraint remains "
                f"inactive for {candidate.material_key}"
            ),
            row.cost_status,
            "INACTIVE",
        )

        expected_optimization_status = (
            "ELIGIBLE"
            if (expected_thickness_status == "PASS" and expected_mass_status == "PASS")
            else "REJECTED"
        )

        assert_equal(
            (
                "V1.10 overall feasibility matches "
                f"active constraints for {candidate.material_key}"
            ),
            row.optimization_status,
            expected_optimization_status,
        )

        assert_equal(
            (f"V1.10 selected state matches plot data for {candidate.material_key}"),
            row.is_selected,
            candidate.is_selected,
        )

    assert_raises(
        ("V1.10 photon-fluence response curve rejects G-P exposure buildup"),
        ValueError,
        lambda: create_response_curve(
            source=manual_source,
            material=materials["lead"],
            detector_distance_cm=detector_distance,
            minimum_thickness_cm=0.0,
            maximum_thickness_cm=10.0,
            number_of_points=21,
            apply_buildup=True,
        ),
        "do not support G-P exposure buildup",
    )

    selected_feasibility_rows = [row for row in feasibility_rows if row.is_selected]

    assert_equal(
        "V1.10 feasibility data contains one selected material",
        len(selected_feasibility_rows),
        1,
    )

    assert_equal(
        "V1.10 uncollided minimum-mass design selects Lead",
        selected_feasibility_rows[0].material_key,
        "lead",
    )


def test_air_kerma_plot_data() -> None:
    solver_materials = get_material_library()
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

    air_kerma_plot_data = create_optimization_plot_data(air_kerma_minimum_mass_result)

    assert_equal(
        "V1.12 air-kerma plot data preserves candidate count",
        len(air_kerma_plot_data.candidates),
        len(air_kerma_minimum_mass_result.all_candidates),
    )

    assert_equal(
        "V1.12 air-kerma plot data preserves selected material",
        air_kerma_plot_data.selected_material_key,
        "lead",
    )

    plotted_air_kerma_lead = get_material_plot_point_by_key(
        air_kerma_plot_data,
        "lead",
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

    optimized_lead_candidate = get_optimized_candidate_by_material_key(
        air_kerma_minimum_mass_result,
        "lead",
    )

    optimized_lead_thickness = assert_not_none(
        "V1.12 optimized air-kerma Lead thickness exists",
        (optimized_lead_candidate.base_candidate.required_thickness),
    )

    assert_close(
        "V1.12 air-kerma plot data preserves Lead thickness",
        plotted_lead_thickness,
        optimized_lead_thickness,
        1.0e-12,
    )

    plotted_lead_mass = assert_not_none(
        "V1.12 plotted air-kerma Lead mass exists",
        (plotted_air_kerma_lead.mass_per_area_g_per_cm2),
    )

    optimized_lead_mass = assert_not_none(
        "V1.12 optimized air-kerma Lead mass exists",
        (optimized_lead_candidate.mass_per_area_g_per_cm2),
    )

    assert_close(
        "V1.12 air-kerma plot data preserves Lead mass",
        plotted_lead_mass,
        optimized_lead_mass,
        1.0e-12,
    )

    plotted_air_kerma_polyethylene = get_material_plot_point_by_key(
        air_kerma_plot_data,
        "polyethylene",
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate remains visible",
        (plotted_air_kerma_polyethylene.optimization_status),
        "FAILED",
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has unavailable buildup",
        (plotted_air_kerma_polyethylene.buildup_display),
        "UNAVAILABLE",
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has no thickness",
        (plotted_air_kerma_polyethylene.required_thickness_cm),
        None,
    )

    assert_equal(
        "V1.12 failed air-kerma plot candidate has no mass",
        (plotted_air_kerma_polyethylene.mass_per_area_g_per_cm2),
        None,
    )

    if plotted_air_kerma_polyethylene.failure_reason is None or (
        plotted_air_kerma_polyethylene.failure_reason.strip() == ""
    ):
        raise AssertionError(
            "Failed plotted air-kerma candidate did not preserve its failure reason."
        )

    air_kerma_constraint_plot_data = create_optimization_plot_data(
        air_kerma_thickness_constraint_result
    )

    air_kerma_feasibility_rows = create_constraint_feasibility_rows(
        air_kerma_constraint_plot_data
    )

    air_kerma_lead_feasibility = get_feasibility_row_by_material_key(
        air_kerma_feasibility_rows,
        "lead",
    )

    air_kerma_tungsten_feasibility = get_feasibility_row_by_material_key(
        air_kerma_feasibility_rows,
        "tungsten",
    )

    assert_equal(
        "V1.12 air-kerma Lead fails thickness feasibility check",
        air_kerma_lead_feasibility.thickness_status,
        "FAIL",
    )

    assert_equal(
        "V1.12 air-kerma Lead remains rejected in feasibility data",
        (air_kerma_lead_feasibility.optimization_status),
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

    air_kerma_pareto_plot_data = create_optimization_plot_data(
        air_kerma_minimum_thickness_result
    )

    air_kerma_pareto_points = create_pareto_points(
        air_kerma_pareto_plot_data,
        eligible_only=True,
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
        point.thickness_cm for point in air_kerma_pareto_points
    ]

    assert_equal(
        "V1.12 air-kerma Pareto points are sorted by thickness",
        air_kerma_pareto_thicknesses,
        sorted(air_kerma_pareto_thicknesses),
    )
