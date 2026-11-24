"""Look up and interpolate mass energy-absorption coefficients for dry air."""

import math
from typing import Literal

from shielding.data.dry_air import (
    get_dry_air_mu_en_over_rho_library,
)
from shielding.physics.response_models import (
    AirKermaCoefficient,
)

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
            "Air-kerma coefficient library must contain at least two entries."
        )

    for index in range(len(library) - 1):
        current = library[index]
        following = library[index + 1]

        if current.photon_energy_mev > following.photon_energy_mev:
            raise ValueError(
                "Air-kerma coefficient energies must be sorted in nondecreasing order."
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
        raise ValueError("Log-log interpolation requires positive values.")

    if x2 <= x1:
        raise ValueError("Log-log interpolation requires x2 to be greater than x1.")

    if x < x1 or x > x2:
        raise ValueError("Interpolation point must lie inside the supplied interval.")

    logarithmic_fraction = math.log(x / x1) / math.log(x2 / x1)

    return math.exp(math.log(y1) + logarithmic_fraction * math.log(y2 / y1))


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
        raise ValueError("Photon energy must be greater than zero.")

    if edge_side is not None:
        if edge_side not in VALID_ABSORPTION_EDGE_SIDES:
            raise ValueError("Absorption-edge side must be below or above.")

    if library is None:
        library = get_dry_air_mu_en_over_rho_library()

    validate_air_kerma_coefficient_library(library)

    matching_coefficients = [
        coefficient
        for coefficient in library
        if (coefficient.photon_energy_mev == photon_energy_mev)
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
        raise ValueError("Photon energy must be greater than zero.")

    if library is None:
        library = get_dry_air_mu_en_over_rho_library()

    validate_air_kerma_coefficient_library(library)

    exact_matches = [
        coefficient
        for coefficient in library
        if (coefficient.photon_energy_mev == photon_energy_mev)
    ]

    if len(exact_matches) > 0:
        return get_exact_air_kerma_coefficient(
            photon_energy_mev=photon_energy_mev,
            library=library,
            edge_side=edge_side,
        )

    minimum_energy = library[0].photon_energy_mev

    maximum_energy = library[-1].photon_energy_mev

    if photon_energy_mev < minimum_energy or photon_energy_mev > maximum_energy:
        raise ValueError(
            "Requested photon energy is outside the dry-air "
            "coefficient range: "
            f"{minimum_energy:.8g} to "
            f"{maximum_energy:.8g} MeV."
        )

    for index in range(len(library) - 1):
        lower = library[index]
        upper = library[index + 1]

        lower_energy = lower.photon_energy_mev

        upper_energy = upper.photon_energy_mev

        # Skip the zero-width interval between the two published values at
        # an absorption edge.
        if lower_energy == upper_energy:
            continue

        if lower_energy < photon_energy_mev < upper_energy:
            if lower.source != upper.source:
                raise ValueError(
                    "Cannot interpolate between coefficients "
                    "from different data sources."
                )

            interpolated_coefficient = log_log_interpolate_positive_value(
                x=photon_energy_mev,
                x1=lower_energy,
                y1=(lower.mu_en_over_rho_cm2_per_g),
                x2=upper_energy,
                y2=(upper.mu_en_over_rho_cm2_per_g),
            )

            return AirKermaCoefficient(
                photon_energy_mev=photon_energy_mev,
                mu_en_over_rho_cm2_per_g=(interpolated_coefficient),
                source=lower.source,
            )

    raise ValueError(
        "Unable to bracket the requested photon energy "
        "within the dry-air coefficient library."
    )
