# V1.12 collision-air-kerma response plots.
#
# This module renders line-by-line deterministic response results.
# Numerical air-kerma calculations remain in air_response.py.


from __future__ import annotations

import textwrap

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from shielding.physics.response_models import (
    PhotonLineAirKermaResult,
    SourceAirKermaResult,
)
from shielding.physics.units import (
    convert_gy_per_s_to_microgy_per_h,
)
from shielding.reporting.style import (
    PLOT_THEME,
    get_plot_colors,
)


def require_adjusted_line_response(
    line_result: PhotonLineAirKermaResult,
) -> float:
    # Return one required buildup-adjusted line contribution.

    adjusted_response = line_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s

    if adjusted_response is None:
        raise ValueError(
            "The line-contribution figure requires "
            "G-P exposure buildup to be applied to "
            "every photon line."
        )

    return adjusted_response


def create_line_label(
    line_result: PhotonLineAirKermaResult,
) -> str:
    # Include the quantities that explain why each line contributes
    # differently to the final source response.

    buildup_factor = line_result.buildup_factor

    if buildup_factor is None:
        raise ValueError(
            "The line-contribution figure requires a "
            "buildup factor for every photon line."
        )

    return (
        f"{line_result.photon_energy_mev:.6f} MeV\n"
        f"I = {line_result.emission_intensity:.4f}, "
        f"B = {buildup_factor:.3f}"
    )


def annotate_contribution_bars(
    axes,
    bars,
    values: list[float],
    total: float,
) -> None:
    # Label each bar with its air-kerma contribution and its
    # percentage of the corresponding source total.

    if total <= 0:
        raise ValueError("Line-contribution total must be greater than zero.")

    for bar, value in zip(
        bars,
        values,
        strict=True,
    ):
        contribution_percent = 100.0 * value / total

        axes.annotate(
            (f"{value:.3e}\n{contribution_percent:.1f}%"),
            xy=(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
            ),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color="black",
            zorder=4,
        )


def plot_isotope_line_air_kerma_contributions(
    result: SourceAirKermaResult,
    scenario_context: str | None = None,
) -> Figure:
    # Compare uncollided and G-P-adjusted collision-air-kerma
    # contributions for every photon line in one isotope source.
    #
    # Percentages are calculated separately within the uncollided
    # and buildup-adjusted response totals.

    if result.activity_bq is None:
        raise ValueError(
            "The isotope line-contribution figure requires "
            "a radioactive source with an activity."
        )

    if len(result.line_results) < 2:
        raise ValueError(
            "The isotope line-contribution figure requires at least two photon lines."
        )

    if result.buildup_status != "applied":
        raise ValueError(
            "The isotope line-contribution figure requires "
            "G-P exposure buildup to be applied successfully "
            "to every photon line."
        )

    adjusted_total_gy_per_s = (
        result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    if adjusted_total_gy_per_s is None:
        raise ValueError(
            "The source result is missing its total "
            "buildup-adjusted collision air-kerma rate."
        )

    line_labels = [
        create_line_label(line_result) for line_result in result.line_results
    ]

    uncollided_values = [
        convert_gy_per_s_to_microgy_per_h(
            line_result.uncollided_collision_air_kerma_rate_gy_per_s
        )
        for line_result in result.line_results
    ]

    adjusted_values = [
        convert_gy_per_s_to_microgy_per_h(require_adjusted_line_response(line_result))
        for line_result in result.line_results
    ]

    uncollided_total = convert_gy_per_s_to_microgy_per_h(
        result.total_uncollided_collision_air_kerma_rate_gy_per_s
    )

    adjusted_total = convert_gy_per_s_to_microgy_per_h(adjusted_total_gy_per_s)

    x_positions = list(range(len(result.line_results)))

    bar_width = 0.34

    primary_color, warning_color, _ = get_plot_colors()

    figure, axes = plt.subplots(figsize=(11.5, 6.8))

    uncollided_bars = axes.bar(
        [position - bar_width / 2.0 for position in x_positions],
        uncollided_values,
        width=bar_width,
        label="Uncollided collision air kerma",
        color=primary_color,
        alpha=1.0,
        edgecolor="black",
        linewidth=0.8,
        zorder=3,
    )

    adjusted_bars = axes.bar(
        [position + bar_width / 2.0 for position in x_positions],
        adjusted_values,
        width=bar_width,
        label=("G-P exposure-buildup-adjusted collision air kerma"),
        color=warning_color,
        alpha=1.0,
        edgecolor="black",
        linewidth=0.8,
        zorder=3,
    )

    annotate_contribution_bars(
        axes=axes,
        bars=uncollided_bars,
        values=uncollided_values,
        total=uncollided_total,
    )

    annotate_contribution_bars(
        axes=axes,
        bars=adjusted_bars,
        values=adjusted_values,
        total=adjusted_total,
    )

    axes.set_xticks(x_positions)

    axes.set_xticklabels(
        line_labels,
        fontsize=9,
    )

    axes.set_ylabel("Collision air-kerma-rate contribution (µGy/h)")

    axes.set_xlabel(f"{result.source_name} photon line")

    axes.set_axisbelow(True)

    axes.grid(
        axis="y",
        alpha=0.28,
        zorder=0,
    )
    legend = axes.legend(
        loc="upper left",
        frameon=True,
    )

    legend_frame = legend.get_frame()

    legend_frame.set_facecolor("white")

    legend_frame.set_edgecolor("black")

    legend_frame.set_linewidth(1.0)

    legend_frame.set_alpha(1.0)

    for legend_text in legend.get_texts():
        legend_text.set_color("black")

    maximum_value = max(adjusted_values + uncollided_values)

    axes.set_ylim(
        0.0,
        maximum_value * 1.28,
    )

    figure.suptitle(
        (f"{result.source_name} Photon-Line Contributions to Collision Air Kerma"),
        x=0.08,
        y=0.965,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=PLOT_THEME.text,
    )

    if scenario_context is not None:
        figure.text(
            0.08,
            0.885,
            scenario_context,
            ha="left",
            va="top",
            fontsize=9,
            color=PLOT_THEME.muted_text,
        )

    figure_note = (
        "Bar labels show each line's collision air-kerma-rate "
        "contribution and percentage of the corresponding source total. "
        "I is photon emission intensity in photons per decay; "
        "B is the line-specific G-P exposure buildup factor. "
        "Dry-air response coefficients use NIST mu_en/rho data."
    )

    figure.text(
        0.08,
        0.025,
        textwrap.fill(
            figure_note,
            width=135,
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=PLOT_THEME.muted_text,
    )

    figure.subplots_adjust(
        left=0.11,
        right=0.96,
        top=0.79,
        bottom=0.19,
    )

    return figure
