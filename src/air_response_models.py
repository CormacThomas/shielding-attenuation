# V1.12 collision-air-kerma response models.
#
# This module defines explicit, unit-labeled coefficient,
# photon-line, and source-level response data.
#
# Attenuation, coefficient interpolation, response folding,
# and buildup calculations are implemented in air_response.py.


from dataclasses import dataclass, field
from typing import Literal


BuildupStatus = Literal[
    "not_requested",
    "applied",
    "unavailable",
    "fallback",
]


VALID_BUILDUP_STATUSES = (
    "not_requested",
    "applied",
    "unavailable",
    "fallback",
)


@dataclass(frozen=True)
class AirKermaCoefficient:
    # One dry-air mass energy-absorption coefficient.
    #
    # photon_energy_mev:
    #   Photon energy in MeV.
    #
    # mu_en_over_rho_cm2_per_g:
    #   Dry-air mass energy-absorption coefficient in cm²/g.
    #
    # source:
    #   Human-readable identification of the coefficient dataset.

    photon_energy_mev: float
    mu_en_over_rho_cm2_per_g: float
    source: str

    def __post_init__(self) -> None:
        if self.photon_energy_mev <= 0:
            raise ValueError(
                "Air-kerma coefficient energy must be greater than zero."
            )

        if self.mu_en_over_rho_cm2_per_g <= 0:
            raise ValueError(
                "Dry-air mass energy-absorption coefficient "
                "must be greater than zero."
            )

        if self.source.strip() == "":
            raise ValueError(
                "Air-kerma coefficient source cannot be empty."
            )


@dataclass
class PhotonLineAirKermaResult:
    # Collision air-kerma result for one emitted photon line.
    #
    # Canonical internal air-kerma-rate unit:
    #   Gy/s
    #
    # Photon fluence-rate unit:
    #   photons/cm²/s
    #
    # Energy fluence-rate unit:
    #   MeV/cm²/s

    photon_energy_mev: float
    emission_intensity: float
    photon_rate_per_s: float

    uncollided_photon_fluence_rate_per_cm2_s: float
    energy_fluence_rate_mev_per_cm2_s: float

    air_mu_en_over_rho_cm2_per_g: float
    uncollided_collision_air_kerma_rate_gy_per_s: float

    calculation_method: str
    coefficient_source: str
    buildup_status: BuildupStatus

    buildup_factor: float | None = None

    buildup_adjusted_collision_air_kerma_rate_gy_per_s: (
        float | None
    ) = None

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if self.photon_energy_mev <= 0:
            raise ValueError(
                "Photon-line energy must be greater than zero."
            )

        if self.emission_intensity < 0:
            raise ValueError(
                "Photon-line emission intensity cannot be negative."
            )

        if self.photon_rate_per_s < 0:
            raise ValueError(
                "Photon emission rate cannot be negative."
            )

        if (
            self.uncollided_photon_fluence_rate_per_cm2_s
            < 0
        ):
            raise ValueError(
                "Uncollided photon fluence rate cannot be negative."
            )

        if self.energy_fluence_rate_mev_per_cm2_s < 0:
            raise ValueError(
                "Energy fluence rate cannot be negative."
            )

        if self.air_mu_en_over_rho_cm2_per_g <= 0:
            raise ValueError(
                "Dry-air mass energy-absorption coefficient "
                "must be greater than zero."
            )

        if (
            self.uncollided_collision_air_kerma_rate_gy_per_s
            < 0
        ):
            raise ValueError(
                "Uncollided collision air-kerma rate "
                "cannot be negative."
            )

        if self.calculation_method.strip() == "":
            raise ValueError(
                "Calculation method cannot be empty."
            )

        if self.coefficient_source.strip() == "":
            raise ValueError(
                "Coefficient source cannot be empty."
            )

        if self.buildup_status not in VALID_BUILDUP_STATUSES:
            raise ValueError(
                "Unsupported buildup status."
            )

        if (
            self.buildup_factor is not None
            and self.buildup_factor < 1
        ):
            raise ValueError(
                "Buildup factor cannot be less than one."
            )

        adjusted_rate = (
            self
            .buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_rate is not None and adjusted_rate < 0:
            raise ValueError(
                "Buildup-adjusted collision air-kerma rate "
                "cannot be negative."
            )

        if self.buildup_status == "applied":
            if self.buildup_factor is None:
                raise ValueError(
                    "Applied buildup requires a buildup factor."
                )

            if adjusted_rate is None:
                raise ValueError(
                    "Applied buildup requires a buildup-adjusted "
                    "collision air-kerma rate."
                )

            if (
                adjusted_rate
                < self.uncollided_collision_air_kerma_rate_gy_per_s
            ):
                raise ValueError(
                    "Buildup-adjusted collision air-kerma rate "
                    "cannot be less than the uncollided rate."
                )

        else:
            if self.buildup_factor is not None:
                raise ValueError(
                    "A buildup factor may only be stored when "
                    "buildup status is applied."
                )

            if adjusted_rate is not None:
                raise ValueError(
                    "A buildup-adjusted response may only be stored "
                    "when buildup status is applied."
                )


@dataclass
class SourceAirKermaResult:
    # Complete collision air-kerma result for a manual or isotope source.
    #
    # A source-level buildup-adjusted result is available only when buildup
    # was successfully applied to every contributing photon line.

    source_name: str
    activity_bq: float | None
    line_results: list[PhotonLineAirKermaResult]

    total_uncollided_photon_fluence_rate_per_cm2_s: float
    total_uncollided_collision_air_kerma_rate_gy_per_s: float

    buildup_status: BuildupStatus

    total_buildup_adjusted_collision_air_kerma_rate_gy_per_s: (
        float | None
    ) = None

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if self.source_name.strip() == "":
            raise ValueError(
                "Source name cannot be empty."
            )

        if self.activity_bq is not None and self.activity_bq < 0:
            raise ValueError(
                "Source activity cannot be negative."
            )

        if len(self.line_results) == 0:
            raise ValueError(
                "Source air-kerma result must contain "
                "at least one photon-line result."
            )

        if (
            self.total_uncollided_photon_fluence_rate_per_cm2_s
            < 0
        ):
            raise ValueError(
                "Total uncollided photon fluence rate "
                "cannot be negative."
            )

        if (
            self.total_uncollided_collision_air_kerma_rate_gy_per_s
            < 0
        ):
            raise ValueError(
                "Total uncollided collision air-kerma rate "
                "cannot be negative."
            )

        if self.buildup_status not in VALID_BUILDUP_STATUSES:
            raise ValueError(
                "Unsupported source buildup status."
            )

        adjusted_total = (
            self
            .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_total is not None and adjusted_total < 0:
            raise ValueError(
                "Total buildup-adjusted collision air-kerma rate "
                "cannot be negative."
            )

        if self.buildup_status == "applied":
            if adjusted_total is None:
                raise ValueError(
                    "Applied source buildup requires a total "
                    "buildup-adjusted collision air-kerma rate."
                )

            if (
                adjusted_total
                < self.total_uncollided_collision_air_kerma_rate_gy_per_s
            ):
                raise ValueError(
                    "Total buildup-adjusted collision air-kerma rate "
                    "cannot be less than the total uncollided rate."
                )

        elif adjusted_total is not None:
            raise ValueError(
                "A total buildup-adjusted response may only be stored "
                "when source buildup status is applied."
            )