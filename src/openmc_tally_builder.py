# V1.13 OpenMC benchmark tally construction.
#
# This module attaches the two official V1.13 tallies to an already-built
# OpenMC photon model:
#
#   1. energy-resolved photon track-length flux;
#   2. direct dry-air collision-air-kerma response.
#
# The OpenMC import remains delayed through openmc_model_builder so importing
# this module does not require OpenMC in the normal deterministic environment.
#
# Raw spectrum tally unit:
#
#   photon cm/source particle
#
# after division by evaluation-shell volume:
#
#   photon/(cm^2 source particle)
#
# Direct response tally unit:
#
#   flux score
#       [photon cm/source particle]
#
#   x response coefficient
#       [Gy cm^2/photon]
#
#   =
#
#   Gy cm^3/source particle
#
# after division by evaluation-shell volume:
#
#   Gy/source particle


from dataclasses import dataclass
from typing import Any


from openmc_model_builder import (
    OpenMCModelBuildResult,
    load_openmc_module,
)
from openmc_models import (
    OpenMCSettings,
)
from openmc_response_coefficients import (
    OpenMCAirKermaResponseFunction,
    create_openmc_dry_air_response_function,
    validate_response_function_covers_openmc_settings,
)


SPECTRUM_TALLY_ID = 4001
DIRECT_RESPONSE_TALLY_ID = 4002

EVALUATION_CELL_FILTER_ID = 5001
PHOTON_PARTICLE_FILTER_ID = 5002
SPECTRUM_ENERGY_FILTER_ID = 5003
AIR_KERMA_RESPONSE_FILTER_ID = 5004

SPECTRUM_TALLY_NAME = (
    "v113_evaluation_shell_photon_flux_spectrum"
)

DIRECT_RESPONSE_TALLY_NAME = (
    "v113_evaluation_shell_direct_air_kerma_response"
)


@dataclass
class OpenMCTallyBuildResult:
    # OpenMC objects and supporting metadata created by the benchmark tally
    # builder.
    #
    # All OpenMC objects are typed as Any because OpenMC is imported only in
    # the isolated backend environment.

    model_build_result: (
        OpenMCModelBuildResult
    )

    tallies: Any

    spectrum_tally: Any
    direct_response_tally: Any

    evaluation_cell_filter: Any
    photon_particle_filter: Any

    spectrum_energy_filter: Any
    air_kerma_response_filter: Any

    response_function: (
        OpenMCAirKermaResponseFunction
    )

    def __post_init__(self) -> None:
        if self.spectrum_tally.id != SPECTRUM_TALLY_ID:
            raise ValueError(
                "Unexpected V1.13 spectrum tally ID."
            )

        if (
            self.direct_response_tally.id
            != DIRECT_RESPONSE_TALLY_ID
        ):
            raise ValueError(
                "Unexpected V1.13 direct-response tally ID."
            )

        if (
            self.spectrum_tally.name
            != SPECTRUM_TALLY_NAME
        ):
            raise ValueError(
                "Unexpected V1.13 spectrum tally name."
            )

        if (
            self.direct_response_tally.name
            != DIRECT_RESPONSE_TALLY_NAME
        ):
            raise ValueError(
                "Unexpected V1.13 direct-response tally name."
            )

        if self.spectrum_tally.scores != [
            "flux"
        ]:
            raise ValueError(
                "V1.13 spectrum tally must use the "
                "flux score."
            )

        if (
            self.direct_response_tally.scores
            != [
                "flux",
            ]
        ):
            raise ValueError(
                "V1.13 direct-response tally must use "
                "the flux score."
            )

        if (
            self.spectrum_tally.estimator
            != "tracklength"
        ):
            raise ValueError(
                "V1.13 spectrum tally must use the "
                "track-length estimator."
            )

        if (
            self.direct_response_tally.estimator
            != "tracklength"
        ):
            raise ValueError(
                "V1.13 direct-response tally must use "
                "the track-length estimator."
            )

        if len(self.tallies) != 2:
            raise ValueError(
                "V1.13 benchmark model must contain "
                "exactly two tallies."
            )

        if (
            self.spectrum_energy_filter.num_bins
            <= 0
        ):
            raise ValueError(
                "V1.13 spectrum tally must contain "
                "at least one energy bin."
            )

        if (
            self.air_kerma_response_filter.num_bins
            != 1
        ):
            raise ValueError(
                "OpenMC EnergyFunctionFilter must "
                "contain exactly one tally bin."
            )


def create_v113_spectrum_tally(
    openmc_module: Any,
    evaluation_cell_filter: Any,
    photon_particle_filter: Any,
    settings_profile: OpenMCSettings,
) -> tuple[Any, Any]:
    # Create the energy-resolved evaluation-shell photon-flux tally.

    spectrum_energy_filter = (
        openmc_module.EnergyFilter(
            settings_profile
            .energy_bin_boundaries_ev,
            filter_id=(
                SPECTRUM_ENERGY_FILTER_ID
            ),
        )
    )

    spectrum_tally = (
        openmc_module.Tally(
            tally_id=SPECTRUM_TALLY_ID,
            name=SPECTRUM_TALLY_NAME,
        )
    )

    spectrum_tally.filters = [
        evaluation_cell_filter,
        photon_particle_filter,
        spectrum_energy_filter,
    ]

    spectrum_tally.scores = [
        "flux",
    ]

    spectrum_tally.estimator = (
        "tracklength"
    )

    return (
        spectrum_tally,
        spectrum_energy_filter,
    )


def create_v113_direct_response_tally(
    openmc_module: Any,
    evaluation_cell_filter: Any,
    photon_particle_filter: Any,
    response_function: (
        OpenMCAirKermaResponseFunction
    ),
) -> tuple[Any, Any]:
    # Create the authoritative direct dry-air collision-air-kerma tally.
    #
    # The EnergyFunctionFilter applies the response coefficient continuously
    # at each incident photon energy rather than approximating the response
    # with one coefficient per spectrum bin.

    air_kerma_response_filter = (
        openmc_module.EnergyFunctionFilter(
            energy=(
                response_function.energy_ev
            ),
            y=(
                response_function
                .response_coefficients_gy_cm2_per_photon
            ),
            interpolation=(
                response_function.interpolation
            ),
            filter_id=(
                AIR_KERMA_RESPONSE_FILTER_ID
            ),
        )
    )

    direct_response_tally = (
        openmc_module.Tally(
            tally_id=(
                DIRECT_RESPONSE_TALLY_ID
            ),
            name=(
                DIRECT_RESPONSE_TALLY_NAME
            ),
        )
    )

    direct_response_tally.filters = [
        evaluation_cell_filter,
        photon_particle_filter,
        air_kerma_response_filter,
    ]

    direct_response_tally.scores = [
        "flux",
    ]

    direct_response_tally.estimator = (
        "tracklength"
    )

    return (
        direct_response_tally,
        air_kerma_response_filter,
    )


def attach_v113_benchmark_tallies(
    model_build_result: (
        OpenMCModelBuildResult
    ),
    settings_profile: OpenMCSettings,
    response_function: (
        OpenMCAirKermaResponseFunction
        | None
    ) = None,
) -> OpenMCTallyBuildResult:
    # Attach the complete V1.13 tally set to an existing OpenMC model.

    openmc_module = load_openmc_module()

    if response_function is None:
        response_function = (
            create_openmc_dry_air_response_function()
        )

    validate_response_function_covers_openmc_settings(
        response_function=response_function,
        settings=settings_profile,
    )

    evaluation_cell_filter = (
        openmc_module.CellFilter(
            model_build_result
            .evaluation_shell_cell,
            filter_id=(
                EVALUATION_CELL_FILTER_ID
            ),
        )
    )

    photon_particle_filter = (
        openmc_module.ParticleFilter(
            "photon",
            filter_id=(
                PHOTON_PARTICLE_FILTER_ID
            ),
        )
    )

    (
        spectrum_tally,
        spectrum_energy_filter,
    ) = create_v113_spectrum_tally(
        openmc_module=openmc_module,
        evaluation_cell_filter=(
            evaluation_cell_filter
        ),
        photon_particle_filter=(
            photon_particle_filter
        ),
        settings_profile=(
            settings_profile
        ),
    )

    (
        direct_response_tally,
        air_kerma_response_filter,
    ) = create_v113_direct_response_tally(
        openmc_module=openmc_module,
        evaluation_cell_filter=(
            evaluation_cell_filter
        ),
        photon_particle_filter=(
            photon_particle_filter
        ),
        response_function=(
            response_function
        ),
    )

    tallies = openmc_module.Tallies(
        [
            spectrum_tally,
            direct_response_tally,
        ]
    )

    model_build_result.model.tallies = (
        tallies
    )

    return OpenMCTallyBuildResult(
        model_build_result=(
            model_build_result
        ),
        tallies=tallies,
        spectrum_tally=(
            spectrum_tally
        ),
        direct_response_tally=(
            direct_response_tally
        ),
        evaluation_cell_filter=(
            evaluation_cell_filter
        ),
        photon_particle_filter=(
            photon_particle_filter
        ),
        spectrum_energy_filter=(
            spectrum_energy_filter
        ),
        air_kerma_response_filter=(
            air_kerma_response_filter
        ),
        response_function=(
            response_function
        ),
    )