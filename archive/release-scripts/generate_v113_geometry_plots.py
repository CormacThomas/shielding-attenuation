# Generate the official V1.13 OpenMC geometry plots.
#
# This script constructs the production benchmark geometry
# from the authoritative scenario and OpenMC settings profile.
#
# It generates:
#
#   1. a full-domain view showing the evaluation shell;
#   2. a central-detail view showing the source cavity and
#      5 cm Lead shield.
#
# No particles are transported.
#
# Run inside the OpenMC Docker environment from the
# repository root:
#
#   python examples/generate_v113_geometry_plots.py


from __future__ import annotations


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

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "geometry_plot"
)


if str(SOURCE_DIRECTORY) not in sys.path:
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
from scenario_io import (
    load_scenario,
)


FULL_DOMAIN_FILENAME = (
    "v113_geometry_full_domain"
)

CENTRAL_DETAIL_FILENAME = (
    "v113_geometry_central_detail"
)


def prepare_output_directory() -> None:
    # Recreate only the dedicated geometry-plot directory.
    # Existing production transport and processed results
    # remain untouched.

    if OUTPUT_DIRECTORY.exists():
        shutil.rmtree(
            OUTPUT_DIRECTORY
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def create_cell_colors(
    model_build_result,
) -> dict:
    # Use the same colors in both views so every physical
    # region has a consistent visual meaning.

    cell_colors = {
        model_build_result.source_cavity_cell: (
            173,
            216,
            230,
        ),
        model_build_result.transport_void_cell: (
            246,
            247,
            249,
        ),
        model_build_result.evaluation_shell_cell: (
            230,
            126,
            34,
        ),
        model_build_result.exterior_void_cell: (
            218,
            229,
            240,
        ),
    }

    for shield_cell in (
        model_build_result.shield_cells
    ):
        cell_colors[
            shield_cell
        ] = (
            80,
            85,
            94,
        )

    return cell_colors


def apply_shared_plot_settings(
    plot,
    model_build_result,
) -> None:
    plot.type = "slice"
    plot.basis = "xy"

    plot.origin = (
        0.0,
        0.0,
        0.0,
    )

    plot.color_by = "cell"

    plot.colors = create_cell_colors(
        model_build_result
    )

    plot.background = (
        255,
        255,
        255,
    )

    # Any geometry overlap appears bright magenta rather
    # than being silently hidden.
    plot.show_overlaps = True

    plot.overlap_color = (
        255,
        0,
        255,
    )


def create_full_domain_plot(
    openmc_module,
    model_build_result,
):
    # Show the complete transport domain from the source
    # through the evaluation shell and outer vacuum boundary.
    #
    # At 1600 pixels over 220 cm, the 1 cm evaluation
    # shell is approximately seven pixels thick.

    plot = openmc_module.Plot(
        plot_id=1301,
        name=(
            "V1.13 production geometry — "
            "full domain"
        ),
    )

    plot.filename = (
        FULL_DOMAIN_FILENAME
    )

    plot.width = (
        220.0,
        220.0,
    )

    plot.pixels = (
        1600,
        1600,
    )

    apply_shared_plot_settings(
        plot=plot,
        model_build_result=(
            model_build_result
        ),
    )

    return plot


def create_central_detail_plot(
    openmc_module,
    model_build_result,
):
    # Magnify the central 16 × 16 cm region.
    #
    # This clearly resolves:
    #   - centered point-source location;
    #   - 1 cm vacuum cavity;
    #   - Lead shell from 1 to 6 cm;
    #   - surrounding transport vacuum.

    plot = openmc_module.Plot(
        plot_id=1302,
        name=(
            "V1.13 production geometry — "
            "central detail"
        ),
    )

    plot.filename = (
        CENTRAL_DETAIL_FILENAME
    )

    plot.width = (
        16.0,
        16.0,
    )

    plot.pixels = (
        1200,
        1200,
    )

    apply_shared_plot_settings(
        plot=plot,
        model_build_result=(
            model_build_result
        ),
    )

    return plot


def require_generated_plot(
    filename_stem: str,
) -> Path:
    plot_path = (
        OUTPUT_DIRECTORY
        / f"{filename_stem}.png"
    )

    if not plot_path.is_file():
        raise RuntimeError(
            "Expected OpenMC geometry plot was not "
            f"created: {plot_path}"
        )

    return plot_path


def main() -> int:
    prepare_output_directory()

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

    full_domain_plot = (
        create_full_domain_plot(
            openmc_module=openmc_module,
            model_build_result=(
                model_build_result
            ),
        )
    )

    central_detail_plot = (
        create_central_detail_plot(
            openmc_module=openmc_module,
            model_build_result=(
                model_build_result
            ),
        )
    )

    # Export the same model that drives V1.13 transport.
    model_build_result.model.export_to_xml(
        directory=OUTPUT_DIRECTORY
    )

    plots = openmc_module.Plots(
        [
            full_domain_plot,
            central_detail_plot,
        ]
    )

    plots.export_to_xml(
        OUTPUT_DIRECTORY
        / "plots.xml"
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 GEOMETRY PLOT GENERATION")
    print("=" * 72)

    print(
        f"Scenario ID: {scenario.scenario_id}"
    )

    print(
        "Source cavity radius: "
        f"{scenario.geometry.source_cavity_radius_cm:.3f} cm"
    )

    print(
        "Outer shield radius: "
        f"{scenario.geometry.outer_shield_radius_cm:.3f} cm"
    )

    print(
        "Evaluation shell: "
        f"{model_build_result.evaluation_shell.inner_radius_cm:.3f} "
        "to "
        f"{model_build_result.evaluation_shell.outer_radius_cm:.3f} cm"
    )

    print(
        "Outer boundary radius: "
        f"{settings_profile.outer_boundary_radius_cm:.3f} cm"
    )

    print("-" * 72)
    print(
        "Running OpenMC in geometry plotting mode."
    )
    print("-" * 72)

    openmc_module.plot_geometry(
        output=True,
        cwd=OUTPUT_DIRECTORY,
    )

    full_domain_path = (
        require_generated_plot(
            FULL_DOMAIN_FILENAME
        )
    )

    central_detail_path = (
        require_generated_plot(
            CENTRAL_DETAIL_FILENAME
        )
    )

    print()
    print("=" * 72)
    print("OPENMC V1.13 GEOMETRY PLOTS CREATED")
    print("=" * 72)

    print(
        "Full-domain plot:"
    )

    print(
        f"  {full_domain_path}"
    )

    print(
        "Central-detail plot:"
    )

    print(
        f"  {central_detail_path}"
    )

    print()
    print(
        "No particles were transported."
    )

    print("=" * 72)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )