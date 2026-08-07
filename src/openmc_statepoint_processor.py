# Reusable OpenMC benchmark statepoint processing and physical normalization.
#
# Introduced for the V1.13 matched benchmark and reused by later benchmark
# studies.
# 
# This module converts raw OpenMC benchmark tallies into physical photon
# fluence rates and dry-air collision-air-kerma rates.
#
# Spectrum normalization:
#
#   raw track-length flux
#       [photon cm/source]
#
#   divided by evaluation-shell volume
#       [cm^3]
#
#   =
#
#   photon fluence per source
#       [photon/(cm^2 source)]
#
#   multiplied by physical photon source rate
#       [source/s]
#
#   =
#
#   physical photon fluence rate
#       [photon/(cm^2 s)]
#
# Direct-response normalization:
#
#   raw response tally
#       [Gy cm^3/source]
#
#   divided by evaluation-shell volume
#       [cm^3]
#
#   =
#
#   response per source
#       [Gy/source]
#
#   multiplied by physical photon source rate
#       [source/s]
#
#   =
#
#   physical collision-air-kerma rate
#       [Gy/s]
#
# OpenMC is imported dynamically only when a statepoint is processed.


from __future__ import annotations


import math
from pathlib import Path
from typing import Any


from benchmark_models import (
    SphericalEvaluationShell,
)
from fixed_shield_response import (
    create_fixed_shield_runtime_source,
    get_runtime_source_lines,
)
from openmc_model_builder import (
    load_openmc_module,
)
from openmc_models import (
    OpenMCEnergyBinResult,
    OpenMCResponseResult,
    OpenMCSettings,
)
from openmc_response import (
    calculate_relative_uncertainty,
    calculate_spherical_shell_volume_cm3,
    normalize_openmc_track_length_flux_tally,
    scale_per_source_estimate_to_physical_rate,
)
from openmc_response_coefficients import (
    OpenMCAirKermaResponseFunction,
    calculate_energy_bin_response_coefficient_gy_cm2_per_photon,
    create_openmc_dry_air_response_function,
    fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s,
    validate_response_function_covers_openmc_settings,
)
from openmc_tally_builder import (
    DIRECT_RESPONSE_TALLY_ID,
    DIRECT_RESPONSE_TALLY_NAME,
    SPECTRUM_TALLY_ID,
    SPECTRUM_TALLY_NAME,
)
from scenario_models import (
    ShieldingScenario,
)


def calculate_scenario_physical_source_rate_per_s(
    scenario: ShieldingScenario,
) -> float:
    # Calculate the total physical photon emission rate represented by one
    # fixed-shield scenario.
    #
    # This is independent of OpenMC's normalized one-particle-per-history
    # source distribution.

    if (
        scenario.calculation_mode
        != "fixed_shield_response"
    ):
        raise ValueError(
            "Physical source-rate calculation requires "
            "fixed_shield_response mode."
        )

    runtime_source = (
        create_fixed_shield_runtime_source(
            scenario
        )
    )

    (
        _source_name,
        _activity_bq,
        source_lines,
    ) = get_runtime_source_lines(
        runtime_source
    )

    physical_source_rate_per_s = sum(
        photon_rate_per_s
        for (
            _photon_line,
            photon_rate_per_s,
        ) in source_lines
    )

    if physical_source_rate_per_s <= 0:
        raise ValueError(
            "OpenMC statepoint processing requires a "
            "positive physical photon source rate."
        )

    return physical_source_rate_per_s


def require_finite_nonnegative_value(
    value: float,
    description: str,
) -> None:
    # Validate one raw or normalized tally quantity.

    if not math.isfinite(
        value
    ):
        raise ValueError(
            f"{description} must be finite."
        )

    if value < 0:
        raise ValueError(
            f"{description} cannot be negative."
        )


def extract_single_score_tally_vectors(
    tally: Any,
    expected_value_count: int,
    description: str,
) -> tuple[
    list[float],
    list[float],
]:
    # Extract flattened mean and standard-deviation vectors from a tally that
    # contains one nuclide and one score.
    #
    # The spectrum tally has one cell bin, one particle bin, and many energy
    # bins. The direct response has one bin in every filter.

    mean_array = tally.get_reshaped_data(
        value="mean"
    )

    standard_deviation_array = (
        tally.get_reshaped_data(
            value="std_dev"
        )
    )

    flattened_means = (
        mean_array.reshape(-1)
    )

    flattened_standard_deviations = (
        standard_deviation_array
        .reshape(-1)
    )

    if (
        flattened_means.size
        != expected_value_count
    ):
        raise ValueError(
            f"{description} has an unexpected value count: "
            f"expected {expected_value_count}, "
            f"found {flattened_means.size}."
        )

    if (
        flattened_standard_deviations.size
        != expected_value_count
    ):
        raise ValueError(
            f"{description} has an unexpected "
            "uncertainty count."
        )

    means: list[float] = []
    standard_deviations: list[
        float
    ] = []

    for index in range(
        expected_value_count
    ):
        mean = float(
            flattened_means[index]
        )

        standard_deviation = float(
            flattened_standard_deviations[
                index
            ]
        )

        require_finite_nonnegative_value(
            mean,
            f"{description} mean",
        )

        require_finite_nonnegative_value(
            standard_deviation,
            f"{description} standard deviation",
        )

        means.append(
            mean
        )

        standard_deviations.append(
            standard_deviation
        )

    return (
        means,
        standard_deviations,
    )


def validate_statepoint_metadata(
    statepoint: Any,
    settings_profile: OpenMCSettings,
    expected_batch: int | None = None,
) -> None:
    # Confirm that the statepoint was created by the expected photon settings
    # profile before interpreting its numerical results.
    #
    # expected_batch defaults to the final configured batch. Supplying an
    # earlier configured statepoint batch allows cumulative convergence
    # analysis without weakening the final-state validation.

    if expected_batch is None:
        expected_batch = (
            settings_profile.batches
        )

    if (
        isinstance(expected_batch, bool)
        or not isinstance(
            expected_batch,
            int,
        )
        or expected_batch <= 0
    ):
        raise ValueError(
            "Expected OpenMC statepoint batch must "
            "be a positive integer."
        )

    if (
        expected_batch
        > settings_profile.batches
    ):
        raise ValueError(
            "Expected OpenMC statepoint batch cannot "
            "exceed the configured batch count."
        )

    if (
        expected_batch
        not in settings_profile
        .statepoint_batches
    ):
        raise ValueError(
            "Expected OpenMC statepoint batch must be "
            "listed in the settings profile."
        )

    if not statepoint.tallies_present:
        raise ValueError(
            "OpenMC statepoint contains no "
            "user-defined tally results."
        )

    if not statepoint.photon_transport:
        raise ValueError(
            "OpenMC statepoint does not report "
            "photon transport as active."
        )

    if (
        statepoint.current_batch
        != expected_batch
    ):
        raise ValueError(
            "OpenMC statepoint batch does not match "
            "the expected checkpoint batch."
        )

    if (
        statepoint.n_particles
        != settings_profile
        .particles_per_batch
    ):
        raise ValueError(
            "OpenMC statepoint particles per batch do "
            "not match the settings profile."
        )


def validate_statepoint_tally(
    tally: Any,
    expected_id: int,
    expected_name: str,
    description: str,
) -> None:
    # Confirm stable tally identity and scoring conventions.

    if tally.id != expected_id:
        raise ValueError(
            f"{description} has an unexpected tally ID."
        )

    if tally.name != expected_name:
        raise ValueError(
            f"{description} has an unexpected tally name."
        )

    if tally.scores != [
        "flux",
    ]:
        raise ValueError(
            f"{description} must contain only the flux score."
        )

    if tally.estimator != "tracklength":
        raise ValueError(
            f"{description} must use the track-length estimator."
        )


def create_processed_energy_bin_results(
    raw_spectrum_means_cm_per_source: list[float],
    raw_spectrum_standard_deviations_cm_per_source: list[float],
    settings_profile: OpenMCSettings,
    shell_volume_cm3: float,
    physical_source_rate_per_s: float,
    response_function: OpenMCAirKermaResponseFunction,
) -> list[
    OpenMCEnergyBinResult
]:
    # Normalize every spectrum bin and fold it with the dry-air response
    # coefficient evaluated at the bin's geometric representative energy.

    expected_bin_count = (
        len(
            settings_profile
            .energy_bin_boundaries_ev
        )
        - 1
    )

    if (
        len(
            raw_spectrum_means_cm_per_source
        )
        != expected_bin_count
    ):
        raise ValueError(
            "Raw OpenMC spectrum mean count does not "
            "match the configured energy-bin count."
        )

    if (
        len(
            raw_spectrum_standard_deviations_cm_per_source
        )
        != expected_bin_count
    ):
        raise ValueError(
            "Raw OpenMC spectrum uncertainty count does "
            "not match the configured energy-bin count."
        )

    energy_bin_results: list[
        OpenMCEnergyBinResult
    ] = []

    for energy_bin_index in range(
        expected_bin_count
    ):
        lower_energy_ev = (
            settings_profile
            .energy_bin_boundaries_ev[
                energy_bin_index
            ]
        )

        upper_energy_ev = (
            settings_profile
            .energy_bin_boundaries_ev[
                energy_bin_index + 1
            ]
        )

        raw_mean = (
            raw_spectrum_means_cm_per_source[
                energy_bin_index
            ]
        )

        raw_standard_deviation = (
            raw_spectrum_standard_deviations_cm_per_source[
                energy_bin_index
            ]
        )

        (
            volume_normalized_mean,
            volume_normalized_standard_deviation,
        ) = normalize_openmc_track_length_flux_tally(
            raw_mean_cm_per_source=(
                raw_mean
            ),
            raw_standard_deviation_cm_per_source=(
                raw_standard_deviation
            ),
            tally_volume_cm3=(
                shell_volume_cm3
            ),
        )

        (
            physical_fluence_rate_mean,
            physical_fluence_rate_standard_deviation,
        ) = scale_per_source_estimate_to_physical_rate(
            mean_per_source=(
                volume_normalized_mean
            ),
            standard_deviation_per_source=(
                volume_normalized_standard_deviation
            ),
            physical_source_rate_per_s=(
                physical_source_rate_per_s
            ),
        )

        response_coefficient = (
            calculate_energy_bin_response_coefficient_gy_cm2_per_photon(
                response_function=(
                    response_function
                ),
                lower_energy_ev=(
                    lower_energy_ev
                ),
                upper_energy_ev=(
                    upper_energy_ev
                ),
            )
        )

        air_kerma_rate_contribution = (
            fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s(
                photon_fluence_rate_per_cm2_s=(
                    physical_fluence_rate_mean
                ),
                response_coefficient_gy_cm2_per_photon=(
                    response_coefficient
                ),
            )
        )

        energy_bin_results.append(
            OpenMCEnergyBinResult(
                lower_energy_ev=(
                    lower_energy_ev
                ),
                upper_energy_ev=(
                    upper_energy_ev
                ),
                raw_track_length_flux_mean_cm_per_source=(
                    raw_mean
                ),
                raw_track_length_flux_standard_deviation_cm_per_source=(
                    raw_standard_deviation
                ),
                volume_normalized_fluence_mean_per_cm2_per_source=(
                    volume_normalized_mean
                ),
                volume_normalized_fluence_standard_deviation_per_cm2_per_source=(
                    volume_normalized_standard_deviation
                ),
                physical_fluence_rate_mean_per_cm2_s=(
                    physical_fluence_rate_mean
                ),
                physical_fluence_rate_standard_deviation_per_cm2_s=(
                    physical_fluence_rate_standard_deviation
                ),
                response_coefficient_gy_cm2_per_photon=(
                    response_coefficient
                ),
                air_kerma_rate_contribution_gy_per_s=(
                    air_kerma_rate_contribution
                ),
            )
        )

    return energy_bin_results


def process_openmc_benchmark_statepoint(
    statepoint_path: str | Path,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    evaluation_shell_thickness_cm: float = 1.0,
    response_function: (
        OpenMCAirKermaResponseFunction
        | None
    ) = None,
    expected_batch: int | None = None,
) -> OpenMCResponseResult:
    # Process one completed benchmark statepoint into physical response units.
    if (
        scenario.calculation_mode
        != "fixed_shield_response"
    ):
        raise ValueError(
            "OpenMC statepoint processing requires "
            "fixed_shield_response mode."
        )

    input_path = Path(
        statepoint_path
    )

    if not input_path.is_file():
        raise FileNotFoundError(
            "OpenMC statepoint file does not exist: "
            f"{input_path}"
        )

    evaluation_shell = (
        SphericalEvaluationShell(
            center_radius_cm=(
                scenario
                .geometry
                .evaluation_radius_cm
            ),
            thickness_cm=(
                evaluation_shell_thickness_cm
            ),
        )
    )

    if (
        evaluation_shell.inner_radius_cm
        <= (
            scenario
            .geometry
            .outer_shield_radius_cm
        )
    ):
        raise ValueError(
            "OpenMC evaluation shell must be entirely "
            "beyond the outer shield radius."
        )

    if (
        settings_profile
        .outer_boundary_radius_cm
        <= evaluation_shell.outer_radius_cm
    ):
        raise ValueError(
            "OpenMC outer boundary must be beyond "
            "the evaluation shell."
        )

    shell_volume_cm3 = (
        calculate_spherical_shell_volume_cm3(
            inner_radius_cm=(
                evaluation_shell
                .inner_radius_cm
            ),
            outer_radius_cm=(
                evaluation_shell
                .outer_radius_cm
            ),
        )
    )

    physical_source_rate_per_s = (
        calculate_scenario_physical_source_rate_per_s(
            scenario
        )
    )

    if response_function is None:
        response_function = (
            create_openmc_dry_air_response_function()
        )

    validate_response_function_covers_openmc_settings(
        response_function=(
            response_function
        ),
        settings=(
            settings_profile
        ),
    )

    openmc_module = (
        load_openmc_module()
    )

    statepoint = openmc_module.StatePoint(
        input_path,
        autolink=False,
    )

    try:
        validate_statepoint_metadata(
            statepoint=statepoint,
            settings_profile=(
                settings_profile
            ),
            expected_batch=(
                expected_batch
            ),
        )

        spectrum_tally = (
            statepoint.get_tally(
                id=SPECTRUM_TALLY_ID
            )
        )

        direct_response_tally = (
            statepoint.get_tally(
                id=(
                    DIRECT_RESPONSE_TALLY_ID
                )
            )
        )

        validate_statepoint_tally(
            tally=spectrum_tally,
            expected_id=(
                SPECTRUM_TALLY_ID
            ),
            expected_name=(
                SPECTRUM_TALLY_NAME
            ),
            description=(
                "OpenMC spectrum tally"
            ),
        )

        validate_statepoint_tally(
            tally=direct_response_tally,
            expected_id=(
                DIRECT_RESPONSE_TALLY_ID
            ),
            expected_name=(
                DIRECT_RESPONSE_TALLY_NAME
            ),
            description=(
                "OpenMC direct-response tally"
            ),
        )

        expected_energy_bin_count = (
            len(
                settings_profile
                .energy_bin_boundaries_ev
            )
            - 1
        )

        (
            raw_spectrum_means,
            raw_spectrum_standard_deviations,
        ) = extract_single_score_tally_vectors(
            tally=spectrum_tally,
            expected_value_count=(
                expected_energy_bin_count
            ),
            description=(
                "OpenMC spectrum tally"
            ),
        )

        (
            direct_response_means,
            direct_response_standard_deviations,
        ) = extract_single_score_tally_vectors(
            tally=direct_response_tally,
            expected_value_count=1,
            description=(
                "OpenMC direct-response tally"
            ),
        )

        raw_direct_response_mean = (
            direct_response_means[0]
        )

        raw_direct_response_standard_deviation = (
            direct_response_standard_deviations[0]
        )

        if raw_direct_response_mean <= 0:
            raise ValueError(
                "OpenMC direct-response tally must "
                "have a positive mean."
            )

        energy_bin_results = (
            create_processed_energy_bin_results(
                raw_spectrum_means_cm_per_source=(
                    raw_spectrum_means
                ),
                raw_spectrum_standard_deviations_cm_per_source=(
                    raw_spectrum_standard_deviations
                ),
                settings_profile=(
                    settings_profile
                ),
                shell_volume_cm3=(
                    shell_volume_cm3
                ),
                physical_source_rate_per_s=(
                    physical_source_rate_per_s
                ),
                response_function=(
                    response_function
                ),
            )
        )

        direct_response_mean_gy_per_source = (
            raw_direct_response_mean
            / shell_volume_cm3
        )

        direct_response_standard_deviation_gy_per_source = (
            raw_direct_response_standard_deviation
            / shell_volume_cm3
        )

        (
            direct_response_rate_gy_per_s,
            direct_response_rate_standard_deviation_gy_per_s,
        ) = scale_per_source_estimate_to_physical_rate(
            mean_per_source=(
                direct_response_mean_gy_per_source
            ),
            standard_deviation_per_source=(
                direct_response_standard_deviation_gy_per_source
            ),
            physical_source_rate_per_s=(
                physical_source_rate_per_s
            ),
        )

        relative_uncertainty = (
            calculate_relative_uncertainty(
                mean=(
                    direct_response_rate_gy_per_s
                ),
                standard_deviation=(
                    direct_response_rate_standard_deviation_gy_per_s
                ),
            )
        )

        spectrum_folded_response_rate_gy_per_s = sum(
            energy_bin_result
            .air_kerma_rate_contribution_gy_per_s
            for energy_bin_result
            in energy_bin_results
        )

        return OpenMCResponseResult(
            scenario_id=(
                scenario.scenario_id
            ),
            settings_profile_name=(
                settings_profile.profile_name
            ),
            evaluation_shell=(
                evaluation_shell
            ),
            shell_volume_cm3=(
                shell_volume_cm3
            ),
            physical_source_rate_per_s=(
                physical_source_rate_per_s
            ),
            energy_bin_results=(
                energy_bin_results
            ),
            raw_direct_response_mean_gy_cm3_per_source=(
                raw_direct_response_mean
            ),
            raw_direct_response_standard_deviation_gy_cm3_per_source=(
                raw_direct_response_standard_deviation
            ),
            direct_response_mean_gy_per_source=(
                direct_response_mean_gy_per_source
            ),
            direct_response_standard_deviation_gy_per_source=(
                direct_response_standard_deviation_gy_per_source
            ),
            direct_response_rate_gy_per_s=(
                direct_response_rate_gy_per_s
            ),
            direct_response_rate_standard_deviation_gy_per_s=(
                direct_response_rate_standard_deviation_gy_per_s
            ),
            relative_uncertainty=(
                relative_uncertainty
            ),
            spectrum_folded_response_rate_gy_per_s=(
                spectrum_folded_response_rate_gy_per_s
            ),
        )

    finally:
        statepoint.close()


def process_openmc_v113_statepoint(
    statepoint_path: str | Path,
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    evaluation_shell_thickness_cm: float = 1.0,
    response_function: (
        OpenMCAirKermaResponseFunction
        | None
    ) = None,
    expected_batch: int | None = None,
) -> OpenMCResponseResult:
    # Backward-compatible V1.13 entry point.
    #
    # New benchmark-study code should call
    # process_openmc_benchmark_statepoint() directly.

    return process_openmc_benchmark_statepoint(
        statepoint_path=(
            statepoint_path
        ),
        scenario=scenario,
        settings_profile=(
            settings_profile
        ),
        evaluation_shell_thickness_cm=(
            evaluation_shell_thickness_cm
        ),
        response_function=(
            response_function
        ),
        expected_batch=(
            expected_batch
        ),
    )