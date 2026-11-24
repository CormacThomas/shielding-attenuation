# Run and inspect the first V1.13 OpenMC photon-transport calculation.
#
# This development run:
#   - uses the 1 cm Lead development scenario;
#   - transports 100,000 source photons;
#   - writes the final statepoint;
#   - retrieves both official V1.13 tallies;
#   - inspects raw tally shapes and values;
#   - performs no physical normalization yet.
#
# Run inside the OpenMC Docker environment:
#
#   python examples/openmc_v113_development_run.py
#
# The run directory is recreated each time.


from __future__ import annotations


from pathlib import Path
import shutil
import sys
import time


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


from openmc_model_builder import (
    build_openmc_v113_model,
    load_openmc_module,
)
from openmc_settings_io import (
    load_openmc_settings,
)
from openmc_tally_builder import (
    DIRECT_RESPONSE_TALLY_ID,
    SPECTRUM_TALLY_ID,
    attach_v113_benchmark_tallies,
)
from scenario_io import (
    load_scenario,
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

RUN_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "development_run"
    / "cs137_v113_development__v113_development"
)


def prepare_run_directory(
    run_directory: Path,
) -> None:
    # Remove all files from a previous development run so the final statepoint
    # and XML inputs cannot be confused with older results.

    if run_directory.exists():
        shutil.rmtree(
            run_directory
        )

    run_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


def resolve_statepoint_path(
    returned_statepoint_path: Path,
    run_directory: Path,
) -> Path:
    # Model.run() normally returns the complete statepoint path. This helper
    # also handles an implementation returning only a filename.

    candidate_paths = [
        returned_statepoint_path,
        run_directory
        / returned_statepoint_path.name,
    ]

    for candidate_path in candidate_paths:
        if candidate_path.is_file():
            return candidate_path.resolve()

    raise RuntimeError(
        "OpenMC reported a final statepoint, but the "
        "file could not be located. Returned path: "
        f"{returned_statepoint_path}"
    )


def require_finite_nonnegative_array(
    array,
    description: str,
) -> None:
    # NumPy is supplied by the OpenMC environment, but this script avoids a
    # separate static import and instead uses the array's vectorized methods.

    if not array.size > 0:
        raise RuntimeError(
            f"{description} is empty."
        )

    if not array.dtype.kind in (
        "f",
        "i",
        "u",
    ):
        raise RuntimeError(
            f"{description} is not numerical."
        )

    if not (
        array
        == array
    ).all():
        raise RuntimeError(
            f"{description} contains NaN values."
        )

    if not (
        abs(array)
        != float("inf")
    ).all():
        raise RuntimeError(
            f"{description} contains infinite values."
        )

    if not (
        array >= 0
    ).all():
        raise RuntimeError(
            f"{description} contains negative values."
        )


def print_top_spectrum_bins(
    energy_boundaries_ev: list[float],
    spectrum_means,
    spectrum_standard_deviations,
    maximum_bin_count: int = 10,
) -> None:
    # Print the spectrum bins with the largest raw track-length scores.
    #
    # With the cell and particle filters each having one bin, flattening the
    # reshaped result leaves the configured energy-bin order unchanged.

    ranked_indices = sorted(
        range(
            len(spectrum_means)
        ),
        key=lambda index: (
            spectrum_means[index]
        ),
        reverse=True,
    )

    print(
        "Largest raw spectrum bins:"
    )

    printed_count = 0

    for energy_bin_index in ranked_indices:
        mean = float(
            spectrum_means[
                energy_bin_index
            ]
        )

        standard_deviation = float(
            spectrum_standard_deviations[
                energy_bin_index
            ]
        )

        if mean <= 0:
            continue

        lower_energy_ev = (
            energy_boundaries_ev[
                energy_bin_index
            ]
        )

        upper_energy_ev = (
            energy_boundaries_ev[
                energy_bin_index + 1
            ]
        )

        relative_uncertainty = (
            standard_deviation / mean
            if mean > 0
            else 0.0
        )

        print(
            f"  Bin {energy_bin_index + 1:02d}: "
            f"{lower_energy_ev:10.1f} to "
            f"{upper_energy_ev:10.1f} eV | "
            f"mean {mean:.8e} cm/source | "
            f"std. dev. {standard_deviation:.8e} | "
            f"relative uncertainty "
            f"{relative_uncertainty:.4%}"
        )

        printed_count += 1

        if printed_count >= maximum_bin_count:
            break

    if printed_count == 0:
        raise RuntimeError(
            "No positive spectrum bins were observed."
        )


def main() -> int:
    openmc_module = load_openmc_module()

    scenario = load_scenario(
        SCENARIO_PATH
    )

    settings_profile = (
        load_openmc_settings(
            SETTINGS_PATH
        )
    )

    model_build_result = (
        build_openmc_v113_model(
            scenario=scenario,
            settings_profile=(
                settings_profile
            ),
            evaluation_shell_thickness_cm=1.0,
        )
    )

    tally_build_result = (
        attach_v113_benchmark_tallies(
            model_build_result=(
                model_build_result
            ),
            settings_profile=(
                settings_profile
            ),
        )
    )

    prepare_run_directory(
        RUN_DIRECTORY
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 DEVELOPMENT TRANSPORT RUN")
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
        "Particles per batch: "
        f"{settings_profile.particles_per_batch}"
    )

    print(
        "Batches: "
        f"{settings_profile.batches}"
    )

    print(
        "Total source histories: "
        f"{settings_profile.total_source_particles}"
    )

    print(
        "Threads: "
        f"{settings_profile.threads}"
    )

    print(
        "Run directory: "
        f"{RUN_DIRECTORY}"
    )

    print("-" * 72)
    print(
        "Beginning OpenMC photon transport."
    )
    print("-" * 72)

    start_time = time.perf_counter()

    returned_statepoint_path = (
        model_build_result
        .model
        .run(
            threads=(
                settings_profile.threads
            ),
            output=True,
            cwd=RUN_DIRECTORY,
            export_model_xml=False,
        )
    )

    runtime_seconds = (
        time.perf_counter()
        - start_time
    )

    if returned_statepoint_path is None:
        raise RuntimeError(
            "OpenMC completed without returning a "
            "statepoint path."
        )

    statepoint_path = (
        resolve_statepoint_path(
            returned_statepoint_path=Path(
                returned_statepoint_path
            ),
            run_directory=RUN_DIRECTORY,
        )
    )

    statepoint = openmc_module.StatePoint(
        statepoint_path,
        autolink=False,
    )

    try:
        if not statepoint.tallies_present:
            raise RuntimeError(
                "The OpenMC statepoint contains no "
                "user-defined tally results."
            )

        if not statepoint.photon_transport:
            raise RuntimeError(
                "The statepoint does not report photon "
                "transport as active."
            )

        if (
            statepoint.current_batch
            != settings_profile.batches
        ):
            raise RuntimeError(
                "Unexpected final statepoint batch: "
                f"expected {settings_profile.batches}, "
                f"found {statepoint.current_batch}."
            )

        if (
            statepoint.n_particles
            != settings_profile
            .particles_per_batch
        ):
            raise RuntimeError(
                "Unexpected particles per batch in "
                "the statepoint."
            )

        spectrum_tally = (
            statepoint.get_tally(
                id=SPECTRUM_TALLY_ID
            )
        )

        direct_response_tally = (
            statepoint.get_tally(
                id=(
                    DIRECT_RESPONSE_TALLY_ID
                )
            )
        )

        spectrum_mean_reshaped = (
            spectrum_tally
            .get_reshaped_data(
                value="mean"
            )
        )

        spectrum_std_dev_reshaped = (
            spectrum_tally
            .get_reshaped_data(
                value="std_dev"
            )
        )

        direct_mean_reshaped = (
            direct_response_tally
            .get_reshaped_data(
                value="mean"
            )
        )

        direct_std_dev_reshaped = (
            direct_response_tally
            .get_reshaped_data(
                value="std_dev"
            )
        )

        require_finite_nonnegative_array(
            spectrum_mean_reshaped,
            "Raw spectrum means",
        )

        require_finite_nonnegative_array(
            spectrum_std_dev_reshaped,
            "Raw spectrum standard deviations",
        )

        require_finite_nonnegative_array(
            direct_mean_reshaped,
            "Raw direct-response mean",
        )

        require_finite_nonnegative_array(
            direct_std_dev_reshaped,
            "Raw direct-response standard deviation",
        )

        spectrum_means = (
            spectrum_mean_reshaped
            .reshape(-1)
        )

        spectrum_standard_deviations = (
            spectrum_std_dev_reshaped
            .reshape(-1)
        )

        direct_means = (
            direct_mean_reshaped
            .reshape(-1)
        )

        direct_standard_deviations = (
            direct_std_dev_reshaped
            .reshape(-1)
        )

        expected_energy_bin_count = (
            len(
                settings_profile
                .energy_bin_boundaries_ev
            )
            - 1
        )

        if (
            spectrum_means.size
            != expected_energy_bin_count
        ):
            raise RuntimeError(
                "Unexpected flattened spectrum size: "
                f"expected {expected_energy_bin_count}, "
                f"found {spectrum_means.size}."
            )

        if (
            spectrum_standard_deviations.size
            != expected_energy_bin_count
        ):
            raise RuntimeError(
                "Unexpected flattened spectrum "
                "uncertainty size."
            )

        if direct_means.size != 1:
            raise RuntimeError(
                "The direct-response tally must produce "
                "exactly one value."
            )

        if (
            direct_standard_deviations.size
            != 1
        ):
            raise RuntimeError(
                "The direct-response tally must produce "
                "exactly one uncertainty value."
            )

        raw_direct_response_mean = float(
            direct_means[0]
        )

        raw_direct_response_standard_deviation = float(
            direct_standard_deviations[0]
        )

        if raw_direct_response_mean <= 0:
            raise RuntimeError(
                "The direct-response tally did not "
                "produce a positive score."
            )

        raw_direct_relative_uncertainty = (
            raw_direct_response_standard_deviation
            / raw_direct_response_mean
        )

        total_raw_spectrum_mean = float(
            spectrum_means.sum()
        )

        total_raw_spectrum_standard_deviation_quadrature = float(
            (
                (
                    spectrum_standard_deviations
                    ** 2
                )
                .sum()
            )
            ** 0.5
        )

        positive_spectrum_bin_count = int(
            (
                spectrum_means > 0
            ).sum()
        )

        source_energy_ev = (
            model_build_result
            .source_energies_ev[0]
        )

        source_bin_index = None

        for energy_bin_index in range(
            expected_energy_bin_count
        ):
            lower_energy_ev = (
                settings_profile
                .energy_bin_boundaries_ev[
                    energy_bin_index
                ]
            )

            upper_energy_ev = (
                settings_profile
                .energy_bin_boundaries_ev[
                    energy_bin_index + 1
                ]
            )

            if (
                lower_energy_ev
                <= source_energy_ev
                < upper_energy_ev
            ):
                source_bin_index = (
                    energy_bin_index
                )

                break

        if source_bin_index is None:
            raise RuntimeError(
                "The source energy was not contained "
                "in the spectrum boundaries."
            )

        source_bin_mean = float(
            spectrum_means[
                source_bin_index
            ]
        )

        source_bin_standard_deviation = float(
            spectrum_standard_deviations[
                source_bin_index
            ]
        )

        if source_bin_mean <= 0:
            raise RuntimeError(
                "The configured Cs-137 source-energy "
                "bin did not receive a positive score."
            )

        source_bin_lower_energy_ev = (
            settings_profile
            .energy_bin_boundaries_ev[
                source_bin_index
            ]
        )

        source_bin_upper_energy_ev = (
            settings_profile
            .energy_bin_boundaries_ev[
                source_bin_index + 1
            ]
        )

        print()
        print("=" * 72)
        print("OPENMC V1.13 DEVELOPMENT RUN PASSED")
        print("=" * 72)

        print(
            "OpenMC version: "
            f"{model_build_result.openmc_version}"
        )

        print(
            "Statepoint: "
            f"{statepoint_path}"
        )

        print(
            "Completed batch: "
            f"{statepoint.current_batch}"
        )

        print(
            "Tally realizations: "
            f"{statepoint.n_realizations}"
        )

        print(
            "Measured wall-clock runtime: "
            f"{runtime_seconds:.6f} s"
        )

        print("-" * 72)
        print("Raw spectrum tally:")

        print(
            "  Stored array shape: "
            f"{spectrum_tally.mean.shape}"
        )

        print(
            "  Reshaped array shape: "
            f"{spectrum_mean_reshaped.shape}"
        )

        print(
            "  Flattened energy bins: "
            f"{spectrum_means.size}"
        )

        print(
            "  Positive energy bins: "
            f"{positive_spectrum_bin_count}"
        )

        print(
            "  Total raw track-length mean: "
            f"{total_raw_spectrum_mean:.10e} "
            "cm/source"
        )

        print(
            "  Quadrature raw uncertainty: "
            f"{total_raw_spectrum_standard_deviation_quadrature:.10e}"
        )

        print(
            "  Cs-137 source-energy bin: "
            f"{source_bin_lower_energy_ev:.1f} to "
            f"{source_bin_upper_energy_ev:.1f} eV"
        )

        print(
            "  Cs-137 source-bin raw mean: "
            f"{source_bin_mean:.10e} cm/source"
        )

        print(
            "  Cs-137 source-bin raw std. dev.: "
            f"{source_bin_standard_deviation:.10e}"
        )

        print("-" * 72)

        print_top_spectrum_bins(
            energy_boundaries_ev=(
                settings_profile
                .energy_bin_boundaries_ev
            ),
            spectrum_means=(
                spectrum_means
            ),
            spectrum_standard_deviations=(
                spectrum_standard_deviations
            ),
        )

        print("-" * 72)
        print("Raw direct-response tally:")

        print(
            "  Stored array shape: "
            f"{direct_response_tally.mean.shape}"
        )

        print(
            "  Reshaped array shape: "
            f"{direct_mean_reshaped.shape}"
        )

        print(
            "  Raw mean: "
            f"{raw_direct_response_mean:.10e} "
            "Gy cm^3/source"
        )

        print(
            "  Raw standard deviation: "
            f"{raw_direct_response_standard_deviation:.10e} "
            "Gy cm^3/source"
        )

        print(
            "  Raw relative uncertainty: "
            f"{raw_direct_relative_uncertainty:.4%}"
        )

        print("-" * 72)

        print(
            "These are raw OpenMC values. No shell-volume "
            "or physical-source-rate normalization has "
            "been applied."
        )

        print("=" * 72)
        print()

    finally:
        statepoint.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )