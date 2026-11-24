# Process the completed V1.13 development statepoint.
#
# This script does not rerun OpenMC. It reads the existing statepoint and:
#
#   - normalizes the photon spectrum;
#   - normalizes the direct air-kerma response;
#   - folds the spectrum through the dry-air response function;
#   - creates the matched deterministic shell-average result;
#   - compares OpenMC with deterministic uncollided and G-P responses.
#
# Run inside Docker:
#
#   python examples/openmc_v113_process_development.py


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


if str(
    SOURCE_DIRECTORY
) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )

from openmc_result_io import (
    save_openmc_benchmark_outputs,
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
    / "cs137_v113_development.json"
)

SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v113_development.json"
)

STATEPOINT_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "development_run"
    / "cs137_v113_development__v113_development"
    / "statepoint.10.h5"
)

PROCESSED_OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "development_run"
    / "cs137_v113_development__v113_development"
    / "processed"
)


DIRECT_VS_FOLDED_TOLERANCE = 0.02

REQUIRED_RELATIVE_UNCERTAINTY = 0.05

PREFERRED_RELATIVE_UNCERTAINTY = 0.02


def print_largest_physical_spectrum_bins(
    energy_bin_results,
    maximum_bin_count: int = 10,
) -> None:
    ranked_results = sorted(
        energy_bin_results,
        key=lambda result: (
            result
            .physical_fluence_rate_mean_per_cm2_s
        ),
        reverse=True,
    )

    print(
        "Largest physical spectrum bins:"
    )

    printed_count = 0

    for result in ranked_results:
        if (
            result
            .physical_fluence_rate_mean_per_cm2_s
            <= 0
        ):
            continue

        mean = (
            result
            .physical_fluence_rate_mean_per_cm2_s
        )

        standard_deviation = (
            result
            .physical_fluence_rate_standard_deviation_per_cm2_s
        )

        relative_uncertainty = (
            standard_deviation / mean
        )

        contribution_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                result
                .air_kerma_rate_contribution_gy_per_s
            )
        )

        print(
            "  "
            f"{result.lower_energy_ev:10.1f} to "
            f"{result.upper_energy_ev:10.1f} eV | "
            f"{mean:.8e} photons/cm^2/s | "
            f"rel. unc. {relative_uncertainty:.4%} | "
            f"{contribution_microgy_per_h:.8e} µGy/h"
        )

        printed_count += 1

        if printed_count >= maximum_bin_count:
            break


def main() -> int:
    scenario = load_scenario(
        SCENARIO_PATH
    )

    settings_profile = (
        load_openmc_settings(
            SETTINGS_PATH
        )
    )

    openmc_result = (
        process_openmc_v113_statepoint(
            statepoint_path=(
                STATEPOINT_PATH
            ),
            scenario=scenario,
            settings_profile=(
                settings_profile
            ),
            evaluation_shell_thickness_cm=1.0,
        )
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

    comparison = (
        DeterministicOpenMCComparison(
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

    output_paths = (
        save_openmc_benchmark_outputs(
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

    print()
    print("=" * 72)
    print("OPENMC V1.13 DEVELOPMENT STATEPOINT PROCESSING")
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
        "Statepoint: "
        f"{STATEPOINT_PATH}"
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
        f"{openmc_result.physical_source_rate_per_s:.8e} "
        "photons/s"
    )

    print("-" * 72)
    print("Physical photon spectrum:")

    print(
        "  Energy bins: "
        f"{len(openmc_result.energy_bin_results)}"
    )

    print(
        "  Total photon fluence rate: "
        f"{total_physical_fluence_rate:.10e} "
        "photons/cm^2/s"
    )

    print("-" * 72)

    print_largest_physical_spectrum_bins(
        openmc_result.energy_bin_results
    )

    print("-" * 72)
    print("OpenMC direct response:")

    print(
        "  Raw tally mean: "
        f"{openmc_result.raw_direct_response_mean_gy_cm3_per_source:.10e} "
        "Gy cm^3/source"
    )

    print(
        "  Response per source: "
        f"{openmc_result.direct_response_mean_gy_per_source:.10e} "
        "Gy/source"
    )

    print(
        "  Physical response: "
        f"{openmc_result.direct_response_rate_gy_per_s:.10e} "
        "Gy/s"
    )

    print(
        "  Physical response: "
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
        f"{openmc_result.spectrum_folded_response_rate_gy_per_s:.10e} "
        "Gy/s"
    )

    print(
        "  Folded response: "
        f"{folded_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Folded difference from direct tally: "
        f"{direct_vs_folded_difference:+.4%}"
    )

    print(
        "  Absolute folded difference: "
        f"{abs(direct_vs_folded_difference):.4%}"
    )

    print(
        "  V1.13 folded tolerance: "
        f"{DIRECT_VS_FOLDED_TOLERANCE:.2%}"
    )

    print(
        "  Folded cross-check status: "
        f"{'PASS' if abs(direct_vs_folded_difference) <= DIRECT_VS_FOLDED_TOLERANCE else 'REVIEW'}"
    )

    print("-" * 72)
    print("Matched deterministic comparison:")

    print(
        "  Deterministic uncollided response: "
        f"{deterministic_uncollided_microgy_per_h:.10e} µGy/h"
    )

    if (
        deterministic_gp_microgy_per_h
        is not None
    ):
        print(
            "  Deterministic G-P-adjusted response: "
            f"{deterministic_gp_microgy_per_h:.10e} µGy/h"
        )

    print(
        "  OpenMC direct response: "
        f"{direct_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  OpenMC difference from uncollided: "
        f"{comparison.relative_difference_from_uncollided:+.4%}"
    )

    if (
        comparison
        .relative_difference_from_gp
        is not None
    ):
        print(
            "  OpenMC difference from G-P: "
            f"{comparison.relative_difference_from_gp:+.4%}"
        )

    print(
        "  Observed Monte Carlo buildup ratio: "
        f"{comparison.observed_monte_carlo_buildup_ratio:.6f}"
    )

    print("-" * 72)
    print("Development statistical checks:")

    print(
        "  Required uncertainty threshold: "
        f"{REQUIRED_RELATIVE_UNCERTAINTY:.2%}"
    )

    print(
        "  Required uncertainty status: "
        f"{'PASS' if openmc_result.relative_uncertainty <= REQUIRED_RELATIVE_UNCERTAINTY else 'FAIL'}"
    )

    print(
        "  Preferred uncertainty threshold: "
        f"{PREFERRED_RELATIVE_UNCERTAINTY:.2%}"
    )

    print(
        "  Preferred uncertainty status: "
        f"{'PASS' if openmc_result.relative_uncertainty <= PREFERRED_RELATIVE_UNCERTAINTY else 'NOT YET'}"
    )

    print("=" * 72)
    print()

    return 0

    print("-" * 72)
    print("Saved processed outputs:")

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


if __name__ == "__main__":
    raise SystemExit(
        main()
    )