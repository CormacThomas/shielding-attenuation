# Generate the official V1.13 deterministic-versus-OpenMC
# benchmark figure from processed result files.
#
# This script has no OpenMC dependency.
#
# Run from the repository root:
#
#   python examples/generate_v113_benchmark_figure.py

from pathlib import Path
import sys


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "src"
)

PROCESSED_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "production_recovery"
    / "processed"
    / "final"
)

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "docs"
    / "figures"
    / "v1.13"
)

GEOMETRY_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.13"
    / "geometry_plot"
)

FULL_DOMAIN_GEOMETRY_PATH = (
    GEOMETRY_DIRECTORY
    / "v113_geometry_full_domain.png"
)

CENTRAL_DETAIL_GEOMETRY_PATH = (
    GEOMETRY_DIRECTORY
    / "v113_geometry_central_detail.png"
)


if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


import matplotlib

matplotlib.use("Agg")


import matplotlib.pyplot as plt

from openmc_benchmark_plot_data import (
    create_openmc_benchmark_plot_data,
)
from openmc_benchmark_plots import (
    plot_openmc_v113_benchmark,
    plot_v113_geometry_annotated,
)
from plotting import (
    save_figure_formats,
)
from plotting_utils import (
    apply_project_plot_style,
)
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import (
    FigureCanvasAgg,
)


def get_figure_axes_by_gid(
    figure: Figure,
    axes_gid: str,
) -> Axes:
    matches = [
        axes
        for axes in figure.axes
        if axes.get_gid() == axes_gid
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one figure axes with GID "
            f"{axes_gid!r}, but found {len(matches)}."
        )

    return matches[0]


def save_figure_panel_formats(
    figure: Figure,
    axes: Axes,
    output_stem: Path,
    formats: tuple[str, ...] = (
        "png",
        "svg",
    ),
    dpi: int = 300,
) -> list[Path]:
    # Save one axes region from the authoritative combined
    # figure without reimplementing the panel's plotting logic.

    if dpi <= 0:
        raise ValueError(
            "Panel export DPI must be greater than zero."
        )

    canvas = figure.canvas

    if not isinstance(
        canvas,
        FigureCanvasAgg,
    ):
        raise RuntimeError(
            "V1.13 panel export requires the Matplotlib "
            "Agg rendering backend."
        )

    canvas.draw()

    renderer = canvas.get_renderer()

    panel_bounds = axes.get_tightbbox(
        renderer
    )

    if panel_bounds is None:
        raise RuntimeError(
            "Could not determine the panel export bounds."
        )

    # Include comfortable space around titles, labels,
    # annotations, and the panel letter.
    expanded_bounds = panel_bounds.expanded(
        1.10,
        1.14,
    )

    bounds_inches = (
        expanded_bounds.transformed(
            figure.dpi_scale_trans.inverted()
        )
    )

    output_stem.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved_paths: list[Path] = []

    figure_text_visibility = [
        (
            figure_text,
            figure_text.get_visible(),
        )
        for figure_text in figure.texts
    ]

    for (
        figure_text,
        _,
    ) in figure_text_visibility:
        figure_text.set_visible(
            False
        )

    try:
        for output_format in formats:
            normalized_format = (
                output_format.lower().strip()
            )

            if normalized_format not in (
                "png",
                "svg",
            ):
                raise ValueError(
                    "V1.13 panel export supports only "
                    "PNG and SVG formats."
                )

            output_path = output_stem.with_suffix(
                f".{normalized_format}"
            )

            figure.savefig(
                output_path,
                format=normalized_format,
                dpi=dpi,
                bbox_inches=bounds_inches,
                facecolor=figure.get_facecolor(),
                edgecolor="none",
            )

            saved_paths.append(
                output_path
            )

    finally:
        for (
            figure_text,
            was_visible,
        ) in figure_text_visibility:
            figure_text.set_visible(
                was_visible
            )

    return saved_paths


def main() -> int:
    plt.style.use(
        "default"
    )

    apply_project_plot_style()

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

    geometry_figure = (
        plot_v113_geometry_annotated(
            full_domain_image_path=(
                FULL_DOMAIN_GEOMETRY_PATH
            ),
            central_detail_image_path=(
                CENTRAL_DETAIL_GEOMETRY_PATH
            ),
        )
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    geometry_saved_paths = save_figure_formats(
        figure=geometry_figure,
        output_stem=(
            OUTPUT_DIRECTORY
            / "v113_geometry_annotated"
        ),
        formats=(
            "png",
            "svg",
        ),
        dpi=300,
    )

    plt.close(
        geometry_figure
    )


    benchmark_figure = (
        plot_openmc_v113_benchmark(
            plot_data=plot_data,
            full_domain_geometry_path=(
                FULL_DOMAIN_GEOMETRY_PATH
            ),
            central_detail_geometry_path=(
                CENTRAL_DETAIL_GEOMETRY_PATH
            ),
        )
    )

    benchmark_saved_paths = save_figure_formats(
        figure=benchmark_figure,
        output_stem=(
            OUTPUT_DIRECTORY
            / "cs137_lead_openmc_benchmark"
        ),
        formats=(
            "png",
            "svg",
        ),
        dpi=300,
    )

    spectrum_axes = get_figure_axes_by_gid(
        benchmark_figure,
        "v113_panel_spectrum",
    )

    response_axes = get_figure_axes_by_gid(
        benchmark_figure,
        "v113_panel_response",
    )

    summary_axes = get_figure_axes_by_gid(
        benchmark_figure,
        "v113_panel_summary",
    )

    spectrum_saved_paths = (
        save_figure_panel_formats(
            figure=benchmark_figure,
            axes=spectrum_axes,
            output_stem=(
                OUTPUT_DIRECTORY
                / "v113_photon_spectrum"
            ),
        )
    )

    response_saved_paths = (
        save_figure_panel_formats(
            figure=benchmark_figure,
            axes=response_axes,
            output_stem=(
                OUTPUT_DIRECTORY
                / "v113_response_comparison"
            ),
        )
    )

    summary_saved_paths = (
        save_figure_panel_formats(
            figure=benchmark_figure,
            axes=summary_axes,
            output_stem=(
                OUTPUT_DIRECTORY
                / "v113_benchmark_summary"
            ),
        )
    )

    plt.close(
        benchmark_figure
    )

    all_saved_paths = (
        geometry_saved_paths
        + spectrum_saved_paths
        + response_saved_paths
        + summary_saved_paths
        + benchmark_saved_paths
    )

    print()
    print(
        "V1.13 benchmark figure generation complete."
    )

    for output_path in all_saved_paths:
        print(
            "- "
            f"{output_path.relative_to(REPOSITORY_ROOT)}"
        )

    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )