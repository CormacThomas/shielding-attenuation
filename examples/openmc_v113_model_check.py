# Validate and export the V1.13 OpenMC model without running particles.
#
# Run this script inside the same OpenMC Docker environment used by:
#
#   examples/openmc_smoke_test.py
#
# Default:
#
#   python examples/openmc_v113_model_check.py
#
# Production geometry/profile:
#
#   python examples/openmc_v113_model_check.py \
#       scenarios/cs137_v113_production.json \
#       config/openmc/v113_production.json


from __future__ import annotations


import argparse
from pathlib import Path
import shutil
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


from openmc_model_builder import (
    build_openmc_v113_model,
)
from openmc_settings_io import (
    load_openmc_settings,
)
from scenario_io import (
    load_scenario,
)


DEFAULT_SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_v113_development.json"
)

DEFAULT_SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v113_development.json"
)


def parse_arguments() -> (
    argparse.Namespace
):
    parser = argparse.ArgumentParser(
        description=(
            "Construct and export the V1.13 OpenMC "
            "photon benchmark model without running it."
        )
    )

    parser.add_argument(
        "scenario_path",
        nargs="?",
        type=Path,
        default=DEFAULT_SCENARIO_PATH,
        help=(
            "Fixed-shield scenario JSON path."
        ),
    )

    parser.add_argument(
        "settings_path",
        nargs="?",
        type=Path,
        default=DEFAULT_SETTINGS_PATH,
        help=(
            "OpenMC settings-profile JSON path."
        ),
    )

    parser.add_argument(
        "--evaluation-shell-thickness-cm",
        type=float,
        default=1.0,
        help=(
            "Matched spherical evaluation-shell "
            "thickness in centimeters."
        ),
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help=(
            "Optional output directory for generated "
            "OpenMC XML files."
        ),
    )

    return parser.parse_args()


def prepare_output_directory(
    output_directory: Path,
) -> None:
    # Remove any previous model export so every check describes only the
    # current scenario and settings profile.

    if output_directory.exists():
        shutil.rmtree(
            output_directory
        )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


def require_exported_file(
    output_directory: Path,
    filename: str,
) -> Path:
    exported_path = (
        output_directory
        / filename
    )

    if not exported_path.is_file():
        raise RuntimeError(
            "Expected OpenMC XML file was not created: "
            f"{exported_path}"
        )

    return exported_path


def main() -> int:
    arguments = parse_arguments()

    scenario = load_scenario(
        arguments.scenario_path
    )

    settings_profile = (
        load_openmc_settings(
            arguments.settings_path
        )
    )

    build_result = (
        build_openmc_v113_model(
            scenario=scenario,
            settings_profile=(
                settings_profile
            ),
            evaluation_shell_thickness_cm=(
                arguments
                .evaluation_shell_thickness_cm
            ),
        )
    )

    if (
        arguments.output_directory
        is None
    ):
        output_directory = (
            REPOSITORY_ROOT
            / "results"
            / "v1.13"
            / "model_build"
            / (
                f"{scenario.scenario_id}__"
                f"{settings_profile.profile_name}"
            )
        )

    else:
        output_directory = (
            arguments.output_directory
        )

    prepare_output_directory(
        output_directory
    )

    # Model.export_to_xml() writes separate materials.xml, geometry.xml, and
    # settings.xml files. Tallies are added in the following V1.13 step.
    build_result.model.export_to_xml(
        directory=output_directory
    )

    materials_path = (
        require_exported_file(
            output_directory,
            "materials.xml",
        )
    )

    geometry_path = (
        require_exported_file(
            output_directory,
            "geometry.xml",
        )
    )

    settings_path = (
        require_exported_file(
            output_directory,
            "settings.xml",
        )
    )

    geometry_cells = (
        build_result
        .model
        .geometry
        .get_all_cells()
    )

    expected_cell_count = (
        len(
            scenario.geometry.layers
        )
        + 4
    )

    if (
        len(geometry_cells)
        != expected_cell_count
    ):
        raise RuntimeError(
            "Unexpected OpenMC geometry cell count: "
            f"expected {expected_cell_count}, "
            f"found {len(geometry_cells)}."
        )

    if (
        build_result
        .outer_boundary_surface
        .boundary_type
        != "vacuum"
    ):
        raise RuntimeError(
            "OpenMC outer boundary is not vacuum."
        )

    if (
        build_result
        .evaluation_shell_cell
        .fill
        is not None
    ):
        raise RuntimeError(
            "OpenMC evaluation shell must remain vacuum."
        )

    lead = (
        build_result
        .materials_by_key[
            "lead"
        ]
    )

    lead_density = (
        lead.get_mass_density()
    )

    if abs(
        lead_density
        - 11.34
    ) > 1.0e-12:
        raise RuntimeError(
            "Unexpected OpenMC Lead density: "
            f"{lead_density}"
        )

    print()
    print("=" * 72)
    print("OPENMC V1.13 MODEL-CONSTRUCTION CHECK PASSED")
    print("=" * 72)

    print(
        "OpenMC version: "
        f"{build_result.openmc_version}"
    )

    print(
        "Cross sections: "
        f"{build_result.cross_sections_path}"
    )

    print(
        "Scenario ID:    "
        f"{scenario.scenario_id}"
    )

    print(
        "Settings profile: "
        f"{settings_profile.profile_name}"
    )

    print(
        "Physical source rate: "
        f"{build_result.physical_source_rate_per_s:.8e} "
        "photons/s"
    )

    print(
        "Source energies: "
        f"{build_result.source_energies_ev} eV"
    )

    print(
        "Source probabilities: "
        f"{build_result.source_probabilities}"
    )

    print("-" * 72)

    print(
        "Source cavity radius: "
        f"{scenario.geometry.source_cavity_radius_cm:.6f} cm"
    )

    print(
        "Outer shield radius:  "
        f"{scenario.geometry.outer_shield_radius_cm:.6f} cm"
    )

    print(
        "Evaluation shell:     "
        f"{build_result.evaluation_shell.inner_radius_cm:.6f} "
        "to "
        f"{build_result.evaluation_shell.outer_radius_cm:.6f} cm"
    )

    print(
        "Outer vacuum radius:  "
        f"{settings_profile.outer_boundary_radius_cm:.6f} cm"
    )

    print(
        "Geometry cell count:  "
        f"{len(geometry_cells)}"
    )

    print("-" * 72)

    print(
        "Lead density: "
        f"{lead_density:.6f} g/cm^3"
    )

    print(
        "Lead shield cells: "
        f"{len(build_result.shield_cells)}"
    )

    print(
        "Evaluation shell material: Vacuum"
    )

    print("-" * 72)

    print(
        "Run mode: "
        f"{build_result.model.settings.run_mode}"
    )

    print(
        "Photon transport: "
        f"{build_result.model.settings.photon_transport}"
    )

    print(
        "Electron treatment: "
        f"{build_result.model.settings.electron_treatment}"
    )

    print(
        "Atomic relaxation: "
        f"{build_result.model.settings.atomic_relaxation}"
    )

    print(
        "Particles per batch: "
        f"{build_result.model.settings.particles}"
    )

    print(
        "Batches: "
        f"{build_result.model.settings.batches}"
    )

    print(
        "Total configured histories: "
        f"{settings_profile.total_source_particles}"
    )

    print("-" * 72)

    print(
        "Exported materials: "
        f"{materials_path}"
    )

    print(
        "Exported geometry:  "
        f"{geometry_path}"
    )

    print(
        "Exported settings:  "
        f"{settings_path}"
    )

    print()
    print(
        "No particles were transported and no "
        "benchmark tallies were created."
    )

    print("=" * 72)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )