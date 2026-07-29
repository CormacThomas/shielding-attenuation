# OpenMC-independent response and normalization mathematics.
#
# This module contains pure, deterministic calculations shared by the
# deterministic-versus-OpenMC benchmark pipeline. It intentionally does not
# import OpenMC so the normal project environment and validation suite remain
# independent of the Monte Carlo installation.
#
# V1.13 responsibilities:
#   - spherical evaluation-shell volume
#   - shell-averaged point-source fluence
#   - OpenMC track-length tally volume normalization
#   - physical source-rate scaling
#   - statistical uncertainty and comparison metrics


import math
from benchmark_models import (
    DeterministicShellAverageResult,
    DeterministicShellPhotonLineResult,
    SphericalEvaluationShell,
)
from fixed_shield_models import (
    FixedShieldDeterministicResult,
)


def calculate_spherical_shell_volume_cm3(
    inner_radius_cm: float,
    outer_radius_cm: float,
) -> float:
    # Calculate the volume of a spherical shell:
    #
    #   V = (4 pi / 3)(r_outer^3 - r_inner^3)
    #
    # Radii are measured from the same center and supplied in centimeters.
    # The returned volume is in cubic centimeters.

    if inner_radius_cm < 0:
        raise ValueError(
            "Spherical-shell inner radius cannot be negative."
        )

    if outer_radius_cm <= inner_radius_cm:
        raise ValueError(
            "Spherical-shell outer radius must be greater "
            "than the inner radius."
        )

    return (
        4.0
        * math.pi
        / 3.0
        * (
            outer_radius_cm ** 3
            - inner_radius_cm ** 3
        )
    )


def calculate_shell_average_geometric_factor_per_cm2(
    inner_radius_cm: float,
    outer_radius_cm: float,
) -> float:
    # Calculate the volume average of the isotropic point-source geometric
    # factor 1 / (4 pi r^2) throughout a concentric spherical shell.
    #
    # The volume average is:
    #
    #   [integral from r1 to r2 of
    #       (1 / 4 pi r^2)(4 pi r^2 dr)] / V_shell
    #
    # which simplifies to:
    #
    #   (r2 - r1) / V_shell
    #
    # The returned unit is inverse square centimeters.

    shell_volume_cm3 = (
        calculate_spherical_shell_volume_cm3(
            inner_radius_cm=inner_radius_cm,
            outer_radius_cm=outer_radius_cm,
        )
    )

    return (
        outer_radius_cm
        - inner_radius_cm
    ) / shell_volume_cm3


def calculate_deterministic_shell_averaged_fluence_rate(
    photon_emission_rate_per_s: float,
    transmission: float,
    inner_radius_cm: float,
    outer_radius_cm: float,
) -> float:
    # Calculate the narrow-beam photon fluence rate averaged throughout a
    # concentric spherical evaluation shell.
    #
    # For photon emission rate S and shield transmission T:
    #
    #   average fluence rate
    #       = S T (r2 - r1) / V_shell
    #
    # The returned unit is photons/(cm^2 s).

    if photon_emission_rate_per_s < 0:
        raise ValueError(
            "Photon emission rate cannot be negative."
        )

    if transmission < 0 or transmission > 1:
        raise ValueError(
            "Transmission must be between zero and one."
        )

    geometric_factor_per_cm2 = (
        calculate_shell_average_geometric_factor_per_cm2(
            inner_radius_cm=inner_radius_cm,
            outer_radius_cm=outer_radius_cm,
        )
    )

    return (
        photon_emission_rate_per_s
        * transmission
        * geometric_factor_per_cm2
    )


def calculate_photon_line_emission_rate_per_s(
    activity_bq: float,
    emission_intensity: float,
) -> float:
    # Convert isotope activity and one photon-line emission intensity into a
    # physical photon emission rate.
    #
    #   photons/s = decays/s x photons/decay

    if activity_bq < 0:
        raise ValueError(
            "Source activity cannot be negative."
        )

    if emission_intensity < 0:
        raise ValueError(
            "Photon emission intensity cannot be negative."
        )

    return activity_bq * emission_intensity


def normalize_openmc_track_length_flux_tally(
    raw_mean_cm_per_source: float,
    raw_standard_deviation_cm_per_source: float,
    tally_volume_cm3: float,
) -> tuple[float, float]:
    # Divide an OpenMC cell flux tally by the tally-region volume.
    #
    # OpenMC track-length cell flux tally:
    #   cm per source particle
    #
    # After division by volume:
    #   1/cm^2 per source particle
    #
    # The same deterministic scale factor must be applied to the mean and
    # standard deviation.

    if raw_mean_cm_per_source < 0:
        raise ValueError(
            "Raw OpenMC tally mean cannot be negative."
        )

    if raw_standard_deviation_cm_per_source < 0:
        raise ValueError(
            "Raw OpenMC tally standard deviation cannot be negative."
        )

    if tally_volume_cm3 <= 0:
        raise ValueError(
            "OpenMC tally volume must be greater than zero."
        )

    return (
        raw_mean_cm_per_source / tally_volume_cm3,
        (
            raw_standard_deviation_cm_per_source
            / tally_volume_cm3
        ),
    )


def scale_per_source_estimate_to_physical_rate(
    mean_per_source: float,
    standard_deviation_per_source: float,
    physical_source_rate_per_s: float,
) -> tuple[float, float]:
    # Scale one OpenMC estimate from a per-source-particle basis to the
    # physical source emission rate.
    #
    # This helper is intentionally unit-generic. For example:
    #
    #   1/cm^2 per source x source/s
    #       -> 1/(cm^2 s)
    #
    # or:
    #
    #   Gy per source x source/s
    #       -> Gy/s
    #
    # Mean and standard deviation receive the same multiplicative scale.

    if mean_per_source < 0:
        raise ValueError(
            "Per-source estimate mean cannot be negative."
        )

    if standard_deviation_per_source < 0:
        raise ValueError(
            "Per-source estimate standard deviation cannot be negative."
        )

    if physical_source_rate_per_s < 0:
        raise ValueError(
            "Physical source rate cannot be negative."
        )

    return (
        mean_per_source
        * physical_source_rate_per_s,
        standard_deviation_per_source
        * physical_source_rate_per_s,
    )


def calculate_relative_uncertainty(
    mean: float,
    standard_deviation: float,
) -> float:
    # Calculate the one-standard-deviation relative statistical uncertainty:
    #
    #   relative uncertainty = standard deviation / mean

    if mean <= 0:
        raise ValueError(
            "Relative uncertainty requires a positive mean."
        )

    if standard_deviation < 0:
        raise ValueError(
            "Standard deviation cannot be negative."
        )

    return standard_deviation / mean


def calculate_relative_difference(
    comparison_value: float,
    reference_value: float,
) -> float:
    # Calculate signed relative difference from a reference:
    #
    #   (comparison - reference) / reference
    #
    # A positive result means the comparison value is larger than the
    # reference. A negative result means it is smaller.

    if comparison_value < 0:
        raise ValueError(
            "Comparison value cannot be negative."
        )

    if reference_value <= 0:
        raise ValueError(
            "Relative difference requires a positive reference value."
        )

    return (
        comparison_value
        - reference_value
    ) / reference_value


def calculate_observed_monte_carlo_buildup_ratio(
    openmc_response: float,
    deterministic_uncollided_response: float,
) -> float:
    # Calculate the scenario-specific ratio of the OpenMC total response to
    # the deterministic uncollided response.
    #
    # This is an observed Monte Carlo buildup ratio for one documented
    # benchmark scenario. It is not a reusable material buildup coefficient.

    if openmc_response < 0:
        raise ValueError(
            "OpenMC response cannot be negative."
        )

    if deterministic_uncollided_response <= 0:
        raise ValueError(
            "Observed buildup ratio requires a positive "
            "deterministic uncollided response."
        )

    return (
        openmc_response
        / deterministic_uncollided_response
    )

def calculate_point_source_geometric_factor_per_cm2(
    radius_cm: float,
) -> float:
    # Calculate the isotropic point-source geometric factor:
    #
    #   1 / (4 pi r^2)
    #
    # The returned unit is inverse square centimeters.

    if radius_cm <= 0:
        raise ValueError(
            "Point-source radius must be greater than zero."
        )

    return (
        1.0
        / (
            4.0
            * math.pi
            * radius_cm ** 2
        )
    )


def calculate_shell_average_to_point_scale_factor(
    point_radius_cm: float,
    shell_inner_radius_cm: float,
    shell_outer_radius_cm: float,
) -> float:
    # Calculate the ratio between:
    #
    #   shell-average isotropic geometric factor
    #
    # and:
    #
    #   point geometric factor at point_radius_cm
    #
    # Multiplying a point response by this factor converts it to the matched
    # shell-volume-average response when no material exists between the point
    # radius and the evaluation shell.

    point_geometric_factor = (
        calculate_point_source_geometric_factor_per_cm2(
            point_radius_cm
        )
    )

    shell_geometric_factor = (
        calculate_shell_average_geometric_factor_per_cm2(
            inner_radius_cm=(
                shell_inner_radius_cm
            ),
            outer_radius_cm=(
                shell_outer_radius_cm
            ),
        )
    )

    return (
        shell_geometric_factor
        / point_geometric_factor
    )


def create_deterministic_shell_average_result(
    fixed_shield_result: FixedShieldDeterministicResult,
    evaluation_shell_thickness_cm: float,
) -> DeterministicShellAverageResult:
    # Convert one deterministic point-response result into the exact
    # shell-volume-average observable used by the OpenMC benchmark.
    #
    # The shield transmission and response coefficients are unchanged.
    # Only the geometric source-to-observation factor changes.

    evaluation_shell = (
        SphericalEvaluationShell(
            center_radius_cm=(
                fixed_shield_result
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
            fixed_shield_result
            .geometry
            .outer_shield_radius_cm
        )
    ):
        raise ValueError(
            "Evaluation shell must be entirely beyond "
            "the outer shield radius."
        )

    scale_factor = (
        calculate_shell_average_to_point_scale_factor(
            point_radius_cm=(
                fixed_shield_result
                .evaluation_radius_cm
            ),
            shell_inner_radius_cm=(
                evaluation_shell
                .inner_radius_cm
            ),
            shell_outer_radius_cm=(
                evaluation_shell
                .outer_radius_cm
            ),
        )
    )

    shell_line_results: list[
        DeterministicShellPhotonLineResult
    ] = []

    for fixed_line_result in (
        fixed_shield_result.line_results
    ):
        shielding_result = (
            fixed_line_result
            .shielding_result
        )

        point_air_kerma_result = (
            fixed_line_result
            .air_kerma_result
        )

        shell_average_fluence_rate = (
            calculate_deterministic_shell_averaged_fluence_rate(
                photon_emission_rate_per_s=(
                    fixed_line_result
                    .photon_rate_per_s
                ),
                transmission=(
                    shielding_result
                    .total_transmission
                ),
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

        shell_average_air_kerma_rate = (
            point_air_kerma_result
            .uncollided_collision_air_kerma_rate_gy_per_s
            * scale_factor
        )

        point_adjusted_response = (
            point_air_kerma_result
            .buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        shell_average_adjusted_response = None

        if point_adjusted_response is not None:
            shell_average_adjusted_response = (
                point_adjusted_response
                * scale_factor
            )

        shell_line_results.append(
            DeterministicShellPhotonLineResult(
                fixed_shield_line_result=(
                    fixed_line_result
                ),
                point_to_shell_average_scale_factor=(
                    scale_factor
                ),
                shell_average_uncollided_photon_fluence_rate_per_cm2_s=(
                    shell_average_fluence_rate
                ),
                shell_average_uncollided_collision_air_kerma_rate_gy_per_s=(
                    shell_average_air_kerma_rate
                ),
                shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
                    shell_average_adjusted_response
                ),
            )
        )

    total_shell_average_fluence_rate = sum(
        line_result
        .shell_average_uncollided_photon_fluence_rate_per_cm2_s
        for line_result in shell_line_results
    )

    total_shell_average_air_kerma_rate = sum(
        line_result
        .shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        for line_result in shell_line_results
    )

    total_shell_average_adjusted_response = None

    if (
        fixed_shield_result.buildup_status
        == "applied"
    ):
        adjusted_line_values: list[
            float
        ] = []

        for line_result in (
            shell_line_results
        ):
            adjusted_line_value = (
                line_result
                .shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            )

            if adjusted_line_value is None:
                raise ValueError(
                    "Applied deterministic buildup is "
                    "missing a shell-average line response."
                )

            adjusted_line_values.append(
                adjusted_line_value
            )

        total_shell_average_adjusted_response = sum(
            adjusted_line_values
        )

    return DeterministicShellAverageResult(
        fixed_shield_result=(
            fixed_shield_result
        ),
        evaluation_shell=(
            evaluation_shell
        ),
        point_to_shell_average_scale_factor=(
            scale_factor
        ),
        line_results=(
            shell_line_results
        ),
        total_shell_average_uncollided_photon_fluence_rate_per_cm2_s=(
            total_shell_average_fluence_rate
        ),
        total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s=(
            total_shell_average_air_kerma_rate
        ),
        total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
            total_shell_average_adjusted_response
        ),
    )