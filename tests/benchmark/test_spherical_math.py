"""Verification cases migrated from the original validation runner."""

from pathlib import Path

from shielding.benchmark.case_models import BenchmarkCaseDefinition
from shielding.benchmark.cases import (
    create_v114_core_case_definitions,
    resolve_benchmark_case,
    resolve_benchmark_cases,
)
from shielding.benchmark.comparison import (
    calculate_deterministic_shell_averaged_fluence_rate,
    calculate_observed_monte_carlo_buildup_ratio,
    calculate_photon_line_emission_rate_per_s,
    calculate_point_source_geometric_factor_per_cm2,
    calculate_relative_difference,
    calculate_relative_uncertainty,
    calculate_shell_average_geometric_factor_per_cm2,
    calculate_shell_average_to_point_scale_factor,
    calculate_spherical_shell_volume_cm3,
    create_deterministic_shell_average_result,
    normalize_openmc_track_length_flux_tally,
    scale_per_source_estimate_to_physical_rate,
)
from shielding.benchmark.shell_models import (
    DeterministicShellAverageResult,
    SphericalEvaluationShell,
)
from shielding.physics.units import convert_gy_per_s_to_microgy_per_h
from shielding.scenarios.fixed_shield import calculate_fixed_shield_response
from shielding.scenarios.json_io import (
    load_scenario,
    scenario_from_dict,
    scenario_to_dict,
)
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_not_none,
    assert_raises,
)


def test_evaluation_shell_math() -> None:
    evaluation_shell_inner_radius_cm = 99.5
    evaluation_shell_outer_radius_cm = 100.5

    evaluation_shell_volume_cm3 = calculate_spherical_shell_volume_cm3(
        inner_radius_cm=(evaluation_shell_inner_radius_cm),
        outer_radius_cm=(evaluation_shell_outer_radius_cm),
    )

    assert_close(
        "V1.13 evaluation-shell volume",
        evaluation_shell_volume_cm3,
        125664.75334114292,
        1.0e-6,
    )

    shell_average_geometric_factor = calculate_shell_average_geometric_factor_per_cm2(
        inner_radius_cm=(evaluation_shell_inner_radius_cm),
        outer_radius_cm=(evaluation_shell_outer_radius_cm),
    )

    assert_close(
        "V1.13 shell-average geometric factor",
        shell_average_geometric_factor,
        7.957680840587762e-6,
        1.0e-15,
    )

    cs137_photon_rate_per_s = calculate_photon_line_emission_rate_per_s(
        activity_bq=3.7e10,
        emission_intensity=0.851,
    )

    assert_close(
        "V1.13 Cs-137 physical photon rate",
        cs137_photon_rate_per_s,
        3.1487e10,
        1.0e-3,
    )

    unshielded_shell_average_fluence_rate = (
        calculate_deterministic_shell_averaged_fluence_rate(
            photon_emission_rate_per_s=(cs137_photon_rate_per_s),
            transmission=1.0,
            inner_radius_cm=(evaluation_shell_inner_radius_cm),
            outer_radius_cm=(evaluation_shell_outer_radius_cm),
        )
    )

    assert_close(
        "V1.13 unshielded shell-average fluence rate",
        unshielded_shell_average_fluence_rate,
        250563.49662758686,
        1.0e-6,
    )

    quarter_transmission_fluence_rate = (
        calculate_deterministic_shell_averaged_fluence_rate(
            photon_emission_rate_per_s=100.0,
            transmission=0.25,
            inner_radius_cm=1.0,
            outer_radius_cm=2.0,
        )
    )

    assert_close(
        "V1.13 shell-average fluence includes transmission",
        quarter_transmission_fluence_rate,
        0.8526157665637252,
        1.0e-12,
    )


def test_tally_normalization() -> None:
    # OpenMC tally normalization

    (
        normalized_flux_mean,
        normalized_flux_standard_deviation,
    ) = normalize_openmc_track_length_flux_tally(
        raw_mean_cm_per_source=25.0,
        raw_standard_deviation_cm_per_source=2.5,
        tally_volume_cm3=100.0,
    )

    assert_close(
        "V1.13 flux tally volume-normalized mean",
        normalized_flux_mean,
        0.25,
        1.0e-12,
    )

    assert_close(
        "V1.13 flux tally volume-normalized standard deviation",
        normalized_flux_standard_deviation,
        0.025,
        1.0e-12,
    )

    (
        physical_flux_rate,
        physical_flux_rate_standard_deviation,
    ) = scale_per_source_estimate_to_physical_rate(
        mean_per_source=normalized_flux_mean,
        standard_deviation_per_source=(normalized_flux_standard_deviation),
        physical_source_rate_per_s=4.0,
    )

    assert_close(
        "V1.13 physical source scaling applies to mean",
        physical_flux_rate,
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 physical source scaling applies to standard deviation",
        physical_flux_rate_standard_deviation,
        0.1,
        1.0e-12,
    )

    relative_uncertainty_before_scaling = calculate_relative_uncertainty(
        mean=normalized_flux_mean,
        standard_deviation=(normalized_flux_standard_deviation),
    )

    relative_uncertainty_after_scaling = calculate_relative_uncertainty(
        mean=physical_flux_rate,
        standard_deviation=(physical_flux_rate_standard_deviation),
    )

    assert_close(
        "V1.13 tally relative uncertainty",
        relative_uncertainty_before_scaling,
        0.1,
        1.0e-12,
    )

    assert_close(
        "V1.13 multiplicative scaling preserves relative uncertainty",
        relative_uncertainty_after_scaling,
        relative_uncertainty_before_scaling,
        1.0e-12,
    )


def test_comparison_metrics() -> None:
    # Comparison metrics

    assert_close(
        "V1.13 positive relative difference",
        calculate_relative_difference(
            comparison_value=12.0,
            reference_value=10.0,
        ),
        0.2,
        1.0e-12,
    )

    assert_close(
        "V1.13 negative relative difference",
        calculate_relative_difference(
            comparison_value=8.0,
            reference_value=10.0,
        ),
        -0.2,
        1.0e-12,
    )

    assert_close(
        "V1.13 observed Monte Carlo buildup ratio",
        calculate_observed_monte_carlo_buildup_ratio(
            openmc_response=15.0,
            deterministic_uncollided_response=10.0,
        ),
        1.5,
        1.0e-12,
    )


def test_invalid_comparison_inputs() -> None:
    # Invalid mathematical inputs

    assert_raises(
        "V1.13 shell volume rejects negative inner radius",
        ValueError,
        lambda: calculate_spherical_shell_volume_cm3(
            inner_radius_cm=-1.0,
            outer_radius_cm=2.0,
        ),
        "inner radius cannot be negative",
    )

    assert_raises(
        "V1.13 shell volume rejects reversed radii",
        ValueError,
        lambda: calculate_spherical_shell_volume_cm3(
            inner_radius_cm=2.0,
            outer_radius_cm=1.0,
        ),
        "outer radius must be greater",
    )

    assert_raises(
        "V1.13 shell-average fluence rejects transmission above one",
        ValueError,
        lambda: calculate_deterministic_shell_averaged_fluence_rate(
            photon_emission_rate_per_s=100.0,
            transmission=1.1,
            inner_radius_cm=1.0,
            outer_radius_cm=2.0,
        ),
        "between zero and one",
    )

    assert_raises(
        "V1.13 photon rate rejects negative activity",
        ValueError,
        lambda: calculate_photon_line_emission_rate_per_s(
            activity_bq=-1.0,
            emission_intensity=0.851,
        ),
        "activity cannot be negative",
    )

    assert_raises(
        "V1.13 tally normalization rejects zero volume",
        ValueError,
        lambda: normalize_openmc_track_length_flux_tally(
            raw_mean_cm_per_source=1.0,
            raw_standard_deviation_cm_per_source=0.1,
            tally_volume_cm3=0.0,
        ),
        "volume must be greater than zero",
    )

    assert_raises(
        "V1.13 tally normalization rejects negative uncertainty",
        ValueError,
        lambda: normalize_openmc_track_length_flux_tally(
            raw_mean_cm_per_source=1.0,
            raw_standard_deviation_cm_per_source=-0.1,
            tally_volume_cm3=100.0,
        ),
        "standard deviation cannot be negative",
    )

    assert_raises(
        "V1.13 relative uncertainty rejects zero mean",
        ValueError,
        lambda: calculate_relative_uncertainty(
            mean=0.0,
            standard_deviation=0.0,
        ),
        "requires a positive mean",
    )

    assert_raises(
        "V1.13 relative difference rejects zero reference",
        ValueError,
        lambda: calculate_relative_difference(
            comparison_value=1.0,
            reference_value=0.0,
        ),
        "requires a positive reference value",
    )

    assert_raises(
        "V1.13 buildup ratio rejects zero uncollided response",
        ValueError,
        lambda: calculate_observed_monte_carlo_buildup_ratio(
            openmc_response=1.0,
            deterministic_uncollided_response=0.0,
        ),
        "requires a positive deterministic",
    )


def test_matched_shell_averaged_result() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    development_scenario = load_scenario(development_scenario_path)
    production_scenario = load_scenario(production_scenario_path)
    development_fixed_result = calculate_fixed_shield_response(development_scenario)
    production_fixed_result = calculate_fixed_shield_response(production_scenario)

    official_evaluation_shell = SphericalEvaluationShell(
        center_radius_cm=100.0,
        thickness_cm=1.0,
    )

    assert_close(
        "V1.13 official evaluation-shell inner radius",
        official_evaluation_shell.inner_radius_cm,
        99.5,
        1.0e-12,
    )

    assert_close(
        "V1.13 official evaluation-shell outer radius",
        official_evaluation_shell.outer_radius_cm,
        100.5,
        1.0e-12,
    )

    point_geometric_factor = calculate_point_source_geometric_factor_per_cm2(
        radius_cm=100.0
    )

    assert_close(
        "V1.13 point geometric factor at 100 cm",
        point_geometric_factor,
        7.957747154594767e-6,
        1.0e-15,
    )

    shell_average_scale_factor = calculate_shell_average_to_point_scale_factor(
        point_radius_cm=100.0,
        shell_inner_radius_cm=99.5,
        shell_outer_radius_cm=100.5,
    )

    assert_close(
        "V1.13 point-to-shell-average scale factor",
        shell_average_scale_factor,
        0.9999916667361105,
        1.0e-15,
    )

    development_shell_result = create_deterministic_shell_average_result(
        fixed_shield_result=(development_fixed_result),
        evaluation_shell_thickness_cm=1.0,
    )

    production_shell_result = create_deterministic_shell_average_result(
        fixed_shield_result=(production_fixed_result),
        evaluation_shell_thickness_cm=1.0,
    )

    assert_equal(
        "V1.13 development returns shell-average result",
        isinstance(
            development_shell_result,
            DeterministicShellAverageResult,
        ),
        True,
    )

    assert_equal(
        "V1.13 production shell result preserves scenario ID",
        production_shell_result.scenario_id,
        "cs137_v113_production",
    )

    assert_equal(
        "V1.13 production shell result preserves source name",
        production_shell_result.source_name,
        "Cs-137",
    )

    assert_close(
        "V1.13 development shell-average fluence",
        (
            development_shell_result.total_shell_average_uncollided_photon_fluence_rate_per_cm2_s
        ),
        71066.08434453273,
        1.0e-8,
    )

    assert_close(
        "V1.13 production shell-average fluence",
        (
            production_shell_result.total_shell_average_uncollided_photon_fluence_rate_per_cm2_s
        ),
        459.87598484786196,
        1.0e-10,
    )

    assert_close(
        "V1.13 development shell-average uncollided air kerma",
        (
            development_shell_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        2.2063545798408556e-7,
        1.0e-18,
    )

    assert_close(
        "V1.13 production shell-average uncollided air kerma",
        (
            production_shell_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.4277548772897367e-9,
        1.0e-20,
    )

    assert_close(
        "V1.13 development shell-average G-P response",
        assert_not_none(
            "V1.13 development shell G-P response exists",
            (
                development_shell_result.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        3.4158906417814603e-7,
        1.0e-18,
    )

    assert_close(
        "V1.13 production shell-average G-P response",
        assert_not_none(
            "V1.13 production shell G-P response exists",
            (
                production_shell_result.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        3.765961442081238e-9,
        1.0e-20,
    )

    assert_close(
        "V1.13 production shell-average air kerma in microGy per hour",
        convert_gy_per_s_to_microgy_per_h(
            production_shell_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        ),
        5.139917558243052,
        1.0e-12,
    )

    assert_close(
        "V1.13 production shell-average G-P response in microGy per hour",
        convert_gy_per_s_to_microgy_per_h(
            assert_not_none(
                "V1.13 production shell adjusted total exists",
                (
                    production_shell_result.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
                ),
            )
        ),
        13.557461191492456,
        1.0e-12,
    )

    assert_equal(
        "V1.13 shell result preserves point result",
        (production_shell_result.fixed_shield_result),
        production_fixed_result,
    )

    assert_equal(
        "V1.13 shell result contains one photon line",
        len(production_shell_result.line_results),
        1,
    )

    assert_close(
        "V1.13 shell line uses common scale factor",
        (production_shell_result.line_results[0].point_to_shell_average_scale_factor),
        shell_average_scale_factor,
        1.0e-15,
    )


def test_invalid_evaluation_shell_inputs() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    production_scenario = load_scenario(production_scenario_path)
    production_fixed_result = calculate_fixed_shield_response(production_scenario)

    # Invalid evaluation-shell inputs

    assert_raises(
        "V1.13 evaluation shell rejects zero thickness",
        ValueError,
        lambda: SphericalEvaluationShell(
            center_radius_cm=100.0,
            thickness_cm=0.0,
        ),
        "thickness must be greater than zero",
    )

    assert_raises(
        "V1.13 evaluation shell rejects nonpositive inner radius",
        ValueError,
        lambda: SphericalEvaluationShell(
            center_radius_cm=1.0,
            thickness_cm=2.0,
        ),
        "inner radius must be greater than zero",
    )

    assert_raises(
        "V1.13 point geometric factor rejects zero radius",
        ValueError,
        lambda: calculate_point_source_geometric_factor_per_cm2(radius_cm=0.0),
        "radius must be greater than zero",
    )

    assert_raises(
        "V1.13 matched shell rejects shield intersection",
        ValueError,
        lambda: create_deterministic_shell_average_result(
            fixed_shield_result=(production_fixed_result),
            evaluation_shell_thickness_cm=190.0,
        ),
        "entirely beyond the outer shield radius",
    )


def test_core_benchmark_cases() -> None:
    definitions = create_v114_core_case_definitions()

    assert_equal(
        "V1.14 core matrix contains eight definitions",
        len(definitions),
        8,
    )

    expected_case_ids = [
        "cs137_lead_01mfp",
        "cs137_lead_05mfp",
        "cs137_lead_10mfp",
        "cs137_tungsten_01mfp",
        "cs137_tungsten_05mfp",
        "cs137_concrete_ordinary_01mfp",
        "cs137_concrete_ordinary_05mfp",
        "cs137_water_05mfp",
    ]

    assert_equal(
        "V1.14 core case order is stable",
        [definition.case_id for definition in definitions],
        expected_case_ids,
    )

    resolved_cases = resolve_benchmark_cases(definitions)

    expected_thickness_by_case_id = {
        "cs137_lead_01mfp": (0.7935864511780163),
        "cs137_lead_05mfp": (3.9679322558900814),
        "cs137_lead_10mfp": (7.935864511780163),
        "cs137_tungsten_01mfp": (0.5269004412604447),
        "cs137_tungsten_05mfp": (2.634502206302223),
        "cs137_concrete_ordinary_01mfp": (5.288973220970279),
        "cs137_concrete_ordinary_05mfp": (26.444866104851393),
        "cs137_water_05mfp": (58.34965139958336),
    }

    for resolved_case in resolved_cases:
        definition = resolved_case.definition

        scenario = resolved_case.scenario

        assert_close(
            f"V1.14 {definition.case_id} physical thickness",
            resolved_case.physical_thickness_cm,
            expected_thickness_by_case_id[definition.case_id],
            1.0e-10,
        )

        assert_close(
            f"V1.14 {definition.case_id} reconstructs target MFP",
            (resolved_case.reconstructed_mean_free_paths),
            definition.target_mean_free_paths,
            1.0e-12,
        )

        assert_equal(
            f"V1.14 {definition.case_id} uses schema 1.1",
            scenario.schema_version,
            "1.1",
        )

        assert_equal(
            f"V1.14 {definition.case_id} uses fixed-shield mode",
            scenario.calculation_mode,
            "fixed_shield_response",
        )

        assert_equal(
            f"V1.14 {definition.case_id} contains one layer",
            len(scenario.geometry.layers),
            1,
        )

        assert_equal(
            f"V1.14 {definition.case_id} preserves material",
            (scenario.geometry.layers[0].material_key),
            definition.material_key,
        )

        assert_equal(
            f"V1.14 {definition.case_id} requests G-P buildup",
            (scenario.deterministic_settings.apply_buildup),
            True,
        )

        assert_equal(
            "V1.14 "
            f"{definition.case_id} scenario dictionary "
            "round trip preserves object",
            scenario_from_dict(scenario_to_dict(scenario)),
            scenario,
        )

        deterministic_result = calculate_fixed_shield_response(scenario)

        assert_equal(
            f"V1.14 {definition.case_id} deterministic result contains one photon line",
            len(deterministic_result.line_results),
            1,
        )

        photon_line_result = deterministic_result.line_results[0]

        assert_close(
            "V1.14 "
            f"{definition.case_id} source-line energy "
            "matches MFP reference energy",
            (photon_line_result.photon_line.energy),
            definition.reference_energy_mev,
            1.0e-12,
        )

        assert_close(
            f"V1.14 {definition.case_id} deterministic layer reproduces target MFP",
            (photon_line_result.shielding_result.total_mfp),
            definition.target_mean_free_paths,
            1.0e-10,
        )

        assert_equal(
            f"V1.14 {definition.case_id} deterministic G-P response is available",
            (deterministic_result.source_air_kerma_result.buildup_status),
            "applied",
        )

        assert_greater_than(
            "V1.14 "
            f"{definition.case_id} deterministic "
            "uncollided air kerma is positive",
            (
                deterministic_result.source_air_kerma_result.total_uncollided_collision_air_kerma_rate_gy_per_s
            ),
            0.0,
        )

    assert_raises(
        "V1.14 duplicate benchmark case IDs rejected",
        ValueError,
        lambda: resolve_benchmark_cases(
            [
                definitions[0],
                definitions[0],
            ]
        ),
        "must be unique",
    )

    assert_raises(
        "V1.14 nonpositive benchmark MFP rejected",
        ValueError,
        lambda: BenchmarkCaseDefinition(
            case_id="invalid_zero_mfp",
            isotope_key="cs137",
            activity_bq=3.7e10,
            material_key="lead",
            reference_energy_mev=0.661657,
            target_mean_free_paths=0.0,
        ),
        "positive finite value",
    )

    assert_raises(
        "V1.14 nonpositive benchmark activity rejected",
        ValueError,
        lambda: BenchmarkCaseDefinition(
            case_id="invalid_zero_activity",
            isotope_key="cs137",
            activity_bq=0.0,
            material_key="lead",
            reference_energy_mev=0.661657,
            target_mean_free_paths=1.0,
        ),
        "positive finite value",
    )

    assert_raises(
        "V1.14 unknown benchmark material rejected",
        ValueError,
        lambda: resolve_benchmark_case(
            BenchmarkCaseDefinition(
                case_id="unknown_material_case",
                isotope_key="cs137",
                activity_bq=3.7e10,
                material_key="unobtainium",
                reference_energy_mev=0.661657,
                target_mean_free_paths=1.0,
            )
        ),
        "unknown material key",
    )

    assert_raises(
        "V1.14 unknown benchmark isotope rejected",
        ValueError,
        lambda: resolve_benchmark_case(
            BenchmarkCaseDefinition(
                case_id="unknown_isotope_case",
                isotope_key="fake_isotope",
                activity_bq=3.7e10,
                material_key="lead",
                reference_energy_mev=0.661657,
                target_mean_free_paths=1.0,
            )
        ),
        "unknown isotope key",
    )

    assert_raises(
        "V1.14 out-of-range benchmark energy rejected",
        ValueError,
        lambda: resolve_benchmark_case(
            BenchmarkCaseDefinition(
                case_id="out_of_range_energy_case",
                isotope_key="cs137",
                activity_bq=3.7e10,
                material_key="lead",
                reference_energy_mev=20.0,
                target_mean_free_paths=1.0,
            )
        ),
        "outside",
    )

    assert_raises(
        "V1.14 benchmark shield exceeding evaluation radius rejected",
        ValueError,
        lambda: resolve_benchmark_case(
            BenchmarkCaseDefinition(
                case_id="oversized_water_case",
                isotope_key="cs137",
                activity_bq=3.7e10,
                material_key="water",
                reference_energy_mev=0.661657,
                target_mean_free_paths=10.0,
                source_cavity_radius_cm=1.0,
                evaluation_radius_cm=100.0,
            )
        ),
        "reaches or exceeds",
    )
