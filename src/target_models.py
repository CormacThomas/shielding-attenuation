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
    # Target uncollided detector flux in photons/cm^2/s.
    target_flux: float

    def __post_init__(self):
        if self.target_flux <= 0:
            raise ValueError("Target flux must be greater than zero.")


@dataclass
class MinimumThicknessResult:
    # Result from a minimum shielding thickness calculation.
    # required_thickness is the minimum material thickness needed to satisfy the target.
    # final_flux is the calculated uncollided flux at that thickness.
    # final_transmission is the total narrow-beam transmission at that thickness.
    material: Material
    required_thickness: float
    final_flux: float
    final_transmission: float
    target_description: str
    warnings: list[str]

    def __post_init__(self):
        if self.required_thickness < 0:
            raise ValueError("Required thickness cannot be negative.")

        if self.final_flux < 0:
            raise ValueError("Final flux cannot be negative.")

        if self.final_transmission < 0:
            raise ValueError("Final transmission cannot be negative.")

        if self.final_transmission > 1:
            raise ValueError("Final transmission cannot be greater than 1.")