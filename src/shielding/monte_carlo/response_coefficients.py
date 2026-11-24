# V1.13 dry-air response-coefficient bridge for OpenMC.
#
# This module converts the project's existing NIST dry-air mass
# energy-absorption coefficients into the response function required by an
# OpenMC EnergyFunctionFilter.
#
# The module intentionally contains no OpenMC import.
#
# Response-coefficient derivation:
#
#   photon energy
#       [MeV/photon]
#
#   x dry-air mu_en/rho
#       [cm^2/g]
#
#   x MeV-to-joule conversion
#       [J/MeV]
#
#   x 1000 g/kg
#
#   =
#
#   response coefficient
#       [J cm^2/(kg photon)]
#       [Gy cm^2/photon]
#
# Applying this coefficient to an OpenMC track-length flux tally:
#
#   flux tally
#       [photon cm/source]
#
#   x response coefficient
#       [Gy cm^2/photon]
#
#   =
#
#   raw response tally
#       [Gy cm^3/source]
#
# Division by the evaluation-shell volume then gives:
#
#   [Gy/source]
#
# which can be multiplied by the physical photon source rate to give:
#
#   [Gy/s]


import math
from dataclasses import dataclass
from typing import Literal

from shielding.data.dry_air import (
    get_dry_air_mu_en_over_rho_library,
)
from shielding.monte_carlo.settings import OpenMCSettings
from shielding.physics.kerma_coefficients import (
    AbsorptionEdgeSide,
    get_air_kerma_coefficient_at_energy,
    log_log_interpolate_positive_value,
    validate_air_kerma_coefficient_library,
)
from shielding.physics.response_models import (
    AirKermaCoefficient,
)
from shielding.physics.units import (
    MEV_TO_JOULES,
)

EV_PER_MEV = 1.0e6

GRAMS_PER_KILOGRAM = 1000.0


OpenMCResponseInterpolation = Literal["log-log",]


@dataclass(frozen=True)
class OpenMCAirKermaResponsePoint:
    # One point in the OpenMC dry-air response function.
    #
    # energy_ev:
    #   Incident photon energy in OpenMC's eV convention.
    #
    # response_coefficient_gy_cm2_per_photon:
    #   Collision-air-kerma response per unit photon fluence.
    #
    # absorption_edge_side:
    #   Identifies a value immediately below or above a published absorption
    #   edge. Most response points are not edge points and store None.

    energy_ev: float

    response_coefficient_gy_cm2_per_photon: float

    coefficient_source: str

    absorption_edge_side: AbsorptionEdgeSide | None = None

    def __post_init__(self) -> None:
        if self.energy_ev <= 0:
            raise ValueError("OpenMC response energy must be greater than zero.")

        if self.response_coefficient_gy_cm2_per_photon <= 0:
            raise ValueError("OpenMC response coefficient must be greater than zero.")

        if self.coefficient_source.strip() == "":
            raise ValueError("OpenMC response coefficient source cannot be empty.")

        if self.absorption_edge_side is not None and self.absorption_edge_side not in (
            "below",
            "above",
        ):
            raise ValueError(
                "OpenMC response absorption-edge side must be below or above."
            )


@dataclass(frozen=True)
class OpenMCAirKermaResponseFunction:
    # Complete dry-air response function supplied to OpenMC.
    #
    # A tuple is used instead of a list so a validated function cannot be
    # modified accidentally after construction.
    #
    # Log-log interpolation is selected because the project's dry-air
    # coefficient library already uses log-log interpolation between NIST
    # tabulated values.

    points: tuple[
        OpenMCAirKermaResponsePoint,
        ...,
    ]

    interpolation: OpenMCResponseInterpolation = "log-log"

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("OpenMC response function requires at least two points.")

        for index in range(len(self.points) - 1):
            current_point = self.points[index]

            following_point = self.points[index + 1]

            if following_point.energy_ev <= current_point.energy_ev:
                raise ValueError(
                    "OpenMC response-function energies must be strictly increasing."
                )

        coefficient_sources = {point.coefficient_source for point in self.points}

        if len(coefficient_sources) != 1:
            raise ValueError(
                "OpenMC response-function points must share one coefficient source."
            )

        if self.interpolation != "log-log":
            raise ValueError(
                "OpenMC air-kerma response function requires log-log interpolation."
            )

    @property
    def energy_ev(self) -> list[float]:
        # Return a new list compatible with the OpenMC Python API.

        return [point.energy_ev for point in self.points]

    @property
    def response_coefficients_gy_cm2_per_photon(
        self,
    ) -> list[float]:
        # Return a new list compatible with the OpenMC Python API.

        return [point.response_coefficient_gy_cm2_per_photon for point in self.points]

    @property
    def coefficient_source(self) -> str:
        return self.points[0].coefficient_source

    @property
    def minimum_energy_ev(self) -> float:
        return self.points[0].energy_ev

    @property
    def maximum_energy_ev(self) -> float:
        return self.points[-1].energy_ev


def calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
    photon_energy_mev: float,
    mu_en_over_rho_cm2_per_g: float,
) -> float:
    # Convert photon energy and dry-air mu_en/rho into a response coefficient:
    #
    #   R(E)
    #       = E x mu_en/rho x J/MeV x g/kg
    #
    # Returned unit:
    #
    #   Gy cm^2/photon

    if photon_energy_mev <= 0:
        raise ValueError("Photon energy must be greater than zero.")

    if mu_en_over_rho_cm2_per_g <= 0:
        raise ValueError(
            "Dry-air mass energy-absorption coefficient must be greater than zero."
        )

    return (
        photon_energy_mev
        * MEV_TO_JOULES
        * GRAMS_PER_KILOGRAM
        * mu_en_over_rho_cm2_per_g
    )


def get_dry_air_response_point_at_energy(
    photon_energy_mev: float,
    edge_side: (AbsorptionEdgeSide | None) = None,
) -> OpenMCAirKermaResponsePoint:
    # Obtain the same exact or log-log-interpolated dry-air coefficient used
    # by V1.12 and convert it into the OpenMC response-coefficient unit.

    coefficient = get_air_kerma_coefficient_at_energy(
        photon_energy_mev=(photon_energy_mev),
        edge_side=edge_side,
    )

    response_coefficient = calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
        photon_energy_mev=(photon_energy_mev),
        mu_en_over_rho_cm2_per_g=(coefficient.mu_en_over_rho_cm2_per_g),
    )

    return OpenMCAirKermaResponsePoint(
        energy_ev=(photon_energy_mev * EV_PER_MEV),
        response_coefficient_gy_cm2_per_photon=(response_coefficient),
        coefficient_source=(coefficient.source),
        absorption_edge_side=(edge_side),
    )


def get_absorption_edge_side_for_library_index(
    library: list[AirKermaCoefficient],
    index: int,
) -> AbsorptionEdgeSide | None:
    # Determine whether one library entry is immediately below or above a
    # duplicated-energy absorption edge.
    #
    # The current dry-air library contains one duplicated-energy pair for the
    # argon K edge.

    coefficient_energy = library[index].photon_energy_mev

    previous_entry_has_same_energy = index > 0 and (
        library[index - 1].photon_energy_mev == coefficient_energy
    )

    following_entry_has_same_energy = index < len(library) - 1 and (
        library[index + 1].photon_energy_mev == coefficient_energy
    )

    if previous_entry_has_same_energy and following_entry_has_same_energy:
        raise ValueError(
            "Dry-air response-function construction "
            "supports at most two entries at one "
            "absorption-edge energy."
        )

    if following_entry_has_same_energy:
        return "below"

    if previous_entry_has_same_energy:
        return "above"

    return None


def create_openmc_dry_air_response_function(
    library: list[AirKermaCoefficient] | None = None,
) -> OpenMCAirKermaResponseFunction:
    # Convert the complete dry-air coefficient library into the continuous
    # response function used by OpenMC.
    #
    # OpenMC interpolation requires an ordered energy grid. The NIST library
    # contains two coefficients at the same argon K-edge energy. To preserve
    # the discontinuity while retaining a strictly increasing grid:
    #
    #   below-edge point
    #       -> next representable float below the edge energy
    #
    #   above-edge point
    #       -> next representable float at or above the edge energy
    #
    # This creates a numerically negligible interval across which the jump is
    # represented without deleting either published coefficient.

    if library is None:
        library = get_dry_air_mu_en_over_rho_library()

    validate_air_kerma_coefficient_library(library)

    response_points: list[OpenMCAirKermaResponsePoint] = []

    for index, coefficient in enumerate(library):
        edge_side = get_absorption_edge_side_for_library_index(
            library=library,
            index=index,
        )

        published_energy_ev = coefficient.photon_energy_mev * EV_PER_MEV

        response_energy_ev = published_energy_ev

        if edge_side == "below":
            response_energy_ev = math.nextafter(
                published_energy_ev,
                -math.inf,
            )

        elif edge_side == "above":
            response_energy_ev = math.nextafter(
                published_energy_ev,
                math.inf,
            )

        response_coefficient = (
            calculate_air_kerma_response_coefficient_gy_cm2_per_photon(
                photon_energy_mev=(coefficient.photon_energy_mev),
                mu_en_over_rho_cm2_per_g=(coefficient.mu_en_over_rho_cm2_per_g),
            )
        )

        response_points.append(
            OpenMCAirKermaResponsePoint(
                energy_ev=response_energy_ev,
                response_coefficient_gy_cm2_per_photon=(response_coefficient),
                coefficient_source=(coefficient.source),
                absorption_edge_side=(edge_side),
            )
        )

    return OpenMCAirKermaResponseFunction(
        points=tuple(response_points),
        interpolation="log-log",
    )


def evaluate_openmc_response_function_at_energy_ev(
    response_function: (OpenMCAirKermaResponseFunction),
    energy_ev: float,
) -> float:
    # Evaluate the response function using the same log-log interpolation
    # that will be requested from OpenMC.
    #
    # OpenMC evaluates the function as zero outside its supplied energy range.
    # This pure-Python evaluator mirrors that behavior for validation.

    if energy_ev <= 0:
        raise ValueError(
            "OpenMC response-function evaluation energy must be greater than zero."
        )

    if (
        energy_ev < response_function.minimum_energy_ev
        or energy_ev > response_function.maximum_energy_ev
    ):
        return 0.0

    for point in response_function.points:
        if energy_ev == point.energy_ev:
            return point.response_coefficient_gy_cm2_per_photon

    for lower_point, upper_point in zip(
        response_function.points[:-1],
        response_function.points[1:],
        strict=True,
    ):
        if lower_point.energy_ev < energy_ev < upper_point.energy_ev:
            return log_log_interpolate_positive_value(
                x=energy_ev,
                x1=lower_point.energy_ev,
                y1=(lower_point.response_coefficient_gy_cm2_per_photon),
                x2=upper_point.energy_ev,
                y2=(upper_point.response_coefficient_gy_cm2_per_photon),
            )

    raise ValueError("Unable to bracket energy within the OpenMC response function.")


def calculate_energy_bin_representative_energy_ev(
    lower_energy_ev: float,
    upper_energy_ev: float,
) -> float:
    # Use the geometric midpoint as the representative energy of a spectrum
    # bin. This is compatible with the logarithmic response interpolation.
    #
    # The direct EnergyFunctionFilter tally remains authoritative. This
    # representative energy is used only by the spectrum-folded cross-check.

    if lower_energy_ev <= 0:
        raise ValueError("Energy-bin lower boundary must be greater than zero.")

    if upper_energy_ev <= lower_energy_ev:
        raise ValueError(
            "Energy-bin upper boundary must be greater than the lower boundary."
        )

    return math.sqrt(lower_energy_ev * upper_energy_ev)


def calculate_energy_bin_response_coefficient_gy_cm2_per_photon(
    response_function: (OpenMCAirKermaResponseFunction),
    lower_energy_ev: float,
    upper_energy_ev: float,
) -> float:
    # Evaluate the response coefficient at one spectrum bin's geometric
    # representative energy.

    representative_energy_ev = calculate_energy_bin_representative_energy_ev(
        lower_energy_ev=(lower_energy_ev),
        upper_energy_ev=(upper_energy_ev),
    )

    response_coefficient = evaluate_openmc_response_function_at_energy_ev(
        response_function=(response_function),
        energy_ev=(representative_energy_ev),
    )

    if response_coefficient <= 0:
        raise ValueError(
            "Energy-bin representative energy lies "
            "outside the OpenMC response-function range."
        )

    return response_coefficient


def fold_photon_fluence_rate_to_air_kerma_rate_gy_per_s(
    photon_fluence_rate_per_cm2_s: float,
    response_coefficient_gy_cm2_per_photon: float,
) -> float:
    # Fold one photon fluence rate with one dry-air response coefficient:
    #
    #   photons/(cm^2 s)
    #
    #   x Gy cm^2/photon
    #
    #   = Gy/s

    if photon_fluence_rate_per_cm2_s < 0:
        raise ValueError("Photon fluence rate cannot be negative.")

    if response_coefficient_gy_cm2_per_photon <= 0:
        raise ValueError("Air-kerma response coefficient must be greater than zero.")

    return photon_fluence_rate_per_cm2_s * response_coefficient_gy_cm2_per_photon


def validate_response_function_covers_openmc_settings(
    response_function: (OpenMCAirKermaResponseFunction),
    settings: OpenMCSettings,
) -> None:
    # Confirm that the response function covers every photon energy retained
    # and tallied by one OpenMC profile.
    #
    # EnergyFunctionFilter values outside its supplied range are zero, so a
    # profile extending beyond this range would silently lose response.

    if response_function.minimum_energy_ev > settings.photon_cutoff_energy_ev:
        raise ValueError(
            "OpenMC response-function minimum energy "
            "must not exceed the photon cutoff energy."
        )

    if response_function.minimum_energy_ev > settings.minimum_spectrum_energy_ev:
        raise ValueError(
            "OpenMC response-function minimum energy "
            "must cover the spectrum minimum energy."
        )

    if response_function.maximum_energy_ev < settings.maximum_spectrum_energy_ev:
        raise ValueError(
            "OpenMC response-function maximum energy "
            "must cover the spectrum maximum energy."
        )
