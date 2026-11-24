# Run, process, and preserve the official V1.13 OpenMC production benchmark.
#
# Production configuration:
#   - centered Cs-137 photon source
#   - 5.0 cm spherical Lead shield
#   - 99.5 to 100.5 cm evaluation shell
#   - 5,000,000 total photon histories
#   - statepoint checkpoints at batches 25, 50, 75, and 100
#
# The script:
#   1. constructs the model and tallies;
#   2. runs OpenMC;
#   3. creates a reproducibility manifest;
#   4. processes every cumulative statepoint;
#   5. saves checkpoint and final processed outputs;
#   6. writes a convergence CSV;
#   7. applies the V1.13 statistical acceptance checks.
#
# Run inside Docker:
#
#   python examples/openmc_v113_production_run.py


from __future__ import annotations


import csv
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
import platform
import shutil
import subprocess
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


from fixed_shield_response import (
    calculate_fixed_shield_response,
)
from openmc_model_builder import (
    build_openmc_v113_model,
)
from openmc_models import (
    DeterministicOpenMCComparison,
    OpenMCResponseResult,
    OpenMCRunManifest,
)
from openmc_response import (
    calculate_observed_monte_carlo_buildup_ratio,
    calculate_relative_difference,
    create_deterministic_shell_average_result,
)
from openmc_result_io import (
    save_openmc_benchmark_outputs,
    save_openmc_run_manifest,
)
from openmc_settings_io import (
    load_openmc_settings,
)
from openmc_statepoint_processor import (
    process_openmc_v113_statepoint,
)
from openmc_tally_builder import (
    attach_v113_benchmark_tallies,
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

RUN_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_run"
    / "cs137_v113_production__v113_production"
)

PROCESSED_DIRECTORY = (
    RUN_DIRECTORY
    / "processed"
)


DIRECT_VS_FOLDED_TOLERANCE = 0.02

REQUIRED_RELATIVE_UNCERTAINTY = 0.05

PREFERRED_RELATIVE_UNCERTAINTY = 0.02


def prepare_run_directory(
    run_directory: Path,
) -> None:
    # Remove all files from a previous production run so no statepoint or
    # processed result can be confused with a newer execution.

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
    # Handle either an absolute returned path or a filename relative to the
    # configured OpenMC working directory.

    candidate_paths = [
        returned_statepoint_path,
        run_directory
        / returned_statepoint_path.name,
    ]

    for candidate_path in candidate_paths:
        if candidate_path.is_file():
            return candidate_path.resolve()

    raise RuntimeError(
        "OpenMC reported a final statepoint, but "
        "the file could not be located. Returned path: "
        f"{returned_statepoint_path}"
    )


def get_git_commit(
    repository_root: Path,
) -> str | None:
    # Preserve the current Git commit when Git is available. An uncommitted
    # working tree is still possible, so this does not replace preserving the
    # exact scenario, configuration, and processed outputs.

    try:
        completed_process = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )

    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
    ):
        return None

    commit = (
        completed_process.stdout.strip()
    )

    if commit == "":
        return None

    return commit


def create_matched_comparison(
    deterministic_result,
    openmc_result: OpenMCResponseResult,
) -> DeterministicOpenMCComparison:
    # Create one formally matched deterministic-versus-OpenMC comparison.

    deterministic_uncollided = (
        deterministic_result
        .total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
    )

    deterministic_gp = (
        deterministic_result
        .total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    openmc_response = (
        openmc_result
        .direct_response_rate_gy_per_s
    )

    relative_difference_from_gp = None

    if deterministic_gp is not None:
        relative_difference_from_gp = (
            calculate_relative_difference(
                comparison_value=(
                    openmc_response
                ),
                reference_value=(
                    deterministic_gp
                ),
            )
        )

    return DeterministicOpenMCComparison(
        deterministic_result=(
            deterministic_result
        ),
        openmc_result=openmc_result,
        relative_difference_from_uncollided=(
            calculate_relative_difference(
                comparison_value=(
                    openmc_response
                ),
                reference_value=(
                    deterministic_uncollided
                ),
            )
        ),
        relative_difference_from_gp=(
            relative_difference_from_gp
        ),
        observed_monte_carlo_buildup_ratio=(
            calculate_observed_monte_carlo_buildup_ratio(
                openmc_response=(
                    openmc_response
                ),
                deterministic_uncollided_response=(
                    deterministic_uncollided
                ),
            )
        ),
    )


def calculate_direct_vs_folded_difference(
    result: OpenMCResponseResult,
) -> float:
    return calculate_relative_difference(
        comparison_value=(
            result
            .spectrum_folded_response_rate_gy_per_s
        ),
        reference_value=(
            result.direct_response_rate_gy_per_s
        ),
    )


def save_convergence_csv(
    checkpoint_records: list[
        tuple[
            int,
            OpenMCResponseResult,
            DeterministicOpenMCComparison,
        ]
    ],
    particles_per_batch: int,
    output_path: Path,
) -> Path:
    # Save cumulative checkpoint behavior relative to the final production
    # statepoint.

    if particles_per_batch <= 0:
        raise ValueError(
            "Convergence output particles per batch "
            "must be greater than zero."
        )

    if len(checkpoint_records) == 0:
        raise ValueError(
            "Production convergence output requires "
            "at least one checkpoint."
        )

    final_result = (
        checkpoint_records[-1][1]
    )

    final_response = (
        final_result
        .direct_response_rate_gy_per_s
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "batch",
        "total_histories",
        "direct_response_rate_gy_per_s",
        "direct_response_rate_microgy_per_h",
        "standard_deviation_gy_per_s",
        "standard_deviation_microgy_per_h",
        "relative_uncertainty",
        "spectrum_folded_response_rate_gy_per_s",
        "direct_vs_folded_relative_difference",
        "relative_difference_from_final_response",
        "relative_difference_from_deterministic_uncollided",
        "relative_difference_from_deterministic_gp",
        "observed_monte_carlo_buildup_ratio",
    ]

    with output_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for (
            batch,
            result,
            comparison,
        ) in checkpoint_records:
            relative_difference_from_final = (
                calculate_relative_difference(
                    comparison_value=(
                        result
                        .direct_response_rate_gy_per_s
                    ),
                    reference_value=(
                        final_response
                    ),
                )
            )

            writer.writerow(
                {
                    "batch": batch,
                    "total_histories": (
                        batch
                        * particles_per_batch
                    ),
                    "direct_response_rate_gy_per_s": (
                        result
                        .direct_response_rate_gy_per_s
                    ),
                    "direct_response_rate_microgy_per_h": (
                        convert_gy_per_s_to_microgy_per_h(
                            result
                            .direct_response_rate_gy_per_s
                        )
                    ),
                    "standard_deviation_gy_per_s": (
                        result
                        .direct_response_rate_standard_deviation_gy_per_s
                    ),
                    "standard_deviation_microgy_per_h": (
                        convert_gy_per_s_to_microgy_per_h(
                            result
                            .direct_response_rate_standard_deviation_gy_per_s
                        )
                    ),
                    "relative_uncertainty": (
                        result.relative_uncertainty
                    ),
                    "spectrum_folded_response_rate_gy_per_s": (
                        result
                        .spectrum_folded_response_rate_gy_per_s
                    ),
                    "direct_vs_folded_relative_difference": (
                        calculate_direct_vs_folded_difference(
                            result
                        )
                    ),
                    "relative_difference_from_final_response": (
                        relative_difference_from_final
                    ),
                    "relative_difference_from_deterministic_uncollided": (
                        comparison
                        .relative_difference_from_uncollided
                    ),
                    "relative_difference_from_deterministic_gp": (
                        comparison
                        .relative_difference_from_gp
                    ),
                    "observed_monte_carlo_buildup_ratio": (
                        comparison
                        .observed_monte_carlo_buildup_ratio
                    ),
                }
            )

    return output_path



def main() -> int:
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

    attach_v113_benchmark_tallies(
        model_build_result=(
            model_build_result
        ),
        settings_profile=(
            settings_profile
        ),
    )

    prepare_run_directory(
        RUN_DIRECTORY
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 PRODUCTION BENCHMARK RUN")
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
        "Shield thickness: "
        f"{scenario.geometry.total_shield_thickness_cm:.6f} cm"
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
        "Statepoint checkpoints: "
        f"{settings_profile.statepoint_batches}"
    )

    print(
        "Run directory: "
        f"{RUN_DIRECTORY}"
    )

    print("-" * 72)
    print(
        "Beginning official OpenMC production transport."
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
            "final statepoint path."
        )

    final_statepoint_path = (
        resolve_statepoint_path(
            returned_statepoint_path=Path(
                returned_statepoint_path
            ),
            run_directory=RUN_DIRECTORY,
        )
    )

    checkpoint_paths: dict[
        int,
        Path,
    ] = {}

    missing_checkpoint_batches: list[
        int
    ] = []

    for batch in (
        settings_profile
        .statepoint_batches
    ):
        checkpoint_path = (
            RUN_DIRECTORY
            / f"statepoint.{batch}.h5"
        )

        if checkpoint_path.is_file():
            checkpoint_paths[
                batch
            ] = checkpoint_path

        elif batch == settings_profile.batches:
            # Model.run() already resolved and verified the final statepoint.
            checkpoint_paths[
                batch
            ] = final_statepoint_path

        else:
            missing_checkpoint_batches.append(
                batch
            )

    # These checks must be OUTSIDE the for-loop.
    if (
        settings_profile.batches
        not in checkpoint_paths
    ):
        raise RuntimeError(
            "The final production statepoint "
            "could not be located."
        )

    if missing_checkpoint_batches:
        print(
            "Warning: intermediate OpenMC statepoints "
            "were not available for batches "
            f"{missing_checkpoint_batches}. "
            "The final production statepoint will still "
            "be processed."
        )

    manifest = OpenMCRunManifest(
        scenario_id=scenario.scenario_id,
        settings_profile_name=(
            settings_profile.profile_name
        ),
        openmc_version=(
            model_build_result.openmc_version
        ),
        python_version=(
            platform.python_version()
        ),
        cross_section_library=(
            model_build_result
            .cross_sections_path
        ),
        electron_treatment=(
            settings_profile
            .electron_treatment
        ),
        atomic_relaxation=(
            settings_profile
            .atomic_relaxation
        ),
        photon_cutoff_energy_ev=(
            settings_profile
            .photon_cutoff_energy_ev
        ),
        particles_per_batch=(
            settings_profile
            .particles_per_batch
        ),
        batches=settings_profile.batches,
        total_source_particles=(
            settings_profile
            .total_source_particles
        ),
        random_seed=(
            settings_profile.random_seed
        ),
        threads=settings_profile.threads,
        runtime_seconds=runtime_seconds,
        statepoint_filename=(
            final_statepoint_path.name
        ),
        execution_timestamp_utc=(
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        git_commit=get_git_commit(
            REPOSITORY_ROOT
        ),
    )

    manifest_path = (
        save_openmc_run_manifest(
            manifest=manifest,
            output_path=(
                RUN_DIRECTORY
                / "run_manifest.json"
            ),
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

    checkpoint_records: list[
        tuple[
            int,
            OpenMCResponseResult,
            DeterministicOpenMCComparison,
        ]
    ] = []

    for batch in sorted(
        checkpoint_paths
    ):
        openmc_result = (
            process_openmc_v113_statepoint(
                statepoint_path=(
                    checkpoint_paths[batch]
                ),
                scenario=scenario,
                settings_profile=(
                    settings_profile
                ),
                evaluation_shell_thickness_cm=1.0,
                expected_batch=batch,
            )
        )

        comparison = (
            create_matched_comparison(
                deterministic_result=(
                    deterministic_result
                ),
                openmc_result=(
                    openmc_result
                ),
            )
        )

        checkpoint_records.append(
            (
                batch,
                openmc_result,
                comparison,
            )
        )

        checkpoint_output_directory = (
            PROCESSED_DIRECTORY
            / "checkpoints"
            / f"batch_{batch:03d}"
        )

        save_openmc_benchmark_outputs(
            openmc_result=openmc_result,
            comparison=comparison,
            output_directory=(
                checkpoint_output_directory
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

    (
        final_batch,
        final_result,
        final_comparison,
    ) = checkpoint_records[-1]

    if (
        final_batch
        != settings_profile.batches
    ):
        raise RuntimeError(
            "The final processed checkpoint does not "
            "match the configured production batch count."
        )

    final_output_paths = (
        save_openmc_benchmark_outputs(
            openmc_result=final_result,
            comparison=final_comparison,
            output_directory=(
                PROCESSED_DIRECTORY
                / "final"
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

    convergence_path = (
        save_convergence_csv(
            checkpoint_records=(
                checkpoint_records
            ),
            particles_per_batch=(
                settings_profile
                .particles_per_batch
            ),
            output_path=(
                PROCESSED_DIRECTORY
                / "convergence.csv"
            ),
        )
    )

    final_direct_vs_folded_difference = (
        calculate_direct_vs_folded_difference(
            final_result
        )
    )

    final_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            final_result
            .direct_response_rate_gy_per_s
        )
    )

    final_standard_deviation_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            final_result
            .direct_response_rate_standard_deviation_gy_per_s
        )
    )

    required_uncertainty_pass = (
        final_result.relative_uncertainty
        <= REQUIRED_RELATIVE_UNCERTAINTY
    )

    preferred_uncertainty_pass = (
        final_result.relative_uncertainty
        <= PREFERRED_RELATIVE_UNCERTAINTY
    )

    folded_check_pass = (
        abs(
            final_direct_vs_folded_difference
        )
        <= DIRECT_VS_FOLDED_TOLERANCE
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 PRODUCTION BENCHMARK RESULTS")
    print("=" * 72)

    print(
        "OpenMC version: "
        f"{model_build_result.openmc_version}"
    )

    print(
        "Final statepoint: "
        f"{final_statepoint_path}"
    )

    print(
        "Measured wall-clock runtime: "
        f"{runtime_seconds:.6f} s"
    )

    print(
        "Run manifest: "
        f"{manifest_path}"
    )

    print("-" * 72)
    print("Checkpoint convergence:")

    for (
        batch,
        result,
        _comparison,
    ) in checkpoint_records:
        response_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                result
                .direct_response_rate_gy_per_s
            )
        )

        difference_from_final = (
            calculate_relative_difference(
                comparison_value=(
                    result
                    .direct_response_rate_gy_per_s
                ),
                reference_value=(
                    final_result
                    .direct_response_rate_gy_per_s
                ),
            )
        )

        print(
            f"  Batch {batch:3d} | "
            f"{batch * settings_profile.particles_per_batch:9d} histories | "
            f"{response_microgy_per_h:.8e} µGy/h | "
            f"rel. unc. {result.relative_uncertainty:.4%} | "
            f"from final {difference_from_final:+.4%}"
        )

    print("-" * 72)
    print("Final OpenMC direct response:")

    print(
        "  Response: "
        f"{final_result.direct_response_rate_gy_per_s:.10e} Gy/s"
    )

    print(
        "  Response: "
        f"{final_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Standard deviation: "
        f"{final_standard_deviation_microgy_per_h:.10e} µGy/h"
    )

    print(
        "  Relative uncertainty: "
        f"{final_result.relative_uncertainty:.4%}"
    )

    print(
        "  Spectrum-folded difference: "
        f"{final_direct_vs_folded_difference:+.4%}"
    )

    print("-" * 72)
    print("Matched deterministic comparison:")

    print(
        "  Difference from deterministic uncollided: "
        f"{final_comparison.relative_difference_from_uncollided:+.4%}"
    )

    if (
        final_comparison
        .relative_difference_from_gp
        is not None
    ):
        print(
            "  Difference from deterministic G-P: "
            f"{final_comparison.relative_difference_from_gp:+.4%}"
        )

    print(
        "  Observed Monte Carlo buildup ratio: "
        f"{final_comparison.observed_monte_carlo_buildup_ratio:.6f}"
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
    print("Saved final outputs:")

    print(
        "  OpenMC response JSON: "
        f"{final_output_paths.response_json_path}"
    )

    print(
        "  Comparison JSON: "
        f"{final_output_paths.comparison_json_path}"
    )

    print(
        "  Photon spectrum CSV: "
        f"{final_output_paths.spectrum_csv_path}"
    )

    print(
        "  Convergence CSV: "
        f"{convergence_path}"
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