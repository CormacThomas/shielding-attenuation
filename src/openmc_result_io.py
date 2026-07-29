# V1.13 processed OpenMC benchmark output serialization.
#
# This module writes human-readable, backend-independent records from:
#
#   - OpenMCResponseResult
#   - DeterministicOpenMCComparison
#   - the processed energy-resolved photon spectrum
#
# Raw Monte Carlo data remain preserved in the OpenMC statepoint. These files
# preserve the physical normalization, engineering comparison, units, and
# acceptance checks needed for reports, plots, and future reproducibility.
#
# This module contains no OpenMC import.


from __future__ import annotations

from openmc_models import (
    DeterministicOpenMCComparison,
    OpenMCEnergyBinResult,
    OpenMCResponseResult,
    OpenMCRunManifest,
)
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


from openmc_models import (
    DeterministicOpenMCComparison,
    OpenMCEnergyBinResult,
    OpenMCResponseResult,
)
from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
)


OPENMC_PROCESSED_RESULT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class OpenMCBenchmarkOutputPaths:
    # Paths created for one processed benchmark result.

    response_json_path: Path
    comparison_json_path: Path
    spectrum_csv_path: Path

    def __post_init__(self) -> None:
        output_paths = (
            self.response_json_path,
            self.comparison_json_path,
            self.spectrum_csv_path,
        )

        for output_path in output_paths:
            if not output_path.is_file():
                raise ValueError(
                    "Processed OpenMC benchmark output "
                    "file does not exist: "
                    f"{output_path}"
                )


def evaluation_shell_to_dict(
    inner_radius_cm: float,
    outer_radius_cm: float,
    center_radius_cm: float,
    thickness_cm: float,
) -> dict[str, float]:
    # Serialize the exact spatial observation region.

    return {
        "center_radius_cm": center_radius_cm,
        "thickness_cm": thickness_cm,
        "inner_radius_cm": inner_radius_cm,
        "outer_radius_cm": outer_radius_cm,
    }


def openmc_energy_bin_result_to_dict(
    energy_bin_result: OpenMCEnergyBinResult,
    bin_index: int,
) -> dict[str, Any]:
    # Serialize one normalized spectrum bin.

    if bin_index <= 0:
        raise ValueError(
            "OpenMC energy-bin output index must be positive."
        )

    physical_mean = (
        energy_bin_result
        .physical_fluence_rate_mean_per_cm2_s
    )

    physical_standard_deviation = (
        energy_bin_result
        .physical_fluence_rate_standard_deviation_per_cm2_s
    )

    relative_uncertainty = None

    if physical_mean > 0:
        relative_uncertainty = (
            physical_standard_deviation
            / physical_mean
        )

    representative_energy_ev = math.sqrt(
        energy_bin_result.lower_energy_ev
        * energy_bin_result.upper_energy_ev
    )

    return {
        "bin_index": bin_index,
        "lower_energy_ev": (
            energy_bin_result.lower_energy_ev
        ),
        "upper_energy_ev": (
            energy_bin_result.upper_energy_ev
        ),
        "representative_energy_ev": (
            representative_energy_ev
        ),
        "raw_track_length_flux_mean_cm_per_source": (
            energy_bin_result
            .raw_track_length_flux_mean_cm_per_source
        ),
        "raw_track_length_flux_standard_deviation_cm_per_source": (
            energy_bin_result
            .raw_track_length_flux_standard_deviation_cm_per_source
        ),
        "volume_normalized_fluence_mean_per_cm2_per_source": (
            energy_bin_result
            .volume_normalized_fluence_mean_per_cm2_per_source
        ),
        "volume_normalized_fluence_standard_deviation_per_cm2_per_source": (
            energy_bin_result
            .volume_normalized_fluence_standard_deviation_per_cm2_per_source
        ),
        "physical_fluence_rate_mean_per_cm2_s": (
            physical_mean
        ),
        "physical_fluence_rate_standard_deviation_per_cm2_s": (
            physical_standard_deviation
        ),
        "relative_uncertainty": (
            relative_uncertainty
        ),
        "response_coefficient_gy_cm2_per_photon": (
            energy_bin_result
            .response_coefficient_gy_cm2_per_photon
        ),
        "air_kerma_rate_contribution_gy_per_s": (
            energy_bin_result
            .air_kerma_rate_contribution_gy_per_s
        ),
        "air_kerma_rate_contribution_microgy_per_h": (
            convert_gy_per_s_to_microgy_per_h(
                energy_bin_result
                .air_kerma_rate_contribution_gy_per_s
            )
        ),
    }


def openmc_response_result_to_dict(
    result: OpenMCResponseResult,
) -> dict[str, Any]:
    # Serialize the complete processed OpenMC response.

    total_physical_fluence_rate = sum(
        energy_bin_result
        .physical_fluence_rate_mean_per_cm2_s
        for energy_bin_result
        in result.energy_bin_results
    )

    total_raw_spectrum_mean = sum(
        energy_bin_result
        .raw_track_length_flux_mean_cm_per_source
        for energy_bin_result
        in result.energy_bin_results
    )

    direct_response_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result.direct_response_rate_gy_per_s
        )
    )

    direct_standard_deviation_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .direct_response_rate_standard_deviation_gy_per_s
        )
    )

    folded_response_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .spectrum_folded_response_rate_gy_per_s
        )
    )

    return {
        "schema_version": (
            OPENMC_PROCESSED_RESULT_SCHEMA_VERSION
        ),
        "record_type": "openmc_response",
        "scenario_id": result.scenario_id,
        "settings_profile_name": (
            result.settings_profile_name
        ),
        "response_quantity": (
            "shell-volume-averaged dry-air "
            "collision air-kerma rate"
        ),
        "evaluation_shell": evaluation_shell_to_dict(
            inner_radius_cm=(
                result.evaluation_shell.inner_radius_cm
            ),
            outer_radius_cm=(
                result.evaluation_shell.outer_radius_cm
            ),
            center_radius_cm=(
                result.evaluation_shell.center_radius_cm
            ),
            thickness_cm=(
                result.evaluation_shell.thickness_cm
            ),
        ),
        "normalization": {
            "shell_volume_cm3": (
                result.shell_volume_cm3
            ),
            "physical_source_rate_per_s": (
                result.physical_source_rate_per_s
            ),
        },
        "spectrum_summary": {
            "energy_bin_count": len(
                result.energy_bin_results
            ),
            "total_raw_track_length_flux_mean_cm_per_source": (
                total_raw_spectrum_mean
            ),
            "total_physical_photon_fluence_rate_per_cm2_s": (
                total_physical_fluence_rate
            ),
            "spectrum_folded_response_rate_gy_per_s": (
                result
                .spectrum_folded_response_rate_gy_per_s
            ),
            "spectrum_folded_response_rate_microgy_per_h": (
                folded_response_microgy_per_h
            ),
        },
        "direct_response": {
            "raw_mean_gy_cm3_per_source": (
                result
                .raw_direct_response_mean_gy_cm3_per_source
            ),
            "raw_standard_deviation_gy_cm3_per_source": (
                result
                .raw_direct_response_standard_deviation_gy_cm3_per_source
            ),
            "mean_gy_per_source": (
                result
                .direct_response_mean_gy_per_source
            ),
            "standard_deviation_gy_per_source": (
                result
                .direct_response_standard_deviation_gy_per_source
            ),
            "rate_gy_per_s": (
                result.direct_response_rate_gy_per_s
            ),
            "rate_microgy_per_h": (
                direct_response_microgy_per_h
            ),
            "standard_deviation_gy_per_s": (
                result
                .direct_response_rate_standard_deviation_gy_per_s
            ),
            "standard_deviation_microgy_per_h": (
                direct_standard_deviation_microgy_per_h
            ),
            "relative_uncertainty": (
                result.relative_uncertainty
            ),
        },
        "energy_bins": [
            openmc_energy_bin_result_to_dict(
                energy_bin_result=energy_bin_result,
                bin_index=bin_index,
            )
            for bin_index, energy_bin_result in enumerate(
                result.energy_bin_results,
                start=1,
            )
        ],
        "warnings": list(
            result.warnings
        ),
    }


def deterministic_openmc_comparison_to_dict(
    comparison: DeterministicOpenMCComparison,
    direct_vs_folded_tolerance: float = 0.02,
    required_relative_uncertainty: float = 0.05,
    preferred_relative_uncertainty: float = 0.02,
) -> dict[str, Any]:
    # Serialize the formal matched deterministic-versus-OpenMC comparison.

    if direct_vs_folded_tolerance < 0:
        raise ValueError(
            "Direct-versus-folded tolerance cannot be negative."
        )

    if required_relative_uncertainty < 0:
        raise ValueError(
            "Required relative uncertainty cannot be negative."
        )

    if preferred_relative_uncertainty < 0:
        raise ValueError(
            "Preferred relative uncertainty cannot be negative."
        )

    deterministic_result = (
        comparison.deterministic_result
    )

    openmc_result = (
        comparison.openmc_result
    )

    deterministic_uncollided = (
        deterministic_result
        .total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
    )

    deterministic_gp = (
        deterministic_result
        .total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    direct_response = (
        openmc_result
        .direct_response_rate_gy_per_s
    )

    folded_response = (
        openmc_result
        .spectrum_folded_response_rate_gy_per_s
    )

    direct_vs_folded_relative_difference = (
        (
            folded_response
            - direct_response
        )
        / direct_response
    )

    deterministic_gp_microgy_per_h = None

    if deterministic_gp is not None:
        deterministic_gp_microgy_per_h = (
            convert_gy_per_s_to_microgy_per_h(
                deterministic_gp
            )
        )

    return {
        "schema_version": (
            OPENMC_PROCESSED_RESULT_SCHEMA_VERSION
        ),
        "record_type": (
            "deterministic_openmc_comparison"
        ),
        "scenario_id": (
            deterministic_result.scenario_id
        ),
        "settings_profile_name": (
            openmc_result.settings_profile_name
        ),
        "response_quantity": (
            "shell-volume-averaged dry-air "
            "collision air-kerma rate"
        ),
        "evaluation_shell": evaluation_shell_to_dict(
            inner_radius_cm=(
                deterministic_result
                .evaluation_shell
                .inner_radius_cm
            ),
            outer_radius_cm=(
                deterministic_result
                .evaluation_shell
                .outer_radius_cm
            ),
            center_radius_cm=(
                deterministic_result
                .evaluation_shell
                .center_radius_cm
            ),
            thickness_cm=(
                deterministic_result
                .evaluation_shell
                .thickness_cm
            ),
        ),
        "deterministic": {
            "uncollided_response_rate_gy_per_s": (
                deterministic_uncollided
            ),
            "uncollided_response_rate_microgy_per_h": (
                convert_gy_per_s_to_microgy_per_h(
                    deterministic_uncollided
                )
            ),
            "gp_adjusted_response_rate_gy_per_s": (
                deterministic_gp
            ),
            "gp_adjusted_response_rate_microgy_per_h": (
                deterministic_gp_microgy_per_h
            ),
            "buildup_status": (
                deterministic_result.buildup_status
            ),
        },
        "openmc": {
            "direct_response_rate_gy_per_s": (
                direct_response
            ),
            "direct_response_rate_microgy_per_h": (
                convert_gy_per_s_to_microgy_per_h(
                    direct_response
                )
            ),
            "direct_response_standard_deviation_gy_per_s": (
                openmc_result
                .direct_response_rate_standard_deviation_gy_per_s
            ),
            "direct_response_standard_deviation_microgy_per_h": (
                convert_gy_per_s_to_microgy_per_h(
                    openmc_result
                    .direct_response_rate_standard_deviation_gy_per_s
                )
            ),
            "relative_uncertainty": (
                openmc_result.relative_uncertainty
            ),
            "spectrum_folded_response_rate_gy_per_s": (
                folded_response
            ),
            "spectrum_folded_response_rate_microgy_per_h": (
                convert_gy_per_s_to_microgy_per_h(
                    folded_response
                )
            ),
        },
        "comparison": {
            "relative_difference_from_uncollided": (
                comparison
                .relative_difference_from_uncollided
            ),
            "relative_difference_from_gp": (
                comparison
                .relative_difference_from_gp
            ),
            "observed_monte_carlo_buildup_ratio": (
                comparison
                .observed_monte_carlo_buildup_ratio
            ),
            "direct_vs_folded_relative_difference": (
                direct_vs_folded_relative_difference
            ),
            "absolute_direct_vs_folded_relative_difference": (
                abs(
                    direct_vs_folded_relative_difference
                )
            ),
        },
        "acceptance_checks": {
            "direct_vs_folded_tolerance": (
                direct_vs_folded_tolerance
            ),
            "direct_vs_folded_pass": (
                abs(
                    direct_vs_folded_relative_difference
                )
                <= direct_vs_folded_tolerance
            ),
            "required_relative_uncertainty": (
                required_relative_uncertainty
            ),
            "required_uncertainty_pass": (
                openmc_result.relative_uncertainty
                <= required_relative_uncertainty
            ),
            "preferred_relative_uncertainty": (
                preferred_relative_uncertainty
            ),
            "preferred_uncertainty_pass": (
                openmc_result.relative_uncertainty
                <= preferred_relative_uncertainty
            ),
        },
        "warnings": [
            *deterministic_result.warnings,
            *openmc_result.warnings,
            *comparison.warnings,
        ],
    }


def save_json_record(
    record: dict[str, Any],
    output_path: str | Path,
) -> Path:
    # Save one processed record as formatted UTF-8 JSON.

    resolved_output_path = Path(
        output_path
    )

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with resolved_output_path.open(
        mode="w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            record,
            output_file,
            indent=2,
            ensure_ascii=False,
        )

        output_file.write(
            "\n"
        )

    return resolved_output_path


def save_openmc_spectrum_csv(
    result: OpenMCResponseResult,
    output_path: str | Path,
) -> Path:
    # Save the complete processed photon spectrum in a plotting-friendly CSV.

    resolved_output_path = Path(
        output_path
    )

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "bin_index",
        "lower_energy_ev",
        "upper_energy_ev",
        "representative_energy_ev",
        "raw_track_length_flux_mean_cm_per_source",
        "raw_track_length_flux_standard_deviation_cm_per_source",
        "volume_normalized_fluence_mean_per_cm2_per_source",
        "volume_normalized_fluence_standard_deviation_per_cm2_per_source",
        "physical_fluence_rate_mean_per_cm2_s",
        "physical_fluence_rate_standard_deviation_per_cm2_s",
        "relative_uncertainty",
        "response_coefficient_gy_cm2_per_photon",
        "air_kerma_rate_contribution_gy_per_s",
        "air_kerma_rate_contribution_microgy_per_h",
    ]

    with resolved_output_path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for bin_index, energy_bin_result in enumerate(
            result.energy_bin_results,
            start=1,
        ):
            writer.writerow(
                openmc_energy_bin_result_to_dict(
                    energy_bin_result=(
                        energy_bin_result
                    ),
                    bin_index=bin_index,
                )
            )

    return resolved_output_path


def openmc_run_manifest_to_dict(
    manifest: OpenMCRunManifest,
) -> dict[str, Any]:
    # Serialize the reproducibility metadata for one completed OpenMC run.

    return {
        "schema_version": (
            OPENMC_PROCESSED_RESULT_SCHEMA_VERSION
        ),
        "record_type": "openmc_run_manifest",
        "scenario_id": manifest.scenario_id,
        "settings_profile_name": (
            manifest.settings_profile_name
        ),
        "software": {
            "openmc_version": (
                manifest.openmc_version
            ),
            "python_version": (
                manifest.python_version
            ),
            "git_commit": (
                manifest.git_commit
            ),
        },
        "nuclear_data": {
            "cross_section_library": (
                manifest.cross_section_library
            ),
        },
        "physics": {
            "electron_treatment": (
                manifest.electron_treatment
            ),
            "atomic_relaxation": (
                manifest.atomic_relaxation
            ),
            "photon_cutoff_energy_ev": (
                manifest.photon_cutoff_energy_ev
            ),
        },
        "execution": {
            "particles_per_batch": (
                manifest.particles_per_batch
            ),
            "batches": manifest.batches,
            "total_source_particles": (
                manifest.total_source_particles
            ),
            "random_seed": manifest.random_seed,
            "threads": manifest.threads,
            "runtime_seconds": (
                manifest.runtime_seconds
            ),
            "execution_timestamp_utc": (
                manifest.execution_timestamp_utc
            ),
        },
        "output": {
            "statepoint_filename": (
                manifest.statepoint_filename
            ),
        },
    }


def save_openmc_run_manifest(
    manifest: OpenMCRunManifest,
    output_path: str | Path,
) -> Path:
    # Save one completed OpenMC execution manifest.

    return save_json_record(
        record=openmc_run_manifest_to_dict(
            manifest
        ),
        output_path=output_path,
    )


def save_openmc_benchmark_outputs(
    openmc_result: OpenMCResponseResult,
    comparison: DeterministicOpenMCComparison,
    output_directory: str | Path,
    direct_vs_folded_tolerance: float = 0.02,
    required_relative_uncertainty: float = 0.05,
    preferred_relative_uncertainty: float = 0.02,
) -> OpenMCBenchmarkOutputPaths:
    # Save the complete processed output set for one benchmark run.

    if (
        comparison.openmc_result
        != openmc_result
    ):
        raise ValueError(
            "Benchmark comparison must reference the "
            "OpenMC result being saved."
        )

    resolved_output_directory = Path(
        output_directory
    )

    resolved_output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    response_json_path = save_json_record(
        record=openmc_response_result_to_dict(
            openmc_result
        ),
        output_path=(
            resolved_output_directory
            / "openmc_response.json"
        ),
    )

    comparison_json_path = save_json_record(
        record=(
            deterministic_openmc_comparison_to_dict(
                comparison=comparison,
                direct_vs_folded_tolerance=(
                    direct_vs_folded_tolerance
                ),
                required_relative_uncertainty=(
                    required_relative_uncertainty
                ),
                preferred_relative_uncertainty=(
                    preferred_relative_uncertainty
                ),
            )
        ),
        output_path=(
            resolved_output_directory
            / "deterministic_openmc_comparison.json"
        ),
    )

    spectrum_csv_path = save_openmc_spectrum_csv(
        result=openmc_result,
        output_path=(
            resolved_output_directory
            / "photon_spectrum.csv"
        ),
    )

    return OpenMCBenchmarkOutputPaths(
        response_json_path=(
            response_json_path
        ),
        comparison_json_path=(
            comparison_json_path
        ),
        spectrum_csv_path=(
            spectrum_csv_path
        ),
    )