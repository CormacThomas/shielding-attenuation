# Reproducible V1.12 isotope line-contribution figure.
#
# This script calculates the line-by-line collision-air-kerma
# response from a 1 Ci Co-60 source through 5 cm of Lead at
# an evaluation distance of 100 cm.
#
# Run from the repository root:
#
#   python examples/generate_v112_line_contribution_figure.py


from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIRECTORY = (
    PROJECT_ROOT
    / "src"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "docs"
    / "figures"
    / "v1.12"
)


if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


# Select a noninteractive backend before importing pyplot or
# project plotting modules.
import matplotlib

matplotlib.use("Agg")


import matplotlib.pyplot as plt

from air_response import (
    calculate_source_air_kerma_result,
)
from material_library import (
    get_material_library,
)
from models import Layer
from plotting import (
    plot_isotope_line_air_kerma_contributions,
    save_figure_formats,
)
from plotting_utils import (
    apply_project_plot_style,
)
from source_library import (
    create_isotope_source,
)
from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
)


SOURCE_ACTIVITY_BQ = 3.7e10

SHIELD_MATERIAL_KEY = "lead"
SHIELD_THICKNESS_CM = 5.0

DETECTOR_DISTANCE_CM = 100.0

OUTPUT_NAME = (
    "co60_photon_line_air_kerma_contributions"
)

OUTPUT_FORMATS = (
    "png",
    "svg",
)


SCENARIO_CONTEXT = (
    "Source: Co-60 | Activity: 1.00 Ci "
    "(3.70 × 10¹⁰ Bq) | Shield: 5.00 cm Lead "
    "| Evaluation distance: 100 cm | "
    "Response basis: collision air kerma in dry air"
)


def require_adjusted_total(
    value_gy_per_s: float | None,
) -> float:
    if value_gy_per_s is None:
        raise RuntimeError(
            "The Co-60 portfolio result is missing its "
            "G-P-adjusted collision-air-kerma total."
        )

    return value_gy_per_s


def main() -> None:
    # Reset Matplotlib before applying the authoritative project
    # figure style so local user settings cannot alter the output.

    plt.style.use(
        "default"
    )

    apply_project_plot_style()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    materials = get_material_library()

    lead = materials[
        SHIELD_MATERIAL_KEY
    ]

    source = create_isotope_source(
        "co60",
        SOURCE_ACTIVITY_BQ,
    )

    layers = [
        Layer(
            thickness=SHIELD_THICKNESS_CM,
            material=lead,
        )
    ]

    result = calculate_source_air_kerma_result(
        source=source,
        layers=layers,
        detector_distance_cm=(
            DETECTOR_DISTANCE_CM
        ),
        apply_buildup=True,
    )

    if result.buildup_status != "applied":
        raise RuntimeError(
            "The Co-60 portfolio case requires G-P "
            "exposure buildup to be applied successfully "
            "to every photon line."
        )

    adjusted_total_gy_per_s = (
        require_adjusted_total(
            result
            .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )
    )

    uncollided_total_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        )
    )

    adjusted_total_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            adjusted_total_gy_per_s
        )
    )

    figure = (
        plot_isotope_line_air_kerma_contributions(
            result=result,
            scenario_context=SCENARIO_CONTEXT,
        )
    )

    saved_paths = save_figure_formats(
        figure=figure,
        output_stem=(
            OUTPUT_DIRECTORY
            / OUTPUT_NAME
        ),
        formats=OUTPUT_FORMATS,
        dpi=300,
    )

    plt.close(
        figure
    )

    print()
    print(
        "V1.12 line-contribution figure generation "
        "complete."
    )

    print(
        f"Source: {result.source_name}"
    )

    print(
        f"Photon lines: {len(result.line_results)}"
    )

    print(
        "Shield: "
        f"{SHIELD_THICKNESS_CM:.2f} cm "
        f"{lead.name}"
    )

    print(
        "Uncollided collision air-kerma rate: "
        f"{uncollided_total_microgy_per_h:.6e} "
        "microGy/h"
    )

    print(
        "G-P-adjusted collision air-kerma rate: "
        f"{adjusted_total_microgy_per_h:.6e} "
        "microGy/h"
    )

    print(
        "Generated files:"
    )

    for saved_path in saved_paths:
        relative_path = saved_path.relative_to(
            PROJECT_ROOT
        )

        print(
            f"- {relative_path}"
        )


if __name__ == "__main__":
    main()