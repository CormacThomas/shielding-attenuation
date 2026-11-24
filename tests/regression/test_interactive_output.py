"""Verification cases migrated from the original validation runner."""

from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from shielding.cli.interactive import (
    run_minimum_thickness_mode,
)
from shielding.cli.interactive_output import (
    print_air_kerma_material_comparison_result,
    print_air_kerma_minimum_thickness_result,
    print_material_comparison_result,
    print_minimum_thickness_result,
    print_optimized_design_result,
    print_source_air_kerma_result,
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
)
from shielding.design.optimization import (
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
)
from shielding.design.thickness import get_target_description
from shielding.scenarios.geometry import ConcentricSphericalGeometry
from shielding.scenarios.models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ShieldingScenario,
)
from shielding.scenarios.runner import run_scenario
from tests.checks import (
    assert_equal,
    assert_raises,
    get_air_kerma_candidate_by_material_key,
)


def test_air_kerma_console_output() -> None:
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

    source_output_buffer = StringIO()

    with redirect_stdout(source_output_buffer):
        print_source_air_kerma_result(buildup_solver_result.final_source_response)

    source_output_text = source_output_buffer.getvalue()

    source_output_requirements = [
        "Collision air-kerma response result",
        "Total uncollided photon fluence rate:",
        "Total uncollided collision air-kerma rate:",
        ("Total G-P buildup-adjusted collision air-kerma rate:"),
        "Photon-line contributions:",
        "Energy fluence rate:",
        "Dry-air mu_en/rho:",
        "G-P exposure buildup factor:",
        "Coefficient source:",
        "µGy/h",
        "Gy/s",
    ]

    for required_text in source_output_requirements:
        assert_equal(
            f"V1.12 source air-kerma output contains {required_text}",
            required_text in source_output_text,
            True,
        )

    minimum_output_buffer = StringIO()

    with redirect_stdout(minimum_output_buffer):
        print_air_kerma_minimum_thickness_result(buildup_solver_result)

    minimum_output_text = minimum_output_buffer.getvalue()

    minimum_output_requirements = [
        ("Air-kerma minimum shielding thickness result"),
        "Required thickness:",
        ("Final target-comparison collision air-kerma rate:"),
        ("Final uncollided collision air-kerma rate:"),
        ("Final G-P buildup-adjusted collision air-kerma rate:"),
        "Final selected-response ratio:",
        "Buildup used: Yes",
        "Final detailed source response:",
        "Photon-line contributions:",
    ]

    for required_text in minimum_output_requirements:
        assert_equal(
            f"V1.12 minimum-thickness output contains {required_text}",
            required_text in minimum_output_text,
            True,
        )


def test_air_kerma_comparison_output() -> None:
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
    polyethylene_air_kerma_candidate = get_air_kerma_candidate_by_material_key(
        air_kerma_comparison,
        "polyethylene",
    )

    # Air-kerma material-comparison console output

    air_kerma_comparison_output_buffer = StringIO()

    with redirect_stdout(air_kerma_comparison_output_buffer):
        print_air_kerma_material_comparison_result(air_kerma_comparison)

    air_kerma_comparison_output_text = air_kerma_comparison_output_buffer.getvalue()

    air_kerma_comparison_output_requirements = [
        ("Collision air-kerma material comparison result"),
        ("Single-material collision air-kerma design comparison"),
        ("G-P exposure buildup requested: Yes"),
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

    for required_text in air_kerma_comparison_output_requirements:
        assert_equal(
            f"V1.12 air-kerma comparison output contains {required_text}",
            (required_text in air_kerma_comparison_output_text),
            True,
        )

    assert_equal(
        "V1.12 air-kerma comparison output does not use Final Flux column",
        ("Final Flux" in air_kerma_comparison_output_text),
        False,
    )

    assert_equal(
        "V1.12 air-kerma comparison output displays microGy per hour units",
        ("µGy/h" in air_kerma_comparison_output_text),
        True,
    )

    assert_equal(
        "V1.12 air-kerma comparison output preserves strict failure",
        (
            polyethylene_air_kerma_candidate.failure_reason
            in air_kerma_comparison_output_text
        ),
        True,
    )


def test_optimization_output() -> None:
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

    # Response-aware engineering optimization output

    air_kerma_optimization_output_buffer = StringIO()

    with redirect_stdout(air_kerma_optimization_output_buffer):
        print_optimized_design_result(air_kerma_minimum_mass_result)

    air_kerma_optimization_output_text = air_kerma_optimization_output_buffer.getvalue()

    air_kerma_optimization_output_requirements = [
        "Optimized material selection",
        "Best material: Lead",
        ("Selected final G-P exposure-buildup-adjusted collision air-kerma rate:"),
        "Selected final response ratio:",
        "µGy/h",
        "Lead",
        "Tungsten",
        "Polyethylene",
        "Unavailable",
        "FAILED",
    ]

    for required_text in air_kerma_optimization_output_requirements:
        assert_equal(
            f"V1.12 air-kerma optimization output contains {required_text}",
            (required_text in air_kerma_optimization_output_text),
            True,
        )


def test_response_aware_optimization_output() -> None:
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

    # Response-aware engineering optimization output

    air_kerma_optimization_output_buffer = StringIO()

    with redirect_stdout(air_kerma_optimization_output_buffer):
        print_optimized_design_result(air_kerma_minimum_mass_result)

    air_kerma_optimization_output_text = air_kerma_optimization_output_buffer.getvalue()

    air_kerma_optimization_output_requirements = [
        "Optimized material selection",
        "Best material: Lead",
        ("Selected final G-P exposure-buildup-adjusted collision air-kerma rate:"),
        "Selected final response ratio:",
        "µGy/h",
        "Lead",
        "Tungsten",
        "Polyethylene",
        "Unavailable",
        "FAILED",
    ]

    for required_text in air_kerma_optimization_output_requirements:
        assert_equal(
            f"V1.12 air-kerma optimization output contains {required_text}",
            (required_text in air_kerma_optimization_output_text),
            True,
        )

    strict_optimization_output_buffer = StringIO()

    with redirect_stdout(strict_optimization_output_buffer):
        print_optimized_design_result(strict_air_kerma_failure_result)

    strict_optimization_output_text = strict_optimization_output_buffer.getvalue()

    strict_output_requirements = [
        "Best material: None",
        "Polyethylene",
        "Unavailable",
        "FAILED",
        "requires valid G-P exposure buildup",
    ]

    for required_text in strict_output_requirements:
        assert_equal(
            f"V1.12 strict optimization output contains {required_text}",
            (required_text in strict_optimization_output_text),
            True,
        )

    assert_equal(
        "V1.12 strict failed candidate is not displayed as fallback",
        ("Fallback" in strict_optimization_output_text),
        False,
    )

    uncollided_warning_optimization_result = optimize_air_kerma_material_selection(
        source=cs137_solver_source,
        materials=[
            solver_lead,
        ],
        detector_distance=100.0,
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=(1.0e6)),
        constraints=DesignConstraints(),
        optimization_mode="minimum_mass",
        calculation_max_thickness=20.0,
        apply_buildup=False,
    )

    uncollided_warning_output_buffer = StringIO()

    with redirect_stdout(uncollided_warning_output_buffer):
        print_optimized_design_result(uncollided_warning_optimization_result)

    uncollided_warning_output_text = uncollided_warning_output_buffer.getvalue()

    assert_equal(
        "V1.12 uncollided optimization output identifies response",
        (
            "Selected final uncollided collision "
            "air-kerma rate:" in uncollided_warning_output_text
        ),
        True,
    )

    assert_equal(
        "V1.12 uncollided air-kerma warning is not labeled fallback",
        ("Fallback" in uncollided_warning_output_text),
        False,
    )

    assert_equal(
        "V1.12 uncollided air-kerma output reports buildup not requested",
        ("Buildup requested: No" in uncollided_warning_output_text),
        True,
    )

    assert_raises(
        ("V1.12 photon optimization rejects the historical buildup fallback pathway"),
        ValueError,
        lambda: optimize_material_selection(
            source=cs137_solver_source,
            materials=[
                solver_materials["concrete_barite"],
            ],
            detector_distance=100.0,
            target=FluxTarget(target_flux=100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_thickness",
            calculation_max_thickness=100.0,
            apply_buildup=True,
        ),
        "not supported for photon fluence",
    )


def test_photon_response_terminology() -> None:
    solver_materials = get_material_library()
    solver_lead = solver_materials["lead"]
    cs137_solver_source = create_isotope_source(
        "cs137",
        3.7e10,
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
        ),
        patch(
            "shielding.cli.interactive.print_air_kerma_minimum_thickness_result",
        ),
        patch(
            "shielding.cli.interactive.print_minimum_thickness_result",
        ) as photon_minimum_output,
    ):
        run_minimum_thickness_mode()
    cli_photon_design = photon_minimum_output.call_args.args[0]
    cli_comparison_materials = [
        solver_materials["lead"],
        solver_materials["tungsten"],
        solver_materials["polyethylene"],
    ]
    cli_photon_comparison_target = FluxTarget(target_flux=100.0)
    cli_photon_comparison_result = compare_materials_for_target(
        source=cs137_solver_source,
        materials=cli_comparison_materials,
        detector_distance=100.0,
        target=cli_photon_comparison_target,
        max_thickness=20.0,
        apply_buildup=False,
    )

    # Remaining photon-response terminology

    assert_equal(
        "V1.12 photon target description identifies uncollided fluence rate",
        get_target_description(
            FluxTarget(target_flux=100.0),
        ),
        ("Uncollided photon fluence-rate target <= 100 photons/cm^2/s"),
    )

    photon_minimum_output_buffer = StringIO()

    with redirect_stdout(photon_minimum_output_buffer):
        print_minimum_thickness_result(cli_photon_design)

    photon_minimum_output_text = photon_minimum_output_buffer.getvalue()

    photon_minimum_requirements = [
        ("Photon-fluence minimum shielding thickness result"),
        ("Final uncollided response ratio:"),
        ("Final target-comparison uncollided photon fluence rate:"),
        "photons/cm^2/s",
    ]

    for required_text in photon_minimum_requirements:
        assert_equal(
            f"V1.12 photon minimum output contains {required_text}",
            (required_text in photon_minimum_output_text),
            True,
        )

    assert_equal(
        "V1.12 photon minimum output removes generic flux label",
        ("Final target-comparison flux:" in photon_minimum_output_text),
        False,
    )

    photon_comparison_output_buffer = StringIO()

    with redirect_stdout(photon_comparison_output_buffer):
        print_material_comparison_result(cli_photon_comparison_result)

    photon_comparison_output_text = photon_comparison_output_buffer.getvalue()

    photon_comparison_requirements = [
        ("Photon-fluence material comparison result"),
        ("Single-material uncollided photon-fluence design comparison"),
        "Final Fluence Rate",
        "photons/cm^2/s",
    ]

    for required_text in photon_comparison_requirements:
        assert_equal(
            f"V1.12 photon comparison output contains {required_text}",
            (required_text in photon_comparison_output_text),
            True,
        )

    assert_equal(
        ("V1.12 photon comparison output removes legacy response-basis column"),
        ("Response Basis" in photon_comparison_output_text),
        False,
    )

    assert_equal(
        ("V1.12 photon comparison output removes legacy G-P terminology"),
        ("Legacy G-P" in photon_comparison_output_text),
        False,
    )

    assert_equal(
        "V1.12 photon comparison output removes Final Flux column",
        ("Final Flux" in photon_comparison_output_text),
        False,
    )
    assert_equal(
        ("V1.12 photon comparison output removes legacy response-basis column"),
        ("Response Basis" in photon_comparison_output_text),
        False,
    )

    assert_equal(
        ("V1.12 photon comparison output removes legacy G-P terminology"),
        ("Legacy G-P" in photon_comparison_output_text),
        False,
    )
