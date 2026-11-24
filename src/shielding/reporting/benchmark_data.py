# V1.13 OpenMC benchmark plot-data preparation.
#
# This module reads the backend-independent processed OpenMC outputs and
# converts them into one validated plotting-data model.
#
# It intentionally contains no OpenMC or Matplotlib imports.
#
# Input files:
#
#   openmc_response.json
#   deterministic_openmc_comparison.json
#   photon_spectrum.csv
#
# Responsibilities:
#
#   - verify record types and matching scenario identifiers;
#   - verify that JSON and CSV values describe the same result;
#   - preserve deterministic and OpenMC comparison values;
#   - preserve the energy-resolved fluence and air-kerma spectrum;
#   - provide reusable data for the final V1.13 engineering figure.


from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPECTED_RESULT_SCHEMA_VERSION = "1.0"

EXPECTED_RESPONSE_RECORD_TYPE = "openmc_response"

EXPECTED_COMPARISON_RECORD_TYPE = "deterministic_openmc_comparison"


def values_match(
    first_value: float,
    second_value: float,
) -> bool:
    # Compare values serialized independently in JSON and CSV outputs.

    return math.isclose(
        first_value,
        second_value,
        rel_tol=1.0e-9,
        abs_tol=1.0e-18,
    )


def require_finite_value(
    value: float,
    description: str,
) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{description} must be finite.")


def require_nonnegative_value(
    value: float,
    description: str,
) -> None:
    require_finite_value(
        value,
        description,
    )

    if value < 0:
        raise ValueError(f"{description} cannot be negative.")


def require_positive_value(
    value: float,
    description: str,
) -> None:
    require_finite_value(
        value,
        description,
    )

    if value <= 0:
        raise ValueError(f"{description} must be greater than zero.")


@dataclass(frozen=True)
class OpenMCBenchmarkSpectrumBin:
    # One plotting-ready OpenMC photon-spectrum bin.

    bin_index: int

    lower_energy_ev: float
    upper_energy_ev: float
    representative_energy_ev: float

    photon_fluence_rate_per_cm2_s: float
    photon_fluence_rate_standard_deviation_per_cm2_s: float

    relative_uncertainty: float | None

    response_coefficient_gy_cm2_per_photon: float

    air_kerma_rate_contribution_gy_per_s: float
    air_kerma_rate_contribution_microgy_per_h: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.bin_index, bool)
            or not isinstance(
                self.bin_index,
                int,
            )
            or self.bin_index <= 0
        ):
            raise ValueError("OpenMC spectrum-bin index must be a positive integer.")

        require_positive_value(
            self.lower_energy_ev,
            "OpenMC spectrum-bin lower energy",
        )

        require_positive_value(
            self.upper_energy_ev,
            "OpenMC spectrum-bin upper energy",
        )

        if self.upper_energy_ev <= self.lower_energy_ev:
            raise ValueError(
                "OpenMC spectrum-bin upper energy must exceed its lower energy."
            )

        require_positive_value(
            self.representative_energy_ev,
            "OpenMC spectrum-bin representative energy",
        )

        expected_representative_energy_ev = math.sqrt(
            self.lower_energy_ev * self.upper_energy_ev
        )

        if not values_match(
            self.representative_energy_ev,
            expected_representative_energy_ev,
        ):
            raise ValueError(
                "OpenMC spectrum-bin representative "
                "energy must equal the geometric midpoint."
            )

        require_nonnegative_value(
            self.photon_fluence_rate_per_cm2_s,
            "OpenMC spectrum-bin photon fluence rate",
        )

        require_nonnegative_value(
            self.photon_fluence_rate_standard_deviation_per_cm2_s,
            ("OpenMC spectrum-bin photon fluence-rate standard deviation"),
        )

        if self.relative_uncertainty is not None:
            require_nonnegative_value(
                self.relative_uncertainty,
                ("OpenMC spectrum-bin relative uncertainty"),
            )

            if self.photon_fluence_rate_per_cm2_s <= 0:
                raise ValueError(
                    "A zero-fluence spectrum bin cannot store a relative uncertainty."
                )

            expected_relative_uncertainty = (
                self.photon_fluence_rate_standard_deviation_per_cm2_s
                / self.photon_fluence_rate_per_cm2_s
            )

            if not values_match(
                self.relative_uncertainty,
                expected_relative_uncertainty,
            ):
                raise ValueError(
                    "OpenMC spectrum-bin relative uncertainty is inconsistent."
                )

        elif self.photon_fluence_rate_per_cm2_s > 0:
            raise ValueError(
                "A positive-fluence spectrum bin must store its relative uncertainty."
            )

        require_positive_value(
            self.response_coefficient_gy_cm2_per_photon,
            ("OpenMC spectrum-bin response coefficient"),
        )

        require_nonnegative_value(
            self.air_kerma_rate_contribution_gy_per_s,
            ("OpenMC spectrum-bin air-kerma-rate contribution"),
        )

        require_nonnegative_value(
            (self.air_kerma_rate_contribution_microgy_per_h),
            ("OpenMC spectrum-bin air-kerma-rate contribution in microGy/h"),
        )

        expected_contribution_gy_per_s = (
            self.photon_fluence_rate_per_cm2_s
            * self.response_coefficient_gy_cm2_per_photon
        )

        if not values_match(
            self.air_kerma_rate_contribution_gy_per_s,
            expected_contribution_gy_per_s,
        ):
            raise ValueError(
                "OpenMC spectrum-bin response must equal "
                "fluence rate times response coefficient."
            )

        expected_contribution_microgy_per_h = (
            self.air_kerma_rate_contribution_gy_per_s * 3.6e9
        )

        if not values_match(
            (self.air_kerma_rate_contribution_microgy_per_h),
            expected_contribution_microgy_per_h,
        ):
            raise ValueError(
                "OpenMC spectrum-bin microGy/h conversion is inconsistent."
            )


@dataclass(frozen=True)
class OpenMCBenchmarkPlotData:
    # Complete plotting-ready result for the official V1.13 benchmark.

    scenario_id: str
    settings_profile_name: str

    response_quantity: str

    evaluation_shell_inner_radius_cm: float
    evaluation_shell_outer_radius_cm: float

    physical_source_rate_per_s: float

    deterministic_uncollided_microgy_per_h: float
    deterministic_gp_microgy_per_h: float | None

    openmc_direct_microgy_per_h: float
    openmc_direct_standard_deviation_microgy_per_h: float

    openmc_folded_microgy_per_h: float

    openmc_relative_uncertainty: float

    relative_difference_from_uncollided: float
    relative_difference_from_gp: float | None

    observed_monte_carlo_buildup_ratio: float

    direct_vs_folded_relative_difference: float

    direct_vs_folded_tolerance: float
    direct_vs_folded_pass: bool

    required_relative_uncertainty: float
    required_uncertainty_pass: bool

    preferred_relative_uncertainty: float
    preferred_uncertainty_pass: bool

    spectrum_bins: tuple[
        OpenMCBenchmarkSpectrumBin,
        ...,
    ]

    def __post_init__(self) -> None:
        if self.scenario_id.strip() == "":
            raise ValueError("OpenMC benchmark plot scenario ID cannot be empty.")

        if self.settings_profile_name.strip() == "":
            raise ValueError("OpenMC benchmark plot settings profile cannot be empty.")

        if self.response_quantity.strip() == "":
            raise ValueError("OpenMC benchmark response quantity cannot be empty.")

        require_positive_value(
            self.evaluation_shell_inner_radius_cm,
            "Evaluation-shell inner radius",
        )

        require_positive_value(
            self.evaluation_shell_outer_radius_cm,
            "Evaluation-shell outer radius",
        )

        if (
            self.evaluation_shell_outer_radius_cm
            <= self.evaluation_shell_inner_radius_cm
        ):
            raise ValueError(
                "Evaluation-shell outer radius must exceed its inner radius."
            )

        require_positive_value(
            self.physical_source_rate_per_s,
            "Physical photon source rate",
        )

        require_positive_value(
            self.deterministic_uncollided_microgy_per_h,
            "Deterministic uncollided response",
        )

        if self.deterministic_gp_microgy_per_h is not None:
            require_positive_value(
                self.deterministic_gp_microgy_per_h,
                "Deterministic G-P-adjusted response",
            )

            if self.deterministic_gp_microgy_per_h < (
                self.deterministic_uncollided_microgy_per_h
            ):
                raise ValueError(
                    "Deterministic G-P-adjusted response "
                    "cannot be below the uncollided response."
                )

        require_positive_value(
            self.openmc_direct_microgy_per_h,
            "OpenMC direct response",
        )

        require_nonnegative_value(
            (self.openmc_direct_standard_deviation_microgy_per_h),
            "OpenMC direct-response standard deviation",
        )

        require_nonnegative_value(
            self.openmc_folded_microgy_per_h,
            "OpenMC folded response",
        )

        require_nonnegative_value(
            self.openmc_relative_uncertainty,
            "OpenMC relative uncertainty",
        )

        expected_relative_uncertainty = (
            self.openmc_direct_standard_deviation_microgy_per_h
            / self.openmc_direct_microgy_per_h
        )

        if not values_match(
            self.openmc_relative_uncertainty,
            expected_relative_uncertainty,
        ):
            raise ValueError("OpenMC benchmark relative uncertainty is inconsistent.")

        require_finite_value(
            self.relative_difference_from_uncollided,
            ("OpenMC relative difference from uncollided"),
        )

        expected_uncollided_difference = (
            self.openmc_direct_microgy_per_h
            - self.deterministic_uncollided_microgy_per_h
        ) / self.deterministic_uncollided_microgy_per_h

        if not values_match(
            self.relative_difference_from_uncollided,
            expected_uncollided_difference,
        ):
            raise ValueError(
                "OpenMC relative difference from the "
                "deterministic uncollided response is "
                "inconsistent."
            )

        if self.deterministic_gp_microgy_per_h is None:
            if self.relative_difference_from_gp is not None:
                raise ValueError(
                    "A G-P relative difference requires a deterministic G-P response."
                )

        else:
            if self.relative_difference_from_gp is None:
                raise ValueError(
                    "An available deterministic G-P "
                    "response requires a relative difference."
                )

            expected_gp_difference = (
                self.openmc_direct_microgy_per_h - self.deterministic_gp_microgy_per_h
            ) / self.deterministic_gp_microgy_per_h

            if not values_match(
                self.relative_difference_from_gp,
                expected_gp_difference,
            ):
                raise ValueError(
                    "OpenMC relative difference from the "
                    "deterministic G-P response is "
                    "inconsistent."
                )

        require_positive_value(
            self.observed_monte_carlo_buildup_ratio,
            "Observed Monte Carlo buildup ratio",
        )

        expected_buildup_ratio = (
            self.openmc_direct_microgy_per_h
            / self.deterministic_uncollided_microgy_per_h
        )

        if not values_match(
            self.observed_monte_carlo_buildup_ratio,
            expected_buildup_ratio,
        ):
            raise ValueError("Observed Monte Carlo buildup ratio is inconsistent.")

        require_finite_value(
            self.direct_vs_folded_relative_difference,
            "Direct-versus-folded relative difference",
        )

        expected_direct_vs_folded_difference = (
            self.openmc_folded_microgy_per_h - self.openmc_direct_microgy_per_h
        ) / self.openmc_direct_microgy_per_h

        if not values_match(
            self.direct_vs_folded_relative_difference,
            expected_direct_vs_folded_difference,
        ):
            raise ValueError(
                "Direct-versus-folded relative difference is inconsistent."
            )

        require_nonnegative_value(
            self.direct_vs_folded_tolerance,
            "Direct-versus-folded tolerance",
        )

        expected_folded_pass = (
            abs(self.direct_vs_folded_relative_difference)
            <= self.direct_vs_folded_tolerance
        )

        if self.direct_vs_folded_pass != expected_folded_pass:
            raise ValueError("Direct-versus-folded acceptance status is inconsistent.")

        require_nonnegative_value(
            self.required_relative_uncertainty,
            "Required uncertainty threshold",
        )

        expected_required_pass = (
            self.openmc_relative_uncertainty <= self.required_relative_uncertainty
        )

        if self.required_uncertainty_pass != expected_required_pass:
            raise ValueError("Required uncertainty acceptance status is inconsistent.")

        require_nonnegative_value(
            self.preferred_relative_uncertainty,
            "Preferred uncertainty threshold",
        )

        expected_preferred_pass = (
            self.openmc_relative_uncertainty <= self.preferred_relative_uncertainty
        )

        if self.preferred_uncertainty_pass != expected_preferred_pass:
            raise ValueError("Preferred uncertainty acceptance status is inconsistent.")

        if len(self.spectrum_bins) == 0:
            raise ValueError(
                "OpenMC benchmark plot data must contain at least one spectrum bin."
            )

        for expected_index, spectrum_bin in enumerate(
            self.spectrum_bins,
            start=1,
        ):
            if spectrum_bin.bin_index != expected_index:
                raise ValueError(
                    "OpenMC spectrum-bin indices must be consecutive and begin at one."
                )

        for current_bin, following_bin in zip(
            self.spectrum_bins[:-1],
            self.spectrum_bins[1:],
            strict=True,
        ):
            if not values_match(
                current_bin.upper_energy_ev,
                following_bin.lower_energy_ev,
            ):
                raise ValueError("OpenMC spectrum bins must be ordered and contiguous.")

        folded_spectrum_total_microgy_per_h = sum(
            spectrum_bin.air_kerma_rate_contribution_microgy_per_h
            for spectrum_bin in self.spectrum_bins
        )

        if not values_match(
            folded_spectrum_total_microgy_per_h,
            self.openmc_folded_microgy_per_h,
        ):
            raise ValueError(
                "OpenMC folded response must equal the "
                "sum of spectrum-bin contributions."
            )

    @property
    def total_photon_fluence_rate_per_cm2_s(
        self,
    ) -> float:
        return sum(
            spectrum_bin.photon_fluence_rate_per_cm2_s
            for spectrum_bin in self.spectrum_bins
        )

    @property
    def positive_spectrum_bin_count(
        self,
    ) -> int:
        return sum(
            1
            for spectrum_bin in self.spectrum_bins
            if (spectrum_bin.photon_fluence_rate_per_cm2_s > 0)
        )


def load_json_object(
    file_path: str | Path,
    description: str,
) -> dict[str, Any]:
    input_path = Path(file_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"{description} does not exist: {input_path}")

    try:
        with input_path.open(
            mode="r",
            encoding="utf-8",
        ) as input_file:
            value = json.load(input_file)

    except json.JSONDecodeError as error:
        raise ValueError(f"{description} contains invalid JSON: {error}") from error

    if not isinstance(value, dict):
        raise ValueError(f"{description} root must be a JSON object.")

    return value


def require_matching_string(
    first_value: Any,
    second_value: Any,
    description: str,
) -> str:
    if not isinstance(first_value, str) or not isinstance(second_value, str):
        raise ValueError(f"{description} values must be strings.")

    if first_value != second_value:
        raise ValueError(
            f"{description} values do not match: {first_value!r} and {second_value!r}."
        )

    if first_value.strip() == "":
        raise ValueError(f"{description} cannot be empty.")

    return first_value


def parse_optional_float(
    value: Any,
    description: str,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(f"{description} must be numerical or null.")

    parsed_value = float(value)

    require_finite_value(
        parsed_value,
        description,
    )

    return parsed_value


def parse_required_float(
    value: Any,
    description: str,
) -> float:
    parsed_value = parse_optional_float(
        value,
        description,
    )

    if parsed_value is None:
        raise ValueError(f"{description} cannot be null.")

    return parsed_value


def parse_required_bool(
    value: Any,
    description: str,
) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{description} must be Boolean.")

    return value


def load_spectrum_bins(
    spectrum_csv_path: str | Path,
) -> tuple[
    OpenMCBenchmarkSpectrumBin,
    ...,
]:
    input_path = Path(spectrum_csv_path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"OpenMC photon-spectrum CSV does not exist: {input_path}"
        )

    spectrum_bins: list[OpenMCBenchmarkSpectrumBin] = []

    with input_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        required_columns = {
            "bin_index",
            "lower_energy_ev",
            "upper_energy_ev",
            "representative_energy_ev",
            "physical_fluence_rate_mean_per_cm2_s",
            ("physical_fluence_rate_standard_deviation_per_cm2_s"),
            "relative_uncertainty",
            ("response_coefficient_gy_cm2_per_photon"),
            ("air_kerma_rate_contribution_gy_per_s"),
            ("air_kerma_rate_contribution_microgy_per_h"),
        }

        actual_columns = set(reader.fieldnames or [])

        missing_columns = required_columns - actual_columns

        if missing_columns:
            raise ValueError(
                "OpenMC photon-spectrum CSV is missing "
                "required columns: " + ", ".join(sorted(missing_columns))
            )

        for row in reader:
            relative_uncertainty_text = row["relative_uncertainty"].strip()

            relative_uncertainty = None

            if relative_uncertainty_text != "":
                relative_uncertainty = float(relative_uncertainty_text)

            spectrum_bins.append(
                OpenMCBenchmarkSpectrumBin(
                    bin_index=int(row["bin_index"]),
                    lower_energy_ev=float(row["lower_energy_ev"]),
                    upper_energy_ev=float(row["upper_energy_ev"]),
                    representative_energy_ev=float(row["representative_energy_ev"]),
                    photon_fluence_rate_per_cm2_s=float(
                        row[("physical_fluence_rate_mean_per_cm2_s")]
                    ),
                    photon_fluence_rate_standard_deviation_per_cm2_s=float(
                        row[("physical_fluence_rate_standard_deviation_per_cm2_s")]
                    ),
                    relative_uncertainty=(relative_uncertainty),
                    response_coefficient_gy_cm2_per_photon=float(
                        row[("response_coefficient_gy_cm2_per_photon")]
                    ),
                    air_kerma_rate_contribution_gy_per_s=float(
                        row[("air_kerma_rate_contribution_gy_per_s")]
                    ),
                    air_kerma_rate_contribution_microgy_per_h=float(
                        row[("air_kerma_rate_contribution_microgy_per_h")]
                    ),
                )
            )

    return tuple(spectrum_bins)


def create_openmc_benchmark_plot_data(
    response_json_path: str | Path,
    comparison_json_path: str | Path,
    spectrum_csv_path: str | Path,
) -> OpenMCBenchmarkPlotData:
    response_data = load_json_object(
        response_json_path,
        "Processed OpenMC response JSON",
    )

    comparison_data = load_json_object(
        comparison_json_path,
        "Deterministic/OpenMC comparison JSON",
    )

    response_schema_version = response_data.get("schema_version")

    comparison_schema_version = comparison_data.get("schema_version")

    if response_schema_version != EXPECTED_RESULT_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported processed OpenMC response "
            "schema version: "
            f"{response_schema_version}"
        )

    if comparison_schema_version != EXPECTED_RESULT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported comparison schema version: {comparison_schema_version}"
        )

    if response_data.get("record_type") != EXPECTED_RESPONSE_RECORD_TYPE:
        raise ValueError("Unexpected processed OpenMC response record type.")

    if comparison_data.get("record_type") != EXPECTED_COMPARISON_RECORD_TYPE:
        raise ValueError("Unexpected deterministic/OpenMC comparison record type.")

    scenario_id = require_matching_string(
        response_data.get("scenario_id"),
        comparison_data.get("scenario_id"),
        "Scenario ID",
    )

    settings_profile_name = require_matching_string(
        response_data.get("settings_profile_name"),
        comparison_data.get("settings_profile_name"),
        "Settings profile name",
    )

    response_quantity = require_matching_string(
        response_data.get("response_quantity"),
        comparison_data.get("response_quantity"),
        "Response quantity",
    )

    response_shell = response_data["evaluation_shell"]

    comparison_shell = comparison_data["evaluation_shell"]

    response_inner_radius = parse_required_float(
        response_shell["inner_radius_cm"],
        ("Response evaluation-shell inner radius"),
    )

    comparison_inner_radius = parse_required_float(
        comparison_shell["inner_radius_cm"],
        ("Comparison evaluation-shell inner radius"),
    )

    if not values_match(
        response_inner_radius,
        comparison_inner_radius,
    ):
        raise ValueError("Response and comparison inner shell radii do not match.")

    response_outer_radius = parse_required_float(
        response_shell["outer_radius_cm"],
        ("Response evaluation-shell outer radius"),
    )

    comparison_outer_radius = parse_required_float(
        comparison_shell["outer_radius_cm"],
        ("Comparison evaluation-shell outer radius"),
    )

    if not values_match(
        response_outer_radius,
        comparison_outer_radius,
    ):
        raise ValueError("Response and comparison outer shell radii do not match.")

    response_direct = response_data["direct_response"]

    comparison_openmc = comparison_data["openmc"]

    direct_response_microgy_per_h = parse_required_float(
        response_direct["rate_microgy_per_h"],
        "OpenMC direct response",
    )

    comparison_direct_response = parse_required_float(
        comparison_openmc["direct_response_rate_microgy_per_h"],
        "Comparison OpenMC direct response",
    )

    if not values_match(
        direct_response_microgy_per_h,
        comparison_direct_response,
    ):
        raise ValueError("Response and comparison direct OpenMC values do not match.")

    folded_response_microgy_per_h = parse_required_float(
        response_data["spectrum_summary"][
            ("spectrum_folded_response_rate_microgy_per_h")
        ],
        "OpenMC folded response",
    )

    comparison_folded_response = parse_required_float(
        comparison_openmc[("spectrum_folded_response_rate_microgy_per_h")],
        "Comparison OpenMC folded response",
    )

    if not values_match(
        folded_response_microgy_per_h,
        comparison_folded_response,
    ):
        raise ValueError("Response and comparison folded OpenMC values do not match.")

    spectrum_bins = load_spectrum_bins(spectrum_csv_path)

    expected_energy_bin_count = int(
        response_data["spectrum_summary"]["energy_bin_count"]
    )

    if len(spectrum_bins) != expected_energy_bin_count:
        raise ValueError(
            "Photon-spectrum CSV bin count does not match the OpenMC response JSON."
        )

    deterministic_data = comparison_data["deterministic"]

    comparison_values = comparison_data["comparison"]

    acceptance_checks = comparison_data["acceptance_checks"]

    return OpenMCBenchmarkPlotData(
        scenario_id=scenario_id,
        settings_profile_name=(settings_profile_name),
        response_quantity=response_quantity,
        evaluation_shell_inner_radius_cm=(response_inner_radius),
        evaluation_shell_outer_radius_cm=(response_outer_radius),
        physical_source_rate_per_s=(
            parse_required_float(
                response_data["normalization"]["physical_source_rate_per_s"],
                "Physical photon source rate",
            )
        ),
        deterministic_uncollided_microgy_per_h=(
            parse_required_float(
                deterministic_data[("uncollided_response_rate_microgy_per_h")],
                "Deterministic uncollided response",
            )
        ),
        deterministic_gp_microgy_per_h=(
            parse_optional_float(
                deterministic_data[("gp_adjusted_response_rate_microgy_per_h")],
                "Deterministic G-P response",
            )
        ),
        openmc_direct_microgy_per_h=(direct_response_microgy_per_h),
        openmc_direct_standard_deviation_microgy_per_h=(
            parse_required_float(
                response_direct[("standard_deviation_microgy_per_h")],
                ("OpenMC direct-response standard deviation"),
            )
        ),
        openmc_folded_microgy_per_h=(folded_response_microgy_per_h),
        openmc_relative_uncertainty=(
            parse_required_float(
                response_direct["relative_uncertainty"],
                "OpenMC relative uncertainty",
            )
        ),
        relative_difference_from_uncollided=(
            parse_required_float(
                comparison_values[("relative_difference_from_uncollided")],
                ("Relative difference from uncollided"),
            )
        ),
        relative_difference_from_gp=(
            parse_optional_float(
                comparison_values["relative_difference_from_gp"],
                "Relative difference from G-P",
            )
        ),
        observed_monte_carlo_buildup_ratio=(
            parse_required_float(
                comparison_values[("observed_monte_carlo_buildup_ratio")],
                ("Observed Monte Carlo buildup ratio"),
            )
        ),
        direct_vs_folded_relative_difference=(
            parse_required_float(
                comparison_values[("direct_vs_folded_relative_difference")],
                ("Direct-versus-folded relative difference"),
            )
        ),
        direct_vs_folded_tolerance=(
            parse_required_float(
                acceptance_checks["direct_vs_folded_tolerance"],
                ("Direct-versus-folded tolerance"),
            )
        ),
        direct_vs_folded_pass=(
            parse_required_bool(
                acceptance_checks["direct_vs_folded_pass"],
                ("Direct-versus-folded acceptance status"),
            )
        ),
        required_relative_uncertainty=(
            parse_required_float(
                acceptance_checks["required_relative_uncertainty"],
                ("Required uncertainty threshold"),
            )
        ),
        required_uncertainty_pass=(
            parse_required_bool(
                acceptance_checks["required_uncertainty_pass"],
                ("Required uncertainty acceptance status"),
            )
        ),
        preferred_relative_uncertainty=(
            parse_required_float(
                acceptance_checks["preferred_relative_uncertainty"],
                ("Preferred uncertainty threshold"),
            )
        ),
        preferred_uncertainty_pass=(
            parse_required_bool(
                acceptance_checks["preferred_uncertainty_pass"],
                ("Preferred uncertainty acceptance status"),
            )
        ),
        spectrum_bins=spectrum_bins,
    )
