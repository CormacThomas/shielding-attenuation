# Target and minimum-thickness result models.
#
# Target classes describe what the shielding design must achieve.
# They are intentionally separate from the calculator logic so future versions
# can add new target types without rewriting the physics engine.
#
# MinimumThicknessResult stores the output of a target-driven design calculation.
# The final_flux field is the value used to check the target:
#   - narrow-beam mode: final_flux is uncollided flux
#   - buildup-aware mode: final_flux is buildup-corrected flux


from dataclasses import dataclass
from models import Material


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
    # Target reduction factor.
    # Example: 1000 means final flux should be 1000 times lower than unshielded flux.
    reduction_factor: float

    def __post_init__(self):
        if self.reduction_factor < 1:
            raise ValueError("Reduction factor must be greater than or equal to 1.")


@dataclass
class FluxTarget:
    # Target detector flux in photons/cm^2/s.
    target_flux: float

    def __post_init__(self):
        if self.target_flux <= 0:
            raise ValueError("Target flux must be greater than zero.")


@dataclass
class MinimumThicknessResult:
    # Result from a minimum shielding thickness calculation.
    # final_flux is the flux used to check the target.
    # In narrow-beam mode, final_flux is the uncollided flux.
    # In buildup-aware mode, final_flux is the buildup-corrected flux.
    # final_transmission is the final_flux divided by the unshielded flux.
    material: Material
    required_thickness: float
    final_flux: float
    final_transmission: float
    target_description: str
    warnings: list[str]
    calculation_mode: str = "Narrow-beam minimum thickness design"
    final_uncollided_flux: float | None = None
    final_buildup_corrected_flux: float | None = None
    buildup_used: bool = False

    def __post_init__(self):
        if self.required_thickness < 0:
            raise ValueError("Required thickness cannot be negative.")

        if self.final_flux < 0:
            raise ValueError("Final flux cannot be negative.")

        if self.final_transmission < 0:
            raise ValueError("Final transmission cannot be negative.")

        if self.final_transmission > 1:
            raise ValueError("Final transmission cannot be greater than 1.")

        if self.calculation_mode.strip() == "":
            raise ValueError("Calculation mode cannot be empty.")

        if self.final_uncollided_flux is None:
            self.final_uncollided_flux = self.final_flux

        if self.final_uncollided_flux < 0:
            raise ValueError("Final uncollided flux cannot be negative.")

        if (
            self.final_buildup_corrected_flux is not None
            and self.final_buildup_corrected_flux < 0
        ):
            raise ValueError("Final buildup-corrected flux cannot be negative.")

        if self.buildup_used and self.final_buildup_corrected_flux is None:
            raise ValueError(
                "Buildup-corrected flux must be stored when buildup_used is True."
            )