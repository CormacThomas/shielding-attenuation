"""Verification cases migrated from the original validation runner."""

from pathlib import Path
from tempfile import TemporaryDirectory

from shielding.benchmark.comparison import (
    calculate_observed_monte_carlo_buildup_ratio,
    calculate_relative_difference,
    calculate_spherical_shell_volume_cm3,
    create_deterministic_shell_average_result,
)
from shielding.benchmark.shell_models import SphericalEvaluationShell
from shielding.monte_carlo.models import (
    DeterministicOpenMCComparison,
    OpenMCEnergyBinResult,
    OpenMCResponseResult,
)
from shielding.monte_carlo.response_coefficients import (
    OpenMCAirKermaResponseFunction,
    OpenMCAirKermaResponsePoint,
    calculate_air_kerma_response_coefficient_gy_cm2_per_photon,
    calculate_energy_bin_representative_energy_ev,
    calculate_energy_bin_response_coefficient_gy_cm2_per_photon,
    create_openmc_dry_air_response_function,
    evaluate_openmc_response_function_at_energy_ev,
    fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s,
    get_dry_air_response_point_at_energy,
    validate_response_function_covers_openmc_settings,
)
from shielding.monte_carlo.result_io import (
    deterministic_openmc_comparison_to_dict,
    openmc_response_result_to_dict,
    save_openmc_benchmark_outputs,
)
from shielding.monte_carlo.settings_io import (
    load_openmc_settings,
)
from shielding.monte_carlo.statepoint import (
    calculate_scenario_physical_source_rate_per_s,
)
from shielding.scenarios.fixed_shield import calculate_fixed_shield_response
from shielding.scenarios.fixed_shield_models import FixedShieldDeterministicResult
from shielding.scenarios.json_io import load_scenario
from tests.checks import (
    assert_close,
    assert_equal,
    assert_raises,
)


def test_synthetic_spectrum_result() -> None:
    # Synthetic OpenMC spectrum result

    OpenMCEnergyBinResult(
        lower_energy_ev=1000.0,
        upper_energy_ev=100000.0,
        raw_track_length_flux_mean_cm_per_source=10.0,
        raw_track_length_flux_standard_deviation_cm_per_source=1.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.1,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.01,
        physical_fluence_rate_mean_per_cm2_s=1.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.1,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=0.5,
    )

    second_energy_bin = OpenMCEnergyBinResult(
        lower_energy_ev=100000.0,
        upper_energy_ev=700000.0,
        raw_track_length_flux_mean_cm_per_source=20.0,
        raw_track_length_flux_standard_deviation_cm_per_source=2.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.2,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.02,
        physical_fluence_rate_mean_per_cm2_s=2.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.2,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=1.0,
    )

    assert_close(
        "V1.13 OpenMC energy-bin contribution is stored",
        (second_energy_bin.air_kerma_rate_contribution_gy_per_s),
        1.0,
        1.0e-12,
    )


def test_synthetic_processed_response() -> None:
    first_energy_bin = OpenMCEnergyBinResult(
        lower_energy_ev=1000.0,
        upper_energy_ev=100000.0,
        raw_track_length_flux_mean_cm_per_source=10.0,
        raw_track_length_flux_standard_deviation_cm_per_source=1.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.1,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.01,
        physical_fluence_rate_mean_per_cm2_s=1.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.1,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=0.5,
    )
    second_energy_bin = OpenMCEnergyBinResult(
        lower_energy_ev=100000.0,
        upper_energy_ev=700000.0,
        raw_track_length_flux_mean_cm_per_source=20.0,
        raw_track_length_flux_standard_deviation_cm_per_source=2.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.2,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.02,
        physical_fluence_rate_mean_per_cm2_s=2.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.2,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=1.0,
    )

    # Synthetic processed OpenMC response

    synthetic_evaluation_shell = SphericalEvaluationShell(
        center_radius_cm=100.0,
        thickness_cm=1.0,
    )

    synthetic_shell_volume = calculate_spherical_shell_volume_cm3(
        inner_radius_cm=99.5,
        outer_radius_cm=100.5,
    )

    synthetic_direct_response_rate = 1.5

    synthetic_physical_source_rate = 10.0

    synthetic_response_per_source = (
        synthetic_direct_response_rate / synthetic_physical_source_rate
    )

    synthetic_raw_response = synthetic_response_per_source * synthetic_shell_volume

    synthetic_response_result = OpenMCResponseResult(
        scenario_id=("synthetic_v113_response"),
        settings_profile_name=("v113_test"),
        evaluation_shell=(synthetic_evaluation_shell),
        shell_volume_cm3=(synthetic_shell_volume),
        physical_source_rate_per_s=(synthetic_physical_source_rate),
        energy_bin_results=[
            first_energy_bin,
            second_energy_bin,
        ],
        raw_direct_response_mean_gy_cm3_per_source=(synthetic_raw_response),
        raw_direct_response_standard_deviation_gy_cm3_per_source=(
            synthetic_raw_response * 0.1
        ),
        direct_response_mean_gy_per_source=(synthetic_response_per_source),
        direct_response_standard_deviation_gy_per_source=(
            synthetic_response_per_source * 0.1
        ),
        direct_response_rate_gy_per_s=(synthetic_direct_response_rate),
        direct_response_rate_standard_deviation_gy_per_s=(
            synthetic_direct_response_rate * 0.1
        ),
        relative_uncertainty=0.1,
        spectrum_folded_response_rate_gy_per_s=1.5,
    )

    assert_close(
        "V1.13 OpenMC response preserves physical rate",
        (synthetic_response_result.direct_response_rate_gy_per_s),
        1.5,
        1.0e-12,
    )

    assert_close(
        "V1.13 OpenMC response preserves relative uncertainty",
        (synthetic_response_result.relative_uncertainty),
        0.1,
        1.0e-12,
    )

    assert_close(
        "V1.13 OpenMC response sums spectrum contributions",
        (synthetic_response_result.spectrum_folded_response_rate_gy_per_s),
        1.5,
        1.0e-12,
    )


def test_air_kerma_response_coefficients() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    production_scenario = load_scenario(production_scenario_path)
    production_fixed_result = calculate_fixed_shield_response(production_scenario)
    production_shell_result = create_deterministic_shell_average_result(
        fixed_shield_result=(production_fixed_result),
        evaluation_shell_thickness_cm=1.0,
    )
    development_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_development.json"
    )
    production_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_production.json"
    )
    development_openmc_settings = load_openmc_settings(development_openmc_settings_path)
    production_openmc_settings = load_openmc_settings(production_openmc_settings_path)

    unit_response_coefficient = (
        calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
            photon_energy_mev=1.0,
            mu_en_over_rho_cm2_per_g=1.0,
        )
    )

    assert_close(
        "V1.13 unit dry-air response coefficient",
        unit_response_coefficient,
        1.602176634e-10,
        1.0e-22,
    )

    cs137_response_point = get_dry_air_response_point_at_energy(
        photon_energy_mev=0.661657
    )

    assert_close(
        "V1.13 Cs-137 response-point energy",
        cs137_response_point.energy_ev,
        661657.0,
        1.0e-9,
    )

    assert_close(
        "V1.13 Cs-137 dry-air response coefficient",
        (cs137_response_point.response_coefficient_gy_cm2_per_photon),
        3.1046519590756027e-12,
        1.0e-24,
    )

    assert_equal(
        "V1.13 Cs-137 response point preserves NIST source",
        (
            "NIST X-Ray Mass Attenuation Coefficients"
            in cs137_response_point.coefficient_source
        ),
        True,
    )

    dry_air_response_function = create_openmc_dry_air_response_function()

    assert_equal(
        "V1.13 OpenMC dry-air response function type",
        isinstance(
            dry_air_response_function,
            OpenMCAirKermaResponseFunction,
        ),
        True,
    )

    assert_equal(
        "V1.13 OpenMC dry-air response function has 38 points",
        len(dry_air_response_function.points),
        38,
    )

    assert_equal(
        "V1.13 OpenMC dry-air response function uses log-log interpolation",
        dry_air_response_function.interpolation,
        "log-log",
    )

    assert_close(
        "V1.13 OpenMC response minimum energy",
        (dry_air_response_function.minimum_energy_ev),
        1000.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 OpenMC response maximum energy",
        (dry_air_response_function.maximum_energy_ev),
        20000000.0,
        1.0e-6,
    )

    response_edge_points = [
        point
        for point in (dry_air_response_function.points)
        if (point.absorption_edge_side is not None)
    ]

    assert_equal(
        "V1.13 OpenMC response preserves two argon edge values",
        len(response_edge_points),
        2,
    )

    assert_equal(
        "V1.13 OpenMC response preserves below-edge side",
        (response_edge_points[0].absorption_edge_side),
        "below",
    )

    assert_equal(
        "V1.13 OpenMC response preserves above-edge side",
        (response_edge_points[1].absorption_edge_side),
        "above",
    )

    assert_equal(
        "V1.13 OpenMC response edge energies are strictly increasing",
        (response_edge_points[1].energy_ev > response_edge_points[0].energy_ev),
        True,
    )

    assert_close(
        "V1.13 below-edge dry-air response coefficient",
        (response_edge_points[0].response_coefficient_gy_cm2_per_photon),
        6.825043349581339e-11,
        1.0e-22,
    )

    assert_close(
        "V1.13 above-edge dry-air response coefficient",
        (response_edge_points[1].response_coefficient_gy_cm2_per_photon),
        7.492152849916356e-11,
        1.0e-22,
    )

    interpolated_cs137_response = evaluate_openmc_response_function_at_energy_ev(
        response_function=(dry_air_response_function),
        energy_ev=661657.0,
    )

    assert_close(
        "V1.13 OpenMC response interpolation matches deterministic Cs-137 coefficient",
        interpolated_cs137_response,
        (cs137_response_point.response_coefficient_gy_cm2_per_photon),
        1.0e-23,
    )

    production_shell_air_kerma_from_bridge = fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s(
        photon_fluence_rate_per_cm2_s=(
            production_shell_result.total_shell_average_uncollided_photon_fluence_rate_per_cm2_s
        ),
        response_coefficient_gy_cm2_per_photon=(interpolated_cs137_response),
    )

    assert_close(
        "V1.13 response bridge reproduces production shell air kerma",
        production_shell_air_kerma_from_bridge,
        (
            production_shell_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    representative_source_bin_energy = calculate_energy_bin_representative_energy_ev(
        lower_energy_ev=660000.0,
        upper_energy_ev=665000.0,
    )

    assert_close(
        "V1.13 refined Cs-137 bin geometric energy",
        representative_source_bin_energy,
        662495.2830020754,
        1.0e-9,
    )

    representative_source_bin_response = (
        calculate_energy_bin_response_coefficient_gy_cm2_per_photon(
            response_function=(dry_air_response_function),
            lower_energy_ev=660000.0,
            upper_energy_ev=665000.0,
        )
    )

    assert_close(
        "V1.13 refined Cs-137 bin response coefficient",
        representative_source_bin_response,
        3.1082524326733914e-12,
        1.0e-23,
    )

    assert_close(
        "V1.13 response function is zero below supplied range",
        evaluate_openmc_response_function_at_energy_ev(
            response_function=(dry_air_response_function),
            energy_ev=500.0,
        ),
        0.0,
        0.0,
    )

    validate_response_function_covers_openmc_settings(
        response_function=(dry_air_response_function),
        settings=(development_openmc_settings),
    )

    assert_equal(
        "V1.13 dry-air response covers development profile",
        True,
        True,
    )

    validate_response_function_covers_openmc_settings(
        response_function=(dry_air_response_function),
        settings=(production_openmc_settings),
    )

    assert_equal(
        "V1.13 dry-air response covers production profile",
        True,
        True,
    )


def test_invalid_response_coefficients() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    production_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_production.json"
    )
    production_openmc_settings = load_openmc_settings(production_openmc_settings_path)
    dry_air_response_function = create_openmc_dry_air_response_function()

    # Invalid response-coefficient inputs

    assert_raises(
        "V1.13 response coefficient rejects zero photon energy",
        ValueError,
        lambda: calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
            photon_energy_mev=0.0,
            mu_en_over_rho_cm2_per_g=0.03,
        ),
        "energy must be greater than zero",
    )

    assert_raises(
        "V1.13 response coefficient rejects zero mu_en over rho",
        ValueError,
        lambda: calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
            photon_energy_mev=0.661657,
            mu_en_over_rho_cm2_per_g=0.0,
        ),
        "coefficient must be greater than zero",
    )

    assert_raises(
        "V1.13 OpenMC response point rejects zero coefficient",
        ValueError,
        lambda: OpenMCAirKermaResponsePoint(
            energy_ev=1000.0,
            response_coefficient_gy_cm2_per_photon=0.0,
            coefficient_source="Test source",
        ),
        "coefficient must be greater than zero",
    )

    assert_raises(
        "V1.13 OpenMC response function rejects unordered energies",
        ValueError,
        lambda: OpenMCAirKermaResponseFunction(
            points=(
                OpenMCAirKermaResponsePoint(
                    energy_ev=2000.0,
                    response_coefficient_gy_cm2_per_photon=1.0,
                    coefficient_source="Test source",
                ),
                OpenMCAirKermaResponsePoint(
                    energy_ev=1000.0,
                    response_coefficient_gy_cm2_per_photon=1.0,
                    coefficient_source="Test source",
                ),
            )
        ),
        "strictly increasing",
    )

    assert_raises(
        "V1.13 spectrum-bin response rejects reversed boundaries",
        ValueError,
        lambda: calculate_energy_bin_response_coefficient_gy_cm2_per_photon(
            response_function=(dry_air_response_function),
            lower_energy_ev=700000.0,
            upper_energy_ev=600000.0,
        ),
        "upper boundary must be greater",
    )

    assert_raises(
        "V1.13 response folding rejects negative fluence",
        ValueError,
        lambda: fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s(
            photon_fluence_rate_per_cm2_s=-1.0,
            response_coefficient_gy_cm2_per_photon=(1.0e-12),
        ),
        "fluence rate cannot be negative",
    )

    insufficient_response_function = OpenMCAirKermaResponseFunction(
        points=(
            OpenMCAirKermaResponsePoint(
                energy_ev=2000.0,
                response_coefficient_gy_cm2_per_photon=1.0e-10,
                coefficient_source="Test source",
            ),
            OpenMCAirKermaResponsePoint(
                energy_ev=600000.0,
                response_coefficient_gy_cm2_per_photon=1.0e-12,
                coefficient_source="Test source",
            ),
        )
    )

    assert_raises(
        "V1.13 response coverage rejects minimum above cutoff",
        ValueError,
        lambda: validate_response_function_covers_openmc_settings(
            response_function=(insufficient_response_function),
            settings=(production_openmc_settings),
        ),
        "must not exceed the photon cutoff",
    )


def test_physical_source_rate() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    development_scenario = load_scenario(development_scenario_path)
    production_scenario = load_scenario(production_scenario_path)
    v110_reference_path = repository_root / "scenarios" / "cs137_v110_reference.json"
    schema_10_scenario = load_scenario(v110_reference_path)

    assert_close(
        "V1.13 development statepoint source rate",
        calculate_scenario_physical_source_rate_per_s(development_scenario),
        3.1487e10,
        1.0e-3,
    )

    assert_close(
        "V1.13 production statepoint source rate",
        calculate_scenario_physical_source_rate_per_s(production_scenario),
        3.1487e10,
        1.0e-3,
    )

    assert_raises(
        "V1.13 statepoint source rate rejects optimization mode",
        ValueError,
        lambda: calculate_scenario_physical_source_rate_per_s(schema_10_scenario),
        "requires fixed_shield_response mode",
    )


def test_processed_output_serialization() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    development_scenario = load_scenario(development_scenario_path)
    development_fixed_result = calculate_fixed_shield_response(development_scenario)
    first_energy_bin = OpenMCEnergyBinResult(
        lower_energy_ev=1000.0,
        upper_energy_ev=100000.0,
        raw_track_length_flux_mean_cm_per_source=10.0,
        raw_track_length_flux_standard_deviation_cm_per_source=1.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.1,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.01,
        physical_fluence_rate_mean_per_cm2_s=1.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.1,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=0.5,
    )
    second_energy_bin = OpenMCEnergyBinResult(
        lower_energy_ev=100000.0,
        upper_energy_ev=700000.0,
        raw_track_length_flux_mean_cm_per_source=20.0,
        raw_track_length_flux_standard_deviation_cm_per_source=2.0,
        volume_normalized_fluence_mean_per_cm2_per_source=0.2,
        volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.02,
        physical_fluence_rate_mean_per_cm2_s=2.0,
        physical_fluence_rate_standard_deviation_per_cm2_s=0.2,
        response_coefficient_gy_cm2_per_photon=0.5,
        air_kerma_rate_contribution_gy_per_s=1.0,
    )
    synthetic_evaluation_shell = SphericalEvaluationShell(
        center_radius_cm=100.0,
        thickness_cm=1.0,
    )
    synthetic_shell_volume = calculate_spherical_shell_volume_cm3(
        inner_radius_cm=99.5,
        outer_radius_cm=100.5,
    )
    synthetic_direct_response_rate = 1.5
    synthetic_physical_source_rate = 10.0
    synthetic_response_per_source = (
        synthetic_direct_response_rate / synthetic_physical_source_rate
    )
    synthetic_raw_response = synthetic_response_per_source * synthetic_shell_volume
    synthetic_response_result = OpenMCResponseResult(
        scenario_id=("synthetic_v113_response"),
        settings_profile_name=("v113_test"),
        evaluation_shell=(synthetic_evaluation_shell),
        shell_volume_cm3=(synthetic_shell_volume),
        physical_source_rate_per_s=(synthetic_physical_source_rate),
        energy_bin_results=[
            first_energy_bin,
            second_energy_bin,
        ],
        raw_direct_response_mean_gy_cm3_per_source=(synthetic_raw_response),
        raw_direct_response_standard_deviation_gy_cm3_per_source=(
            synthetic_raw_response * 0.1
        ),
        direct_response_mean_gy_per_source=(synthetic_response_per_source),
        direct_response_standard_deviation_gy_per_source=(
            synthetic_response_per_source * 0.1
        ),
        direct_response_rate_gy_per_s=(synthetic_direct_response_rate),
        direct_response_rate_standard_deviation_gy_per_s=(
            synthetic_direct_response_rate * 0.1
        ),
        relative_uncertainty=0.1,
        spectrum_folded_response_rate_gy_per_s=1.5,
    )

    synthetic_response_data = openmc_response_result_to_dict(synthetic_response_result)

    assert_equal(
        "V1.13 processed response preserves record type",
        synthetic_response_data["record_type"],
        "openmc_response",
    )

    assert_equal(
        "V1.13 processed response preserves energy-bin count",
        (synthetic_response_data["spectrum_summary"]["energy_bin_count"]),
        2,
    )

    assert_close(
        "V1.13 processed response preserves physical rate",
        (synthetic_response_data["direct_response"]["rate_gy_per_s"]),
        1.5,
        1.0e-12,
    )

    synthetic_fixed_result = FixedShieldDeterministicResult(
        scenario_id=("synthetic_v113_response"),
        source_name=(development_fixed_result.source_name),
        activity_bq=(development_fixed_result.activity_bq),
        geometry=(development_fixed_result.geometry),
        line_results=(development_fixed_result.line_results),
        source_air_kerma_result=(development_fixed_result.source_air_kerma_result),
        buildup_requested=(development_fixed_result.buildup_requested),
    )

    synthetic_deterministic_result = create_deterministic_shell_average_result(
        fixed_shield_result=(synthetic_fixed_result),
        evaluation_shell_thickness_cm=1.0,
    )

    synthetic_uncollided = synthetic_deterministic_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s

    synthetic_gp = synthetic_deterministic_result.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s

    synthetic_relative_difference_from_gp = None

    if synthetic_gp is not None:
        synthetic_relative_difference_from_gp = calculate_relative_difference(
            comparison_value=(synthetic_response_result.direct_response_rate_gy_per_s),
            reference_value=(synthetic_gp),
        )

    synthetic_comparison = DeterministicOpenMCComparison(
        deterministic_result=(synthetic_deterministic_result),
        openmc_result=(synthetic_response_result),
        relative_difference_from_uncollided=(
            calculate_relative_difference(
                comparison_value=(
                    synthetic_response_result.direct_response_rate_gy_per_s
                ),
                reference_value=(synthetic_uncollided),
            )
        ),
        relative_difference_from_gp=(synthetic_relative_difference_from_gp),
        observed_monte_carlo_buildup_ratio=(
            calculate_observed_monte_carlo_buildup_ratio(
                openmc_response=(
                    synthetic_response_result.direct_response_rate_gy_per_s
                ),
                deterministic_uncollided_response=(synthetic_uncollided),
            )
        ),
    )

    synthetic_comparison_data = deterministic_openmc_comparison_to_dict(
        synthetic_comparison
    )

    assert_equal(
        "V1.13 processed comparison preserves record type",
        synthetic_comparison_data["record_type"],
        "deterministic_openmc_comparison",
    )

    assert_equal(
        "V1.13 processed comparison direct-versus-folded passes",
        (synthetic_comparison_data["acceptance_checks"]["direct_vs_folded_pass"]),
        True,
    )

    with TemporaryDirectory() as temporary_directory:
        processed_output_paths = save_openmc_benchmark_outputs(
            openmc_result=(synthetic_response_result),
            comparison=(synthetic_comparison),
            output_directory=(Path(temporary_directory)),
        )

        assert_equal(
            "V1.13 processed response JSON is created",
            (processed_output_paths.response_json_path.is_file()),
            True,
        )

        assert_equal(
            "V1.13 processed comparison JSON is created",
            (processed_output_paths.comparison_json_path.is_file()),
            True,
        )

        assert_equal(
            "V1.13 processed spectrum CSV is created",
            (processed_output_paths.spectrum_csv_path.is_file()),
            True,
        )

        spectrum_csv_text = processed_output_paths.spectrum_csv_path.read_text(
            encoding="utf-8"
        )

        assert_equal(
            "V1.13 processed spectrum CSV contains physical fluence column",
            ("physical_fluence_rate_mean_per_cm2_s" in spectrum_csv_text),
            True,
        )
