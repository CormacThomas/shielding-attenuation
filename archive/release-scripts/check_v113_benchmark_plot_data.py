# Validate the processed V1.13 benchmark outputs before figure generation.
#
# This script contains no OpenMC dependency and can be run from the normal
# Windows Python environment.
#
# Run from the repository root:
#
#   python examples/check_v113_benchmark_plot_data.py


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


from openmc_benchmark_plot_data import (
    create_openmc_benchmark_plot_data,
)


PROCESSED_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "processed"
    / "final"
)


def main() -> int:
    plot_data = (
        create_openmc_benchmark_plot_data(
            response_json_path=(
                PROCESSED_DIRECTORY
                / "openmc_response.json"
            ),
            comparison_json_path=(
                PROCESSED_DIRECTORY
                / (
                    "deterministic_openmc_"
                    "comparison.json"
                )
            ),
            spectrum_csv_path=(
                PROCESSED_DIRECTORY
                / "photon_spectrum.csv"
            ),
        )
    )

    print()
    print("=" * 72)
    print("V1.13 BENCHMARK PLOT-DATA CHECK PASSED")
    print("=" * 72)

    print(
        "Scenario ID: "
        f"{plot_data.scenario_id}"
    )

    print(
        "Settings profile: "
        f"{plot_data.settings_profile_name}"
    )

    print(
        "Evaluation shell: "
        f"{plot_data.evaluation_shell_inner_radius_cm:.6f} "
        "to "
        f"{plot_data.evaluation_shell_outer_radius_cm:.6f} cm"
    )

    print(
        "Spectrum bins: "
        f"{len(plot_data.spectrum_bins)}"
    )

    print(
        "Positive spectrum bins: "
        f"{plot_data.positive_spectrum_bin_count}"
    )

    print(
        "Total photon fluence rate: "
        f"{plot_data.total_photon_fluence_rate_per_cm2_s:.10e} "
        "photons/cm^2/s"
    )

    print("-" * 72)

    print(
        "Deterministic uncollided: "
        f"{plot_data.deterministic_uncollided_microgy_per_h:.10e} "
        "microGy/h"
    )

    if (
        plot_data
        .deterministic_gp_microgy_per_h
        is not None
    ):
        print(
            "Deterministic G-P-adjusted: "
            f"{plot_data.deterministic_gp_microgy_per_h:.10e} "
            "microGy/h"
        )

    print(
        "OpenMC direct: "
        f"{plot_data.openmc_direct_microgy_per_h:.10e} "
        "microGy/h"
    )

    print(
        "OpenMC folded: "
        f"{plot_data.openmc_folded_microgy_per_h:.10e} "
        "microGy/h"
    )

    print(
        "OpenMC relative uncertainty: "
        f"{plot_data.openmc_relative_uncertainty:.4%}"
    )

    print(
        "Direct-versus-folded difference: "
        f"{plot_data.direct_vs_folded_relative_difference:+.4%}"
    )

    print(
        "Observed Monte Carlo buildup ratio: "
        f"{plot_data.observed_monte_carlo_buildup_ratio:.6f}"
    )

    print("-" * 72)

    print(
        "Required uncertainty check: "
        f"{'PASS' if plot_data.required_uncertainty_pass else 'FAIL'}"
    )

    print(
        "Preferred uncertainty check: "
        f"{'PASS' if plot_data.preferred_uncertainty_pass else 'FAIL'}"
    )

    print(
        "Direct-versus-folded check: "
        f"{'PASS' if plot_data.direct_vs_folded_pass else 'FAIL'}"
    )

    print("=" * 72)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )