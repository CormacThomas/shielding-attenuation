# Reusable OpenMC benchmark export, execution, and processing orchestration.
#
# This module joins the existing generic model builder, tally builder,
# statepoint processor, deterministic shell-average calculation, and output
# serializers. It contains no top-level OpenMC import.

from __future__ import annotations

import math
import platform
import shutil
import subprocess
import time
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shielding.benchmark.comparison import (
    calculate_observed_monte_carlo_buildup_ratio,
    calculate_relative_difference,
    create_deterministic_shell_average_result,
)
from shielding.monte_carlo.model_builder import (
    OpenMCModelBuildResult,
    build_openmc_benchmark_model,
)
from shielding.monte_carlo.models import (
    DeterministicOpenMCComparison,
    OpenMCResponseResult,
    OpenMCRunManifest,
)
from shielding.monte_carlo.result_io import (
    OpenMCBenchmarkOutputPaths,
    save_json_record,
    save_openmc_benchmark_outputs,
    save_openmc_run_manifest,
)
from shielding.monte_carlo.settings import OpenMCSettings
from shielding.monte_carlo.statepoint import process_openmc_benchmark_statepoint
from shielding.monte_carlo.tallies import (
    DIRECT_RESPONSE_TALLY_ID,
    SPECTRUM_TALLY_ID,
    OpenMCTallyBuildResult,
    attach_openmc_benchmark_tallies,
)
from shielding.scenarios.fixed_shield import calculate_fixed_shield_response
from shielding.scenarios.models import ShieldingScenario


@dataclass(frozen=True)
class OpenMCBenchmarkAcceptanceCriteria:
    direct_vs_folded_tolerance: float = 0.02
    required_relative_uncertainty: float = 0.05
    preferred_relative_uncertainty: float = 0.02

    def __post_init__(self) -> None:
        for value, description in (
            (self.direct_vs_folded_tolerance, "Direct-versus-folded tolerance"),
            (self.required_relative_uncertainty, "Required relative uncertainty"),
            (self.preferred_relative_uncertainty, "Preferred relative uncertainty"),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{description} must be finite and nonnegative.")

        if self.preferred_relative_uncertainty > self.required_relative_uncertainty:
            raise ValueError(
                "Preferred relative uncertainty cannot exceed the required limit."
            )


@dataclass(frozen=True)
class OpenMCBenchmarkModelBundle:
    model_build_result: OpenMCModelBuildResult
    tally_build_result: OpenMCTallyBuildResult


@dataclass(frozen=True)
class OpenMCBenchmarkProcessedBundle:
    openmc_result: OpenMCResponseResult
    comparison: DeterministicOpenMCComparison
    output_paths: OpenMCBenchmarkOutputPaths
    direct_vs_folded_relative_difference: float
    required_uncertainty_pass: bool
    preferred_uncertainty_pass: bool
    direct_vs_folded_pass: bool


@dataclass(frozen=True)
class OpenMCBenchmarkRunBundle:
    model_bundle: OpenMCBenchmarkModelBundle
    processed_bundle: OpenMCBenchmarkProcessedBundle
    run_directory: Path
    final_statepoint_path: Path
    manifest_path: Path
    runtime_seconds: float


def prepare_clean_directory(directory: str | Path, *, overwrite: bool) -> Path:
    output_directory = Path(directory)

    if output_directory.exists():
        if not overwrite:
            raise FileExistsError(
                "OpenMC benchmark output directory already exists. "
                "Use overwrite=True only when replacement is intentional: "
                f"{output_directory}"
            )

        shutil.rmtree(output_directory)

    output_directory.mkdir(parents=True, exist_ok=False)
    return output_directory


def get_git_commit(repository_root: str | Path) -> str | None:
    try:
        completed_process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repository_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    commit = completed_process.stdout.strip()
    return commit or None


def resolve_statepoint_path(
    returned_statepoint_path: str | Path,
    run_directory: str | Path,
) -> Path:
    returned_path = Path(returned_statepoint_path)
    resolved_run_directory = Path(run_directory)

    candidates = (
        returned_path,
        resolved_run_directory / returned_path.name,
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "OpenMC reported a final statepoint, but the file could not be located. "
        f"Returned path: {returned_path}"
    )


def validate_source_energies_within_spectrum(
    model_build_result: OpenMCModelBuildResult,
    settings_profile: OpenMCSettings,
) -> None:
    minimum_energy_ev = settings_profile.minimum_spectrum_energy_ev
    maximum_energy_ev = settings_profile.maximum_spectrum_energy_ev

    for source_energy_ev in model_build_result.source_energies_ev:
        if source_energy_ev < minimum_energy_ev:
            raise ValueError(
                "OpenMC source energy is below the spectrum tally range: "
                f"{source_energy_ev:.12g} eV < {minimum_energy_ev:.12g} eV."
            )

        if source_energy_ev >= maximum_energy_ev:
            raise ValueError(
                "OpenMC source energy must be below the final spectrum boundary: "
                f"{source_energy_ev:.12g} eV >= {maximum_energy_ev:.12g} eV."
            )


def build_attached_openmc_benchmark_model(
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    evaluation_shell_thickness_cm: float = 1.0,
) -> OpenMCBenchmarkModelBundle:
    model_build_result = build_openmc_benchmark_model(
        scenario=scenario,
        settings_profile=settings_profile,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
    )

    validate_source_energies_within_spectrum(
        model_build_result=model_build_result,
        settings_profile=settings_profile,
    )

    tally_build_result = attach_openmc_benchmark_tallies(
        model_build_result=model_build_result,
        settings_profile=settings_profile,
    )

    return OpenMCBenchmarkModelBundle(
        model_build_result=model_build_result,
        tally_build_result=tally_build_result,
    )


def create_matched_openmc_comparison(
    scenario: ShieldingScenario,
    openmc_result: OpenMCResponseResult,
    evaluation_shell_thickness_cm: float = 1.0,
) -> DeterministicOpenMCComparison:
    fixed_shield_result = calculate_fixed_shield_response(scenario)

    deterministic_result = create_deterministic_shell_average_result(
        fixed_shield_result=fixed_shield_result,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
    )

    deterministic_uncollided = deterministic_result.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s

    deterministic_gp = deterministic_result.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s

    relative_difference_from_gp = None
    if deterministic_gp is not None:
        relative_difference_from_gp = calculate_relative_difference(
            comparison_value=openmc_result.direct_response_rate_gy_per_s,
            reference_value=deterministic_gp,
        )

    return DeterministicOpenMCComparison(
        deterministic_result=deterministic_result,
        openmc_result=openmc_result,
        relative_difference_from_uncollided=calculate_relative_difference(
            comparison_value=openmc_result.direct_response_rate_gy_per_s,
            reference_value=deterministic_uncollided,
        ),
        relative_difference_from_gp=relative_difference_from_gp,
        observed_monte_carlo_buildup_ratio=(
            calculate_observed_monte_carlo_buildup_ratio(
                openmc_response=openmc_result.direct_response_rate_gy_per_s,
                deterministic_uncollided_response=deterministic_uncollided,
            )
        ),
    )


def calculate_direct_vs_folded_relative_difference(
    result: OpenMCResponseResult,
) -> float:
    return calculate_relative_difference(
        comparison_value=result.spectrum_folded_response_rate_gy_per_s,
        reference_value=result.direct_response_rate_gy_per_s,
    )


def process_openmc_benchmark_result(
    *,
    statepoint_path: str | Path,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    output_directory: str | Path,
    evaluation_shell_thickness_cm: float = 1.0,
    expected_batch: int | None = None,
    acceptance_criteria: OpenMCBenchmarkAcceptanceCriteria | None = None,
    overwrite: bool = False,
) -> OpenMCBenchmarkProcessedBundle:
    if acceptance_criteria is None:
        acceptance_criteria = OpenMCBenchmarkAcceptanceCriteria()

    if overwrite and Path(statepoint_path).resolve().is_relative_to(
        Path(output_directory).resolve()
    ):
        raise ValueError("The output directory must not contain the input statepoint.")

    openmc_result = process_openmc_benchmark_statepoint(
        statepoint_path=statepoint_path,
        scenario=scenario,
        settings_profile=settings_profile,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
        expected_batch=expected_batch,
    )

    comparison = create_matched_openmc_comparison(
        scenario=scenario,
        openmc_result=openmc_result,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
    )

    output_directory = prepare_clean_directory(output_directory, overwrite=overwrite)

    output_paths = save_openmc_benchmark_outputs(
        openmc_result=openmc_result,
        comparison=comparison,
        output_directory=output_directory,
        direct_vs_folded_tolerance=(acceptance_criteria.direct_vs_folded_tolerance),
        required_relative_uncertainty=(
            acceptance_criteria.required_relative_uncertainty
        ),
        preferred_relative_uncertainty=(
            acceptance_criteria.preferred_relative_uncertainty
        ),
    )

    direct_vs_folded_relative_difference = (
        calculate_direct_vs_folded_relative_difference(openmc_result)
    )

    return OpenMCBenchmarkProcessedBundle(
        openmc_result=openmc_result,
        comparison=comparison,
        output_paths=output_paths,
        direct_vs_folded_relative_difference=direct_vs_folded_relative_difference,
        required_uncertainty_pass=(
            openmc_result.relative_uncertainty
            <= acceptance_criteria.required_relative_uncertainty
        ),
        preferred_uncertainty_pass=(
            openmc_result.relative_uncertainty
            <= acceptance_criteria.preferred_relative_uncertainty
        ),
        direct_vs_folded_pass=(
            abs(direct_vs_folded_relative_difference)
            <= acceptance_criteria.direct_vs_folded_tolerance
        ),
    )


def create_export_summary(
    *,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    model_bundle: OpenMCBenchmarkModelBundle,
    model_xml_path: Path,
) -> dict[str, Any]:
    model_build_result = model_bundle.model_build_result

    xml_tree = ElementTree.parse(model_xml_path)
    root = xml_tree.getroot()

    if root.tag != "model":
        raise RuntimeError(f"Unexpected OpenMC model XML root tag: {root.tag}")

    required_sections = {
        "materials",
        "geometry",
        "settings",
        "tallies",
    }

    present_sections = {child.tag for child in root}
    missing_sections = required_sections - present_sections
    if missing_sections:
        raise RuntimeError(
            f"Exported OpenMC model XML is missing sections: {sorted(missing_sections)}"
        )

    materials_node = root.find("materials")
    geometry_node = root.find("geometry")
    tallies_node = root.find("tallies")

    if materials_node is None or geometry_node is None or tallies_node is None:
        raise RuntimeError("Exported OpenMC model XML structure is incomplete.")

    material_nodes = materials_node.findall("material")
    cell_nodes = geometry_node.findall("cell")
    surface_nodes = geometry_node.findall("surface")
    tally_nodes = tallies_node.findall("tally")

    expected_cell_count = len(model_build_result.shield_cells) + 4
    expected_surface_count = len(model_build_result.shield_cells) + 4

    if len(material_nodes) != len(model_build_result.materials_by_key):
        raise RuntimeError("Exported OpenMC material count is inconsistent.")

    if len(cell_nodes) != expected_cell_count:
        raise RuntimeError("Exported OpenMC cell count is inconsistent.")

    if len(surface_nodes) != expected_surface_count:
        raise RuntimeError("Exported OpenMC surface count is inconsistent.")

    if len(tally_nodes) != 2:
        raise RuntimeError("Exported OpenMC model must contain exactly two tallies.")

    exported_tally_ids = {int(tally_node.attrib["id"]) for tally_node in tally_nodes}

    if exported_tally_ids != {SPECTRUM_TALLY_ID, DIRECT_RESPONSE_TALLY_ID}:
        raise RuntimeError(
            "Exported OpenMC tally IDs do not match the benchmark contract."
        )

    return {
        "record_type": "openmc_benchmark_model_export",
        "version": "1.14",
        "transport_executed": False,
        "scenario_id": scenario.scenario_id,
        "settings_profile_name": settings_profile.profile_name,
        "openmc_version": model_build_result.openmc_version,
        "cross_sections_path": model_build_result.cross_sections_path,
        "model_xml_path": str(model_xml_path),
        "material_keys": sorted(model_build_result.materials_by_key),
        "material_count": len(material_nodes),
        "shield_cell_count": len(model_build_result.shield_cells),
        "cell_count": len(cell_nodes),
        "surface_count": len(surface_nodes),
        "tally_ids": sorted(exported_tally_ids),
        "source_energies_ev": list(model_build_result.source_energies_ev),
        "source_probabilities": list(model_build_result.source_probabilities),
        "physical_source_rate_per_s": (model_build_result.physical_source_rate_per_s),
        "evaluation_shell": {
            "center_radius_cm": model_build_result.evaluation_shell.center_radius_cm,
            "thickness_cm": model_build_result.evaluation_shell.thickness_cm,
            "inner_radius_cm": model_build_result.evaluation_shell.inner_radius_cm,
            "outer_radius_cm": model_build_result.evaluation_shell.outer_radius_cm,
        },
        "spectrum": {
            "energy_bin_count": (len(settings_profile.energy_bin_boundaries_ev) - 1),
            "minimum_energy_ev": settings_profile.minimum_spectrum_energy_ev,
            "maximum_energy_ev": settings_profile.maximum_spectrum_energy_ev,
        },
    }


def export_openmc_benchmark_model(
    *,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    output_directory: str | Path,
    evaluation_shell_thickness_cm: float = 1.0,
    overwrite: bool = False,
) -> Path:
    model_bundle = build_attached_openmc_benchmark_model(
        scenario=scenario,
        settings_profile=settings_profile,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
    )

    export_directory = prepare_clean_directory(
        output_directory,
        overwrite=overwrite,
    )

    model_xml_path = export_directory / "model.xml"
    model_bundle.model_build_result.model.export_to_model_xml(path=model_xml_path)

    if not model_xml_path.is_file():
        raise RuntimeError(f"OpenMC model XML was not created: {model_xml_path}")

    summary = create_export_summary(
        scenario=scenario,
        settings_profile=settings_profile,
        model_bundle=model_bundle,
        model_xml_path=model_xml_path,
    )

    save_json_record(
        summary,
        export_directory / "model_export_summary.json",
    )

    return model_xml_path


def run_openmc_benchmark_case(
    *,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    run_directory: str | Path,
    repository_root: str | Path,
    evaluation_shell_thickness_cm: float = 1.0,
    acceptance_criteria: OpenMCBenchmarkAcceptanceCriteria | None = None,
    overwrite: bool = False,
    output: bool = True,
) -> OpenMCBenchmarkRunBundle:
    if acceptance_criteria is None:
        acceptance_criteria = OpenMCBenchmarkAcceptanceCriteria()

    model_bundle = build_attached_openmc_benchmark_model(
        scenario=scenario,
        settings_profile=settings_profile,
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
    )

    resolved_run_directory = prepare_clean_directory(
        run_directory,
        overwrite=overwrite,
    )

    start_time = time.perf_counter()

    returned_statepoint_path = model_bundle.model_build_result.model.run(
        threads=settings_profile.threads,
        output=output,
        cwd=resolved_run_directory,
        export_model_xml=True,
    )

    runtime_seconds = time.perf_counter() - start_time

    if returned_statepoint_path is None:
        raise RuntimeError(
            "OpenMC completed without returning a final statepoint path."
        )

    final_statepoint_path = resolve_statepoint_path(
        returned_statepoint_path=returned_statepoint_path,
        run_directory=resolved_run_directory,
    )

    manifest = OpenMCRunManifest(
        scenario_id=scenario.scenario_id,
        settings_profile_name=settings_profile.profile_name,
        openmc_version=model_bundle.model_build_result.openmc_version,
        python_version=platform.python_version(),
        cross_section_library=(model_bundle.model_build_result.cross_sections_path),
        electron_treatment=settings_profile.electron_treatment,
        atomic_relaxation=settings_profile.atomic_relaxation,
        photon_cutoff_energy_ev=settings_profile.photon_cutoff_energy_ev,
        particles_per_batch=settings_profile.particles_per_batch,
        batches=settings_profile.batches,
        total_source_particles=settings_profile.total_source_particles,
        random_seed=settings_profile.random_seed,
        threads=settings_profile.threads,
        runtime_seconds=runtime_seconds,
        statepoint_filename=final_statepoint_path.name,
        execution_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=get_git_commit(repository_root),
    )

    manifest_path = save_openmc_run_manifest(
        manifest=manifest,
        output_path=resolved_run_directory / "run_manifest.json",
    )

    processed_bundle = process_openmc_benchmark_result(
        statepoint_path=final_statepoint_path,
        scenario=scenario,
        settings_profile=settings_profile,
        output_directory=resolved_run_directory / "processed" / "final",
        evaluation_shell_thickness_cm=evaluation_shell_thickness_cm,
        expected_batch=settings_profile.batches,
        acceptance_criteria=acceptance_criteria,
    )

    return OpenMCBenchmarkRunBundle(
        model_bundle=model_bundle,
        processed_bundle=processed_bundle,
        run_directory=resolved_run_directory,
        final_statepoint_path=final_statepoint_path,
        manifest_path=manifest_path,
        runtime_seconds=runtime_seconds,
    )
