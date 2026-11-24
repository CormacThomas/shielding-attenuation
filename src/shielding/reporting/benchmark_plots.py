# V1.13 deterministic-versus-OpenMC benchmark figure.
#
# This module renders the already validated benchmark plot data.
# It performs no transport, response folding, normalization, or
# result-file parsing.

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import (
    Circle,
    FancyBboxPatch,
    Patch,
)

from shielding.reporting.benchmark_data import (
    OpenMCBenchmarkPlotData,
)
from shielding.reporting.style import (
    PLOT_THEME,
    get_plot_colors,
)

GEOMETRY_CAVITY_COLOR = "#A9D5E5"
GEOMETRY_LEAD_COLOR = "#585E68"
GEOMETRY_TRANSPORT_VOID_COLOR = "#F6F7F9"
GEOMETRY_EVALUATION_COLOR = "#ED7D18"
GEOMETRY_EXTERIOR_VOID_COLOR = "#D7E4F0"


def require_geometry_image(
    image_path: Path,
    description: str,
) -> Path:
    if not image_path.is_file():
        raise FileNotFoundError(f"{description} does not exist: {image_path}")

    return image_path


def require_gp_response(
    plot_data: OpenMCBenchmarkPlotData,
) -> float:
    gp_response = plot_data.deterministic_gp_microgy_per_h

    if gp_response is None:
        raise ValueError(
            "The official V1.13 benchmark figure requires "
            "a deterministic G-P-adjusted response."
        )

    return gp_response


def add_panel_label(
    axes,
    label: str,
) -> None:
    axes.text(
        -0.08,
        1.06,
        label,
        transform=axes.transAxes,
        fontsize=12,
        fontweight="bold",
        color=PLOT_THEME.text,
        ha="left",
        va="bottom",
    )


def annotate_response_bars(
    axes,
    bars,
    values: list[float],
) -> None:
    for bar, value in zip(
        bars,
        values,
        strict=True,
    ):
        axes.annotate(
            f"{value:.3f}",
            xy=(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
            ),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color=PLOT_THEME.axes_text,
        )


def render_v113_geometry_panel(
    axes,
    full_domain_image_path: Path,
    central_detail_image_path: Path,
    include_panel_label: bool = True,
) -> None:
    # Render the raw OpenMC full-domain geometry as the
    # primary view and the central shield geometry as an
    # inset.
    #
    # Physical coordinate extents reproduce the OpenMC
    # plot widths:
    #
    # full domain:
    #   220 cm × 220 cm
    #
    # central detail:
    #   16 cm × 16 cm

    require_geometry_image(
        full_domain_image_path,
        "Full-domain OpenMC geometry image",
    )

    require_geometry_image(
        central_detail_image_path,
        "Central-detail OpenMC geometry image",
    )

    full_domain_image = mpimg.imread(full_domain_image_path)

    central_detail_image = mpimg.imread(central_detail_image_path)

    axes.imshow(
        full_domain_image,
        extent=(
            -110.0,
            110.0,
            -110.0,
            110.0,
        ),
        interpolation="nearest",
        zorder=1,
    )

    axes.set_xlim(
        -112.0,
        112.0,
    )

    axes.set_ylim(
        -112.0,
        112.0,
    )

    axes.set_aspect("equal")

    axes.axis("off")

    axes.set_title(
        "OpenMC spherical benchmark geometry",
        loc="left",
        fontweight="bold",
    )

    # Explicitly identify the two important outer radii.
    evaluation_shell_outline = Circle(
        (
            0.0,
            0.0,
        ),
        radius=100.0,
        fill=False,
        edgecolor=GEOMETRY_EVALUATION_COLOR,
        linewidth=1.5,
        zorder=3,
    )

    outer_boundary_outline = Circle(
        (
            0.0,
            0.0,
        ),
        radius=110.0,
        fill=False,
        edgecolor=PLOT_THEME.axes_muted_text,
        linewidth=1.0,
        linestyle="--",
        zorder=3,
    )

    axes.add_patch(evaluation_shell_outline)

    axes.add_patch(outer_boundary_outline)

    axes.annotate(
        ("Evaluation shell\n99.5–100.5 cm"),
        xy=(
            -70.7,
            70.7,
        ),
        xytext=(
            -103.0,
            87.0,
        ),
        ha="left",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color=PLOT_THEME.axes_text,
        arrowprops={
            "arrowstyle": "->",
            "color": PLOT_THEME.axes_text,
            "linewidth": 0.9,
        },
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": "#AEB5BD",
            "alpha": 0.96,
        },
        zorder=6,
    )

    axes.annotate(
        "Outer vacuum boundary: 110 cm",
        xy=(
            -77.5,
            -77.5,
        ),
        xytext=(
            -97.0,
            -68.0,
        ),
        ha="left",
        va="center",
        fontsize=8.0,
        color=PLOT_THEME.axes_text,
        arrowprops={
            "arrowstyle": "->",
            "color": PLOT_THEME.axes_text,
            "linewidth": 0.8,
        },
        zorder=6,
    )

    # ------------------------------------------------------------
    # Central-detail inset
    # ------------------------------------------------------------

    inset_axes = axes.inset_axes(
        [
            0.56,
            0.53,
            0.40,
            0.40,
        ]
    )

    inset_axes.imshow(
        central_detail_image,
        extent=(
            -8.0,
            8.0,
            -8.0,
            8.0,
        ),
        interpolation="nearest",
        zorder=1,
    )

    inset_axes.set_xlim(
        -8.0,
        8.0,
    )

    inset_axes.set_ylim(
        -8.0,
        8.0,
    )

    inset_axes.set_aspect("equal")

    inset_axes.set_xticks([])

    inset_axes.set_yticks([])

    inset_axes.set_title(
        "Central shield detail",
        fontsize=8.7,
        fontweight="bold",
        color="black",
        pad=4,
    )

    for spine in inset_axes.spines.values():
        spine.set_color("black")

        spine.set_linewidth(1.2)

    # Mathematical point sources have no visible spatial
    # area in the raw OpenMC geometry image. Add a marker at
    # the exact model origin.
    inset_axes.scatter(
        0.0,
        0.0,
        marker="*",
        s=95,
        facecolor="#D62728",
        edgecolor="black",
        linewidth=0.7,
        zorder=7,
    )

    # Reproduce the physical cavity and shield boundaries.
    inset_axes.add_patch(
        Circle(
            (
                0.0,
                0.0,
            ),
            radius=1.0,
            fill=False,
            edgecolor="black",
            linewidth=0.8,
            zorder=5,
        )
    )

    inset_axes.add_patch(
        Circle(
            (
                0.0,
                0.0,
            ),
            radius=6.0,
            fill=False,
            edgecolor="black",
            linewidth=0.8,
            zorder=5,
        )
    )

    inset_axes.annotate(
        "Cs-137 point source",
        xy=(
            0.0,
            0.0,
        ),
        xytext=(
            -7.1,
            6.6,
        ),
        ha="left",
        va="center",
        fontsize=7.2,
        fontweight="bold",
        color="black",
        arrowprops={
            "arrowstyle": "->",
            "color": "black",
            "linewidth": 0.7,
        },
        zorder=8,
    )

    inset_axes.annotate(
        ("Vacuum cavity\nradius: 1 cm"),
        xy=(
            -0.7,
            0.5,
        ),
        xytext=(
            -7.1,
            -5.8,
        ),
        ha="left",
        va="center",
        fontsize=7.0,
        color="black",
        arrowprops={
            "arrowstyle": "->",
            "color": "black",
            "linewidth": 0.7,
        },
        zorder=8,
    )

    inset_axes.annotate(
        ("Lead shell\n1–6 cm radius"),
        xy=(
            4.2,
            -2.1,
        ),
        xytext=(
            1.8,
            -7.0,
        ),
        ha="left",
        va="center",
        fontsize=7.0,
        color="black",
        arrowprops={
            "arrowstyle": "->",
            "color": "black",
            "linewidth": 0.7,
        },
        zorder=8,
    )

    # Dimension line showing the 5 cm Lead thickness.
    inset_axes.annotate(
        "",
        xy=(
            1.0,
            6.7,
        ),
        xytext=(
            6.0,
            6.7,
        ),
        arrowprops={
            "arrowstyle": "<->",
            "color": "black",
            "linewidth": 0.8,
        },
        zorder=8,
    )

    inset_axes.text(
        3.5,
        7.05,
        "5 cm Lead",
        ha="center",
        va="bottom",
        fontsize=7.0,
        fontweight="bold",
        color="black",
        zorder=8,
    )

    # ------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------

    legend_handles = [
        Line2D(
            [],
            [],
            marker="*",
            linestyle="none",
            markersize=9,
            markerfacecolor="#D62728",
            markeredgecolor="black",
            label="Cs-137 point source",
        ),
        Patch(
            facecolor=GEOMETRY_CAVITY_COLOR,
            edgecolor="black",
            label="Vacuum source cavity",
        ),
        Patch(
            facecolor=GEOMETRY_LEAD_COLOR,
            edgecolor="black",
            label="Lead shield",
        ),
        Patch(
            facecolor=GEOMETRY_TRANSPORT_VOID_COLOR,
            edgecolor="#AEB5BD",
            label="Transport vacuum",
        ),
        Patch(
            facecolor=GEOMETRY_EVALUATION_COLOR,
            edgecolor=GEOMETRY_EVALUATION_COLOR,
            label="Evaluation shell",
        ),
        Patch(
            facecolor=GEOMETRY_EXTERIOR_VOID_COLOR,
            edgecolor="#AEB5BD",
            label="Exterior vacuum",
        ),
    ]

    geometry_legend = axes.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(
            0.01,
            0.01,
        ),
        fontsize=7.3,
        frameon=True,
        ncol=2,
        borderaxespad=0.0,
    )

    legend_frame = geometry_legend.get_frame()

    legend_frame.set_facecolor("white")

    legend_frame.set_edgecolor("black")

    legend_frame.set_alpha(0.96)

    for legend_text in geometry_legend.get_texts():
        legend_text.set_color("black")

    if include_panel_label:
        add_panel_label(
            axes,
            "A",
        )


def plot_v113_geometry_annotated(
    full_domain_image_path: Path,
    central_detail_image_path: Path,
) -> Figure:
    figure, axes = plt.subplots(
        figsize=(
            10.5,
            8.5,
        )
    )

    render_v113_geometry_panel(
        axes=axes,
        full_domain_image_path=(full_domain_image_path),
        central_detail_image_path=(central_detail_image_path),
        include_panel_label=False,
    )

    figure.suptitle(
        ("V1.13 Cs-137 / Lead OpenMC Benchmark Geometry"),
        x=0.06,
        y=0.97,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=PLOT_THEME.text,
    )

    figure.text(
        0.06,
        0.930,
        (
            "Concentric spherical geometry | "
            "XY slice through model origin | "
            "not drawn as a single uniform scale"
        ),
        ha="left",
        va="top",
        fontsize=9.5,
        color=PLOT_THEME.muted_text,
    )

    figure.text(
        0.005,
        0.005,
        (
            "The full-domain view shows the transport "
            "region, evaluation shell, and outer vacuum "
            "boundary. The inset magnifies the centered "
            "point source, 1 cm vacuum cavity, and 5 cm "
            "Lead shell."
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=PLOT_THEME.muted_text,
    )

    figure.subplots_adjust(
        left=0.06,
        right=0.97,
        top=0.86,
        bottom=0.09,
    )

    return figure


def plot_openmc_v113_benchmark(
    plot_data: OpenMCBenchmarkPlotData,
    full_domain_geometry_path: Path,
    central_detail_geometry_path: Path,
) -> Figure:
    gp_response = require_gp_response(plot_data)

    (
        primary_color,
        comparison_color,
        openmc_color,
    ) = get_plot_colors()

    figure = plt.figure(figsize=(15.5, 11.8))

    grid = figure.add_gridspec(
        nrows=2,
        ncols=2,
        left=0.07,
        right=0.915,
        top=0.86,
        bottom=0.12,
        wspace=0.28,
        hspace=0.34,
        height_ratios=(
            1.30,
            1.00,
        ),
    )

    geometry_axes = figure.add_subplot(grid[0, 0])

    spectrum_axes = figure.add_subplot(grid[0, 1])

    response_axes = figure.add_subplot(grid[1, 0])

    summary_axes = figure.add_subplot(grid[1, 1])

    geometry_axes.set_gid("v113_panel_geometry")

    spectrum_axes.set_gid("v113_panel_spectrum")

    response_axes.set_gid("v113_panel_response")

    summary_axes.set_gid("v113_panel_summary")

    # ------------------------------------------------------------
    # Panel A: OpenMC benchmark geometry
    # ------------------------------------------------------------

    render_v113_geometry_panel(
        axes=geometry_axes,
        full_domain_image_path=(full_domain_geometry_path),
        central_detail_image_path=(central_detail_geometry_path),
        include_panel_label=True,
    )

    # ------------------------------------------------------------
    # Panel C: deterministic-versus-OpenMC response
    # ------------------------------------------------------------

    response_labels = [
        "Deterministic\nuncollided",
        "Deterministic\nG-P adjusted",
        "OpenMC\ndirect",
    ]

    response_values = [
        (plot_data.deterministic_uncollided_microgy_per_h),
        gp_response,
        plot_data.openmc_direct_microgy_per_h,
    ]

    response_bars = response_axes.bar(
        response_labels,
        response_values,
        color=[
            primary_color,
            comparison_color,
            openmc_color,
        ],
        edgecolor=PLOT_THEME.axes_text,
        linewidth=0.8,
        zorder=3,
    )

    response_axes.errorbar(
        x=2,
        y=plot_data.openmc_direct_microgy_per_h,
        yerr=(plot_data.openmc_direct_standard_deviation_microgy_per_h),
        fmt="none",
        ecolor=PLOT_THEME.axes_text,
        elinewidth=1.3,
        capsize=5,
        capthick=1.3,
        zorder=5,
    )

    annotate_response_bars(
        response_axes,
        response_bars,
        response_values,
    )

    response_axes.set_ylabel("Collision air-kerma rate (µGy/h)")

    response_axes.set_title(
        "Matched deterministic and transport responses",
        loc="left",
        fontweight="bold",
    )

    response_axes.grid(
        axis="y",
        linestyle=":",
        alpha=0.35,
        zorder=0,
    )

    response_axes.set_axisbelow(True)

    response_axes.set_ylim(
        0.0,
        max(response_values) * 1.22,
    )

    add_panel_label(
        response_axes,
        "C",
    )

    # ------------------------------------------------------------
    # Panel B: transported photon spectrum
    # ------------------------------------------------------------

    positive_bins = [
        spectrum_bin
        for spectrum_bin in plot_data.spectrum_bins
        if (spectrum_bin.photon_fluence_rate_per_cm2_s > 0)
    ]

    if len(positive_bins) == 0:
        raise ValueError("The V1.13 spectrum contains no positive bins.")

    spectrum_energies_kev = [
        (spectrum_bin.representative_energy_ev / 1000.0)
        for spectrum_bin in positive_bins
    ]

    spectrum_values = [
        (spectrum_bin.photon_fluence_rate_per_cm2_s) for spectrum_bin in positive_bins
    ]

    spectrum_widths_kev = [
        (spectrum_bin.upper_energy_ev - spectrum_bin.lower_energy_ev) / 1000.0
        for spectrum_bin in positive_bins
    ]

    spectrum_axes.bar(
        spectrum_energies_kev,
        spectrum_values,
        width=spectrum_widths_kev,
        color=primary_color,
        edgecolor="none",
        alpha=0.88,
        zorder=3,
    )

    spectrum_axes.set_xscale("log")

    spectrum_axes.set_yscale("log")

    spectrum_axes.set_xlabel(
        "Photon energy (keV)",
        labelpad=5,
    )

    spectrum_axes.set_ylabel("Photon fluence rate (photons/cm²/s)")

    spectrum_axes.set_title(
        "OpenMC photon spectrum in evaluation shell",
        loc="left",
        fontweight="bold",
    )

    spectrum_axes.grid(
        which="major",
        linestyle=":",
        alpha=0.35,
    )

    spectrum_axes.grid(
        which="minor",
        linestyle=":",
        alpha=0.12,
    )

    spectrum_axes.set_axisbelow(True)

    dominant_bin = max(
        positive_bins,
        key=lambda spectrum_bin: spectrum_bin.photon_fluence_rate_per_cm2_s,
    )

    spectrum_axes.annotate(
        "Dominant source-energy bin",
        xy=(
            dominant_bin.representative_energy_ev / 1000.0,
            dominant_bin.photon_fluence_rate_per_cm2_s,
        ),
        xytext=(-20, 25),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        color="#AEB5BD",
        arrowprops={
            "arrowstyle": "-",
            "color": "#AEB5BD",
            "linewidth": 0.8,
        },
    )

    add_panel_label(
        spectrum_axes,
        "B",
    )

    # ------------------------------------------------------------
    # Panel D: benchmark summary
    # ------------------------------------------------------------

    summary_axes.axis("off")

    gp_difference_text = "Unavailable"

    if plot_data.relative_difference_from_gp is not None:
        gp_difference_text = f"{plot_data.relative_difference_from_gp:+.2%}"

    status_text = (
        "PASS"
        if (
            plot_data.required_uncertainty_pass
            and plot_data.preferred_uncertainty_pass
            and plot_data.direct_vs_folded_pass
        )
        else "REVIEW"
    )

    summary_card = FancyBboxPatch(
        (
            0.02,
            0.04,
        ),
        0.96,
        0.91,
        transform=summary_axes.transAxes,
        boxstyle=("round,pad=0.018,rounding_size=0.025"),
        facecolor="white",
        edgecolor="#AEB5BD",
        linewidth=1.2,
        clip_on=False,
    )

    summary_axes.add_patch(summary_card)

    # Left column: benchmark configuration.
    summary_axes.text(
        0.07,
        0.88,
        "Benchmark configuration",
        transform=summary_axes.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.07,
        0.77,
        "Scenario",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.07,
        0.715,
        plot_data.scenario_id,
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.07,
        0.61,
        "Evaluation shell",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.07,
        0.555,
        (
            f"{plot_data.evaluation_shell_inner_radius_cm:.1f}"
            "–"
            f"{plot_data.evaluation_shell_outer_radius_cm:.1f} cm"
        ),
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.07,
        0.45,
        "Physical photon source rate",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.07,
        0.395,
        (f"{plot_data.physical_source_rate_per_s:.4e} photons/s"),
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    # Right column: response comparison.
    summary_axes.text(
        0.55,
        0.88,
        "Response comparison",
        transform=summary_axes.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.55,
        0.77,
        "OpenMC / uncollided",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.55,
        0.715,
        (f"{plot_data.observed_monte_carlo_buildup_ratio:.4f}"),
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.55,
        0.61,
        "Difference from uncollided",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.55,
        0.555,
        (f"{plot_data.relative_difference_from_uncollided:+.2%}"),
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    summary_axes.text(
        0.55,
        0.45,
        "Difference from G-P",
        transform=summary_axes.transAxes,
        fontsize=8.5,
        color="#555555",
    )

    summary_axes.text(
        0.55,
        0.395,
        gp_difference_text,
        transform=summary_axes.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
    )

    # Divider between descriptive and quality-check sections.
    summary_axes.plot(
        [
            0.06,
            0.94,
        ],
        [
            0.32,
            0.32,
        ],
        transform=summary_axes.transAxes,
        color="#C8CDD2",
        linewidth=1.0,
    )

    # Bottom metrics.
    summary_metric_positions = [
        (
            0.08,
            "OpenMC uncertainty",
            f"{plot_data.openmc_relative_uncertainty:.4%}",
        ),
        (
            0.39,
            "Direct vs. folded",
            (f"{plot_data.direct_vs_folded_relative_difference:+.4%}"),
        ),
        (
            0.70,
            "Positive spectrum bins",
            (f"{plot_data.positive_spectrum_bin_count}/{len(plot_data.spectrum_bins)}"),
        ),
    ]

    for (
        x_position,
        metric_label,
        metric_value,
    ) in summary_metric_positions:
        summary_axes.text(
            x_position,
            0.245,
            metric_label,
            transform=summary_axes.transAxes,
            ha="left",
            va="top",
            fontsize=8.2,
            color="#555555",
        )

        summary_axes.text(
            x_position,
            0.175,
            metric_value,
            transform=summary_axes.transAxes,
            ha="left",
            va="top",
            fontsize=12,
            fontweight="bold",
            color="black",
        )

    summary_axes.text(
        0.50,
        0.075,
        (f"V1.13 ACCEPTANCE STATUS: {status_text}"),
        transform=summary_axes.transAxes,
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="black",
    )

    add_panel_label(
        summary_axes,
        "D",
    )

    # ------------------------------------------------------------
    # Figure-level title and note
    # ------------------------------------------------------------

    figure.suptitle(
        ("V1.13 Cs-137 / Lead Deterministic–OpenMC Benchmark"),
        x=0.07,
        y=0.965,
        ha="left",
        fontsize=18,
        fontweight="bold",
        color=PLOT_THEME.text,
    )

    figure.text(
        0.07,
        0.925,
        (
            "Centered Cs-137 photon source | "
            "5.0 cm spherical Lead shield | "
            "99.5–100.5 cm evaluation shell | "
            "collision air kerma in dry air"
        ),
        ha="left",
        va="top",
        fontsize=10,
        color=PLOT_THEME.muted_text,
    )

    figure_note = (
        "OpenMC uncertainty bars represent one standard deviation. "
        "The direct tally and independently spectrum-folded response "
        "agree within the configured acceptance tolerance. The G-P "
        "result uses exposure buildup coefficients applied to the "
        "deterministic collision-air-kerma response."
    )

    figure.text(
        0.07,
        0.014,
        textwrap.fill(
            figure_note,
            width=165,
        ),
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=PLOT_THEME.muted_text,
    )

    return figure
