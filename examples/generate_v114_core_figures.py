# Generate the first V1.14 core deterministic-versus-OpenMC analysis figures.
#
# This script has no OpenMC dependency. It reads the authoritative aggregated
# V1.14 core matrix and produces two report-ready figures:
#
#   1. G-P versus Monte Carlo buildup across the core matrix.
#   2. OpenMC relative difference from the deterministic G-P response.
#
# Run from the repository root:
#
#   python examples/generate_v114_core_figures.py

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


import matplotlib

matplotlib.use("Agg")


import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np


from plotting import save_figure_formats  # noqa: E402
from plotting_utils import apply_project_plot_style  # noqa: E402


MATRIX_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "analysis"
    / "v114_core_matrix.json"
)

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "docs"
    / "figures"
    / "v1.14"
)

OUTPUT_FORMATS = (
    "png",
    "svg",
)

DPI = 300

EXPECTED_RECORD_TYPE = (
    "v114_core_deterministic_openmc_matrix"
)

EXPECTED_CASE_COUNT = 8

MATERIAL_ORDER = (
    "lead",
    "tungsten",
    "concrete_ordinary",
    "water",
)

MATERIAL_LABELS = {
    "lead": "Lead",
    "tungsten": "Tungsten",
    "concrete_ordinary": "Ordinary\nConcrete",
    "water": "Water",
}

SCENARIO_CONTEXT = (
    "Cs-137 | 3.70 × 10¹⁰ Bq | concentric spherical benchmark | "
    "evaluation shell 99.5–100.5 cm | 5.0 × 10⁶ OpenMC histories/case"
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(
            message
        )


def require_number(
    value: Any,
    description: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{description} must be numerical."
        )

    number = float(
        value
    )

    if not math.isfinite(
        number
    ):
        raise ValueError(
            f"{description} must be finite."
        )

    return number


def load_matrix() -> dict[str, Any]:
    if not MATRIX_PATH.is_file():
        raise FileNotFoundError(
            "V1.14 aggregated core matrix does not exist: "
            f"{MATRIX_PATH}"
        )

    try:
        matrix = json.loads(
            MATRIX_PATH.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "V1.14 aggregated core matrix contains invalid JSON: "
            f"{error}"
        ) from error

    require(
        isinstance(matrix, dict),
        (
            "V1.14 aggregated core matrix "
            "must be a JSON object."
        ),
    )

    require(
        matrix.get(
            "record_type"
        )
        == EXPECTED_RECORD_TYPE,
        (
            "Unexpected V1.14 matrix record type."
        ),
    )

    require(
        matrix.get(
            "case_count"
        )
        == EXPECTED_CASE_COUNT,
        (
            "V1.14 core figure generation "
            "requires exactly eight cases."
        ),
    )

    cases = matrix.get(
        "cases"
    )

    require(
        isinstance(cases, list),
        (
            "V1.14 aggregated matrix must "
            "contain a case list."
        ),
    )

    require(
        len(cases)
        == EXPECTED_CASE_COUNT,
        (
            "V1.14 aggregated matrix case "
            "list has the wrong length."
        ),
    )

    return matrix


def get_case_map(
    matrix: dict[str, Any],
) -> dict[
    tuple[str, float],
    dict[str, Any],
]:
    case_map: dict[
        tuple[str, float],
        dict[str, Any],
    ] = {}

    cases = matrix[
        "cases"
    ]

    for case in cases:
        require(
            isinstance(case, dict),
            (
                "Every V1.14 core case "
                "must be a JSON object."
            ),
        )

        material_key = case.get(
            "material_key"
        )

        require(
            isinstance(material_key, str),
            (
                "Every V1.14 core case must "
                "contain a material key."
            ),
        )

        target_mfp = require_number(
            case.get(
                "target_mean_free_paths"
            ),
            (
                "V1.14 core case target MFP"
            ),
        )

        key = (
            material_key,
            target_mfp,
        )

        require(
            key not in case_map,
            (
                "Duplicate V1.14 matrix "
                f"entry for {key}."
            ),
        )

        case_map[
            key
        ] = case

    expected_keys = {
        ("lead", 1.0),
        ("lead", 5.0),
        ("lead", 10.0),
        ("tungsten", 1.0),
        ("tungsten", 5.0),
        ("concrete_ordinary", 1.0),
        ("concrete_ordinary", 5.0),
        ("water", 5.0),
    }

    require(
        set(
            case_map
        )
        == expected_keys,
        (
            "V1.14 core matrix does not "
            "contain the expected eight cases."
        ),
    )

    return case_map


def add_figure_context(
    figure: Figure,
) -> None:
    figure.text(
        0.5,
        0.012,
        SCENARIO_CONTEXT,
        ha="center",
        va="bottom",
        fontsize=8.5,
    )


def plot_buildup_comparison(
    case_map: dict[
        tuple[str, float],
        dict[str, Any],
    ],
) -> Figure:
    # Show matched 1-MFP and 5-MFP material comparisons, plus the Lead
    # 10-MFP extension. The two response models are shown side-by-side so
    # both material dependence and optical-thickness dependence remain
    # immediately visible.

    ordered_cases = [
        ("lead", 1.0),
        ("tungsten", 1.0),
        ("concrete_ordinary", 1.0),
        ("lead", 5.0),
        ("tungsten", 5.0),
        ("concrete_ordinary", 5.0),
        ("water", 5.0),
        ("lead", 10.0),
    ]

    labels = [
        "Lead\n1 MFP",
        "Tungsten\n1 MFP",
        "Concrete\n1 MFP",
        "Lead\n5 MFP",
        "Tungsten\n5 MFP",
        "Concrete\n5 MFP",
        "Water\n5 MFP",
        "Lead\n10 MFP",
    ]

    gp_values: list[float] = []
    mc_values: list[float] = []
    mc_buildup_uncertainties: list[
        float
    ] = []

    for key in ordered_cases:
        case = case_map[
            key
        ]

        gp_buildup = require_number(
            case.get(
                "gp_buildup_factor"
            ),
            (
                f"{key}: G-P buildup factor"
            ),
        )

        mc_buildup = require_number(
            case.get(
                "openmc_buildup_ratio"
            ),
            (
                f"{key}: Monte Carlo buildup ratio"
            ),
        )

        openmc_direct = require_number(
            case.get(
                "openmc_direct_microgy_per_h"
            ),
            (
                f"{key}: OpenMC direct response"
            ),
        )

        openmc_std = require_number(
            case.get(
                "openmc_standard_deviation_microgy_per_h"
            ),
            (
                f"{key}: OpenMC standard deviation"
            ),
        )

        deterministic_uncollided = (
            require_number(
                case.get(
                    "deterministic_uncollided_microgy_per_h"
                ),
                (
                    f"{key}: deterministic "
                    "uncollided response"
                ),
            )
        )

        require(
            gp_buildup > 0.0,
            (
                f"{key}: G-P buildup factor "
                "must be positive."
            ),
        )

        require(
            mc_buildup > 0.0,
            (
                f"{key}: Monte Carlo buildup "
                "ratio must be positive."
            ),
        )

        require(
            openmc_direct > 0.0,
            (
                f"{key}: OpenMC direct response "
                "must be positive."
            ),
        )

        require(
            openmc_std >= 0.0,
            (
                f"{key}: OpenMC standard deviation "
                "cannot be negative."
            ),
        )

        require(
            deterministic_uncollided > 0.0,
            (
                f"{key}: deterministic uncollided "
                "response must be positive."
            ),
        )

        gp_values.append(
            gp_buildup
        )

        mc_values.append(
            mc_buildup
        )

        mc_buildup_uncertainties.append(
            openmc_std
            / deterministic_uncollided
        )

    x_values = np.arange(
        len(
            ordered_cases
        ),
        dtype=float,
    )

    bar_width = 0.36

    figure, axes = plt.subplots(
        figsize=(
            11.8,
            6.7,
        )
    )
    axes.set_facecolor(
        "white"
    )

    axes.bar(
        x_values
        - bar_width / 2.0,
        gp_values,
        width=bar_width,
        label="G-P deterministic buildup",
        alpha=1.0,
    )

    axes.bar(
        x_values
        + bar_width / 2.0,
        mc_values,
        width=bar_width,
        yerr=mc_buildup_uncertainties,
        capsize=3.0,
        label="OpenMC observed buildup",
        alpha=1.0,
    )

    axes.set_title(
        "Cs-137 Photon Buildup: Deterministic G-P vs OpenMC"
    )

    axes.set_ylabel(
        "Buildup factor / observed buildup ratio"
    )

    axes.set_xlabel(
        "Shield material and optical thickness"
    )

    axes.set_xticks(
        x_values,
        labels=labels,
    )

    axes.set_ylim(
        bottom=0.0
    )

    axes.grid(
        axis="y",
        alpha=0.25,
    )

    legend = axes.legend(
        loc="upper left"
    )

    legend.get_frame().set_facecolor(
        "white"
    )
    legend.get_frame().set_alpha(
        1.0
    )
    legend.get_frame().set_edgecolor(
        "0.8"
    )

    for legend_text in legend.get_texts():
        legend_text.set_color(
            "black"
        )

    axes.axvline(
        2.5,
        linewidth=1.0,
        linestyle="--",
        alpha=0.55,
    )

    axes.axvline(
        6.5,
        linewidth=1.0,
        linestyle="--",
        alpha=0.55,
    )

    upper_limit = max(
        max(
            gp_values
        ),
        max(
            mc_values
        ),
    )

    axes.text(
        1.0,
        upper_limit * 1.035,
        "1 MFP",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black",
    )

    axes.text(
        4.5,
        upper_limit * 1.035,
        "5 MFP",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black",
    )

    axes.text(
        7.0,
        upper_limit * 1.035,
        "10 MFP",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black",
    )

    axes.set_ylim(
        0.0,
        upper_limit * 1.15,
    )

    add_figure_context(
        figure
    )

    figure.tight_layout(
        rect=(
            0.0,
            0.045,
            1.0,
            1.0,
        )
    )

    return figure


def plot_openmc_vs_gp_difference(
    case_map: dict[
        tuple[str, float],
        dict[str, Any],
    ],
) -> Figure:
    # Signed error figure:
    #
    #   (OpenMC - G-P) / G-P
    #
    # Positive values mean OpenMC predicts a larger response than the
    # deterministic G-P model. Negative values mean G-P is larger.

    ordered_cases = [
        ("lead", 1.0),
        ("tungsten", 1.0),
        ("concrete_ordinary", 1.0),
        ("lead", 5.0),
        ("tungsten", 5.0),
        ("concrete_ordinary", 5.0),
        ("water", 5.0),
        ("lead", 10.0),
    ]

    labels = [
        "Lead — 1 MFP",
        "Tungsten — 1 MFP",
        "Concrete — 1 MFP",
        "Lead — 5 MFP",
        "Tungsten — 5 MFP",
        "Concrete — 5 MFP",
        "Water — 5 MFP",
        "Lead — 10 MFP",
    ]

    differences_percent: list[
        float
    ] = []

    uncertainties_percent: list[
        float
    ] = []

    for key in ordered_cases:
        case = case_map[
            key
        ]

        relative_difference = (
            require_number(
                case.get(
                    "openmc_vs_gp_relative_difference"
                ),
                (
                    f"{key}: OpenMC-vs-G-P "
                    "relative difference"
                ),
            )
        )

        openmc_direct = require_number(
            case.get(
                "openmc_direct_microgy_per_h"
            ),
            (
                f"{key}: OpenMC direct response"
            ),
        )

        openmc_std = require_number(
            case.get(
                "openmc_standard_deviation_microgy_per_h"
            ),
            (
                f"{key}: OpenMC standard deviation"
            ),
        )

        deterministic_gp = require_number(
            case.get(
                "deterministic_gp_microgy_per_h"
            ),
            (
                f"{key}: deterministic G-P response"
            ),
        )

        require(
            openmc_direct > 0.0,
            (
                f"{key}: OpenMC direct response "
                "must be positive."
            ),
        )

        require(
            deterministic_gp > 0.0,
            (
                f"{key}: deterministic G-P response "
                "must be positive."
            ),
        )

        differences_percent.append(
            100.0
            * relative_difference
        )

        # Only OpenMC sampling uncertainty is shown. No deterministic-model
        # uncertainty is implied or assigned.
        uncertainties_percent.append(
            100.0
            * openmc_std
            / deterministic_gp
        )

    y_values = np.arange(
        len(
            ordered_cases
        ),
        dtype=float,
    )

    figure, axes = plt.subplots(
        figsize=(
            10.8,
            6.8,
        )
    )
    axes.set_facecolor(
        "white"
    )

    axes.barh(
        y_values,
        differences_percent,
        xerr=uncertainties_percent,
        capsize=3.0,
        alpha=1.0,
    )

    axes.axvline(
        0.0,
        linewidth=1.2,
    )

    axes.set_title(
        "OpenMC Difference from Deterministic G-P Response"
    )

    axes.set_xlabel(
        "Signed relative difference, (OpenMC − G-P) / G-P [%]"
    )

    axes.set_ylabel(
        "Benchmark case"
    )

    axes.set_yticks(
        y_values,
        labels=labels,
    )

    axes.invert_yaxis()

    axes.grid(
        axis="x",
        alpha=0.25,
    )

    # Put numerical labels beyond each error bar so the sign and magnitude
    # remain obvious when the figure is used outside the full report.
    for (
        y_value,
        difference,
        uncertainty,
    ) in zip(
        y_values,
        differences_percent,
        uncertainties_percent,
        strict=True,
    ):
        if difference >= 0.0:
            text_x = (
                difference
                + uncertainty
                + 1.2
            )

            horizontal_alignment = (
                "left"
            )

        else:
            text_x = (
                difference
                - uncertainty
                - 1.2
            )

            horizontal_alignment = (
                "right"
            )

        axes.text(
            text_x,
            y_value,
            f"{difference:+.1f}%",
            va="center",
            ha=(
                horizontal_alignment
            ),
            fontsize=8.5,
            color="black",
        )

    lower_extent = min(
        difference
        - uncertainty
        for difference, uncertainty
        in zip(
            differences_percent,
            uncertainties_percent,
            strict=True,
        )
    )

    upper_extent = max(
        difference
        + uncertainty
        for difference, uncertainty
        in zip(
            differences_percent,
            uncertainties_percent,
            strict=True,
        )
    )

    horizontal_padding = max(
        7.0,
        0.13
        * (
            upper_extent
            - lower_extent
        ),
    )

    axes.set_xlim(
        lower_extent
        - horizontal_padding,
        upper_extent
        + horizontal_padding,
    )

    add_figure_context(
        figure
    )

    figure.tight_layout(
        rect=(
            0.0,
            0.045,
            1.0,
            1.0,
        )
    )

    return figure


def save_and_close(
    figure: Figure,
    output_stem: str,
) -> list[
    Path
]:
    saved_paths = save_figure_formats(
        figure=figure,
        output_stem=(
            OUTPUT_DIRECTORY
            / output_stem
        ),
        formats=(
            OUTPUT_FORMATS
        ),
        dpi=DPI,
    )

    plt.close(
        figure
    )

    return saved_paths


def main() -> None:
    plt.style.use(
        "default"
    )

    apply_project_plot_style()

    matrix = load_matrix()

    case_map = get_case_map(
        matrix
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    figures = [
        (
            "v114_core_buildup_comparison",
            plot_buildup_comparison(
                case_map
            ),
        ),
        (
            "v114_core_openmc_vs_gp_difference",
            plot_openmc_vs_gp_difference(
                case_map
            ),
        ),
    ]

    saved_paths: list[
        Path
    ] = []

    for (
        output_stem,
        figure,
    ) in figures:
        saved_paths.extend(
            save_and_close(
                figure=figure,
                output_stem=(
                    output_stem
                ),
            )
        )

    expected_file_count = (
        len(
            figures
        )
        * len(
            OUTPUT_FORMATS
        )
    )

    require(
        len(
            saved_paths
        )
        == expected_file_count,
        (
            "V1.14 core figure generation "
            "created an unexpected number of files."
        ),
    )

    for saved_path in (
        saved_paths
    ):
        require(
            saved_path.is_file(),
            (
                "Expected V1.14 figure "
                f"was not created: {saved_path}"
            ),
        )

    print()
    print("=" * 88)
    print("V1.14 CORE ANALYSIS FIGURES CREATED")
    print("=" * 88)

    print(
        "Source matrix:"
    )

    print(
        "  "
        f"{MATRIX_PATH}"
    )

    print(
        "Generated figures:"
    )

    for saved_path in (
        saved_paths
    ):
        print(
            "  "
            f"{saved_path}"
        )

    print("=" * 88)
    print()


if __name__ == "__main__":
    main()
