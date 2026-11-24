"""Sampled response curves and their source, material, and target metadata."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResponseCurvePoint:
    # Uncollided photon fluence rate evaluated at one
    # shielding thickness.

    thickness_cm: float
    uncollided_flux: float

    def __post_init__(self):
        if self.thickness_cm < 0:
            raise ValueError("Response-curve thickness cannot be negative.")

        if self.uncollided_flux < 0:
            raise ValueError("Response-curve uncollided flux cannot be negative.")


@dataclass(frozen=True)
class ResponseCurveResult:
    # Complete deterministic or future Monte Carlo response-curve dataset.
    #
    # V1.10 initially uses:
    #   backend_name = "Deterministic"
    #   quantity_name = "Photon flux"
    #   quantity_units = "photons/cm^2/s"
    #
    # The generic metadata allows future OpenMC curve data to use the same
    # plotting layer without rewriting Matplotlib functions.

    backend_name: str
    quantity_name: str
    quantity_units: str

    source_name: str
    material_key: str
    material_name: str

    detector_distance_cm: float
    points: tuple[ResponseCurvePoint, ...]

    target_flux: float | None = None
    required_thickness_cm: float | None = None

    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.backend_name.strip() == "":
            raise ValueError("Response-curve backend name cannot be empty.")

        if self.quantity_name.strip() == "":
            raise ValueError("Response-curve quantity name cannot be empty.")

        if self.quantity_units.strip() == "":
            raise ValueError("Response-curve quantity units cannot be empty.")

        if self.source_name.strip() == "":
            raise ValueError("Response-curve source name cannot be empty.")

        if self.material_key.strip() == "":
            raise ValueError("Response-curve material key cannot be empty.")

        if self.material_name.strip() == "":
            raise ValueError("Response-curve material name cannot be empty.")

        if self.detector_distance_cm <= 0:
            raise ValueError(
                "Response-curve detector distance must be greater than zero."
            )

        if len(self.points) == 0:
            raise ValueError("Response curve must contain at least one point.")

        previous_thickness = None

        for point in self.points:
            if previous_thickness is not None:
                if point.thickness_cm <= previous_thickness:
                    raise ValueError(
                        "Response-curve thickness values must be strictly increasing."
                    )

            previous_thickness = point.thickness_cm

        if self.target_flux is not None:
            if self.target_flux <= 0:
                raise ValueError(
                    "Response-curve target flux must be greater than zero."
                )

        if self.required_thickness_cm is not None:
            if self.required_thickness_cm < 0:
                raise ValueError("Required thickness cannot be negative.")

            minimum_thickness = self.points[0].thickness_cm
            maximum_thickness = self.points[-1].thickness_cm

            if (
                self.required_thickness_cm < minimum_thickness
                or self.required_thickness_cm > maximum_thickness
            ):
                raise ValueError(
                    "Required thickness must fall inside the plotted thickness range."
                )
