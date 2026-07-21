# V1.10 detector-response figures.
#
# This module renders detector response as a function of shield thickness.
# Numerical curve generation remains in response_curve.py.

import math
import textwrap

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.markers import MarkerStyle

from plot_models import (
    ResponseCurvePoint,
    ResponseCurveResult,
)

from plotting_utils import (
    PLOT_THEME,
    format_plot_units,
    get_plot_colors,
    style_legend,
)


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




def plot_response_vs_thickness(
    curve_result: ResponseCurveResult,
    logarithmic: bool = True,
    scenario_context: str | None = None,
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

    # Internal annotations are drawn over a white axes surface, so they use
    # the dark axes palette rather than the light outer-figure text color.
    plot_text_color = PLOT_THEME.axes_text
    reference_color = PLOT_THEME.axes_muted_text

    reference_line_style = (
        0,
        (
            4,
            3,
        ),
    )

    reference_line_width = 1.6

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
            linestyle=reference_line_style,
            linewidth=reference_line_width,
            zorder=2,
        )

        axes.annotate(
            (
                "Design target: "
                f"{target_flux:.6g} "
                f"{display_units}"
            ),
            xy=(
                0.985,
                target_flux,
            ),
            xycoords=axes.get_yaxis_transform(),
            xytext=(
                0,
                7,
            ),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=8.5,
            color=plot_text_color,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": PLOT_THEME.axes_background,
                "edgecolor": "none",
                "alpha": 0.92,
            },
            zorder=6,
        )

    # Selected design thickness and response.
    if curve_result.required_thickness_cm is not None:
        required_thickness = (
            curve_result.required_thickness_cm
        )

        axes.axvline(
            required_thickness,
            color=reference_color,
            linestyle=reference_line_style,
            linewidth=reference_line_width,
            zorder=2,
        )

        axes.annotate(
            (
                "Selected thickness\n"
                f"{required_thickness:.6g} cm"
            ),
            xy=(
                required_thickness,
                0.975,
            ),
            xycoords=axes.get_xaxis_transform(),
            xytext=(
                10,
                -2,
            ),
            textcoords="offset points",
            ha="left",
            va="top",
            fontsize=8.5,
            color=plot_text_color,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": PLOT_THEME.axes_background,
                "edgecolor": "none",
                "alpha": 0.92,
            },
            zorder=6,
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
                s=82,
                marker=design_marker,
                facecolor=design_color,
                edgecolor=plot_text_color,
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
                color=plot_text_color,
                arrowprops={
                    "arrowstyle": "-",
                    "color": plot_text_color,
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
        color=PLOT_THEME.axes_muted_text,
        linestyle=":",
        linewidth=0.8,
        alpha=0.46,
    )
    if logarithmic:
        axes.yaxis.grid(
            True,
            which="minor",
            color=PLOT_THEME.axes_muted_text,
            linestyle=":",
            linewidth=0.55,
            alpha=0.18,
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

    buildup_description = (
        "requested"
        if curve_result.buildup_requested
        else "not requested"
    )

    response_context_lines = []

    if (
        scenario_context is not None
        and scenario_context.strip() != ""
    ):
        response_context_lines.append(
            scenario_context.strip()
        )

    else:
        response_context_lines.append(
            (
                f"Source: {curve_result.source_name}"
                f" | Detector distance: "
                f"{curve_result.detector_distance_cm:.6g} cm"
            )
        )

    response_context_lines.append(
        (
            f"Backend: {curve_result.backend_name}"
            f" | G-P exposure buildup: "
            f"{buildup_description}"
        )
    )

    axes.set_title(
        "\n".join(
            response_context_lines
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
    legend = axes.legend(
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
