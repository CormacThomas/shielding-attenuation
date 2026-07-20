# Reproducible V1.10 portfolio figure generation.
#
# This script builds one documented Cs-137 shielding-design scenario and
# generates the complete V1.10 engineering figure set.
#
# Run from the project root with:
#
#     python examples/generate_v110_figures.py

from pathlib import Path
import sys



# Resolve project paths independently of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "docs"
    / "figures"
    / "v1.10"
)

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIRECTORY),
    )


# Select a noninteractive backend before importing pyplot or project
# plotting modules. This allows the script to run in terminals, CI jobs,
# and other environments without a display.
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from constraint_optimizer import optimize_material_selection
from material_library import get_material_library
from optimization_models import DesignConstraints
from plot_data import create_optimization_plot_data
from plotting import (
    plot_constraint_feasibility_matrix,
    plot_material_design_comparison,
    plot_response_vs_thickness,
    plot_thickness_mass_tradeoff,
    save_figure_formats,
)
from response_curve import create_response_curve
from source_library import create_isotope_source
from target_models import FluxTarget
from plotting_utils import apply_project_plot_style


# Fixed V1.10 portfolio scenario.
SOURCE_ACTIVITY_BQ = 3.7e10
DETECTOR_DISTANCE_CM = 100.0
TARGET_FLUX = 100.0

MAXIMUM_DESIGN_THICKNESS_CM = 20.0
MAXIMUM_MASS_PER_AREA_G_PER_CM2 = 120.0

RESPONSE_MINIMUM_THICKNESS_CM = 0.0
RESPONSE_MAXIMUM_THICKNESS_CM = 12.0
RESPONSE_SAMPLE_COUNT = 121

OUTPUT_FORMATS = (
    "png",
    "svg",
)


def save_and_close_figure(
    figure: Figure,
    output_name: str,
) -> list[Path]:
    # Save one figure in every authoritative V1.10 format and release
    # its Matplotlib resources immediately.

    saved_paths = save_figure_formats(
        figure=figure,
        output_stem=OUTPUT_DIRECTORY / output_name,
        formats=OUTPUT_FORMATS,
        dpi=300,
    )

    plt.close(
        figure
    )

    return saved_paths


def main() -> None:
    # Use Matplotlib's standard style so local user settings do not silently
    # change the project figures.

    plt.style.use(
        "default"
    )

    apply_project_plot_style()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    materials = get_material_library()

    source = create_isotope_source(
        "cs137",
        SOURCE_ACTIVITY_BQ,
    )

    target = FluxTarget(
        TARGET_FLUX
    )

    optimization_result = optimize_material_selection(
        source=source,
        materials=list(materials.values()),
        detector_distance=DETECTOR_DISTANCE_CM,
        target=target,
        constraints=DesignConstraints(
            max_thickness_cm=(
                MAXIMUM_DESIGN_THICKNESS_CM
            ),
            max_mass_per_area_g_per_cm2=(
                MAXIMUM_MASS_PER_AREA_G_PER_CM2
            ),
        ),
        optimization_mode="minimum_mass",
        calculation_max_thickness=(
            DETECTOR_DISTANCE_CM
        ),
        apply_buildup=True,
    )

    if optimization_result.best_candidate is None:
        raise RuntimeError(
            "The V1.10 portfolio scenario did not produce an "
            "eligible selected material."
        )

    best_candidate = (
        optimization_result.best_candidate
    )

    selected_material = (
        best_candidate
        .base_candidate
        .material
    )

    required_thickness_cm = (
        best_candidate
        .base_candidate
        .required_thickness
    )

    if required_thickness_cm is None:
        raise RuntimeError(
            "The selected V1.10 material is missing its "
            "required shielding thickness."
        )

    # The documented V1.10 scenario is expected to select lead. This check
    # prevents a future model or input change from silently generating a
    # mislabeled portfolio figure.
    if selected_material.key != "lead":
        raise RuntimeError(
            "The documented V1.10 scenario expected Lead, but selected "
            f"{selected_material.name}."
        )

    optimization_plot_data = (
        create_optimization_plot_data(
            optimization_result
        )
    )

    response_curve_result = create_response_curve(
        source=source,
        material=selected_material,
        detector_distance_cm=(
            DETECTOR_DISTANCE_CM
        ),
        minimum_thickness_cm=(
            RESPONSE_MINIMUM_THICKNESS_CM
        ),
        maximum_thickness_cm=(
            RESPONSE_MAXIMUM_THICKNESS_CM
        ),
        number_of_points=(
            RESPONSE_SAMPLE_COUNT
        ),
        apply_buildup=True,
        target=target,
        required_thickness_cm=(
            required_thickness_cm
        ),
    )

    figures = (
        (
            "cs137_material_design_comparison",
            plot_material_design_comparison(
                optimization_plot_data
            ),
        ),
        (
            "cs137_constraint_feasibility",
            plot_constraint_feasibility_matrix(
                optimization_plot_data
            ),
        ),
        (
            "cs137_thickness_mass_tradeoff",
            plot_thickness_mass_tradeoff(
                optimization_plot_data
            ),
        ),
        (
            "cs137_lead_response_vs_thickness",
            plot_response_vs_thickness(
                response_curve_result,
                logarithmic=True,
            ),
        ),
    )

    all_saved_paths: list[Path] = []

    for output_name, figure in figures:
        saved_paths = save_and_close_figure(
            figure,
            output_name,
        )

        all_saved_paths.extend(
            saved_paths
        )

    print(
        "\nV1.10 figure generation complete."
    )

    print(
        f"Selected material: {selected_material.name}"
    )

    print(
        "Required thickness: "
        f"{required_thickness_cm:.6g} cm"
    )

    print(
        f"Generated files: {len(all_saved_paths)}"
    )

    for saved_path in all_saved_paths:
        relative_path = saved_path.relative_to(
            PROJECT_ROOT
        )

        print(
            f"- {relative_path}"
        )


if __name__ == "__main__":
    main()