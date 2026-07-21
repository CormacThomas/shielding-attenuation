# Shared V1.10 plotting utilities.
#
# This module contains formatting, color, annotation, and figure-saving
# helpers shared by optimization and response plots.

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.legend import Legend

from plot_models import OptimizationPlotData

from typing import Literal


@dataclass(frozen=True)
class PlotTheme:
    # Shared visual design tokens for every project figure.
    #
    # The palette is intentionally restrained:
    #   - blue for primary engineering data
    #   - amber for limits and cautions
    #   - green for selected designs
    #   - neutral grays for structure and secondary information

    figure_background: str = "#1A1E21"
    axes_background: str = "#FFFFFF"

    text: str = "#BABABA"
    muted_text: str = "#BABABA"

    # Text and marks drawn inside white axes or table surfaces.
    axes_text: str = "#111827"
    axes_muted_text: str = "#475467"

    # Opaque feasibility-table colors.
    table_header_background: str = "#E9EEF5"
    table_header_text: str = "#344054"

    table_row_background: str = "#FFFFFF"
    table_alternate_row_background: str = "#F8FAFC"

    table_pass_background: str = "#DBEAFE"
    table_fail_background: str = "#FFEDD5"

    table_selected_background: str = "#DCFCE7"
    table_eligible_background: str = "#E8F0FE"
    table_rejected_background: str = "#FFF1E6"
    table_unavailable_background: str = "#F2F4F7"

    border: str = "#D0D5DD"
    grid: str = "#1C1C1C"

    primary: str = "#2563EB"
    secondary: str = "#0F766E"
    warning: str = "#D97706"
    selected: str = "#16A34A"

    success: str = "#16A34A"
    danger: str = "#DC2626"
    neutral: str = "#98A2B3"

    soft_fill: str = "#F2F4F7"


PLOT_THEME = PlotTheme()


def get_plot_colors() -> tuple[str, str, str]:
    # Preserve the existing three-color plotting interface while using
    # the project theme instead of Matplotlib's default color cycle.
    #
    # Existing callers interpret these colors as:
    #   primary data
    #   limit / comparison / secondary data
    #   selected design

    return (
        PLOT_THEME.primary,
        PLOT_THEME.warning,
        PLOT_THEME.selected,
    )


def apply_project_plot_style() -> None:
    # Apply the shared V1.10 visual theme to Matplotlib.
    #
    # Call this once before generating figures. The reproducible figure
    # script performs that setup for the authoritative project outputs.

    plt.rcParams.update(
        {
            # Figure and axes surfaces
            "figure.facecolor": PLOT_THEME.figure_background,
            "savefig.facecolor": PLOT_THEME.figure_background,
            "axes.facecolor": PLOT_THEME.axes_background,

            # Typography
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Segoe UI",
                "Inter",
                "Arial",
                "DejaVu Sans",
            ],
            "font.size": 10,
            "text.color": PLOT_THEME.text,

            # Figure titles
            "figure.titlesize": 15,
            "figure.titleweight": "semibold",

            # Axes titles and labels
            "axes.titlesize": 11,
            "axes.titleweight": "semibold",
            "axes.titlecolor": PLOT_THEME.text,
            "axes.labelsize": 10,
            "axes.labelweight": "medium",
            "axes.labelcolor": PLOT_THEME.text,

            # Ticks
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.color": PLOT_THEME.muted_text,
            "ytick.color": PLOT_THEME.muted_text,

            # Spines
            "axes.edgecolor": PLOT_THEME.border,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,

            # Grid
            "grid.color": PLOT_THEME.grid,
            "grid.linewidth": 0.8,
            "grid.alpha": 0.85,

            # Lines and patches
            "lines.linewidth": 2.2,
            "patch.linewidth": 0.8,

            # Legend
            "legend.fontsize": 9,
            "legend.frameon": True,
            "legend.fancybox": True,
            "legend.framealpha": 1.0,
            "legend.facecolor": PLOT_THEME.axes_background,
            "legend.edgecolor": PLOT_THEME.border,

            # Export
            "savefig.dpi": 300,
        }
    )


def apply_modern_figure_style(
    figure: Figure,
) -> None:
    # Give every figure the same subtle application-style background.

    figure.patch.set_facecolor(
        PLOT_THEME.figure_background
    )


def apply_modern_axes_style(
    axes: Axes,
    grid_axis: Literal["both", "x", "y"] = "both",
) -> None:
    # Apply consistent modern styling to one set of axes.
    #
    # Plot-specific functions remain responsible for deciding whether
    # logarithmic minor grids or special reference lines are needed.

    axes.set_facecolor(
        PLOT_THEME.axes_background
    )

    axes.set_axisbelow(
        True
    )

    axes.grid(
        True,
        axis=grid_axis,
        which="major",
        color=PLOT_THEME.grid,
        linewidth=0.8,
        alpha=0.85,
    )

    axes.spines["top"].set_visible(
        False
    )

    axes.spines["right"].set_visible(
        False
    )

    for spine_name in (
        "left",
        "bottom",
    ):
        axes.spines[spine_name].set_color(
            PLOT_THEME.border
        )

        axes.spines[spine_name].set_linewidth(
            0.8
        )

    axes.tick_params(
        axis="both",
        which="both",
        length=0,
        pad=6,
        colors=PLOT_THEME.muted_text,
    )


def style_legend(
    legend: Legend | None,
) -> None:
    # Make legends resemble light interface cards rather than default
    # Matplotlib boxes.

    if legend is None:
        return

    frame = legend.get_frame()

    frame.set_facecolor(
        PLOT_THEME.axes_background
    )

    frame.set_edgecolor(
        PLOT_THEME.border
    )

    frame.set_linewidth(
        0.8
    )

    frame.set_alpha(
        1.0
    )

    for legend_text in legend.get_texts():
        legend_text.set_color(
            PLOT_THEME.axes_text
        )


def format_optimization_mode(mode: str) -> str:
    return mode.replace("_", " ").title()


def format_plot_text(text: str) -> str:
    # Convert plain-text engineering notation into cleaner figure text.
    #
    # Internal calculation and CLI strings remain unchanged. This function
    # only improves typography in generated figures.

    return (
        text
        .replace("<=", "≤")
        .replace(">=", "≥")
        .replace("cm^2", "cm²")
        .replace("cm^3", "cm³")
    )


def create_plot_subtitle(
    plot_data: OptimizationPlotData,
    scenario_context: str | None = None,
) -> str:
    buildup_text = (
        "Yes" if plot_data.buildup_requested else "No"
    )

    target_description = format_plot_text(
        plot_data.target_description
    )

    subtitle_lines = []

    if (
        scenario_context is not None
        and scenario_context.strip() != ""
    ):
        subtitle_lines.append(
            scenario_context.strip()
        )

    subtitle_lines.extend(
        [
            target_description,
            (
                f"Objective: "
                f"{format_optimization_mode(plot_data.optimization_mode)}"
                f" | G-P buildup requested: {buildup_text}"
            ),
        ]
    )

    return "\n".join(
        subtitle_lines
    )


def get_failed_candidate_note(
    plot_data: OptimizationPlotData,
) -> str | None:
    failed_material_names = [
        candidate.material_name
        for candidate in plot_data.candidates
        if candidate.optimization_status == "FAILED"
    ]

    if len(failed_material_names) == 0:
        return None

    return (
        "Failed calculations excluded from numerical bars: "
        + ", ".join(failed_material_names)
        + "."
    )


def format_metric_value(value: float) -> str:
    # Six significant digits matches the existing engineering output tables.

    return f"{value:.6g}"


def format_plot_units(units: str) -> str:
    # Convert plain-text scientific units into cleaner figure labels.

    return units.replace(
        "cm^2",
        "cm²",
    )



def save_figure(
    figure: Figure,
    output_path: str | Path,
    dpi: int = 300,
) -> Path:
    # Save one Matplotlib figure.
    #
    # File format is determined from the output extension, such as:
    #   .png
    #   .svg
    #   .pdf

    path = Path(output_path)

    if path.suffix == "":
        raise ValueError(
            "Figure output path must include a file extension."
        )

    if dpi <= 0:
        raise ValueError(
            "Figure DPI must be greater than zero."
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        str(path),
        dpi=dpi,
        bbox_inches="tight",
    )

    return path


def save_figure_formats(
    figure: Figure,
    output_stem: str | Path,
    formats: tuple[str, ...] = ("png", "svg"),
    dpi: int = 300,
) -> list[Path]:
    # Save the same figure in multiple formats.
    #
    # output_stem must not include a suffix:
    #
    #   docs/figures/v1.10/cs137_required_thickness
    #
    # becomes:
    #
    #   cs137_required_thickness.png
    #   cs137_required_thickness.svg

    stem = Path(output_stem)

    if stem.suffix != "":
        raise ValueError(
            "Multi-format output stem must not include a file extension."
        )

    if len(formats) == 0:
        raise ValueError(
            "At least one figure format is required."
        )

    saved_paths = []

    for figure_format in formats:
        cleaned_format = figure_format.lower().strip().lstrip(".")

        if cleaned_format == "":
            raise ValueError(
                "Figure format cannot be empty."
            )

        output_path = stem.with_suffix(
            f".{cleaned_format}"
        )

        saved_path = save_figure(
            figure,
            output_path,
            dpi=dpi,
        )

        saved_paths.append(saved_path)

    return saved_paths