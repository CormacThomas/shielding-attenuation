# Process the recovered V1.13 production statepoint without rerunning OpenMC.
#
# The five-million-history transport already completed successfully. This
# script reads the preserved final statepoint, performs physical normalization,
# compares it with the matched deterministic result, and saves the official
# processed production outputs.
#
# Run inside Docker:
#
#   python examples/openmc_v113_process_production_recovery.py


from __future__ import annotations


from pathlib import Path
import sys


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "src"
)


if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from fixed_shield_response import (
    calculate_fixed_shield_response,
)
from openmc_models import (
    DeterministicOpenMCComparison,
)
from openmc_response import (
    calculate_observed_monte_carlo_buildup_ratio,
    calculate_relative_difference,
    create_deterministic_shell_average_result,
)
from openmc_result_io import (
    save_openmc_benchmark_outputs,
)
from openmc_settings_io import (
    load_openmc_settings,
)
from openmc_statepoint_processor import (
    process_openmc_v113_statepoint,
)
from scenario_io import (
    load_scenario,
)
from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
)


SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_v113_production.json"
)

SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v113_production.json"
)

RECOVERED_STATEPOINT_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "statepoint.100.h5"
)

PROCESSED_OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "processed"
    / "final"
)


DIRECT_VS_FOLDED_TOLERANCE = 0.02
REQUIRED_RELATIVE_UNCERTAINTY = 0.05
PREFERRED_RELATIVE_UNCERTAINTY = 0.02


def main() -> int:
    if not RECOVERED_STATEPOINT_PATH.is_file():
        raise FileNotFoundError(
            "Recovered production statepoint does not exist: "
            f"{RECOVERED_STATEPOINT_PATH}"
        )

    scenario = load_scenario(
        SCENARIO_PATH
    )

    settings_profile = load_openmc_settings(
        SETTINGS_PATH
    )

    if settings_profile.batches != 100:
        raise RuntimeError(
            "The production settings profile must end at batch 100."
        )

    print()
    print("=" * 72)
    print("OPENMC V1.13 RECOVERED PRODUCTION PROCESSING")
    print("=" * 72)

    print(
        "Scenario ID: "
        f"{scenario.scenario_id}"
    )

    print(
        "Settings profile: "
        f"{settings_profile.profile_name}"
    )

    print(
        "Recovered statepoint: "
        f"{RECOVERED_STATEPOINT_PATH}"
    )

    print(
        "Configured histories: "
        f"{settings_profile.total_source_particles}"
    )

    print("-" * 72)
    print(
        "Reading and normalizing the completed production statepoint."
    )
    print("-" * 72)

    openmc_result = process_openmc_v113_statepoint(
        statepoint_path=(
            RECOVERED_STATEPOINT_PATH
        ),
        scenario=scenario,
        settings_profile=(
            settings_profile
        ),
        evaluation_shell_thickness_cm=1.0,
        expected_batch=(
            settings_profile.batches
        ),
    )

    fixed_shield_result = (
        calculate_fixed_shield_response(
            scenario
        )
    )

    deterministic_result = (
        create_deterministic_shell_average_result(
            fixed_shield_result=(
                fixed_shield_result
            ),
            evaluation_shell_thickness_cm=1.0,
        )
    )

    deterministic_uncollided = (
        deterministic_result
        .total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
    )

    deterministic_gp = (
        deterministic_result
        .total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    openmc_direct_response = (
        openmc_result
        .direct_response_rate_gy_per_s
    )

    relative_difference_from_uncollided = (
        calculate_relative_difference(
            comparison_value=(
                openmc_direct_response
            ),
            reference_value=(
                deterministic_uncollided
            ),
        )
    )

    relative_difference_from_gp = None

    if deterministic_gp is not None:
        relative_difference_from_gp = (
            calculate_relative_difference(
                comparison_value=(
                    openmc_direct_response
                ),
                reference_value=(
                    deterministic_gp
                ),
            )
        )

    observed_buildup_ratio = (
        calculate_observed_monte_carlo_buildup_ratio(
            openmc_response=(
                openmc_direct_response
            ),
            deterministic_uncollided_response=(
                deterministic_uncollided
            ),
        )
    )

    comparison = DeterministicOpenMCComparison(
        deterministic_result=(
            deterministic_result
        ),
        openmc_result=(
            openmc_result
        ),
        relative_difference_from_uncollided=(
            relative_difference_from_uncollided
        ),
        relative_difference_from_gp=(
            relative_difference_from_gp
        ),
        observed_monte_carlo_buildup_ratio=(
            observed_buildup_ratio
        ),
    )

    direct_vs_folded_difference = (
        calculate_relative_difference(
            comparison_value=(
                openmc_result
                .spectrum_folded_response_rate_gy_per_s
            ),
            reference_value=(
                openmc_result
                .direct_response_rate_gy_per_s
            ),
        )
    )

    output_paths = save_openmc_benchmark_outputs(
        openmc_result=openmc_result,
        comparison=comparison,
        output_directory=(
            PROCESSED_OUTPUT_DIRECTORY
        ),
        direct_vs_folded_tolerance=(
            DIRECT_VS_FOLDED_TOLERANCE
        ),
        required_relative_uncertainty=(
            REQUIRED_RELATIVE_UNCERTAINTY
        ),
        preferred_relative_uncertainty=(
            PREFERRED_RELATIVE_UNCERTAINTY
        ),
    )

    total_physical_fluence_rate = sum(
        energy_bin_result
        .physical_fluence_rate_mean_per_cm2_s
        for energy_bin_result
        in openmc_result.energy_bin_results
    )

    direct_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            openmc_result
            .direct_response_rate_gy_per_s
        )
    )

    direct_standard_deviation_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            openmc_result
            .direct_response_rate_standard_deviation_gy_per_s
        )
    )

    folded_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            openmc_result
            .spectrum_folded_response_rate_gy_per_s
        )
    )

    deterministic_uncollided_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            deterministic_uncollided
        )
    )

    deterministic_gp_microgy_per_h = None

    if deterministic_gp is not None:
        deterministic_gp_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                deterministic_gp
            )
        )

    required_uncertainty_pass = (
        openmc_result.relative_uncertainty
        <= REQUIRED_RELATIVE_UNCERTAINTY
    )

    preferred_uncertainty_pass = (
        openmc_result.relative_uncertainty
        <= PREFERRED_RELATIVE_UNCERTAINTY
    )

    folded_check_pass = (
        abs(direct_vs_folded_difference)
        <= DIRECT_VS_FOLDED_TOLERANCE
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 PRODUCTION BENCHMARK RESULTS")
    print("=" * 72)

    print(
        "Statepoint batch: "
        f"{settings_profile.batches}"
    )

    print(
        "Total source histories: "
        f"{settings_profile.total_source_particles}"
    )

    print(
        "Evaluation shell: "
        f"{openmc_result.evaluation_shell.inner_radius_cm:.6f} "
        "to "
        f"{openmc_result.evaluation_shell.outer_radius_cm:.6f} cm"
    )

    print(
        "Evaluation-shell volume: "
        f"{openmc_result.shell_volume_cm3:.9f} cm^3"
    )

    print(
        "Physical photon source rate: "
        f"{openmc_result.physical_source_rate_per_s:.8e} photons/s"
    )

    print("-" * 72)
    print("Physical photon spectrum:")

    print(
        "  Energy bins: "
        f"{len(openmc_result.energy_bin_results)}"
    )

    print(
        "  Total photon fluence rate: "
        f"{total_physical_fluence_rate:.10e} photons/cm^2/s"
    )

    print("-" * 72)
    print("OpenMC direct response:")

    print(
        "  Response: "
        f"{openmc_result.direct_response_rate_gy_per_s:.10e} Gy/s"
    )

    print(
        "  Response: "
        f"{direct_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Standard deviation: "
        f"{direct_standard_deviation_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Relative uncertainty: "
        f"{openmc_result.relative_uncertainty:.4%}"
    )

    print("-" * 72)
    print("Spectrum-folded cross-check:")

    print(
        "  Folded response: "
        f"{folded_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Difference from direct tally: "
        f"{direct_vs_folded_difference:+.4%}"
    )

    print("-" * 72)
    print("Matched deterministic comparison:")

    print(
        "  Deterministic uncollided: "
        f"{deterministic_uncollided_microgy_per_h:.10e} µGy/h"
    )

    if deterministic_gp_microgy_per_h is not None:
        print(
            "  Deterministic G-P-adjusted: "
            f"{deterministic_gp_microgy_per_h:.10e} µGy/h"
        )

    print(
        "  OpenMC direct response: "
        f"{direct_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Difference from uncollided: "
        f"{comparison.relative_difference_from_uncollided:+.4%}"
    )

    if comparison.relative_difference_from_gp is not None:
        print(
            "  Difference from G-P: "
            f"{comparison.relative_difference_from_gp:+.4%}"
        )

    print(
        "  Observed Monte Carlo buildup ratio: "
        f"{comparison.observed_monte_carlo_buildup_ratio:.6f}"
    )

    print("-" * 72)
    print("V1.13 acceptance checks:")

    print(
        "  Required uncertainty <= 5%: "
        f"{'PASS' if required_uncertainty_pass else 'FAIL'}"
    )

    print(
        "  Preferred uncertainty <= 2%: "
        f"{'PASS' if preferred_uncertainty_pass else 'NOT MET'}"
    )

    print(
        "  Direct-versus-folded <= 2%: "
        f"{'PASS' if folded_check_pass else 'FAIL'}"
    )

    print("-" * 72)
    print("Saved production outputs:")

    print(
        "  OpenMC response JSON: "
        f"{output_paths.response_json_path}"
    )

    print(
        "  Comparison JSON: "
        f"{output_paths.comparison_json_path}"
    )

    print(
        "  Photon spectrum CSV: "
        f"{output_paths.spectrum_csv_path}"
    )

    print("-" * 72)
    print(
        "Intermediate checkpoint convergence was not available "
        "from this run. The final five-million-history result "
        "was processed successfully."
    )

    print("=" * 72)
    print()

    if not required_uncertainty_pass:
        return 2

    if not folded_check_pass:
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )