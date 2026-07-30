# Target and minimum-thickness result models.
#
# Target classes define the response requirement for a shielding
# design without performing any transport calculations.
#
# AirKermaRateTarget and AirKermaMinimumThicknessResult use explicit,
# unit-labeled V1.12 collision-air-kerma quantities.
#
# MinimumThicknessResult retains historical field names such as
# final_flux for compatibility with V1.07 through V1.11.

from dataclasses import dataclass

from air_response_models import (
    SourceAirKermaResult,
)
from models import Material
from unit_conversions import (
    convert_gy_per_s_to_microgy_per_h,
    convert_microgy_per_h_to_gy_per_s,
)


@dataclass
class TransmissionTarget:
    # Target final shield transmission as a fraction.
    # Example: 0.01 means 1% transmission.
    target_transmission: float

    def __post_init__(self):
        if self.target_transmission <= 0:
            raise ValueError("Target transmission must be greater than zero.")

        if self.target_transmission > 1:
            raise ValueError("Target transmission cannot be greater than 1.")


@dataclass
class ReductionFactorTarget:
    # Target reduction factor for the selected photon response.
    #
    # Example:
    #   1000 means the final response must be no more than
    #   one-thousandth of the unshielded response.

    reduction_factor: float

    def __post_init__(self):
        if self.reduction_factor < 1:
            raise ValueError("Reduction factor must be greater than or equal to 1.")


@dataclass
class FluxTarget:
    # Target uncollided photon fluence rate in photons/cm^2/s.
    #
    # The class name is retained for backward compatibility.
    target_flux: float

    def __post_init__(self):
        if self.target_flux <= 0:
            raise ValueError("Target flux must be greater than zero.")


@dataclass
class AirKermaRateTarget:
    # Target collision air-kerma rate at the evaluation location.
    #
    # The user-facing input unit is µGy/h because it is practical for
    # shielding-design scenarios.
    #
    # The deterministic solver converts the target to Gy/s, which is the
    # canonical internal air-kerma-rate unit used by V1.12.

    target_air_kerma_rate_microgy_per_h: float

    def __post_init__(self) -> None:
        if self.target_air_kerma_rate_microgy_per_h <= 0:
            raise ValueError(
                "Target air-kerma rate must be greater than zero."
            )

    @property
    def target_air_kerma_rate_gy_per_s(self) -> float:
        return convert_microgy_per_h_to_gy_per_s(
            self.target_air_kerma_rate_microgy_per_h
        )


@dataclass
class MinimumThicknessResult:
    # Result of an uncollided photon-fluence
    # minimum-thickness calculation.
    #
    # final_flux:
    #   Final uncollided photon fluence rate at the
    #   detector in photons/cm^2/s.
    #
    # final_transmission:
    #   Final uncollided response divided by the
    #   corresponding unshielded response.

    material: Material
    required_thickness: float
    final_flux: float
    final_transmission: float
    target_description: str
    warnings: list[str]

    calculation_mode: str = (
        "Uncollided photon-fluence "
        "minimum thickness design"
    )

    def __post_init__(self):
        if self.required_thickness < 0:
            raise ValueError(
                "Required thickness cannot be negative."
            )

        if self.final_flux < 0:
            raise ValueError(
                "Final flux cannot be negative."
            )

        if self.final_transmission < 0:
            raise ValueError(
                "Final transmission cannot be negative."
            )

        if self.final_transmission > 1:
            raise ValueError(
                "Final transmission cannot be greater than 1."
            )

        if self.target_description.strip() == "":
            raise ValueError(
                "Target description cannot be empty."
            )

        if self.calculation_mode.strip() == "":
            raise ValueError(
                "Calculation mode cannot be empty."
            )

@dataclass
class AirKermaMinimumThicknessResult:
    # Result from an air-kerma-rate minimum-thickness calculation.
    #
    # This model is intentionally separate from MinimumThicknessResult.
    #
    # MinimumThicknessResult:
    #   photon-fluence-oriented legacy result
    #
    # AirKermaMinimumThicknessResult:
    #   explicitly stores a collision air-kerma response
    #
    # final_source_response preserves the complete line-by-line result,
    # including:
    #   - photon energies
    #   - photon emission rates
    #   - uncollided photon fluence rates
    #   - dry-air response coefficients
    #   - uncollided collision air-kerma rates
    #   - G-P buildup factors
    #   - buildup-adjusted responses
    #   - warnings and coefficient provenance

    material: Material
    required_thickness: float
    final_source_response: SourceAirKermaResult
    final_response_ratio: float
    target_description: str
    warnings: list[str]

    calculation_mode: str = (
        "Uncollided collision air-kerma minimum thickness design"
    )

    buildup_used: bool = False

    def __post_init__(self) -> None:
        if self.required_thickness < 0:
            raise ValueError(
                "Required thickness cannot be negative."
            )

        if self.final_response_ratio < 0:
            raise ValueError(
                "Final air-kerma response ratio cannot be negative."
            )

        if self.target_description.strip() == "":
            raise ValueError(
                "Target description cannot be empty."
            )

        if self.calculation_mode.strip() == "":
            raise ValueError(
                "Calculation mode cannot be empty."
            )

        if self.buildup_used:
            if (
                self.final_source_response.buildup_status
                != "applied"
            ):
                raise ValueError(
                    "A buildup-aware air-kerma design requires "
                    "an applied source buildup result."
                )

            if (
                self
                .final_source_response
                .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
                is None
            ):
                raise ValueError(
                    "A buildup-aware air-kerma design requires "
                    "a buildup-adjusted source response."
                )

        elif (
            self.final_source_response.buildup_status
            == "applied"
        ):
            raise ValueError(
                "An applied source buildup result must be marked "
                "as buildup_used in the design result."
            )

    @property
    def final_uncollided_collision_air_kerma_rate_gy_per_s(
        self,
    ) -> float:
        return (
            self
            .final_source_response
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        )

    @property
    def final_buildup_adjusted_collision_air_kerma_rate_gy_per_s(
        self,
    ) -> float | None:
        return (
            self
            .final_source_response
            .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

    @property
    def final_air_kerma_rate_gy_per_s(
        self,
    ) -> float:
        # Return the exact response used to evaluate the design target.

        if not self.buildup_used:
            return (
                self
                .final_uncollided_collision_air_kerma_rate_gy_per_s
            )

        adjusted_rate = (
            self
            .final_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_rate is None:
            # The dataclass validation already prevents this state.
            # This explicit check keeps the property type-safe.
            raise ValueError(
                "Buildup-adjusted air-kerma rate is unavailable."
            )

        return adjusted_rate

    @property
    def final_air_kerma_rate_microgy_per_h(
        self,
    ) -> float:
        return convert_gy_per_s_to_microgy_per_h(
            self.final_air_kerma_rate_gy_per_s
        )