# Assemble the canonical V1.13 benchmark release package.
#
# This script:
#
#   - validates the authoritative benchmark records;
#   - verifies both matching production statepoints;
#   - copies inputs, processed outputs, and figures;
#   - creates comparison_summary.csv;
#   - creates a reconstructed run manifest;
#   - refuses to overwrite a different existing artifact.
#
# Run from the repository root:
#
#   python examples/package_v113_release.py

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
from typing import Any


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
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

PROCESSED_SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "processed"
    / "final"
)

FIGURE_SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "docs"
    / "figures"
    / "v1.13"
)

RAW_GEOMETRY_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "geometry_plot"
)

CANONICAL_STATEPOINT_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_run"
    / (
        "cs137_v113_production"
        "__v113_production"
    )
    / "statepoint.100.h5"
)

PROCESSING_STATEPOINT_COPY_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "statepoint.100.h5"
)

RELEASE_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "cs137_lead_benchmark"
)

EXPECTED_STATEPOINT_SHA256 = (
    "3D8342114E7F00A1B590CF1CF77EE9D"
    "95B2259E7C576EFB52C956E03B7695562"
)

OPENMC_VERSION = "0.15.3"

CROSS_SECTION_LIBRARY_PATH = (
    "/root/nndc_hdf5/cross_sections.xml"
)


def repository_relative_path(
    path: Path,
) -> str:
    return path.relative_to(
        REPOSITORY_ROOT
    ).as_posix()


def require_file(
    path: Path,
    description: str,
) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"{description} does not exist: {path}"
        )

    return path


def calculate_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as input_file:
        while True:
            block = input_file.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest().upper()


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    require_file(
        path,
        "JSON input",
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        value = json.load(
            input_file
        )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected a JSON object in {path}."
        )

    return value


def require_equal(
    name: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise ValueError(
            f"{name} mismatch: expected "
            f"{expected!r}, received {actual!r}."
        )


def require_close(
    name: str,
    actual: float,
    expected: float,
) -> None:
    if not math.isclose(
        actual,
        expected,
        rel_tol=1.0e-12,
        abs_tol=1.0e-15,
    ):
        raise ValueError(
            f"{name} mismatch: expected "
            f"{expected:.17g}, received "
            f"{actual:.17g}."
        )


def copy_verified_artifact(
    source_path: Path,
    destination_path: Path,
) -> Path:
    require_file(
        source_path,
        "Release source artifact",
    )

    source_hash = calculate_sha256(
        source_path
    )

    if destination_path.exists():
        if not destination_path.is_file():
            raise RuntimeError(
                "Release destination exists but is "
                f"not a file: {destination_path}"
            )

        destination_hash = calculate_sha256(
            destination_path
        )

        if destination_hash != source_hash:
            raise RuntimeError(
                "Refusing to overwrite a different "
                f"release artifact: {destination_path}"
            )

        return destination_path

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source_path,
        destination_path,
    )

    copied_hash = calculate_sha256(
        destination_path
    )

    if copied_hash != source_hash:
        raise RuntimeError(
            "Copied artifact failed SHA-256 "
            f"verification: {destination_path}"
        )

    return destination_path


def write_verified_text(
    destination_path: Path,
    content: str,
) -> Path:
    if destination_path.exists():
        if not destination_path.is_file():
            raise RuntimeError(
                "Release destination exists but is "
                f"not a file: {destination_path}"
            )

        existing_content = (
            destination_path.read_text(
                encoding="utf-8",
            )
        )

        if existing_content != content:
            raise RuntimeError(
                "Refusing to overwrite a different "
                f"generated artifact: {destination_path}"
            )

        return destination_path

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )

    return destination_path


def format_numeric_value(
    value: int | float,
) -> str:
    if isinstance(
        value,
        int,
    ):
        return str(
            value
        )

    return format(
        value,
        ".17g",
    )


def create_comparison_summary_csv(
    response_record: dict[str, Any],
    comparison_record: dict[str, Any],
) -> str:
    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output,
        lineterminator="\n",
    )

    writer.writerow(
        [
            "category",
            "metric",
            "value",
            "units",
            "status",
        ]
    )

    spectrum_summary = (
        response_record["spectrum_summary"]
    )

    deterministic = (
        comparison_record["deterministic"]
    )

    openmc_result = (
        comparison_record["openmc"]
    )

    comparison = (
        comparison_record["comparison"]
    )

    acceptance = (
        comparison_record["acceptance_checks"]
    )

    rows = [
        (
            "spectrum",
            "total_photon_fluence_rate",
            (
                spectrum_summary[
                    "total_physical_"
                    "photon_fluence_rate_per_cm2_s"
                ]
            ),
            "photons/cm^2/s",
            "",
        ),
        (
            "deterministic",
            "uncollided_collision_air_kerma_rate",
            (
                deterministic[
                    "uncollided_response_rate_"
                    "microgy_per_h"
                ]
            ),
            "microGy/h",
            "",
        ),
        (
            "deterministic",
            "gp_adjusted_collision_air_kerma_rate",
            (
                deterministic[
                    "gp_adjusted_response_rate_"
                    "microgy_per_h"
                ]
            ),
            "microGy/h",
            deterministic["buildup_status"],
        ),
        (
            "openmc",
            "direct_collision_air_kerma_rate",
            (
                openmc_result[
                    "direct_response_rate_"
                    "microgy_per_h"
                ]
            ),
            "microGy/h",
            "",
        ),
        (
            "openmc",
            "direct_standard_deviation",
            (
                openmc_result[
                    "direct_response_standard_"
                    "deviation_microgy_per_h"
                ]
            ),
            "microGy/h",
            "",
        ),
        (
            "openmc",
            "relative_uncertainty",
            openmc_result["relative_uncertainty"],
            "fraction",
            (
                "PASS"
                if acceptance[
                    "required_uncertainty_pass"
                ]
                else "FAIL"
            ),
        ),
        (
            "openmc",
            "spectrum_folded_collision_air_kerma_rate",
            (
                openmc_result[
                    "spectrum_folded_response_"
                    "rate_microgy_per_h"
                ]
            ),
            "microGy/h",
            "",
        ),
        (
            "comparison",
            "relative_difference_from_uncollided",
            (
                comparison[
                    "relative_difference_from_uncollided"
                ]
            ),
            "fraction",
            "",
        ),
        (
            "comparison",
            "relative_difference_from_gp",
            (
                comparison[
                    "relative_difference_from_gp"
                ]
            ),
            "fraction",
            "",
        ),
        (
            "comparison",
            "observed_monte_carlo_buildup_ratio",
            (
                comparison[
                    "observed_monte_carlo_buildup_ratio"
                ]
            ),
            "dimensionless",
            "",
        ),
        (
            "comparison",
            "direct_vs_folded_relative_difference",
            (
                comparison[
                    "direct_vs_folded_relative_difference"
                ]
            ),
            "fraction",
            (
                "PASS"
                if acceptance[
                    "direct_vs_folded_pass"
                ]
                else "FAIL"
            ),
        ),
        (
            "acceptance",
            "required_relative_uncertainty",
            (
                acceptance[
                    "required_relative_uncertainty"
                ]
            ),
            "fraction",
            (
                "PASS"
                if acceptance[
                    "required_uncertainty_pass"
                ]
                else "FAIL"
            ),
        ),
        (
            "acceptance",
            "preferred_relative_uncertainty",
            (
                acceptance[
                    "preferred_relative_uncertainty"
                ]
            ),
            "fraction",
            (
                "PASS"
                if acceptance[
                    "preferred_uncertainty_pass"
                ]
                else "FAIL"
            ),
        ),
        (
            "acceptance",
            "direct_vs_folded_tolerance",
            (
                acceptance[
                    "direct_vs_folded_tolerance"
                ]
            ),
            "fraction",
            (
                "PASS"
                if acceptance[
                    "direct_vs_folded_pass"
                ]
                else "FAIL"
            ),
        ),
    ]

    for (
        category,
        metric,
        value,
        units,
        status,
    ) in rows:
        writer.writerow(
            [
                category,
                metric,
                format_numeric_value(
                    value
                ),
                units,
                status,
            ]
        )

    return output.getvalue()


def validate_records(
    scenario: dict[str, Any],
    settings: dict[str, Any],
    response_record: dict[str, Any],
    comparison_record: dict[str, Any],
) -> None:
    scenario_id = scenario["scenario_id"]
    profile_name = settings["profile_name"]

    require_equal(
        "Scenario calculation mode",
        scenario["calculation_mode"],
        "fixed_shield_response",
    )

    require_equal(
        "OpenMC response scenario ID",
        response_record["scenario_id"],
        scenario_id,
    )

    require_equal(
        "Comparison scenario ID",
        comparison_record["scenario_id"],
        scenario_id,
    )

    require_equal(
        "OpenMC response settings profile",
        response_record["settings_profile_name"],
        profile_name,
    )

    require_equal(
        "Comparison settings profile",
        comparison_record["settings_profile_name"],
        profile_name,
    )

    response_shell = (
        response_record["evaluation_shell"]
    )

    comparison_shell = (
        comparison_record["evaluation_shell"]
    )

    require_close(
        "Evaluation-shell inner radius",
        response_shell["inner_radius_cm"],
        comparison_shell["inner_radius_cm"],
    )

    require_close(
        "Evaluation-shell outer radius",
        response_shell["outer_radius_cm"],
        comparison_shell["outer_radius_cm"],
    )

    response_direct = (
        response_record["direct_response"]
    )

    comparison_openmc = (
        comparison_record["openmc"]
    )

    require_close(
        "OpenMC direct response",
        response_direct["rate_microgy_per_h"],
        (
            comparison_openmc[
                "direct_response_rate_microgy_per_h"
            ]
        ),
    )

    require_close(
        "OpenMC relative uncertainty",
        response_direct["relative_uncertainty"],
        comparison_openmc["relative_uncertainty"],
    )

    execution = settings["execution"]

    total_histories = (
        execution["particles_per_batch"]
        * execution["batches"]
    )

    require_equal(
        "Production source histories",
        total_histories,
        5_000_000,
    )

    require_equal(
        "Production final statepoint batch",
        max(
            settings["output"][
                "statepoint_batches"
            ]
        ),
        100,
    )


def create_recovery_manifest(
    scenario: dict[str, Any],
    settings: dict[str, Any],
    response_record: dict[str, Any],
    comparison_record: dict[str, Any],
    statepoint_hash: str,
    statepoint_size_bytes: int,
) -> dict[str, Any]:
    geometry = scenario["geometry"]
    layer = geometry["layers"][0]
    execution = settings["execution"]
    physics = settings["physics"]
    acceptance = (
        comparison_record["acceptance_checks"]
    )

    total_histories = (
        execution["particles_per_batch"]
        * execution["batches"]
    )

    return {
        "schema_version": "1.0",
        "manifest_type": (
            "post_run_reconstruction"
        ),
        "release": "V1.13",
        "scenario_id": scenario["scenario_id"],
        "settings_profile_name": (
            settings["profile_name"]
        ),
        "physical_scenario": {
            "source_type": (
                scenario["source"]["type"]
            ),
            "isotope_key": (
                scenario["source"]["isotope_key"]
            ),
            "activity_bq": (
                scenario["source"]["activity_bq"]
            ),
            "modeled_photon_energy_ev": 661657.0,
            "emission_intensity_per_decay": 0.851,
            "physical_source_rate_per_s": (
                response_record[
                    "normalization"
                ][
                    "physical_source_rate_per_s"
                ]
            ),
            "geometry_type": geometry["type"],
            "source_cavity_radius_cm": (
                geometry[
                    "source_cavity_radius_cm"
                ]
            ),
            "shield_material_key": (
                layer["material_key"]
            ),
            "shield_thickness_cm": (
                layer["thickness_cm"]
            ),
            "shield_inner_radius_cm": (
                geometry[
                    "source_cavity_radius_cm"
                ]
            ),
            "shield_outer_radius_cm": (
                geometry[
                    "source_cavity_radius_cm"
                ]
                + layer["thickness_cm"]
            ),
            "evaluation_shell": (
                response_record[
                    "evaluation_shell"
                ]
            ),
        },
        "openmc_execution": {
            "openmc_version": OPENMC_VERSION,
            "cross_section_library_path": (
                CROSS_SECTION_LIBRARY_PATH
            ),
            "particles_per_batch": (
                execution["particles_per_batch"]
            ),
            "batches": execution["batches"],
            "total_source_histories": (
                total_histories
            ),
            "random_seed": (
                execution["random_seed"]
            ),
            "threads": execution["threads"],
            "electron_treatment": (
                physics["electron_treatment"]
            ),
            "atomic_relaxation": (
                physics["atomic_relaxation"]
            ),
            "photon_cutoff_energy_ev": (
                physics[
                    "photon_cutoff_energy_ev"
                ]
            ),
            "outer_boundary_radius_cm": (
                settings["geometry"][
                    "outer_boundary_radius_cm"
                ]
            ),
            "statepoint_batches": (
                settings["output"][
                    "statepoint_batches"
                ]
            ),
        },
        "raw_statepoint": {
            "canonical_path": (
                repository_relative_path(
                    CANONICAL_STATEPOINT_PATH
                )
            ),
            "processing_copy_path": (
                repository_relative_path(
                    PROCESSING_STATEPOINT_COPY_PATH
                )
            ),
            "filename": "statepoint.100.h5",
            "batch": 100,
            "size_bytes": statepoint_size_bytes,
            "sha256": statepoint_hash,
            "copies_match": True,
        },
        "processed_results": {
            "response_quantity": (
                response_record[
                    "response_quantity"
                ]
            ),
            "openmc_response_path": (
                "processed/openmc_response.json"
            ),
            "comparison_path": (
                "processed/"
                "deterministic_openmc_comparison.json"
            ),
            "spectrum_path": (
                "processed/photon_spectrum.csv"
            ),
            "summary_path": (
                "processed/comparison_summary.csv"
            ),
        },
        "acceptance_results": {
            "openmc_relative_uncertainty": (
                comparison_record["openmc"][
                    "relative_uncertainty"
                ]
            ),
            "required_relative_uncertainty": (
                acceptance[
                    "required_relative_uncertainty"
                ]
            ),
            "required_uncertainty_pass": (
                acceptance[
                    "required_uncertainty_pass"
                ]
            ),
            "preferred_relative_uncertainty": (
                acceptance[
                    "preferred_relative_uncertainty"
                ]
            ),
            "preferred_uncertainty_pass": (
                acceptance[
                    "preferred_uncertainty_pass"
                ]
            ),
            "direct_vs_folded_relative_difference": (
                comparison_record["comparison"][
                    "direct_vs_folded_relative_difference"
                ]
            ),
            "direct_vs_folded_tolerance": (
                acceptance[
                    "direct_vs_folded_tolerance"
                ]
            ),
            "direct_vs_folded_pass": (
                acceptance[
                    "direct_vs_folded_pass"
                ]
            ),
        },
        "unavailable_original_metadata": [
            "original wall-clock runtime",
            "original execution timestamp",
            "original Git commit",
        ],
        "notes": [
            (
                "The production photon-transport run "
                "completed successfully."
            ),
            (
                "The original run manifest was not "
                "written because the production workflow "
                "failed during post-run processing."
            ),
            (
                "The canonical production and processing "
                "statepoints are byte-for-byte identical."
            ),
            (
                "This manifest was reconstructed from the "
                "authoritative scenario, settings profile, "
                "statepoint, and processed result records."
            ),
        ],
    }


def main() -> int:
    scenario = load_json_object(
        SCENARIO_PATH
    )

    settings = load_json_object(
        SETTINGS_PATH
    )

    response_source_path = (
        PROCESSED_SOURCE_DIRECTORY
        / "openmc_response.json"
    )

    comparison_source_path = (
        PROCESSED_SOURCE_DIRECTORY
        / (
            "deterministic_openmc_"
            "comparison.json"
        )
    )

    spectrum_source_path = (
        PROCESSED_SOURCE_DIRECTORY
        / "photon_spectrum.csv"
    )

    response_record = load_json_object(
        response_source_path
    )

    comparison_record = load_json_object(
        comparison_source_path
    )

    validate_records(
        scenario=scenario,
        settings=settings,
        response_record=response_record,
        comparison_record=comparison_record,
    )

    require_file(
        CANONICAL_STATEPOINT_PATH,
        "Canonical production statepoint",
    )

    require_file(
        PROCESSING_STATEPOINT_COPY_PATH,
        "Processing statepoint copy",
    )

    canonical_statepoint_hash = (
        calculate_sha256(
            CANONICAL_STATEPOINT_PATH
        )
    )

    processing_statepoint_hash = (
        calculate_sha256(
            PROCESSING_STATEPOINT_COPY_PATH
        )
    )

    require_equal(
        "Canonical statepoint SHA-256",
        canonical_statepoint_hash,
        EXPECTED_STATEPOINT_SHA256,
    )

    require_equal(
        "Processing statepoint SHA-256",
        processing_statepoint_hash,
        EXPECTED_STATEPOINT_SHA256,
    )

    copied_paths: list[Path] = []

    copied_paths.append(
        copy_verified_artifact(
            SCENARIO_PATH,
            (
                RELEASE_DIRECTORY
                / "inputs"
                / SCENARIO_PATH.name
            ),
        )
    )

    copied_paths.append(
        copy_verified_artifact(
            SETTINGS_PATH,
            (
                RELEASE_DIRECTORY
                / "inputs"
                / SETTINGS_PATH.name
            ),
        )
    )

    for source_path in (
        response_source_path,
        comparison_source_path,
        spectrum_source_path,
    ):
        copied_paths.append(
            copy_verified_artifact(
                source_path,
                (
                    RELEASE_DIRECTORY
                    / "processed"
                    / source_path.name
                ),
            )
        )

    figure_names = (
        "v113_geometry_annotated.png",
        "v113_geometry_annotated.svg",
        "v113_photon_spectrum.png",
        "v113_photon_spectrum.svg",
        "v113_response_comparison.png",
        "v113_response_comparison.svg",
        "v113_benchmark_summary.png",
        "v113_benchmark_summary.svg",
        "cs137_lead_openmc_benchmark.png",
        "cs137_lead_openmc_benchmark.svg",
    )

    for figure_name in figure_names:
        copied_paths.append(
            copy_verified_artifact(
                (
                    FIGURE_SOURCE_DIRECTORY
                    / figure_name
                ),
                (
                    RELEASE_DIRECTORY
                    / "figures"
                    / figure_name
                ),
            )
        )

    raw_geometry_names = (
        "v113_geometry_full_domain.png",
        "v113_geometry_central_detail.png",
    )

    for geometry_name in raw_geometry_names:
        copied_paths.append(
            copy_verified_artifact(
                (
                    RAW_GEOMETRY_DIRECTORY
                    / geometry_name
                ),
                (
                    RELEASE_DIRECTORY
                    / "figures"
                    / "raw_openmc"
                    / geometry_name
                ),
            )
        )

    comparison_summary_content = (
        create_comparison_summary_csv(
            response_record=response_record,
            comparison_record=comparison_record,
        )
    )

    summary_path = write_verified_text(
        (
            RELEASE_DIRECTORY
            / "processed"
            / "comparison_summary.csv"
        ),
        comparison_summary_content,
    )

    copied_paths.append(
        summary_path
    )

    manifest = create_recovery_manifest(
        scenario=scenario,
        settings=settings,
        response_record=response_record,
        comparison_record=comparison_record,
        statepoint_hash=(
            canonical_statepoint_hash
        ),
        statepoint_size_bytes=(
            CANONICAL_STATEPOINT_PATH
            .stat()
            .st_size
        ),
    )

    manifest_content = (
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    manifest_path = write_verified_text(
        (
            RELEASE_DIRECTORY
            / "recovery_manifest.json"
        ),
        manifest_content,
    )

    copied_paths.append(
        manifest_path
    )

    print()
    print("=" * 72)
    print("V1.13 RELEASE PACKAGE ASSEMBLED")
    print("=" * 72)

    print(
        "Release directory:"
    )

    print(
        f"  {RELEASE_DIRECTORY}"
    )

    print(
        "Canonical statepoint SHA-256:"
    )

    print(
        f"  {canonical_statepoint_hash}"
    )

    print(
        "Release artifacts:"
    )

    for output_path in sorted(
        copied_paths
    ):
        print(
            "  - "
            f"{repository_relative_path(output_path)}"
        )

    print("-" * 72)
    print(
        "The raw statepoint was verified but not copied "
        "into the compact release package."
    )
    print(
        "Next required artifact: "
        "results/v1.13/cs137_lead_benchmark/README.md"
    )
    print("=" * 72)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )