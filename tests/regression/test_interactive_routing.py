"""Verification cases migrated from the original validation runner."""

from unittest.mock import patch

from shielding.cli.interactive import (
    run_fixed_thickness_mode,
    run_material_comparison_mode,
    run_material_optimization_mode,
    run_minimum_thickness_mode,
)
from shielding.cli.prompts import (
    get_response_quantity_from_user,
    get_target_from_user,
)
from shielding.data.isotopes import create_isotope_source
from shielding.data.materials import get_material_library
from shielding.design.comparison import (
    compare_materials_for_air_kerma_target,
    compare_materials_for_target,
)
from shielding.design.kerma_thickness import calculate_air_kerma_minimum_thickness
from shielding.design.models import (
    DesignConstraints,
    OptimizationWeights,
)
from shielding.design.optimization import (
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
)
from shielding.physics.models import Layer
from shielding.physics.source_models import ManualPhotonSource
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_less_than_or_equal,
    assert_raises,
)


def test_response_quantity_input() -> None:
    # Explicit CLI response-quantity input

    with patch(
        "builtins.input",
        return_value="1",
    ):
        cli_photon_response_quantity = get_response_quantity_from_user()

    assert_equal(
        "V1.12 CLI selects photon fluence-rate response",
        cli_photon_response_quantity,
        "photon_fluence_rate",
    )

    with patch(
        "builtins.input",
        return_value="2",
    ):
        cli_air_kerma_response_quantity = get_response_quantity_from_user()

    assert_equal(
        "V1.12 CLI selects collision air-kerma response",
        cli_air_kerma_response_quantity,
        "collision_air_kerma_rate",
    )

    with patch(
        "builtins.input",
        return_value="1.0",
    ):
        cli_air_kerma_target = get_target_from_user("collision_air_kerma_rate")

    if not isinstance(
        cli_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError("V1.12 CLI did not construct an AirKermaRateTarget.")

    assert_close(
        "V1.12 CLI preserves air-kerma target value",
        (cli_air_kerma_target.target_air_kerma_rate_microgy_per_h),
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
        cli_photon_target = get_target_from_user("photon_fluence_rate")

    if not isinstance(
        cli_photon_target,
        FluxTarget,
    ):
        raise AssertionError(
            "V1.12 CLI did not preserve the legacy photon target type."
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


def test_fixed_and_minimum_thickness_routing() -> None:
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
    buildup_solver_result = calculate_air_kerma_minimum_thickness(
        source=cs137_solver_source,
        material=solver_lead,
        detector_distance_cm=100.0,
        target=solver_target,
        max_thickness_cm=20.0,
        apply_buildup=True,
    )

    # Fixed-thickness and minimum-thickness CLI routing

    cli_fixed_air_kerma_layers = [
        Layer(
            thickness=5.0,
            material=solver_lead,
        )
    ]

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value=("collision_air_kerma_rate"),
        ),
        patch(
            "shielding.cli.interactive.get_layers_from_user",
            return_value=(cli_fixed_air_kerma_layers),
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as fixed_air_buildup_prompt,
        patch(
            "shielding.cli.interactive.print_source_air_kerma_result",
        ) as fixed_air_output,
        patch(
            "shielding.cli.interactive.print_source_results",
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

    fixed_air_kerma_result = fixed_air_output.call_args.args[0]

    assert_equal(
        "V1.12 fixed-thickness CLI applies air-kerma buildup",
        fixed_air_kerma_result.buildup_status,
        "applied",
    )

    assert_greater_than(
        "V1.12 fixed-thickness CLI produces positive air kerma",
        (fixed_air_kerma_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        0.0,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=manual_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "shielding.cli.interactive.get_layers_from_user",
            return_value=(cli_fixed_air_kerma_layers),
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as fixed_photon_buildup_prompt,
        patch(
            "shielding.cli.interactive.print_source_air_kerma_result",
        ) as photon_mode_air_output,
        patch(
            "shielding.cli.interactive.print_source_results",
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

    fixed_photon_result = photon_mode_output.call_args.args[0]

    assert_greater_than(
        ("V1.12 photon fixed-thickness CLI produces positive uncollided fluence"),
        fixed_photon_result.total_uncollided_flux,
        0.0,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value=("collision_air_kerma_rate"),
        ),
        patch(
            "shielding.cli.interactive.get_single_material_from_user",
            return_value=solver_lead,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=solver_target,
        ) as minimum_air_target_prompt,
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as minimum_air_buildup_prompt,
        patch(
            "shielding.cli.interactive.print_air_kerma_minimum_thickness_result",
        ) as minimum_air_output,
        patch(
            "shielding.cli.interactive.print_minimum_thickness_result",
        ) as minimum_photon_output,
    ):
        run_minimum_thickness_mode()

    assert_equal(
        "V1.12 minimum-thickness CLI passes response to target prompt",
        (minimum_air_target_prompt.call_args.args[0]),
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

    cli_air_kerma_design = minimum_air_output.call_args.args[0]

    assert_equal(
        "V1.12 minimum-thickness CLI preserves buildup use",
        cli_air_kerma_design.buildup_used,
        True,
    )

    assert_less_than_or_equal(
        "V1.12 minimum-thickness CLI satisfies air-kerma target",
        (cli_air_kerma_design.final_air_kerma_rate_microgy_per_h),
        1.0 + 1.0e-8,
    )

    assert_close(
        "V1.12 minimum-thickness CLI reproduces Lead design",
        cli_air_kerma_design.required_thickness,
        buildup_solver_result.required_thickness,
        1.0e-8,
    )

    cli_photon_target = FluxTarget(target_flux=100.0)

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "shielding.cli.interactive.get_single_material_from_user",
            return_value=solver_lead,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=cli_photon_target,
        ),
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as minimum_photon_buildup_prompt,
        patch(
            "shielding.cli.interactive.print_air_kerma_minimum_thickness_result",
        ) as photon_minimum_air_output,
        patch(
            "shielding.cli.interactive.print_minimum_thickness_result",
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

    cli_photon_design = photon_minimum_output.call_args.args[0]

    assert_equal(
        ("V1.12 photon minimum-thickness CLI uses uncollided calculation mode"),
        cli_photon_design.calculation_mode,
        ("Uncollided photon-fluence minimum thickness design"),
    )

    assert_less_than_or_equal(
        "V1.12 photon minimum-thickness CLI satisfies fluence target",
        cli_photon_design.final_flux,
        100.0 + 1.0e-6,
    )


def test_material_comparison_routing() -> None:
    solver_materials = get_material_library()
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

    # Material-comparison CLI routing

    cli_comparison_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value=("collision_air_kerma_rate"),
        ),
        patch(
            "shielding.cli.interactive.get_materials_for_comparison_from_user",
            return_value=cli_comparison_materials,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=solver_target,
        ) as comparison_air_target_prompt,
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as comparison_air_buildup_prompt,
        patch(
            "shielding.cli.interactive.compare_materials_for_air_kerma_target",
            return_value=air_kerma_comparison,
        ) as air_kerma_comparison_function,
        patch(
            "shielding.cli.interactive.compare_materials_for_target",
        ) as photon_comparison_function,
        patch(
            "shielding.cli.interactive.print_air_kerma_material_comparison_result",
        ) as air_kerma_comparison_output,
        patch(
            "shielding.cli.interactive.print_material_comparison_result",
        ) as photon_comparison_output,
    ):
        run_material_comparison_mode()

    assert_equal(
        "V1.12 comparison CLI passes air-kerma response to target prompt",
        (comparison_air_target_prompt.call_args.args[0]),
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
        (air_kerma_comparison_output.call_args.args[0]),
        air_kerma_comparison,
    )

    air_kerma_comparison_call = air_kerma_comparison_function.call_args

    assert_equal(
        "V1.12 air-kerma comparison CLI passes source",
        air_kerma_comparison_call.kwargs["source"],
        cs137_solver_source,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI passes selected materials",
        air_kerma_comparison_call.kwargs["materials"],
        cli_comparison_materials,
    )

    assert_close(
        "V1.12 air-kerma comparison CLI passes detector distance",
        air_kerma_comparison_call.kwargs["detector_distance_cm"],
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma comparison CLI passes strict buildup request",
        air_kerma_comparison_call.kwargs["apply_buildup"],
        True,
    )

    assert_close(
        "V1.12 air-kerma comparison CLI passes calculation limit",
        air_kerma_comparison_call.kwargs["max_thickness_cm"],
        20.0,
        1.0e-12,
    )

    cli_photon_comparison_target = FluxTarget(target_flux=100.0)

    cli_photon_comparison_result = compare_materials_for_target(
        source=cs137_solver_source,
        materials=cli_comparison_materials,
        detector_distance=100.0,
        target=cli_photon_comparison_target,
        max_thickness=20.0,
        apply_buildup=False,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "shielding.cli.interactive.get_materials_for_comparison_from_user",
            return_value=cli_comparison_materials,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=(cli_photon_comparison_target),
        ) as comparison_photon_target_prompt,
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as comparison_photon_buildup_prompt,
        patch(
            "shielding.cli.interactive.compare_materials_for_air_kerma_target",
        ) as photon_mode_air_comparison,
        patch(
            "shielding.cli.interactive.compare_materials_for_target",
            return_value=cli_photon_comparison_result,
        ) as photon_mode_comparison,
        patch(
            "shielding.cli.interactive.print_air_kerma_material_comparison_result",
        ) as photon_mode_air_output,
        patch(
            "shielding.cli.interactive.print_material_comparison_result",
        ) as photon_mode_output,
    ):
        run_material_comparison_mode()

    assert_equal(
        "V1.12 photon comparison CLI passes response to target prompt",
        (comparison_photon_target_prompt.call_args.args[0]),
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
        (photon_mode_comparison.call_args.kwargs["apply_buildup"]),
        False,
    )


def test_material_optimization_routing() -> None:
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

    # Material-optimization CLI routing

    cli_optimization_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]

    cli_optimization_constraints = DesignConstraints(
        max_thickness_cm=20.0,
        max_mass_per_area_g_per_cm2=120.0,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value=("collision_air_kerma_rate"),
        ),
        patch(
            "shielding.cli.interactive.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=solver_target,
        ) as optimization_air_target_prompt,
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_design_constraints_from_user",
            return_value=(cli_optimization_constraints),
        ),
        patch(
            "shielding.cli.interactive.get_optimization_mode_from_user",
            return_value="minimum_mass",
        ),
        patch(
            "shielding.cli.interactive.get_optimization_weights_from_user",
        ) as air_optimization_weight_prompt,
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as air_optimization_buildup_prompt,
        patch(
            "shielding.cli.interactive.optimize_air_kerma_material_selection",
            return_value=(air_kerma_minimum_mass_result),
        ) as air_kerma_optimizer,
        patch(
            "shielding.cli.interactive.optimize_material_selection",
        ) as photon_optimizer,
        patch(
            "shielding.cli.interactive.print_optimized_design_result",
        ) as air_optimization_output,
    ):
        run_material_optimization_mode()

    assert_equal(
        "V1.12 optimization CLI passes air-kerma response to target prompt",
        (optimization_air_target_prompt.call_args.args[0]),
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
        (air_optimization_output.call_args.args[0]),
        air_kerma_minimum_mass_result,
    )

    air_kerma_optimizer_call = air_kerma_optimizer.call_args

    assert_equal(
        "V1.12 air-kerma optimization passes source",
        air_kerma_optimizer_call.kwargs["source"],
        cs137_solver_source,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes selected materials",
        air_kerma_optimizer_call.kwargs["materials"],
        cli_optimization_materials,
    )

    assert_close(
        "V1.12 air-kerma optimization passes detector distance",
        air_kerma_optimizer_call.kwargs["detector_distance"],
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes target",
        air_kerma_optimizer_call.kwargs["target"],
        solver_target,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes constraints",
        air_kerma_optimizer_call.kwargs["constraints"],
        cli_optimization_constraints,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes minimum-mass objective",
        air_kerma_optimizer_call.kwargs["optimization_mode"],
        "minimum_mass",
    )

    assert_equal(
        "V1.12 air-kerma optimization passes no weights",
        air_kerma_optimizer_call.kwargs["weights"],
        None,
    )

    assert_equal(
        "V1.12 air-kerma optimization passes strict buildup request",
        air_kerma_optimizer_call.kwargs["apply_buildup"],
        True,
    )

    assert_close(
        "V1.12 air-kerma optimization passes calculation limit",
        air_kerma_optimizer_call.kwargs["calculation_max_thickness"],
        20.0,
        1.0e-12,
    )

    cli_air_optimization_best_candidate = air_optimization_output.call_args.args[
        0
    ].best_candidate

    if cli_air_optimization_best_candidate is None:
        raise AssertionError(
            "V1.12 CLI air-kerma optimization did not preserve a selected design."
        )

    assert_equal(
        "V1.12 CLI minimum-mass air-kerma optimization selects Lead",
        (cli_air_optimization_best_candidate.base_candidate.material.key),
        "lead",
    )

    cli_photon_optimization_target = FluxTarget(target_flux=100.0)

    cli_photon_optimization_result = optimize_material_selection(
        source=cs137_solver_source,
        materials=cli_optimization_materials,
        detector_distance=100.0,
        target=cli_photon_optimization_target,
        constraints=(cli_optimization_constraints),
        optimization_mode="minimum_mass",
        calculation_max_thickness=20.0,
        apply_buildup=False,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value="photon_fluence_rate",
        ),
        patch(
            "shielding.cli.interactive.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=(cli_photon_optimization_target),
        ) as photon_optimization_target_prompt,
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_design_constraints_from_user",
            return_value=(cli_optimization_constraints),
        ),
        patch(
            "shielding.cli.interactive.get_optimization_mode_from_user",
            return_value="minimum_mass",
        ),
        patch(
            "shielding.cli.interactive.get_optimization_weights_from_user",
        ) as photon_optimization_weight_prompt,
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ) as photon_optimization_buildup_prompt,
        patch(
            "shielding.cli.interactive.optimize_air_kerma_material_selection",
        ) as photon_mode_air_optimizer,
        patch(
            "shielding.cli.interactive.optimize_material_selection",
            return_value=(cli_photon_optimization_result),
        ) as photon_mode_optimizer,
        patch(
            "shielding.cli.interactive.print_optimized_design_result",
        ) as photon_optimization_output,
    ):
        run_material_optimization_mode()

    assert_equal(
        "V1.12 photon optimization passes response to target prompt",
        (photon_optimization_target_prompt.call_args.args[0]),
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
        (photon_mode_optimizer.call_args.kwargs["apply_buildup"]),
        False,
    )

    cli_balanced_weights = OptimizationWeights(
        thickness_weight=1.0,
        mass_weight=2.0,
        cost_weight=3.0,
    )

    with (
        patch(
            "shielding.cli.interactive.get_material_library",
            return_value=solver_materials,
        ),
        patch(
            "shielding.cli.interactive.get_source_from_user",
            return_value=cs137_solver_source,
        ),
        patch(
            "shielding.cli.interactive.get_response_quantity_from_user",
            return_value=("collision_air_kerma_rate"),
        ),
        patch(
            "shielding.cli.interactive.get_materials_for_comparison_from_user",
            return_value=cli_optimization_materials,
        ),
        patch(
            "shielding.cli.interactive.get_detector_distance_from_user",
            return_value=100.0,
        ),
        patch(
            "shielding.cli.interactive.get_target_from_user",
            return_value=solver_target,
        ),
        patch(
            "shielding.cli.interactive.get_optional_calculation_max_thickness_from_user",
            return_value=20.0,
        ),
        patch(
            "shielding.cli.interactive.get_design_constraints_from_user",
            return_value=(cli_optimization_constraints),
        ),
        patch(
            "shielding.cli.interactive.get_optimization_mode_from_user",
            return_value="balanced",
        ),
        patch(
            "shielding.cli.interactive.get_optimization_weights_from_user",
            return_value=cli_balanced_weights,
        ) as balanced_weight_prompt,
        patch(
            "shielding.cli.interactive.get_apply_buildup_from_user",
            return_value=True,
        ),
        patch(
            "shielding.cli.interactive.optimize_air_kerma_material_selection",
            return_value=air_kerma_balanced_result,
        ) as balanced_air_optimizer,
        patch(
            "shielding.cli.interactive.print_optimized_design_result",
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
        (balanced_air_optimizer.call_args.kwargs["weights"]),
        cli_balanced_weights,
    )

    assert_equal(
        "V1.12 balanced air-kerma optimization passes objective",
        (balanced_air_optimizer.call_args.kwargs["optimization_mode"]),
        "balanced",
    )
