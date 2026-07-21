# V1.10 optimization and material-design figures.
#
# This module renders:
#   - material design comparison
#   - engineering constraint feasibility matrix
#   - thickness-mass engineering tradeoff

from collections.abc import Callable
import textwrap

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Patch, Rectangle
from matplotlib.transforms import Bbox

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
)

from plotting_utils import (
    PLOT_THEME,
    create_plot_subtitle,
    format_metric_value,
    format_plot_text,
    get_failed_candidate_note,
    get_plot_colors,
    style_legend,
)


MetricGetter = Callable[
    [MaterialPlotPoint],
    float | None,
]

FeasibilityGetter = Callable[
    [MaterialFeasibilityRow],
    ConstraintCheckStatus,
]


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

    plot_text_color = PLOT_THEME.axes_text

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

        # Keep the engineering-limit label inside the plotting surface so it
        # cannot collide with the panel title.
        axes.annotate(
            constraint_label,
            xy=(
                constraint_value,
                0.975,
            ),
            xycoords=axes.get_xaxis_transform(),
            xytext=(
                -6,
                -2,
            ),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=8,
            fontweight="medium",
            color=constraint_color,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": PLOT_THEME.axes_background,
                "edgecolor": "none",
                "alpha": 0.94,
            },
            zorder=4,
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
            edge_color = plot_text_color
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
            color=plot_text_color,
            zorder=3,
        )

    axes.set_title(
        panel_title,
        fontsize=11,
        fontweight="bold",
        pad=10,
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


def plot_constraint_feasibility_matrix(
    plot_data: OptimizationPlotData,
    scenario_context: str | None = None,
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
            PLOT_THEME.border
        )

        cell.set_linewidth(
            0.7
        )

        # Every table cell uses dark text because every table surface
        # is intentionally light and opaque.
        cell.set_text_props(
            color=PLOT_THEME.axes_text
        )

        # Header row.
        if table_row_index == 0:
            cell.set_facecolor(
                PLOT_THEME.table_header_background
            )

            cell.set_text_props(
                color=PLOT_THEME.table_header_text,
                fontweight="bold",
            )

            continue

        feasibility_row = feasibility_rows[
            table_row_index - 1
        ]

        # Give body rows a subtle alternating background before applying
        # any semantic PASS, FAIL, or overall-result coloring.
        if table_row_index % 2 == 0:
            base_row_color = (
                PLOT_THEME.table_alternate_row_background
            )
        else:
            base_row_color = (
                PLOT_THEME.table_row_background
            )

        cell.set_facecolor(
            base_row_color
        )

        # Material-name column.
        if table_column_index == 0:
            cell.set_text_props(
                horizontalalignment="left",
                color=PLOT_THEME.axes_text,
            )

            if feasibility_row.is_selected:
                cell.set_text_props(
                    horizontalalignment="left",
                    color=PLOT_THEME.axes_text,
                    fontweight="bold",
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
                    PLOT_THEME.table_pass_background
                )

                cell.set_text_props(
                    color=PLOT_THEME.axes_text,
                    fontweight="bold",
                )

            elif status == "FAIL":
                cell.set_facecolor(
                    PLOT_THEME.table_fail_background
                )

                cell.set_text_props(
                    color=PLOT_THEME.axes_text,
                    fontweight="bold",
                )

            elif status == "UNAVAILABLE":
                cell.set_facecolor(
                    PLOT_THEME.table_unavailable_background
                )

            continue

        # Overall-result column.
        if feasibility_row.is_selected:
            cell.set_facecolor(
                PLOT_THEME.table_selected_background
            )

            cell.set_text_props(
                color=PLOT_THEME.axes_text,
                fontweight="bold",
            )

        elif (
            feasibility_row.optimization_status
            == "ELIGIBLE"
        ):
            cell.set_facecolor(
                PLOT_THEME.table_pass_background
            )

            cell.set_text_props(
                color=PLOT_THEME.axes_text,
                fontweight="bold",
            )

        elif (
            feasibility_row.optimization_status
            == "REJECTED"
        ):
            cell.set_facecolor(
                PLOT_THEME.table_fail_background
            )

            cell.set_text_props(
                color=PLOT_THEME.axes_text,
                fontweight="bold",
            )

        elif (
            feasibility_row.optimization_status
            == "FAILED"
        ):
            cell.set_facecolor(
                PLOT_THEME.table_unavailable_background
            )

    figure.suptitle(
        "Engineering Constraint Feasibility by Material",
        fontsize=14,
        fontweight="bold",
        y=0.955,
    )

    figure.text(
        0.08,
        0.875,
        create_plot_subtitle(
            plot_data,
            scenario_context,
        ),
        ha="left",
        va="top",
        fontsize=9,
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
            + format_plot_text(
                plot_data.selection_reason
            )
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
        top=0.785,
        bottom=0.14,
    )

    return figure


def plot_material_design_comparison(
    plot_data: OptimizationPlotData,
    scenario_context: str | None = None,
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

    # Align the material labels as a clean category column beside the first
    # panel rather than leaving them attached to visible tick marks.
    thickness_axes.tick_params(
        axis="y",
        which="both",
        length=0,
        pad=8,
        colors=PLOT_THEME.text,
    )

    for tick_label in thickness_axes.get_yticklabels():
        tick_label.set_horizontalalignment(
            "right"
        )

    # A horizontal category heading is easier to read than a distant vertical
    # y-axis title beside long material names.
    thickness_axes.set_ylabel(
        ""
    )

    thickness_axes.text(
        -0.03,
        1.035,
        "Shielding material",
        transform=thickness_axes.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        fontweight="semibold",
        color=PLOT_THEME.text,
        clip_on=False,
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
        create_plot_subtitle(
            plot_data,
            scenario_context,
        ),
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
        legend = figure.legend(
            handles=legend_handles,
            loc="upper right",
            bbox_to_anchor=(
                0.965,
                0.925,
            ),
            frameon=True,
            ncols=len(legend_handles),
            columnspacing=1.6,
            handletextpad=0.7,
        )

        style_legend(
            legend
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
            format_plot_text(
                plot_data.selection_reason
            )
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
        left=0.175,
        right=0.985,
        top=0.79,
        bottom=0.16,
        wspace=0.16,
    )

    return figure


def plot_thickness_mass_tradeoff(
    plot_data: OptimizationPlotData,
    eligible_only: bool = True,
    scenario_context: str | None = None,
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

    # Colors drawn inside the white plotting surface must be independent
    # from the lighter text used around the dark figure background.
    plot_text_color = PLOT_THEME.axes_text
    muted_marker_color = PLOT_THEME.axes_muted_text

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
            edgecolor=plot_text_color,
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
            color=muted_marker_color,
            edgecolor=plot_text_color,
            linewidth=0.8,
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
    # Deterministic offsets prevent nearby engineering designs from receiving
    # overlapping or ambiguous labels.
    #
    # Values are:
    #   horizontal offset in points
    #   vertical offset in points
    #   horizontal alignment

    label_positions = {
        "tungsten": (
            9,
            8,
            "left",
        ),
        "lead": (
            10,
            -17,
            "left",
        ),
        "copper": (
            9,
            9,
            "left",
        ),
        "tin": (
            9,
            -14,
            "left",
        ),
        "concrete_barite": (
            10,
            9,
            "left",
        ),

        # These two points are close together, so their labels are placed
        # on opposite sides of the cluster.
        "aluminum": (
            -10,
            11,
            "right",
        ),
        "concrete_ordinary": (
            10,
            9,
            "left",
        ),

        "polyethylene": (
            10,
            8,
            "left",
        ),
        "water": (
            10,
            -14,
            "left",
        ),
    }


    for point in pareto_points:
        (
            horizontal_offset,
            vertical_offset,
            horizontal_alignment,
        ) = label_positions.get(
            point.material_key,
            (
                9,
                8,
                "left",
            ),
        )

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
                horizontal_offset,
                vertical_offset,
            ),
            textcoords="offset points",
            ha=horizontal_alignment,
            va="center",
            fontsize=8.8,
            fontweight=font_weight,
            color=plot_text_color,
            arrowprops={
                "arrowstyle": "-",
                "color": PLOT_THEME.axes_muted_text,
                "linewidth": 0.65,
                "shrinkA": 2,
                "shrinkB": 4,
            },
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
        create_plot_subtitle(
            plot_data,
            scenario_context,
        ),
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
            markeredgecolor=plot_text_color,
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
                markerfacecolor=muted_marker_color,
                markeredgecolor=plot_text_color,
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

    legend = axes.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(
            1.02,
            1.0,
        ),
        borderaxespad=0.0,
        frameon=True,
    )

    style_legend(
        legend
    )

    figure_notes = [
        (
            "The lower-left region represents designs requiring both "
            "less shielding thickness and less mass per unit area."
        )
    ]

    if plot_data.selection_reason is not None:
        figure_notes.append(
            format_plot_text(
                plot_data.selection_reason
            )
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
