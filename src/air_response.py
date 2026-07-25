# V1.12 deterministic collision-air-kerma calculations.
#
# This module provides:
#   - exact and absorption-edge-aware dry-air coefficient lookup
#   - log-log interpolation of dry-air mu_en/rho
#   - photon energy-fluence-rate calculations
#   - collision air-kerma-rate calculations
#   - line-by-line manual and isotope source responses
#   - optional G-P exposure-buildup adjustment
#   - source-level response aggregation
#
# Canonical internal air-kerma-rate unit:
#   Gy/s
#
# Primary engineering display unit:
#   microGy/h


import math
from typing import Literal

from air_response_library import (
    get_dry_air_mu_en_over_rho_library,
)

from unit_conversions import (
    convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s,
    convert_gy_per_s_to_microgy_per_h,
    convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg,
)

from air_response_models import (
    AirKermaCoefficient,
    BuildupStatus,
    PhotonLineAirKermaResult,
    SourceAirKermaResult,
    VALID_BUILDUP_STATUSES,
)

from source_models import (
    IsotopeSource,
    ManualPhotonSource,
    PhotonLine,
)

from buildup import (
    calculate_gp_buildup_factor,
    get_gp_coefficients_at_energy,
)
from buildup_library import (
    get_gp_coefficients_library,
)
from calculator import (
    calculate_shielding_result,
)
from models import (
    Layer,
    ShieldingResult,
)

Source = ManualPhotonSource | IsotopeSource

AbsorptionEdgeSide = Literal[
    "below",
    "above",
]


VALID_ABSORPTION_EDGE_SIDES = (
    "below",
    "above",
)


def validate_air_kerma_coefficient_library(
    library: list[AirKermaCoefficient],
) -> None:
    # Confirm that a coefficient table is usable for lookup and
    # interpolation.
    #
    # Equal adjacent energies are allowed because absorption edges can have
    # separate values immediately below and above the same published energy.

    if len(library) < 2:
        raise ValueError(
            "Air-kerma coefficient library must contain "
            "at least two entries."
        )

    for index in range(len(library) - 1):
        current = library[index]
        following = library[index + 1]

        if (
            current.photon_energy_mev
            > following.photon_energy_mev
        ):
            raise ValueError(
                "Air-kerma coefficient energies must be "
                "sorted in nondecreasing order."
            )


def log_log_interpolate_positive_value(
    x: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    # Interpolate between two positive tabulated values in logarithmic
    # x-y space.
    #
    # This is consistent with the interpolation approach already used for
    # photon attenuation coefficients elsewhere in the simulator.

    values = (
        x,
        x1,
        y1,
        x2,
        y2,
    )

    if any(value <= 0 for value in values):
        raise ValueError(
            "Log-log interpolation requires positive values."
        )

    if x2 <= x1:
        raise ValueError(
            "Log-log interpolation requires x2 to be "
            "greater than x1."
        )

    if x < x1 or x > x2:
        raise ValueError(
            "Interpolation point must lie inside the "
            "supplied interval."
        )

    logarithmic_fraction = (
        math.log(x / x1)
        / math.log(x2 / x1)
    )

    return math.exp(
        math.log(y1)
        + logarithmic_fraction
        * math.log(y2 / y1)
    )


def get_exact_air_kerma_coefficient(
    photon_energy_mev: float,
    library: list[AirKermaCoefficient] | None = None,
    edge_side: AbsorptionEdgeSide | None = None,
) -> AirKermaCoefficient:
    # Return an exactly tabulated dry-air coefficient.
    #
    # Most energies have one coefficient. An absorption-edge energy may have
    # two coefficients representing the values immediately below and above
    # the discontinuity. In that case, edge_side must be supplied.

    if photon_energy_mev <= 0:
        raise ValueError(
            "Photon energy must be greater than zero."
        )

    if edge_side is not None:
        if edge_side not in VALID_ABSORPTION_EDGE_SIDES:
            raise ValueError(
                "Absorption-edge side must be below or above."
            )

    if library is None:
        library = (
            get_dry_air_mu_en_over_rho_library()
        )

    validate_air_kerma_coefficient_library(
        library
    )

    matching_coefficients = [
        coefficient
        for coefficient in library
        if (
            coefficient.photon_energy_mev
            == photon_energy_mev
        )
    ]

    if len(matching_coefficients) == 0:
        raise ValueError(
            "No exact dry-air mass energy-absorption "
            f"coefficient exists at {photon_energy_mev:.8g} MeV."
        )

    if len(matching_coefficients) == 1:
        return matching_coefficients[0]

    if edge_side is None:
        raise ValueError(
            "The requested energy is an absorption edge with "
            "separate below-edge and above-edge coefficients. "
            "Specify edge_side='below' or edge_side='above'."
        )

    if edge_side == "below":
        return matching_coefficients[0]

    return matching_coefficients[-1]


def get_air_kerma_coefficient_at_energy(
    photon_energy_mev: float,
    library: list[AirKermaCoefficient] | None = None,
    edge_side: AbsorptionEdgeSide | None = None,
) -> AirKermaCoefficient:
    # Return an exact or log-log-interpolated dry-air mass
    # energy-absorption coefficient.
    #
    # Interpolation never crosses the zero-width interval between duplicate
    # absorption-edge energies:
    #
    #   energy below edge
    #       -> interpolate to the below-edge coefficient
    #
    #   energy above edge
    #       -> interpolate from the above-edge coefficient

    if photon_energy_mev <= 0:
        raise ValueError(
            "Photon energy must be greater than zero."
        )

    if library is None:
        library = (
            get_dry_air_mu_en_over_rho_library()
        )

    validate_air_kerma_coefficient_library(
        library
    )

    exact_matches = [
        coefficient
        for coefficient in library
        if (
            coefficient.photon_energy_mev
            == photon_energy_mev
        )
    ]

    if len(exact_matches) > 0:
        return get_exact_air_kerma_coefficient(
            photon_energy_mev=photon_energy_mev,
            library=library,
            edge_side=edge_side,
        )

    minimum_energy = (
        library[0].photon_energy_mev
    )

    maximum_energy = (
        library[-1].photon_energy_mev
    )

    if (
        photon_energy_mev < minimum_energy
        or photon_energy_mev > maximum_energy
    ):
        raise ValueError(
            "Requested photon energy is outside the dry-air "
            "coefficient range: "
            f"{minimum_energy:.8g} to "
            f"{maximum_energy:.8g} MeV."
        )

    for index in range(len(library) - 1):
        lower = library[index]
        upper = library[index + 1]

        lower_energy = (
            lower.photon_energy_mev
        )

        upper_energy = (
            upper.photon_energy_mev
        )

        # Skip the zero-width interval between the two published values at
        # an absorption edge.
        if lower_energy == upper_energy:
            continue

        if (
            lower_energy
            < photon_energy_mev
            < upper_energy
        ):
            if lower.source != upper.source:
                raise ValueError(
                    "Cannot interpolate between coefficients "
                    "from different data sources."
                )

            interpolated_coefficient = (
                log_log_interpolate_positive_value(
                    x=photon_energy_mev,
                    x1=lower_energy,
                    y1=(
                        lower
                        .mu_en_over_rho_cm2_per_g
                    ),
                    x2=upper_energy,
                    y2=(
                        upper
                        .mu_en_over_rho_cm2_per_g
                    ),
                )
            )

            return AirKermaCoefficient(
                photon_energy_mev=photon_energy_mev,
                mu_en_over_rho_cm2_per_g=(
                    interpolated_coefficient
                ),
                source=lower.source,
            )

    raise ValueError(
        "Unable to bracket the requested photon energy "
        "within the dry-air coefficient library."
    )


def calculate_gp_exposure_buildup_factor_for_shielding_result(
    shielding_result: ShieldingResult,
) -> float:
    # Calculate a G-P exposure buildup factor for one completed
    # narrow-beam shielding result.
    #
    # Unlike the legacy calculate_buildup_for_result() function, this
    # helper does not write a "buildup-corrected flux" into
    # ShieldingResult. It returns only the dimensionless exposure
    # buildup factor.
    #
    # The caller applies the returned factor only to the compatible
    # collision-air-kerma response.

    if len(shielding_result.layers) != 1:
        raise ValueError(
            "G-P exposure buildup currently supports only "
            "one homogeneous shielding layer."
        )

    material = (
        shielding_result.layers[0].material
    )

    gp_library = (
        get_gp_coefficients_library()
    )

    if material.key not in gp_library:
        raise ValueError(
            "G-P exposure buildup is not available for "
            f"{material.name}."
        )

    coefficients = get_gp_coefficients_at_energy(
        material_name=material.key,
        energy=shielding_result.photon_energy,
        gp_library=gp_library,
    )

    try:
        return calculate_gp_buildup_factor(
            coefficients=coefficients,
            mfp=shielding_result.total_mfp,
        )

    except ValueError as error:
        raise ValueError(
            "Could not calculate G-P exposure buildup for "
            f"{shielding_result.photon_energy:.8g} MeV "
            f"through {material.name}. "
            f"Total optical thickness was "
            f"{shielding_result.total_mfp:.6g} MFP. "
            f"{error}"
        ) from error


def calculate_energy_fluence_rate_mev_per_cm2_s(
    photon_energy_mev: float,
    photon_fluence_rate_per_cm2_s: float,
) -> float:
    # Calculate photon energy fluence rate:
    #
    # photon energy
    #     ×
    # photon fluence rate
    #
    # MeV/photon × photons/(cm² s)
    #     =
    # MeV/(cm² s)

    if photon_energy_mev <= 0:
        raise ValueError(
            "Photon energy must be greater than zero."
        )

    if photon_fluence_rate_per_cm2_s < 0:
        raise ValueError(
            "Photon fluence rate cannot be negative."
        )

    return (
        photon_energy_mev
        * photon_fluence_rate_per_cm2_s
    )


def calculate_collision_air_kerma_rate_gy_per_s(
    energy_fluence_rate_mev_per_cm2_s: float,
    mu_en_over_rho_cm2_per_g: float,
) -> float:
    # Calculate collision air-kerma rate from photon energy fluence.
    #
    # Energy fluence rate:
    #   MeV/(cm² s)
    #
    # Dry-air mass energy-absorption coefficient:
    #   cm²/g
    #
    # Both values are converted to SI units before multiplication:
    #
    # J/(m² s) × m²/kg
    #     =
    # J/(kg s)
    #     =
    # Gy/s

    if energy_fluence_rate_mev_per_cm2_s < 0:
        raise ValueError(
            "Energy fluence rate cannot be negative."
        )

    if mu_en_over_rho_cm2_per_g <= 0:
        raise ValueError(
            "Dry-air mass energy-absorption coefficient "
            "must be greater than zero."
        )

    energy_fluence_rate_j_per_m2_s = (
        convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s(
            energy_fluence_rate_mev_per_cm2_s
        )
    )

    coefficient_m2_per_kg = (
        convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg(
            mu_en_over_rho_cm2_per_g
        )
    )

    return (
        energy_fluence_rate_j_per_m2_s
        * coefficient_m2_per_kg
    )


def calculate_collision_air_kerma_rate_microgy_per_h(
    energy_fluence_rate_mev_per_cm2_s: float,
    mu_en_over_rho_cm2_per_g: float,
) -> float:
    # Convenience wrapper for engineering output in µGy/h.
    #
    # The canonical internal unit remains Gy/s.

    air_kerma_rate_gy_per_s = (
        calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s,
            mu_en_over_rho_cm2_per_g,
        )
    )

    return convert_gy_per_s_to_microgy_per_h(
        air_kerma_rate_gy_per_s
    )


def calculate_photon_line_air_kerma_result(
    photon_line: PhotonLine,
    photon_rate_per_s: float,
    uncollided_photon_fluence_rate_per_cm2_s: float,
    buildup_status: BuildupStatus = "not_requested",
    buildup_factor: float | None = None,
    warnings: list[str] | None = None,
) -> PhotonLineAirKermaResult:
    # Convert one transported photon line into an explicit collision
    # air-kerma response result.
    #
    # The caller supplies the uncollided photon fluence rate. This keeps
    # attenuation calculations separate from response-coefficient folding.
    #
    # When buildup is applied, the supplied factor must be a G-P exposure
    # buildup factor compatible with the collision-air-kerma response.

    if photon_rate_per_s < 0:
        raise ValueError(
            "Photon emission rate cannot be negative."
        )

    if uncollided_photon_fluence_rate_per_cm2_s < 0:
        raise ValueError(
            "Uncollided photon fluence rate cannot be negative."
        )

    if buildup_status not in VALID_BUILDUP_STATUSES:
        raise ValueError(
            "Unsupported buildup status."
        )

    if buildup_status == "applied":
        if buildup_factor is None:
            raise ValueError(
                "Applied buildup requires a buildup factor."
            )

        if buildup_factor < 1:
            raise ValueError(
                "Buildup factor cannot be less than one."
            )

    elif buildup_factor is not None:
        raise ValueError(
            "A buildup factor may only be supplied when "
            "buildup status is applied."
        )

    coefficient = get_air_kerma_coefficient_at_energy(
        photon_line.energy
    )

    energy_fluence_rate = (
        calculate_energy_fluence_rate_mev_per_cm2_s(
            photon_energy_mev=photon_line.energy,
            photon_fluence_rate_per_cm2_s=(
                uncollided_photon_fluence_rate_per_cm2_s
            ),
        )
    )

    uncollided_air_kerma_rate = (
        calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=(
                energy_fluence_rate
            ),
            mu_en_over_rho_cm2_per_g=(
                coefficient.mu_en_over_rho_cm2_per_g
            ),
        )
    )

    buildup_adjusted_air_kerma_rate = None

    if buildup_status == "applied":
        if buildup_factor is None:
            # This condition is already rejected above. The additional
            # check makes the type narrowing explicit.
            raise ValueError(
                "Applied buildup requires a buildup factor."
            )

        buildup_adjusted_air_kerma_rate = (
            uncollided_air_kerma_rate
            * buildup_factor
        )

        calculation_method = (
            "Deterministic point-source attenuation with "
            "dry-air response-coefficient folding and "
            "G-P exposure buildup"
        )

    else:
        calculation_method = (
            "Deterministic uncollided point-source attenuation "
            "with dry-air response-coefficient folding"
        )

    line_warnings = (
        []
        if warnings is None
        else list(warnings)
    )

    return PhotonLineAirKermaResult(
        photon_energy_mev=photon_line.energy,
        emission_intensity=photon_line.intensity,
        photon_rate_per_s=photon_rate_per_s,
        uncollided_photon_fluence_rate_per_cm2_s=(
            uncollided_photon_fluence_rate_per_cm2_s
        ),
        energy_fluence_rate_mev_per_cm2_s=(
            energy_fluence_rate
        ),
        air_mu_en_over_rho_cm2_per_g=(
            coefficient.mu_en_over_rho_cm2_per_g
        ),
        uncollided_collision_air_kerma_rate_gy_per_s=(
            uncollided_air_kerma_rate
        ),
        calculation_method=calculation_method,
        coefficient_source=coefficient.source,
        buildup_status=buildup_status,
        buildup_factor=buildup_factor,
        buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
            buildup_adjusted_air_kerma_rate
        ),
        warnings=line_warnings,
    )


def collect_unique_line_warnings(
    line_results: list[PhotonLineAirKermaResult],
) -> list[str]:
    # Combine line-level warnings while preserving their original order.
    #
    # The same warning may occur for multiple photon lines. Source-level
    # output should not repeat identical warning text unnecessarily.

    combined_warnings: list[str] = []

    for line_result in line_results:
        for warning in line_result.warnings:
            if warning not in combined_warnings:
                combined_warnings.append(
                    warning
                )

    return combined_warnings


def aggregate_source_air_kerma_results(
    source_name: str,
    activity_bq: float | None,
    line_results: list[PhotonLineAirKermaResult],
) -> SourceAirKermaResult:
    # Combine line-by-line collision air-kerma results into one source result.
    #
    # Source-level buildup behavior:
    #
    # all lines applied
    #     -> buildup-adjusted total is available
    #
    # any line unavailable
    #     -> source buildup status is unavailable
    #
    # any line uses fallback
    #     -> source buildup status is fallback
    #
    # all lines not requested
    #     -> only the uncollided response is reported
    #
    # A mixture of not_requested and another buildup status is rejected
    # because buildup is a source-calculation setting, not a per-line user
    # choice.

    if source_name.strip() == "":
        raise ValueError(
            "Source name cannot be empty."
        )

    if activity_bq is not None and activity_bq < 0:
        raise ValueError(
            "Source activity cannot be negative."
        )

    if len(line_results) == 0:
        raise ValueError(
            "At least one photon-line air-kerma result is required."
        )

    total_uncollided_photon_fluence_rate = sum(
        line_result
        .uncollided_photon_fluence_rate_per_cm2_s
        for line_result in line_results
    )

    total_uncollided_air_kerma_rate = sum(
        line_result
        .uncollided_collision_air_kerma_rate_gy_per_s
        for line_result in line_results
    )

    buildup_statuses = {
        line_result.buildup_status
        for line_result in line_results
    }

    if (
        "not_requested" in buildup_statuses
        and len(buildup_statuses) > 1
    ):
        raise ValueError(
            "Source line results cannot mix not-requested buildup "
            "with applied, unavailable, or fallback buildup states."
        )

    total_buildup_adjusted_air_kerma_rate = None

    if buildup_statuses == {"applied"}:
        source_buildup_status: BuildupStatus = (
            "applied"
        )

        adjusted_line_values = []

        for line_result in line_results:
            adjusted_value = (
                line_result
                .buildup_adjusted_collision_air_kerma_rate_gy_per_s
            )

            if adjusted_value is None:
                raise ValueError(
                    "An applied photon-line buildup result is "
                    "missing its adjusted air-kerma rate."
                )

            adjusted_line_values.append(
                adjusted_value
            )

        total_buildup_adjusted_air_kerma_rate = sum(
            adjusted_line_values
        )

    elif "unavailable" in buildup_statuses:
        source_buildup_status = "unavailable"

    elif "fallback" in buildup_statuses:
        source_buildup_status = "fallback"

    elif buildup_statuses == {"not_requested"}:
        source_buildup_status = "not_requested"

    else:
        raise ValueError(
            "Unable to determine a consistent source-level "
            "buildup status."
        )

    warnings = collect_unique_line_warnings(
        line_results
    )

    return SourceAirKermaResult(
        source_name=source_name,
        activity_bq=activity_bq,
        line_results=list(line_results),
        total_uncollided_photon_fluence_rate_per_cm2_s=(
            total_uncollided_photon_fluence_rate
        ),
        total_uncollided_collision_air_kerma_rate_gy_per_s=(
            total_uncollided_air_kerma_rate
        ),
        buildup_status=source_buildup_status,
        total_buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
            total_buildup_adjusted_air_kerma_rate
        ),
        warnings=warnings,
    )


def calculate_shielded_photon_line_air_kerma_result(
    photon_line: PhotonLine,
    photon_rate_per_s: float,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> PhotonLineAirKermaResult:
    # Calculate attenuation and collision air kerma for one photon line.
    #
    # Workflow:
    #
    # photon rate
    #     -> Beer-Lambert shielding result
    #     -> uncollided photon fluence rate
    #     -> energy fluence rate
    #     -> collision air-kerma rate
    #     -> optional G-P exposure buildup adjustment
    #
    # A failed buildup calculation does not discard the valid
    # uncollided response.

    if photon_rate_per_s < 0:
        raise ValueError(
            "Photon emission rate cannot be negative."
        )

    shielding_result = calculate_shielding_result(
        layers=layers,
        photon_energy=photon_line.energy,
        source_strength=photon_rate_per_s,
        detector_distance=detector_distance_cm,
    )

    buildup_status: BuildupStatus = (
        "not_requested"
    )

    buildup_factor = None
    warnings: list[str] = []

    if apply_buildup:
        try:
            buildup_factor = (
                calculate_gp_exposure_buildup_factor_for_shielding_result(
                    shielding_result
                )
            )

            buildup_status = "applied"

        except ValueError as error:
            buildup_status = "unavailable"

            warnings.append(
                "G-P exposure buildup was unavailable for "
                f"the {photon_line.energy:.8g} MeV photon line. "
                f"{error} "
                "The uncollided collision air-kerma rate "
                "is still reported."
            )

    return calculate_photon_line_air_kerma_result(
        photon_line=photon_line,
        photon_rate_per_s=photon_rate_per_s,
        uncollided_photon_fluence_rate_per_cm2_s=(
            shielding_result.uncollided_flux
        ),
        buildup_status=buildup_status,
        buildup_factor=buildup_factor,
        warnings=warnings,
    )


def calculate_manual_source_air_kerma_result(
    source: ManualPhotonSource,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Calculate collision air kerma for a manual monoenergetic source.

    photon_line = PhotonLine(
        energy=source.energy,
        intensity=1.0,
    )

    line_result = (
        calculate_shielded_photon_line_air_kerma_result(
            photon_line=photon_line,
            photon_rate_per_s=source.photon_rate,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )
    )

    return aggregate_source_air_kerma_results(
        source_name="Manual Photon Source",
        activity_bq=None,
        line_results=[
            line_result
        ],
    )


def calculate_isotope_source_air_kerma_result(
    source: IsotopeSource,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Calculate one collision air-kerma contribution per isotope
    # photon line and sum the complete source response.

    line_results: list[
        PhotonLineAirKermaResult
    ] = []

    for photon_line in source.photon_lines:
        photon_rate_per_s = (
            source.activity_bq
            * photon_line.intensity
        )

        line_result = (
            calculate_shielded_photon_line_air_kerma_result(
                photon_line=photon_line,
                photon_rate_per_s=photon_rate_per_s,
                layers=layers,
                detector_distance_cm=detector_distance_cm,
                apply_buildup=apply_buildup,
            )
        )

        line_results.append(
            line_result
        )

    return aggregate_source_air_kerma_results(
        source_name=source.name,
        activity_bq=source.activity_bq,
        line_results=line_results,
    )


def calculate_source_air_kerma_result(
    source: Source,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Route a supported source type into the correct V1.12 response
    # calculation pathway.

    if isinstance(
        source,
        ManualPhotonSource,
    ):
        return calculate_manual_source_air_kerma_result(
            source=source,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )

    if isinstance(
        source,
        IsotopeSource,
    ):
        return calculate_isotope_source_air_kerma_result(
            source=source,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )

    raise ValueError(
        "Unsupported source type for air-kerma calculation."
    )