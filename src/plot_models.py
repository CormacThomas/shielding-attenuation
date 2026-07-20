# V1.10 plotting data models.
#
# This module defines the structured data used by engineering plots.
# It does not perform shielding calculations, optimization, Pareto analysis,
# or Matplotlib rendering.
#
# Separating plot data from rendering allows:
#   - numerical plot data to be validated without comparing image pixels
#   - the same data to be rendered by the CLI, a future GUI, or reports
#   - deterministic and future OpenMC data to share common structures


from dataclasses import dataclass, field
from typing import Literal

from optimization_models import (
    DesignConstraints,
    OptimizationMode,
    OptimizationStatus,
)


BuildupDisplay = Literal[
    "YES",
    "FALLBACK",
    "NO",
    "UNAVAILABLE",
]


VALID_BUILDUP_DISPLAYS = (
    "YES",
    "FALLBACK",
    "NO",
    "UNAVAILABLE",
)


ConstraintCheckStatus = Literal[
    "PASS",
    "FAIL",
    "INACTIVE",
    "UNAVAILABLE",
]


VALID_CONSTRAINT_CHECK_STATUSES = (
    "PASS",
    "FAIL",
    "INACTIVE",
    "UNAVAILABLE",
)


@dataclass(frozen=True)
class MaterialPlotPoint:
    # Plot-ready information for one optimized material candidate.
    #
    # Successful V1.09 candidates contain thickness, mass, and relative-cost
    # values. Failed candidates preserve their failure reason but do not receive
    # invented numerical plotting values.

    material_key: str
    material_name: str
    optimization_status: OptimizationStatus

    required_thickness_cm: float | None
    mass_per_area_g_per_cm2: float | None
    relative_cost_index_per_area: float | None
    optimization_score: float | None

    buildup_display: BuildupDisplay
    is_selected: bool

    rejection_reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    failure_reason: str | None = None

    def __post_init__(self):
        if self.material_key.strip() == "":
            raise ValueError(
                "Plot material key cannot be empty."
            )

        if self.material_name.strip() == "":
            raise ValueError(
                "Plot material name cannot be empty."
            )

        if self.buildup_display not in VALID_BUILDUP_DISPLAYS:
            raise ValueError(
                "Buildup display must be YES, FALLBACK, NO, or UNAVAILABLE."
            )

        if self.is_selected:
            if self.optimization_status != "ELIGIBLE":
                raise ValueError(
                    "Only an eligible candidate can be marked as selected."
                )

        if self.optimization_status == "FAILED":
            # The underlying shielding calculation did not produce
            # a usable numerical design.

            if len(self.rejection_reasons) > 0:
                raise ValueError(
                    "Failed plot candidates cannot store engineering "
                    "rejection reasons."
                )

            if self.required_thickness_cm is not None:
                raise ValueError(
                    "Failed plot candidates cannot store required thickness."
                )

            if self.mass_per_area_g_per_cm2 is not None:
                raise ValueError(
                    "Failed plot candidates cannot store mass per area."
                )

            if self.relative_cost_index_per_area is not None:
                raise ValueError(
                    "Failed plot candidates cannot store relative cost."
                )

            if self.optimization_score is not None:
                raise ValueError(
                    "Failed plot candidates cannot store an optimization score."
                )

            if (
                self.failure_reason is None
                or self.failure_reason.strip() == ""
            ):
                raise ValueError(
                    "Failed plot candidates must preserve a failure reason."
                )

        elif self.optimization_status == "ELIGIBLE":
            # The calculation succeeded and the candidate satisfies
            # every active engineering constraint.

            if self.required_thickness_cm is None:
                raise ValueError(
                    "Eligible plot candidates must store required thickness."
                )

            if self.mass_per_area_g_per_cm2 is None:
                raise ValueError(
                    "Eligible plot candidates must store mass per area."
                )

            if self.relative_cost_index_per_area is None:
                raise ValueError(
                    "Eligible plot candidates must store relative cost."
                )

            if self.required_thickness_cm < 0:
                raise ValueError(
                    "Required thickness cannot be negative."
                )

            if self.mass_per_area_g_per_cm2 < 0:
                raise ValueError(
                    "Mass per area cannot be negative."
                )

            if self.relative_cost_index_per_area < 0:
                raise ValueError(
                    "Relative cost index per area cannot be negative."
                )

            if len(self.rejection_reasons) > 0:
                raise ValueError(
                    "Eligible plot candidates cannot store rejection reasons."
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "Eligible plot candidates cannot store a failure reason."
                )

            if self.optimization_score is None:
                raise ValueError(
                    "Eligible plot candidates must store an optimization score."
                )

        elif self.optimization_status == "REJECTED":
            # The calculation succeeded, but the candidate violated
            # at least one engineering constraint.

            if self.required_thickness_cm is None:
                raise ValueError(
                    "Rejected plot candidates must store required thickness."
                )

            if self.mass_per_area_g_per_cm2 is None:
                raise ValueError(
                    "Rejected plot candidates must store mass per area."
                )

            if self.relative_cost_index_per_area is None:
                raise ValueError(
                    "Rejected plot candidates must store relative cost."
                )

            if self.required_thickness_cm < 0:
                raise ValueError(
                    "Required thickness cannot be negative."
                )

            if self.mass_per_area_g_per_cm2 < 0:
                raise ValueError(
                    "Mass per area cannot be negative."
                )

            if self.relative_cost_index_per_area < 0:
                raise ValueError(
                    "Relative cost index per area cannot be negative."
                )

            if len(self.rejection_reasons) == 0:
                raise ValueError(
                    "Rejected plot candidates must preserve at least one "
                    "engineering rejection reason."
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "Rejected plot candidates cannot store a failure reason."
                )

            if self.optimization_score is not None:
                raise ValueError(
                    "Rejected plot candidates cannot store an optimization score."
                )

        else:
            raise ValueError(
                "Optimization status must be ELIGIBLE, REJECTED, or FAILED."
            )


@dataclass(frozen=True)
class OptimizationPlotData:
    # Complete plot-ready representation of one V1.09 optimization result.
    #
    # This object contains the engineering metadata needed by the bar charts
    # and Pareto plot without making the rendering functions depend directly
    # on the optimizer implementation.

    target_description: str
    optimization_mode: OptimizationMode
    buildup_requested: bool
    constraints: DesignConstraints

    candidates: tuple[MaterialPlotPoint, ...]

    selected_material_key: str | None = None
    selection_reason: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.target_description.strip() == "":
            raise ValueError(
                "Optimization plot target description cannot be empty."
            )

        if len(self.candidates) == 0:
            raise ValueError(
                "Optimization plot data must contain at least one candidate."
            )

        selected_candidates = [
            candidate
            for candidate in self.candidates
            if candidate.is_selected
        ]

        if self.selected_material_key is None:
            if len(selected_candidates) != 0:
                raise ValueError(
                    "No candidate can be selected when selected_material_key "
                    "is None."
                )

            if self.selection_reason is not None:
                raise ValueError(
                    "Selection reason must be None when no material is selected."
                )

        else:
            if len(selected_candidates) != 1:
                raise ValueError(
                    "Exactly one plot candidate must be marked as selected."
                )

            selected_candidate = selected_candidates[0]

            if (
                selected_candidate.material_key
                != self.selected_material_key
            ):
                raise ValueError(
                    "Selected material key does not match the selected candidate."
                )

            if (
                self.selection_reason is None
                or self.selection_reason.strip() == ""
            ):
                raise ValueError(
                    "A selected material must include a selection reason."
                )


@dataclass(frozen=True)
class MaterialFeasibilityRow:
    # Metric-specific feasibility information for one material.
    #
    # These fields answer three independent questions:
    #   - Does the material satisfy the thickness constraint?
    #   - Does the material satisfy the mass constraint?
    #   - Does the material satisfy the relative-cost constraint?
    #
    # optimization_status remains the overall V1.09 result.

    material_key: str
    material_name: str

    thickness_status: ConstraintCheckStatus
    mass_status: ConstraintCheckStatus
    cost_status: ConstraintCheckStatus

    optimization_status: OptimizationStatus
    is_selected: bool

    def __post_init__(self):
        if self.material_key.strip() == "":
            raise ValueError(
                "Feasibility-row material key cannot be empty."
            )

        if self.material_name.strip() == "":
            raise ValueError(
                "Feasibility-row material name cannot be empty."
            )

        constraint_statuses = (
            self.thickness_status,
            self.mass_status,
            self.cost_status,
        )

        for status in constraint_statuses:
            if status not in VALID_CONSTRAINT_CHECK_STATUSES:
                raise ValueError(
                    "Constraint status must be PASS, FAIL, "
                    "INACTIVE, or UNAVAILABLE."
                )

        if self.is_selected:
            if self.optimization_status != "ELIGIBLE":
                raise ValueError(
                    "Only an eligible feasibility row can be selected."
                )

        if self.optimization_status == "FAILED":
            if any(
                status != "UNAVAILABLE"
                for status in constraint_statuses
            ):
                raise ValueError(
                    "Failed candidates must have UNAVAILABLE status "
                    "for every constraint check."
                )

        else:
            if any(
                status == "UNAVAILABLE"
                for status in constraint_statuses
            ):
                raise ValueError(
                    "Successfully calculated candidates cannot have "
                    "UNAVAILABLE constraint checks."
                )

        if self.optimization_status == "ELIGIBLE":
            if any(
                status == "FAIL"
                for status in constraint_statuses
            ):
                raise ValueError(
                    "Eligible candidates cannot fail an active constraint."
                )

        if self.optimization_status == "REJECTED":
            if not any(
                status == "FAIL"
                for status in constraint_statuses
            ):
                raise ValueError(
                    "Rejected candidates must fail at least one "
                    "active constraint."
                )


@dataclass(frozen=True)
class ParetoPoint:
    # One successful design on a thickness-versus-mass tradeoff plot.
    #
    # Failed candidates are not represented as Pareto points because they do
    # not have valid thickness and mass values.

    material_key: str
    material_name: str

    thickness_cm: float
    mass_per_area_g_per_cm2: float

    optimization_status: OptimizationStatus
    is_selected: bool
    is_pareto_optimal: bool

    def __post_init__(self):
        if self.material_key.strip() == "":
            raise ValueError("Pareto material key cannot be empty.")

        if self.material_name.strip() == "":
            raise ValueError("Pareto material name cannot be empty.")

        if self.optimization_status == "FAILED":
            raise ValueError(
                "Failed candidates cannot be represented as Pareto points."
            )

        if self.thickness_cm < 0:
            raise ValueError(
                "Pareto thickness cannot be negative."
            )

        if self.mass_per_area_g_per_cm2 < 0:
            raise ValueError(
                "Pareto mass per area cannot be negative."
            )

        if self.is_selected:
            if self.optimization_status != "ELIGIBLE":
                raise ValueError(
                    "Only an eligible Pareto point can be selected."
                )


@dataclass(frozen=True)
class ResponseCurvePoint:
    # Detector flux values evaluated at one shielding thickness.
    #
    # buildup_corrected_flux may be None when:
    #   - buildup was not requested
    #   - the material has no G-P coefficients
    #   - the energy is outside the G-P coefficient range
    #   - the thickness exceeds the valid 40-MFP limit
    #
    # None must remain visible as unavailable data. It must not be replaced
    # with an extrapolated or narrow-beam value.

    thickness_cm: float
    uncollided_flux: float
    buildup_corrected_flux: float | None = None

    def __post_init__(self):
        if self.thickness_cm < 0:
            raise ValueError(
                "Response-curve thickness cannot be negative."
            )

        if self.uncollided_flux < 0:
            raise ValueError(
                "Response-curve uncollided flux cannot be negative."
            )

        if (
            self.buildup_corrected_flux is not None
            and self.buildup_corrected_flux < 0
        ):
            raise ValueError(
                "Response-curve buildup-corrected flux cannot be negative."
            )


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

    buildup_requested: bool

    target_flux: float | None = None
    required_thickness_cm: float | None = None

    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.backend_name.strip() == "":
            raise ValueError(
                "Response-curve backend name cannot be empty."
            )

        if self.quantity_name.strip() == "":
            raise ValueError(
                "Response-curve quantity name cannot be empty."
            )

        if self.quantity_units.strip() == "":
            raise ValueError(
                "Response-curve quantity units cannot be empty."
            )

        if self.source_name.strip() == "":
            raise ValueError(
                "Response-curve source name cannot be empty."
            )

        if self.material_key.strip() == "":
            raise ValueError(
                "Response-curve material key cannot be empty."
            )

        if self.material_name.strip() == "":
            raise ValueError(
                "Response-curve material name cannot be empty."
            )

        if self.detector_distance_cm <= 0:
            raise ValueError(
                "Response-curve detector distance must be greater than zero."
            )

        if len(self.points) == 0:
            raise ValueError(
                "Response curve must contain at least one point."
            )

        previous_thickness = None

        for point in self.points:
            if previous_thickness is not None:
                if point.thickness_cm <= previous_thickness:
                    raise ValueError(
                        "Response-curve thickness values must be strictly "
                        "increasing."
                    )

            previous_thickness = point.thickness_cm

        if not self.buildup_requested:
            for point in self.points:
                if point.buildup_corrected_flux is not None:
                    raise ValueError(
                        "Buildup-corrected curve values cannot be stored when "
                        "buildup was not requested."
                    )

        if self.target_flux is not None:
            if self.target_flux <= 0:
                raise ValueError(
                    "Response-curve target flux must be greater than zero."
                )

        if self.required_thickness_cm is not None:
            if self.required_thickness_cm < 0:
                raise ValueError(
                    "Required thickness cannot be negative."
                )

            minimum_thickness = self.points[0].thickness_cm
            maximum_thickness = self.points[-1].thickness_cm

            if (
                self.required_thickness_cm < minimum_thickness
                or self.required_thickness_cm > maximum_thickness
            ):
                raise ValueError(
                    "Required thickness must fall inside the plotted "
                    "thickness range."
                )