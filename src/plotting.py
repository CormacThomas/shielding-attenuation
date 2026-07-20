# V1.10 engineering visualization.
#
# This module renders validated optimization and response-curve data using
# Matplotlib.
#
# Plotting functions accept structured plot-data objects. They do not rerun
# attenuation calculations, minimum-thickness calculations, or optimization.
#
# Current V1.10 figures:
#   - required shielding thickness by material
#   - mass per area by material
#   - relative cost index per area by material
#
# Later V1.10 stages will add:
#   - thickness-versus-mass Pareto plot
#   - photon flux versus shielding thickness

import math
from collections.abc import Callable
from pathlib import Path
import textwrap
from matplotlib.transforms import Bbox
from matplotlib.axes import Axes

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import to_rgba

from plot_data import (
    create_constraint_feasibility_rows,
    create_pareto_points,
    get_successful_plot_candidates,
)

from plot_models import (
    ConstraintCheckStatus,
    MaterialFeasibilityRow,
    MaterialPlotPoint,
    OptimizationPlotData,
    ResponseCurvePoint,
    ResponseCurveResult,
)


MetricGetter = Callable[[MaterialPlotPoint], float | None]

FeasibilityGetter = Callable[
    [MaterialFeasibilityRow],
    ConstraintCheckStatus,
]

def get_plot_colors() -> tuple[str, str, str]:
    # Use the active Matplotlib style's default color cycle rather than
    # hard-coding a project-specific color palette.

    color_values = (
        plt.rcParams["axes.prop_cycle"]
        .by_key()
        .get("color", [])
    )

    if len(color_values) >= 3:
        return (
            color_values[0],
            color_values[1],
            color_values[2],
        )

    return "C0", "C1", "C2"


def format_optimization_mode(mode: str) -> str:
    return mode.replace("_", " ").title()


def create_plot_subtitle(
    plot_data: OptimizationPlotData,
) -> str:
    buildup_text = (
        "Yes" if plot_data.buildup_requested else "No"
    )

    return (
        f"{plot_data.target_description}\n"
        f"Objective: "
        f"{format_optimization_mode(plot_data.optimization_mode)}"
        f" | G-P buildup requested: {buildup_text}"
    )


def get_metric_values(
    plot_data: OptimizationPlotData,
    metric_getter: MetricGetter,
) -> list[tuple[MaterialPlotPoint, float]]:
    # Return all successfully calculated candidates with their metric values.
    #
    # Both ELIGIBLE and REJECTED candidates are included because both have
    # valid physical design calculations. FAILED candidates are excluded from
    # numerical bars and identified in a figure note.

    successful_candidates = get_successful_plot_candidates(
        plot_data
    )

    candidate_values = []

    for candidate in successful_candidates:
        value = metric_getter(candidate)

        if value is None:
            raise ValueError(
                f"Successful candidate {candidate.material_name} "
                "is missing a required plot metric."
            )

        if value < 0:
            raise ValueError(
                f"Plot metric for {candidate.material_name} "
                "cannot be negative."
            )

        candidate_values.append((candidate, value))

    if len(candidate_values) == 0:
        raise ValueError(
            "At least one successfully calculated candidate is required "
            "to create a metric chart."
        )

    candidate_values.sort(
        key=lambda item: (
            item[1],
            item[0].material_key,
        )
    )

    return candidate_values


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


def require_candidate_metric(
    candidate: MaterialPlotPoint,
    value: float | None,
    metric_name: str,
) -> float:
    # Return a required numerical metric for a successfully calculated
    # material candidate.
    #
    # Successful candidates should already contain all three comparison
    # metrics. This helper makes that requirement explicit for plotting
    # and type checking.

    if value is None:
        raise ValueError(
            f"Candidate {candidate.material_name} is missing "
            f"{metric_name}."
        )

    if value < 0:
        raise ValueError(
            f"Candidate {candidate.material_name} has a negative "
            f"{metric_name}."
        )

    return value


def get_material_comparison_candidates(
    plot_data: OptimizationPlotData,
) -> list[MaterialPlotPoint]:
    # Return successfully calculated materials in one shared order.
    #
    # Materials are ordered from smallest to largest required thickness.
    # That ordering is preserved across the thickness, mass, and cost
    # panels so every material remains on the same row.

    candidates = get_successful_plot_candidates(
        plot_data
    )

    if len(candidates) == 0:
        raise ValueError(
            "At least one successfully calculated material is required "
            "for the material design comparison."
        )

    for candidate in candidates:
        require_candidate_metric(
            candidate,
            candidate.required_thickness_cm,
            "required thickness",
        )

        require_candidate_metric(
            candidate,
            candidate.mass_per_area_g_per_cm2,
            "mass per area",
        )

        require_candidate_metric(
            candidate,
            candidate.relative_cost_index_per_area,
            "relative cost index per area",
        )

    candidates.sort(
        key=lambda candidate: (
            require_candidate_metric(
                candidate,
                candidate.required_thickness_cm,
                "required thickness",
            ),
            candidate.material_key,
        )
    )

    return candidates


def plot_material_comparison_panel(
    axes: Axes,
    candidates: list[MaterialPlotPoint],
    metric_getter: MetricGetter,
    metric_name: str,
    panel_title: str,
    x_axis_label: str,
    constraint_value: float | None = None,
    constraint_units: str = "",
) -> None:
    # Render one panel of the combined material comparison.
    #
    # All materials use the same base bar style. Overall optimization
    # eligibility is deliberately not encoded here because the panel
    # displays only one engineering metric.
    #
    # The selected material receives a green outline.
    # Values beyond an active limit fall inside a lightly shaded region.

    base_color, constraint_color, selected_color = (
        get_plot_colors()
    )

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    values = [
        require_candidate_metric(
            candidate,
            metric_getter(candidate),
            metric_name,
        )
        for candidate in candidates
    ]

    maximum_reference_value = max(values)

    if constraint_value is not None:
        if constraint_value <= 0:
            raise ValueError(
                "Displayed comparison constraints must be greater than zero."
            )

        maximum_reference_value = max(
            maximum_reference_value,
            constraint_value,
        )

    if maximum_reference_value == 0:
        maximum_reference_value = 1.0

    x_upper_limit = maximum_reference_value * 1.18

    axes.set_xlim(
        0.0,
        x_upper_limit,
    )

    # Draw the constraint region before the bars.
    if constraint_value is not None:
        axes.axvspan(
            constraint_value,
            x_upper_limit,
            color=constraint_color,
            alpha=0.07,
            zorder=0,
        )

        axes.axvline(
            constraint_value,
            color=constraint_color,
            linestyle="--",
            linewidth=1.5,
            zorder=1,
        )

        constraint_label = (
            f"Limit: {constraint_value:.6g}"
        )

        if constraint_units.strip() != "":
            constraint_label = (
                constraint_label
                + f" {constraint_units}"
            )

        axes.text(
            constraint_value,
            1.015,
            constraint_label,
            transform=axes.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=8,
            color=constraint_color,
        )

    y_positions = list(
        range(len(candidates))
    )

    for y_position, candidate, value in zip(
        y_positions,
        candidates,
        values,
    ):
        if candidate.is_selected:
            edge_color = selected_color
            line_width = 2.7
        else:
            edge_color = text_color
            line_width = 0.8

        axes.barh(
            y_position,
            value,
            height=0.68,
            color=base_color,
            alpha=0.82,
            edgecolor=edge_color,
            linewidth=line_width,
            zorder=2,
        )

        axes.annotate(
            format_metric_value(value),
            xy=(
                value,
                y_position,
            ),
            xytext=(5, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8,
            zorder=3,
        )

    axes.set_title(
        panel_title,
        fontsize=11,
        fontweight="bold",
        pad=12,
    )

    axes.set_xlabel(
        x_axis_label,
        fontsize=9,
    )

    axes.xaxis.grid(
        True,
        linestyle=":",
        alpha=0.35,
    )

    axes.set_axisbelow(True)


def format_constraint_check_status(
    status: ConstraintCheckStatus,
) -> str:
    # Convert internal constraint-check states into clear table labels.

    if status == "PASS":
        return "PASS"

    if status == "FAIL":
        return "FAIL"

    if status == "INACTIVE":
        return "—"

    if status == "UNAVAILABLE":
        return "N/A"

    raise ValueError(
        f"Unsupported constraint-check status: {status}"
    )


def format_overall_feasibility_result(
    row: MaterialFeasibilityRow,
) -> str:
    # Describe the optimizer's final decision for one material.

    if row.is_selected:
        return "SELECTED"

    if row.optimization_status == "ELIGIBLE":
        return "ELIGIBLE"

    if row.optimization_status == "REJECTED":
        return "REJECTED"

    if row.optimization_status == "FAILED":
        return "FAILED"

    raise ValueError(
        f"Unsupported optimization status: "
        f"{row.optimization_status}"
    )


def get_active_feasibility_columns(
    plot_data: OptimizationPlotData,
) -> list[tuple[str, FeasibilityGetter]]:
    constraints = plot_data.constraints

    columns: list[
        tuple[str, FeasibilityGetter]
    ] = []

    if constraints.max_thickness_cm is not None:
        columns.append(
            (
                (
                    "Thickness\n"
                    f"≤ {constraints.max_thickness_cm:.6g} cm"
                ),
                lambda row: row.thickness_status,
            )
        )

    if (
        constraints.max_mass_per_area_g_per_cm2
        is not None
    ):
        columns.append(
            (
                (
                    "Mass per area\n"
                    f"≤ "
                    f"{constraints.max_mass_per_area_g_per_cm2:.6g} "
                    "g/cm²"
                ),
                lambda row: row.mass_status,
            )
        )

    if (
        constraints.max_relative_cost_index_per_area
        is not None
    ):
        columns.append(
            (
                (
                    "Relative cost\n"
                    f"≤ "
                    f"{constraints.max_relative_cost_index_per_area:.6g}"
                ),
                lambda row: row.cost_status,
            )
        )

    if len(columns) == 0:
        raise ValueError(
            "The constraint-feasibility matrix requires at least "
            "one active engineering constraint."
        )

    return columns


def get_response_point_at_thickness(
    curve_result: ResponseCurveResult,
    thickness_cm: float,
    tolerance: float = 1.0e-12,
) -> ResponseCurvePoint:
    # Find the response-curve point corresponding to an exact design
    # thickness inserted by response_curve.create_thickness_samples().

    for point in curve_result.points:
        if abs(point.thickness_cm - thickness_cm) <= tolerance:
            return point

    raise ValueError(
        f"Response curve does not contain the required thickness "
        f"{thickness_cm:.6g} cm."
    )


def create_status_legend(
    plot_data: OptimizationPlotData,
    constraint_handle,
) -> list:
    eligible_color, rejected_color, selected_color = (
        get_plot_colors()
    )

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    handles = [
        Patch(
            facecolor=eligible_color,
            edgecolor=text_color,
            label="Eligible",
        )
    ]

    has_rejected_candidate = any(
        candidate.optimization_status == "REJECTED"
        for candidate in plot_data.candidates
    )

    if has_rejected_candidate:
        handles.append(
            Patch(
                facecolor=rejected_color,
                edgecolor=text_color,
                hatch="//",
                alpha=0.55,
                label="Rejected by constraint",
            )
        )

    if plot_data.selected_material_key is not None:
        handles.append(
            Patch(
                facecolor="none",
                edgecolor=selected_color,
                linewidth=2.5,
                label="Selected design",
            )
        )

    if constraint_handle is not None:
        handles.append(constraint_handle)

    return handles


def plot_horizontal_metric_chart(
    plot_data: OptimizationPlotData,
    metric_getter: MetricGetter,
    title: str,
    x_axis_label: str,
    constraint_value: float | None = None,
    constraint_label: str | None = None,
    footnote: str | None = None,
    logarithmic: bool = False,
) -> Figure:
    # Generic horizontal engineering metric chart.
    #
    # Candidates are sorted from smallest to largest metric value.
    #
    # Visual encoding:
    #   - eligible candidate: normal bar
    #   - rejected candidate: lighter hatched bar
    #   - selected candidate: emphasized outline
    #   - active constraint: vertical dashed line
    #
    # FAILED candidates do not receive invented numerical bars.

    candidate_values = get_metric_values(
        plot_data,
        metric_getter,
    )

    if logarithmic:
        nonpositive_values = [
            value
            for _, value in candidate_values
            if value <= 0
        ]

        if len(nonpositive_values) > 0:
            raise ValueError(
                "A logarithmic metric chart requires every value "
                "to be greater than zero."
            )

    figure_height = max(
        5.0,
        2.2 + 0.55 * len(candidate_values),
    )

    figure, axes = plt.subplots(
        figsize=(10.5, figure_height)
    )

    eligible_color, rejected_color, selected_color = (
        get_plot_colors()
    )

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    material_names = [
        candidate.material_name
        for candidate, _ in candidate_values
    ]

    y_positions = list(range(len(candidate_values)))

    for y_position, (candidate, value) in zip(
        y_positions,
        candidate_values,
    ):
        if candidate.optimization_status == "ELIGIBLE":
            face_color = eligible_color
            bar_alpha = 1.0
            hatch_pattern = None
        else:
            face_color = rejected_color
            bar_alpha = 0.55
            hatch_pattern = "//"

        if candidate.is_selected:
            edge_color = selected_color
            line_width = 2.5
        else:
            edge_color = text_color
            line_width = 0.8

        axes.barh(
            y_position,
            value,
            color=face_color,
            alpha=bar_alpha,
            hatch=hatch_pattern,
            edgecolor=edge_color,
            linewidth=line_width,
            height=0.7,
        )

        axes.annotate(
            format_metric_value(value),
            xy=(value, y_position),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=9,
        )

    axes.set_yticks(y_positions)
    axes.set_yticklabels(material_names)

    # Because candidates are sorted from smallest to largest, invert the axis
    # so the best numerical value appears at the top.
    axes.invert_yaxis()

    axes.set_xlabel(x_axis_label)
    axes.set_ylabel("Shielding material")

    axes.set_title(
        create_plot_subtitle(plot_data),
        loc="left",
        fontsize=9,
        pad=12,
    )

    figure.suptitle(
        title,
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    axes.xaxis.grid(
        True,
        linestyle=":",
        alpha=0.45,
    )

    axes.set_axisbelow(True)

    constraint_handle = None

    if constraint_value is not None:
        if constraint_value <= 0:
            raise ValueError(
                "Displayed constraint values must be greater than zero."
            )

        displayed_constraint_label = (
            constraint_label
            if constraint_label is not None
            else f"Constraint: {constraint_value:.6g}"
        )

        constraint_handle = axes.axvline(
            constraint_value,
            linestyle="--",
            linewidth=1.5,
            label=displayed_constraint_label,
        )

    if logarithmic:
        axes.set_xscale("log")

    axes.margins(x=0.12)

    legend_handles = create_status_legend(
        plot_data,
        constraint_handle,
    )

    axes.legend(
        handles=legend_handles,
        loc="best",
        frameon=True,
    )

    figure_notes = []

    failed_candidate_note = get_failed_candidate_note(
        plot_data
    )

    if failed_candidate_note is not None:
        figure_notes.append(failed_candidate_note)

    if footnote is not None:
        figure_notes.append(footnote)

    bottom_margin = 0.08

    if len(figure_notes) > 0:
        wrapped_notes = [
            textwrap.fill(note, width=125)
            for note in figure_notes
        ]

        figure.text(
            0.01,
            0.015,
            "\n".join(wrapped_notes),
            ha="left",
            va="bottom",
            fontsize=8,
        )

        bottom_margin = 0.14

    figure.subplots_adjust(
        left=0.29,
        right=0.92,
        top=0.84,
        bottom=bottom_margin,
    )

    return figure


def plot_required_thickness(
    plot_data: OptimizationPlotData,
) -> Figure:
    return plot_horizontal_metric_chart(
        plot_data=plot_data,
        metric_getter=(
            lambda candidate:
            candidate.required_thickness_cm
        ),
        title="Required Shielding Thickness by Material",
        x_axis_label="Required thickness (cm)",
        constraint_value=(
            plot_data.constraints.max_thickness_cm
        ),
        constraint_label=(
            None
            if plot_data.constraints.max_thickness_cm is None
            else (
                "Maximum design thickness: "
                f"{plot_data.constraints.max_thickness_cm:.6g} cm"
            )
        ),
    )


def plot_mass_per_area(
    plot_data: OptimizationPlotData,
) -> Figure:
    return plot_horizontal_metric_chart(
        plot_data=plot_data,
        metric_getter=(
            lambda candidate:
            candidate.mass_per_area_g_per_cm2
        ),
        title="Shield Mass per Unit Area by Material",
        x_axis_label="Mass per area (g/cm²)",
        constraint_value=(
            plot_data
            .constraints
            .max_mass_per_area_g_per_cm2
        ),
        constraint_label=(
            None
            if (
                plot_data
                .constraints
                .max_mass_per_area_g_per_cm2
                is None
            )
            else (
                "Maximum mass per area: "
                f"{plot_data.constraints.max_mass_per_area_g_per_cm2:.6g} "
                "g/cm²"
            )
        ),
    )


def plot_relative_cost(
    plot_data: OptimizationPlotData,
    logarithmic: bool = False,
) -> Figure:
    return plot_horizontal_metric_chart(
        plot_data=plot_data,
        metric_getter=(
            lambda candidate:
            candidate.relative_cost_index_per_area
        ),
        title="Relative Cost Index per Area by Material",
        x_axis_label="Relative cost index per area",
        constraint_value=(
            plot_data
            .constraints
            .max_relative_cost_index_per_area
        ),
        constraint_label=(
            None
            if (
                plot_data
                .constraints
                .max_relative_cost_index_per_area
                is None
            )
            else (
                "Maximum relative cost index per area: "
                f"{plot_data.constraints.max_relative_cost_index_per_area:.6g}"
            )
        ),
        footnote=(
            "Relative cost values are simplified comparative indices based "
            "on user-editable material assumptions. They are not currency, "
            "market prices, or procurement estimates."
        ),
        logarithmic=logarithmic,
    )


def plot_constraint_feasibility_matrix(
    plot_data: OptimizationPlotData,
) -> Figure:
    # Show whether every material satisfies each active engineering
    # constraint independently.
    #
    # This figure is intentionally table-like. It answers:
    #
    #   Why was each material eligible or rejected?
    #
    # It does not use overall eligibility to describe an individual metric.

    feasibility_rows = (
        create_constraint_feasibility_rows(
            plot_data
        )
    )

    active_columns = get_active_feasibility_columns(
        plot_data
    )

    if len(feasibility_rows) == 0:
        raise ValueError(
            "At least one material is required for the "
            "constraint-feasibility matrix."
        )

    column_labels = [
        "Material",
        *[
            label
            for label, _ in active_columns
        ],
        "Overall result",
    ]

    cell_text = []

    for row in feasibility_rows:
        row_text = [
            row.material_name,
        ]

        for _, status_getter in active_columns:
            status = status_getter(row)

            row_text.append(
                format_constraint_check_status(
                    status
                )
            )

        row_text.append(
            format_overall_feasibility_result(
                row
            )
        )

        cell_text.append(row_text)

    figure_height = max(
        5.2,
        2.8 + 0.48 * len(feasibility_rows),
    )

    figure, axes = plt.subplots(
        figsize=(11.5, figure_height)
    )

    axes.axis("off")

    pass_color, fail_color, selected_color = (
        get_plot_colors()
    )

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    number_of_constraint_columns = len(
        active_columns
    )

    column_widths = (
        [0.34]
        + [0.19] * number_of_constraint_columns
        + [0.18]
    )

    feasibility_table = axes.table(
        cellText=cell_text,
        colLabels=column_labels,
        cellLoc="center",
        colLoc="center",
        colWidths=column_widths,
        bbox=Bbox.from_bounds(
            0.0,
            0.0,
            1.0,
            1.0,
        ),
    )

    feasibility_table.auto_set_font_size(
        False
    )

    feasibility_table.set_fontsize(9.5)

    table_cells = (
        feasibility_table.get_celld()
    )

    for (
        table_row_index,
        table_column_index,
    ), cell in table_cells.items():
        cell.set_edgecolor(
            to_rgba(text_color, 0.25)
        )

        cell.set_linewidth(0.8)

        # Header row.
        if table_row_index == 0:
            cell.set_text_props(
                fontweight="bold"
            )

            cell.set_facecolor(
                to_rgba(text_color, 0.07)
            )

            continue

        feasibility_row = feasibility_rows[
            table_row_index - 1
        ]

        # Material-name column.
        if table_column_index == 0:
            cell.set_text_props(
                horizontalalignment="left",
            )

            if feasibility_row.is_selected:
                cell.set_text_props(
                    fontweight="bold"
                )

            continue

        # Independent constraint columns.
        if (
            table_column_index
            <= number_of_constraint_columns
        ):
            _, status_getter = active_columns[
                table_column_index - 1
            ]

            status = status_getter(
                feasibility_row
            )

            if status == "PASS":
                cell.set_facecolor(
                    to_rgba(pass_color, 0.18)
                )

                cell.set_text_props(
                    fontweight="bold"
                )

            elif status == "FAIL":
                cell.set_facecolor(
                    to_rgba(fail_color, 0.18)
                )

                cell.set_text_props(
                    fontweight="bold"
                )

            elif status == "UNAVAILABLE":
                cell.set_facecolor(
                    to_rgba(text_color, 0.07)
                )

            continue

        # Overall-result column.
        if feasibility_row.is_selected:
            cell.set_facecolor(
                to_rgba(selected_color, 0.22)
            )

            cell.set_text_props(
                fontweight="bold"
            )

        elif (
            feasibility_row.optimization_status
            == "ELIGIBLE"
        ):
            cell.set_facecolor(
                to_rgba(pass_color, 0.13)
            )

        elif (
            feasibility_row.optimization_status
            == "REJECTED"
        ):
            cell.set_facecolor(
                to_rgba(fail_color, 0.13)
            )

        elif (
            feasibility_row.optimization_status
            == "FAILED"
        ):
            cell.set_facecolor(
                to_rgba(text_color, 0.07)
            )

    axes.set_title(
        create_plot_subtitle(plot_data),
        loc="left",
        fontsize=9,
        pad=14,
    )

    figure.suptitle(
        "Engineering Constraint Feasibility by Material",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    figure_note = (
        "Each constraint is evaluated independently. "
        "A material is eligible only when it passes every "
        "active engineering constraint."
    )

    if plot_data.selection_reason is not None:
        figure_note = (
            figure_note
            + " "
            + plot_data.selection_reason
        )

    figure.text(
        0.08,
        0.025,
        textwrap.fill(
            figure_note,
            width=140,
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
    )

    figure.subplots_adjust(
        left=0.08,
        right=0.95,
        top=0.81,
        bottom=0.14,
    )

    return figure


def plot_material_design_comparison(
    plot_data: OptimizationPlotData,
) -> Figure:
    # Compare the three primary engineering metrics using aligned panels.
    #
    # This figure answers:
    #
    #   How do the candidate shielding materials compare numerically?
    #
    # Constraint pass/fail status is handled separately by the
    # constraint-feasibility matrix.

    candidates = get_material_comparison_candidates(
        plot_data
    )

    figure_height = max(
        6.2,
        2.6 + 0.52 * len(candidates),
    )

    figure, (
        thickness_axes,
        mass_axes,
        cost_axes,
    ) = plt.subplots(
        nrows=1,
        ncols=3,
        figsize=(16.0, figure_height),
        sharey=True,
    )

    plot_material_comparison_panel(
        axes=thickness_axes,
        candidates=candidates,
        metric_getter=(
            lambda candidate:
            candidate.required_thickness_cm
        ),
        metric_name="required thickness",
        panel_title="Required Thickness",
        x_axis_label="Thickness (cm)",
        constraint_value=(
            plot_data.constraints.max_thickness_cm
        ),
        constraint_units="cm",
    )

    plot_material_comparison_panel(
        axes=mass_axes,
        candidates=candidates,
        metric_getter=(
            lambda candidate:
            candidate.mass_per_area_g_per_cm2
        ),
        metric_name="mass per area",
        panel_title="Mass per Unit Area",
        x_axis_label="Mass per area (g/cm²)",
        constraint_value=(
            plot_data
            .constraints
            .max_mass_per_area_g_per_cm2
        ),
        constraint_units="g/cm²",
    )

    plot_material_comparison_panel(
        axes=cost_axes,
        candidates=candidates,
        metric_getter=(
            lambda candidate:
            candidate.relative_cost_index_per_area
        ),
        metric_name="relative cost index per area",
        panel_title="Relative Cost Index",
        x_axis_label="Relative cost index per area",
        constraint_value=(
            plot_data
            .constraints
            .max_relative_cost_index_per_area
        ),
    )

    material_names = [
        candidate.material_name
        for candidate in candidates
    ]

    y_positions = list(
        range(len(candidates))
    )

    thickness_axes.set_yticks(
        y_positions
    )

    thickness_axes.set_yticklabels(
        material_names,
        fontsize=9,
    )

    thickness_axes.set_ylabel(
        "Shielding material",
        fontsize=10,
    )

    # The candidates are sorted from smallest to largest required
    # thickness. Invert the shared y-axis so the smallest value appears
    # at the top.
    thickness_axes.invert_yaxis()

    # Only the first panel needs visible material labels.
    mass_axes.tick_params(
        axis="y",
        labelleft=False,
    )

    cost_axes.tick_params(
        axis="y",
        labelleft=False,
    )

    # Bold the selected material name.
    for tick_label, candidate in zip(
        thickness_axes.get_yticklabels(),
        candidates,
    ):
        if candidate.is_selected:
            tick_label.set_fontweight(
                "bold"
            )

    figure.suptitle(
        "Shielding Material Design Comparison",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    figure.text(
        0.08,
        0.91,
        create_plot_subtitle(plot_data),
        ha="left",
        va="top",
        fontsize=9.5,
    )

    _, _, selected_color = get_plot_colors()

    legend_handles = []

    if plot_data.selected_material_key is not None:
        legend_handles.append(
            Patch(
                facecolor="none",
                edgecolor=selected_color,
                linewidth=2.7,
                label="Selected design",
            )
        )

    has_active_constraint = (
        plot_data.constraints.max_thickness_cm is not None
        or (
            plot_data
            .constraints
            .max_mass_per_area_g_per_cm2
            is not None
        )
        or (
            plot_data
            .constraints
            .max_relative_cost_index_per_area
            is not None
        )
    )

    if has_active_constraint:
        _, constraint_color, _ = (
            get_plot_colors()
        )

        legend_handles.append(
            Line2D(
                [0],
                [0],
                color=constraint_color,
                linestyle="--",
                linewidth=1.5,
                label="Engineering limit",
            )
        )

    if len(legend_handles) > 0:
        figure.legend(
            handles=legend_handles,
            loc="upper right",
            bbox_to_anchor=(
                0.95,
                0.925,
            ),
            frameon=True,
            ncols=len(legend_handles),
        )

    figure_notes = [
        (
            "Lower values indicate less required shielding thickness, "
            "less shield mass per unit area, or lower relative material cost."
        ),
        (
            "Relative cost indices are simplified comparative values, "
            "not currency or procurement estimates."
        ),
    ]

    failed_candidate_note = get_failed_candidate_note(
        plot_data
    )

    if failed_candidate_note is not None:
        figure_notes.append(
            failed_candidate_note
        )

    if plot_data.selection_reason is not None:
        figure_notes.append(
            plot_data.selection_reason
        )

    figure.text(
        0.08,
        0.025,
        "\n".join(
            textwrap.fill(
                note,
                width=180,
            )
            for note in figure_notes
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
    )

    figure.subplots_adjust(
        left=0.22,
        right=0.96,
        top=0.79,
        bottom=0.16,
        wspace=0.18,
    )

    return figure


def plot_thickness_mass_pareto(
    plot_data: OptimizationPlotData,
    eligible_only: bool = True,
) -> Figure:
    # Plot required thickness against mass per unit area.
    #
    # Lower-left is preferred:
    #   - smaller required thickness
    #   - smaller mass per area
    #
    # By default, Pareto membership is calculated among eligible designs
    # only. Rejected candidates remain visible, but they do not define the
    # feasible engineering Pareto front.

    pareto_points = create_pareto_points(
        plot_data,
        eligible_only=eligible_only,
    )

    if len(pareto_points) == 0:
        raise ValueError(
            "At least one successful candidate is required "
            "for the Pareto plot."
        )

    figure, axes = plt.subplots(
        figsize=(10.5, 7.5)
    )

    eligible_color, rejected_color, selected_color = (
        get_plot_colors()
    )

    eligible_marker = MarkerStyle("o")
    rejected_marker = MarkerStyle("X")

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )




    maximum_point_thickness = max(
        point.thickness_cm
        for point in pareto_points
    )

    maximum_point_mass = max(
        point.mass_per_area_g_per_cm2
        for point in pareto_points
    )

    maximum_thickness_constraint = (
        plot_data.constraints.max_thickness_cm
    )

    maximum_mass_constraint = (
        plot_data
        .constraints
        .max_mass_per_area_g_per_cm2
    )

    x_reference_values = [
        maximum_point_thickness
    ]

    if maximum_thickness_constraint is not None:
        x_reference_values.append(
            maximum_thickness_constraint
        )

    y_reference_values = [
        maximum_point_mass
    ]

    if maximum_mass_constraint is not None:
        y_reference_values.append(
            maximum_mass_constraint
        )

    x_upper_limit = max(x_reference_values) * 1.14
    y_upper_limit = max(y_reference_values) * 1.16

    if x_upper_limit == 0:
        x_upper_limit = 1.0

    if y_upper_limit == 0:
        y_upper_limit = 1.0

    axes.set_xlim(
        0.0,
        x_upper_limit,
    )

    axes.set_ylim(
        0.0,
        y_upper_limit,
    )

    # Shade regions that violate active engineering constraints.
    #
    # These regions are drawn before the points so candidate markers remain
    # clearly visible.

    if maximum_thickness_constraint is not None:
        axes.axvspan(
            maximum_thickness_constraint,
            x_upper_limit,
            color=rejected_color,
            alpha=0.07,
            zorder=0,
        )

    if maximum_mass_constraint is not None:
        axes.axhspan(
            maximum_mass_constraint,
            y_upper_limit,
            color=rejected_color,
            alpha=0.07,
            zorder=0,
        )

    eligible_points = [
        point
        for point in pareto_points
        if point.optimization_status == "ELIGIBLE"
    ]

    rejected_points = [
        point
        for point in pareto_points
        if point.optimization_status == "REJECTED"
    ]

    selected_points = [
        point
        for point in pareto_points
        if point.is_selected
    ]

    if len(eligible_points) > 0:
        axes.scatter(
            [
                point.thickness_cm
                for point in eligible_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in eligible_points
            ],
            s=95,
            marker=eligible_marker,
            color=eligible_color,
            edgecolor=text_color,
            linewidth=0.9,
            zorder=4,
        )

    if len(rejected_points) > 0:
        axes.scatter(
            [
                point.thickness_cm
                for point in rejected_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in rejected_points
            ],
            s=95,
            marker=rejected_marker,
            color=rejected_color,
            edgecolor=text_color,
            linewidth=0.8,
            alpha=0.75,
            zorder=3,
        )

    # Draw a larger outline over the selected candidate.
    #
    # The original candidate point remains underneath, so the selected design
    # preserves its eligible/rejected category appearance.

    for selected_point in selected_points:
        axes.scatter(
            selected_point.thickness_cm,
            selected_point.mass_per_area_g_per_cm2,
            s=230,
            marker=eligible_marker,
            facecolor="none",
            edgecolor=selected_color,
            linewidth=2.7,
            zorder=6,
        )

    pareto_front_points = [
        point
        for point in pareto_points
        if point.is_pareto_optimal
    ]

    pareto_front_points.sort(
        key=lambda point: (
            point.thickness_cm,
            point.mass_per_area_g_per_cm2,
            point.material_key,
        )
    )

    if len(pareto_front_points) >= 2:
        axes.plot(
            [
                point.thickness_cm
                for point in pareto_front_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in pareto_front_points
            ],
            linestyle="--",
            linewidth=2.0,
            color=selected_color,
            zorder=2,
        )

    # Label every successfully calculated design.
    #
    # Alternating vertical offsets reduces overlap between nearby materials
    # without introducing another plotting dependency.

    for index, point in enumerate(pareto_points):
        if index % 2 == 0:
            vertical_offset = 8
        else:
            vertical_offset = -14

        axes.annotate(
            point.material_name,
            xy=(
                point.thickness_cm,
                point.mass_per_area_g_per_cm2,
            ),
            xytext=(7, vertical_offset),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
            zorder=7,
        )

    thickness_constraint_handle = None

    if maximum_thickness_constraint is not None:
        thickness_constraint_handle = axes.axvline(
            maximum_thickness_constraint,
            linestyle="--",
            linewidth=1.5,
            label=(
                "Maximum thickness: "
                f"{maximum_thickness_constraint:.6g} cm"
            ),
            zorder=1,
        )

    mass_constraint_handle = None

    if maximum_mass_constraint is not None:
        mass_constraint_handle = axes.axhline(
            maximum_mass_constraint,
            linestyle=":",
            linewidth=1.8,
            label=(
                "Maximum mass per area: "
                f"{maximum_mass_constraint:.6g} g/cm²"
            ),
            zorder=1,
        )

    axes.set_xlabel(
        "Required shielding thickness (cm)"
    )

    axes.set_ylabel(
        "Mass per area (g/cm²)"
    )

    axes.set_title(
        create_plot_subtitle(plot_data),
        loc="left",
        fontsize=9,
        pad=12,
    )

    figure.suptitle(
        "Shielding Thickness–Mass Pareto Tradeoff",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    axes.grid(
        True,
        linestyle=":",
        alpha=0.4,
    )

    axes.set_axisbelow(True)

    # The preferred direction is toward smaller values on both axes.

    axes.annotate(
        "Preferred direction",
        xy=(0.02, 0.04),
        xycoords="axes fraction",
        xytext=(0.15, 0.16),
        textcoords="axes fraction",
        arrowprops={
            "arrowstyle": "->",
            "linewidth": 1.2,
        },
        fontsize=9,
        ha="center",
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=eligible_color,
            markeredgecolor=text_color,
            markersize=8,
            label="Eligible design",
        )
    ]

    if len(rejected_points) > 0:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="X",
                linestyle="none",
                markerfacecolor=rejected_color,
                markeredgecolor=text_color,
                markersize=8,
                label="Rejected by constraint",
            )
        )

    if len(selected_points) > 0:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="none",
                markeredgecolor=selected_color,
                markeredgewidth=2.5,
                markersize=11,
                label="Selected design",
            )
        )

    if len(pareto_front_points) > 0:
        pareto_scope_text = (
            "eligible designs"
            if eligible_only
            else "all successful designs"
        )

        legend_handles.append(
            Line2D(
                [0],
                [0],
                linestyle="--",
                linewidth=2.0,
                color=selected_color,
                label=(
                    "Pareto front among "
                    f"{pareto_scope_text}"
                ),
            )
        )

    if thickness_constraint_handle is not None:
        legend_handles.append(
            thickness_constraint_handle
        )

    if mass_constraint_handle is not None:
        legend_handles.append(
            mass_constraint_handle
        )

    axes.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
    )

    figure_notes = [
        (
            "Lower-left indicates designs requiring both less shielding "
            "thickness and less mass per unit area."
        )
    ]

    failed_candidate_note = get_failed_candidate_note(
        plot_data
    )

    if failed_candidate_note is not None:
        figure_notes.append(
            failed_candidate_note
        )

    figure.text(
        0.01,
        0.015,
        "\n".join(
            textwrap.fill(note, width=125)
            for note in figure_notes
        ),
        ha="left",
        va="bottom",
        fontsize=8,
    )

    figure.subplots_adjust(
        left=0.12,
        right=0.95,
        top=0.84,
        bottom=0.14,
    )

    return figure


def plot_thickness_mass_tradeoff(
    plot_data: OptimizationPlotData,
    eligible_only: bool = True,
) -> Figure:
    # Recruiter-facing thickness-versus-mass engineering tradeoff.
    #
    # This figure answers:
    #
    #   Which designs are feasible, and what tradeoff exists between
    #   compactness and shield mass?
    #
    # Lower-left is preferred because it represents both less required
    # shielding thickness and less mass per unit area.
    #
    # Rejected designs remain visible for context, but only eligible
    # designs define the default engineering Pareto front.

    pareto_points = create_pareto_points(
        plot_data,
        eligible_only=eligible_only,
    )

    if len(pareto_points) == 0:
        raise ValueError(
            "At least one successfully calculated material is required "
            "for the thickness-mass tradeoff."
        )

    figure, axes = plt.subplots(
        figsize=(11.5, 7.2)
    )

    feasible_color, constraint_color, selected_color = (
        get_plot_colors()
    )

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    muted_color = to_rgba(
        text_color,
        0.42,
    )

    eligible_marker = MarkerStyle("o")
    rejected_marker = MarkerStyle("X")

    maximum_point_thickness = max(
        point.thickness_cm
        for point in pareto_points
    )

    maximum_point_mass = max(
        point.mass_per_area_g_per_cm2
        for point in pareto_points
    )

    thickness_limit = (
        plot_data.constraints.max_thickness_cm
    )

    mass_limit = (
        plot_data
        .constraints
        .max_mass_per_area_g_per_cm2
    )

    x_reference_values = [
        maximum_point_thickness
    ]

    if thickness_limit is not None:
        x_reference_values.append(
            thickness_limit
        )

    y_reference_values = [
        maximum_point_mass
    ]

    if mass_limit is not None:
        y_reference_values.append(
            mass_limit
        )

    x_upper_limit = max(
        x_reference_values
    ) * 1.13

    y_upper_limit = max(
        y_reference_values
    ) * 1.15

    if x_upper_limit == 0:
        x_upper_limit = 1.0

    if y_upper_limit == 0:
        y_upper_limit = 1.0

    axes.set_xlim(
        0.0,
        x_upper_limit,
    )

    axes.set_ylim(
        0.0,
        y_upper_limit,
    )

    # Highlight the feasible engineering region rather than shading
    # every infeasible region.
    if (
        thickness_limit is not None
        and mass_limit is not None
    ):
        feasible_region = Rectangle(
            (0.0, 0.0),
            thickness_limit,
            mass_limit,
            facecolor=feasible_color,
            edgecolor="none",
            alpha=0.06,
            zorder=0,
        )

        axes.add_patch(
            feasible_region
        )

    elif thickness_limit is not None:
        axes.axvspan(
            0.0,
            thickness_limit,
            color=feasible_color,
            alpha=0.06,
            zorder=0,
        )

    elif mass_limit is not None:
        axes.axhspan(
            0.0,
            mass_limit,
            color=feasible_color,
            alpha=0.06,
            zorder=0,
        )

    eligible_points = [
        point
        for point in pareto_points
        if point.optimization_status == "ELIGIBLE"
    ]

    rejected_points = [
        point
        for point in pareto_points
        if point.optimization_status == "REJECTED"
    ]

    selected_points = [
        point
        for point in pareto_points
        if point.is_selected
    ]

    if len(eligible_points) > 0:
        axes.scatter(
            [
                point.thickness_cm
                for point in eligible_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in eligible_points
            ],
            s=105,
            marker=eligible_marker,
            color=feasible_color,
            edgecolor=text_color,
            linewidth=0.9,
            zorder=4,
        )

    if len(rejected_points) > 0:
        axes.scatter(
            [
                point.thickness_cm
                for point in rejected_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in rejected_points
            ],
            s=90,
            marker=rejected_marker,
            color=muted_color,
            edgecolor=text_color,
            linewidth=0.7,
            zorder=3,
        )

    # Draw a larger outline around the optimizer's selected material.
    for selected_point in selected_points:
        axes.scatter(
            selected_point.thickness_cm,
            selected_point.mass_per_area_g_per_cm2,
            s=245,
            marker=eligible_marker,
            facecolor="none",
            edgecolor=selected_color,
            linewidth=2.8,
            zorder=6,
        )

    pareto_front_points = [
        point
        for point in pareto_points
        if point.is_pareto_optimal
    ]

    pareto_front_points.sort(
        key=lambda point: (
            point.thickness_cm,
            point.mass_per_area_g_per_cm2,
            point.material_key,
        )
    )

    if len(pareto_front_points) >= 2:
        axes.plot(
            [
                point.thickness_cm
                for point in pareto_front_points
            ],
            [
                point.mass_per_area_g_per_cm2
                for point in pareto_front_points
            ],
            color=selected_color,
            linestyle="--",
            linewidth=2.0,
            zorder=2,
        )

    # Label each successful design.
    #
    # Alternating offsets provide a reasonable generic starting point.
    # We can tune individual offsets during the final visual cleanup.
    for index, point in enumerate(
        pareto_points
    ):
        if index % 2 == 0:
            vertical_offset = 8
        else:
            vertical_offset = -13

        if point.is_selected:
            font_weight = "bold"
        else:
            font_weight = "normal"

        axes.annotate(
            point.material_name,
            xy=(
                point.thickness_cm,
                point.mass_per_area_g_per_cm2,
            ),
            xytext=(
                7,
                vertical_offset,
            ),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8.8,
            fontweight=font_weight,
            zorder=7,
        )

    # Draw and directly label active constraints.
    if thickness_limit is not None:
        axes.axvline(
            thickness_limit,
            color=constraint_color,
            linestyle="--",
            linewidth=1.5,
            zorder=1,
        )

        axes.text(
            thickness_limit,
            0.985,
            (
                "Thickness limit\n"
                f"{thickness_limit:.6g} cm"
            ),
            transform=axes.get_xaxis_transform(),
            ha="right",
            va="top",
            fontsize=8,
            color=constraint_color,
        )

    if mass_limit is not None:
        axes.axhline(
            mass_limit,
            color=constraint_color,
            linestyle=":",
            linewidth=1.8,
            zorder=1,
        )

        axes.text(
            0.985,
            mass_limit,
            (
                "Mass limit: "
                f"{mass_limit:.6g} g/cm²"
            ),
            transform=axes.get_yaxis_transform(),
            ha="right",
            va="bottom",
            fontsize=8,
            color=constraint_color,
        )

    axes.set_xlabel(
        "Required shielding thickness (cm)"
    )

    axes.set_ylabel(
        "Mass per unit area (g/cm²)"
    )

    axes.grid(
        True,
        linestyle=":",
        alpha=0.35,
    )

    axes.set_axisbelow(
        True
    )

    axes.set_title(
        create_plot_subtitle(plot_data),
        loc="left",
        fontsize=9,
        pad=12,
    )

    figure.suptitle(
        "Shielding Thickness–Mass Engineering Tradeoff",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=feasible_color,
            markeredgecolor=text_color,
            markersize=8,
            label="Feasible design",
        )
    ]

    if len(rejected_points) > 0:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="X",
                linestyle="none",
                markerfacecolor=muted_color,
                markeredgecolor=text_color,
                markersize=8,
                label="Infeasible design",
            )
        )

    if len(selected_points) > 0:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="none",
                markeredgecolor=selected_color,
                markeredgewidth=2.5,
                markersize=11,
                label="Selected design",
            )
        )

    if len(pareto_front_points) >= 2:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                color=selected_color,
                linestyle="--",
                linewidth=2.0,
                label="Feasible Pareto front",
            )
        )

    axes.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(
            1.02,
            1.0,
        ),
        borderaxespad=0.0,
        frameon=True,
    )

    figure_notes = [
        (
            "The lower-left region represents designs requiring both "
            "less shielding thickness and less mass per unit area."
        )
    ]

    if plot_data.selection_reason is not None:
        figure_notes.append(
            plot_data.selection_reason
        )

    failed_candidate_note = get_failed_candidate_note(
        plot_data
    )

    if failed_candidate_note is not None:
        figure_notes.append(
            failed_candidate_note
        )

    figure.text(
        0.10,
        0.025,
        "\n".join(
            textwrap.fill(
                note,
                width=145,
            )
            for note in figure_notes
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
    )

    figure.subplots_adjust(
        left=0.11,
        right=0.76,
        top=0.83,
        bottom=0.16,
    )

    return figure


def plot_response_vs_thickness(
    curve_result: ResponseCurveResult,
    logarithmic: bool = True,
) -> Figure:
    # Recruiter-facing detector-response plot for one shielding material.
    #
    # This figure answers:
    #
    #   How does increasing shield thickness reduce detector response,
    #   and where does the selected design satisfy the target?
    #
    # Numerical response values are generated in response_curve.py.
    # This function only renders the validated curve data.

    if len(curve_result.points) < 2:
        raise ValueError(
            "At least two response-curve points are required for plotting."
        )

    thickness_values = [
        point.thickness_cm
        for point in curve_result.points
    ]

    uncollided_values: list[float] = []

    for point in curve_result.points:
        if logarithmic and point.uncollided_flux <= 0:
            # Logarithmic axes cannot display zero.
            #
            # NaN creates an honest visual gap rather than replacing the
            # result with an invented small positive value.
            uncollided_values.append(
                math.nan
            )

        else:
            uncollided_values.append(
                point.uncollided_flux
            )

    buildup_values: list[float] = []

    for point in curve_result.points:
        buildup_value = (
            point.buildup_corrected_flux
        )

        if buildup_value is None:
            buildup_values.append(
                math.nan
            )

        elif logarithmic and buildup_value <= 0:
            buildup_values.append(
                math.nan
            )

        else:
            buildup_values.append(
                buildup_value
            )

    has_buildup_values = any(
        point.buildup_corrected_flux is not None
        for point in curve_result.points
    )

    if logarithmic:
        has_positive_uncollided_value = any(
            point.uncollided_flux > 0
            for point in curve_result.points
        )

        has_positive_buildup_value = any(
            point.buildup_corrected_flux is not None
            and point.buildup_corrected_flux > 0
            for point in curve_result.points
        )

        if (
            not has_positive_uncollided_value
            and not has_positive_buildup_value
        ):
            raise ValueError(
                "A logarithmic response plot requires at least one "
                "positive response value."
            )

    figure, axes = plt.subplots(
        figsize=(11.8, 7.2)
    )

    (
        uncollided_color,
        buildup_color,
        design_color,
    ) = get_plot_colors()

    text_color = plt.rcParams.get(
        "text.color",
        "black",
    )

    # Reference lines use a neutral color so they are visually distinct
    # from the two calculated response series.
    reference_color = to_rgba(
        text_color,
        0.62,
    )

    design_marker = MarkerStyle("o")

    display_units = format_plot_units(
        curve_result.quantity_units
    )

    # Narrow-beam result.
    axes.plot(
        thickness_values,
        uncollided_values,
        color=uncollided_color,
        linestyle="--",
        linewidth=2.1,
        label=(
            "Narrow-beam uncollided photon flux"
        ),
        zorder=3,
    )

    # Current G-P exposure-buildup result.
    if has_buildup_values:
        axes.plot(
            thickness_values,
            buildup_values,
            color=buildup_color,
            linestyle="-",
            linewidth=2.5,
            label=(
                "G-P exposure-buildup response proxy"
            ),
            zorder=4,
        )

    # Design target.
    if curve_result.target_flux is not None:
        target_flux = curve_result.target_flux

        axes.axhline(
            target_flux,
            color=reference_color,
            linestyle=":",
            linewidth=1.9,
            zorder=2,
        )

        axes.text(
            0.985,
            target_flux,
            (
                "Design target: "
                f"{target_flux:.6g} "
                f"{display_units}"
            ),
            transform=axes.get_yaxis_transform(),
            ha="right",
            va="bottom",
            fontsize=8.5,
            color=reference_color,
            zorder=5,
        )

    # Selected design thickness and response.
    if curve_result.required_thickness_cm is not None:
        required_thickness = (
            curve_result.required_thickness_cm
        )

        axes.axvline(
            required_thickness,
            color=reference_color,
            linestyle="-.",
            linewidth=1.7,
            zorder=2,
        )

        axes.text(
            required_thickness,
            0.975,
            (
                "Selected thickness\n"
                f"{required_thickness:.6g} cm"
            ),
            transform=axes.get_xaxis_transform(),
            ha="left",
            va="top",
            fontsize=8.5,
            color=reference_color,
            zorder=5,
        )

        required_point = (
            get_response_point_at_thickness(
                curve_result,
                required_thickness,
            )
        )

        # When the buildup result exists at the selected thickness, it is
        # the target-comparison value used for the design point.
        #
        # Otherwise, the selected point uses the narrow-beam result.
        if (
            required_point.buildup_corrected_flux
            is not None
        ):
            design_response = (
                required_point
                .buildup_corrected_flux
            )

        else:
            design_response = (
                required_point.uncollided_flux
            )

        if not logarithmic or design_response > 0:
            axes.scatter(
                required_thickness,
                design_response,
                s=135,
                marker=design_marker,
                facecolor=design_color,
                edgecolor=text_color,
                linewidth=1.0,
                label="Selected design point",
                zorder=7,
            )

            axes.annotate(
                (
                    f"{design_response:.4g} "
                    f"{display_units}"
                ),
                xy=(
                    required_thickness,
                    design_response,
                ),
                xytext=(
                    12,
                    -27,
                ),
                textcoords="offset points",
                ha="left",
                va="top",
                fontsize=8.8,
                fontweight="bold",
                arrowprops={
                    "arrowstyle": "-",
                    "linewidth": 0.8,
                },
                zorder=8,
            )

    if logarithmic:
        axes.set_yscale(
            "log"
        )

    axes.set_xlim(
        thickness_values[0],
        thickness_values[-1],
    )

    axes.set_xlabel(
        "Shield thickness (cm)",
        fontsize=10,
    )

    # The buildup series uses exposure buildup coefficients, so the shared
    # axis should not describe both series as ordinary photon flux.
    if (
        curve_result.buildup_requested
        and has_buildup_values
    ):
        y_axis_label = (
            "Calculated target-comparison response "
            f"({display_units})"
        )

    else:
        y_axis_label = (
            f"{curve_result.quantity_name} "
            f"({display_units})"
        )

    axes.set_ylabel(
        y_axis_label,
        fontsize=10,
    )

    # Use clear major grid lines and much lighter minor logarithmic lines.
    axes.grid(
        True,
        which="major",
        linestyle=":",
        alpha=0.36,
    )

    if logarithmic:
        axes.yaxis.grid(
            True,
            which="minor",
            linestyle=":",
            alpha=0.12,
        )

        axes.xaxis.grid(
            False,
            which="minor",
        )

    axes.set_axisbelow(
        True
    )

    buildup_description = (
        "requested"
        if curve_result.buildup_requested
        else "not requested"
    )

    axes.set_title(
        (
            f"{curve_result.source_name} source"
            f" | Detector distance: "
            f"{curve_result.detector_distance_cm:.6g} cm"
            f" | Backend: {curve_result.backend_name}\n"
            f"G-P exposure buildup: "
            f"{buildup_description}"
        ),
        loc="left",
        fontsize=9,
        pad=12,
    )

    figure.suptitle(
        (
            f"Effect of {curve_result.material_name} "
            "Shield Thickness on Detector Response"
        ),
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    # The legend contains only calculated series and the selected point.
    #
    # Target and thickness reference lines are labeled directly on the axes.
    axes.legend(
        loc="upper left",
        bbox_to_anchor=(
            1.02,
            1.0,
        ),
        borderaxespad=0.0,
        frameon=True,
    )

    figure_notes = []

    if (
        curve_result.buildup_requested
        and has_buildup_values
    ):
        figure_notes.append(
            "The G-P curve uses exposure buildup coefficients and is "
            "displayed as a target-comparison response proxy. It should "
            "not be interpreted as a general photon-flux estimate."
        )

    elif (
        curve_result.buildup_requested
        and not has_buildup_values
    ):
        figure_notes.append(
            "G-P buildup was requested, but no valid buildup values were "
            "available for the plotted material and thickness range."
        )

    if len(curve_result.warnings) > 0:
        figure_notes.append(
            "Curve warning: "
            + " ".join(
                curve_result.warnings
            )
        )

    contains_uncollided_log_gap = any(
        point.uncollided_flux <= 0
        for point in curve_result.points
    )

    contains_buildup_log_gap = any(
        point.buildup_corrected_flux is not None
        and point.buildup_corrected_flux <= 0
        for point in curve_result.points
    )

    if logarithmic and (
        contains_uncollided_log_gap
        or contains_buildup_log_gap
    ):
        figure_notes.append(
            "Zero-valued numerical-underflow points are omitted from the "
            "logarithmic response axis."
        )

    bottom_margin = 0.11

    if len(figure_notes) > 0:
        wrapped_notes = [
            textwrap.fill(
                note,
                width=150,
            )
            for note in figure_notes
        ]

        figure.text(
            0.10,
            0.025,
            "\n".join(
                wrapped_notes
            ),
            ha="left",
            va="bottom",
            fontsize=8.3,
        )

        bottom_margin = 0.17

    figure.subplots_adjust(
        left=0.11,
        right=0.75,
        top=0.83,
        bottom=bottom_margin,
    )

    return figure


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