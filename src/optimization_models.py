# V1.09 constraint-based optimization models.
#
# V1.08 calculates the shielding thickness required for each candidate material.
# V1.09 adds engineering metrics, design constraints, ranking, and selection.
#
# This module contains data models only. It does not perform shielding,
# mass, cost, constraint, or ranking calculations.


from dataclasses import dataclass, field
from typing import Literal

from design_optimizer import MaterialDesignCandidate


OptimizationStatus = Literal[
    "ELIGIBLE",
    "REJECTED",
    "FAILED",
]

OptimizationMode = Literal[
    "minimum_thickness",
    "minimum_mass",
    "minimum_cost",
    "balanced",
]


VALID_OPTIMIZATION_STATUSES = (
    "ELIGIBLE",
    "REJECTED",
    "FAILED",
)

VALID_OPTIMIZATION_MODES = (
    "minimum_thickness",
    "minimum_mass",
    "minimum_cost",
    "balanced",
)


@dataclass
class DesignConstraints:
    # Optional hard engineering constraints.
    #
    # These are applied after the V1.08 minimum-thickness solver has produced
    # a physically valid candidate.
    #
    # None means that a constraint is not active.

    max_thickness_cm: float | None = None
    max_mass_per_area_g_per_cm2: float | None = None
    max_relative_cost_index_per_area: float | None = None

    def __post_init__(self):
        if (
            self.max_thickness_cm is not None
            and self.max_thickness_cm <= 0
        ):
            raise ValueError(
                "Maximum design thickness must be greater than zero."
            )

        if (
            self.max_mass_per_area_g_per_cm2 is not None
            and self.max_mass_per_area_g_per_cm2 <= 0
        ):
            raise ValueError(
                "Maximum mass per area must be greater than zero."
            )

        if (
            self.max_relative_cost_index_per_area is not None
            and self.max_relative_cost_index_per_area <= 0
        ):
            raise ValueError(
                "Maximum relative cost index per area must be greater than zero."
            )


@dataclass
class OptimizationWeights:
    # Weights used for balanced optimization.
    #
    # Weights do not need to add to 1 because the balanced score is divided
    # by the total supplied weight.

    thickness_weight: float
    mass_weight: float
    cost_weight: float

    def __post_init__(self):
        if self.thickness_weight < 0:
            raise ValueError("Thickness weight cannot be negative.")

        if self.mass_weight < 0:
            raise ValueError("Mass weight cannot be negative.")

        if self.cost_weight < 0:
            raise ValueError("Cost weight cannot be negative.")

        if self.total_weight() == 0:
            raise ValueError(
                "At least one optimization weight must be greater than zero."
            )

    def total_weight(self) -> float:
        return (
            self.thickness_weight
            + self.mass_weight
            + self.cost_weight
        )


@dataclass
class OptimizedMaterialCandidate:
    # V1.09 engineering result for one V1.08 material candidate.
    #
    # base_candidate contains:
    #   - material
    #   - required thickness
    #   - final flux and transmission
    #   - buildup status
    #   - warnings or calculation failure
    #
    # This wrapper adds:
    #   - mass per area
    #   - relative cost index per area
    #   - engineering constraint status
    #   - normalized metrics
    #   - optimization score

    base_candidate: MaterialDesignCandidate
    optimization_status: OptimizationStatus

    mass_per_area_g_per_cm2: float | None = None
    relative_cost_index_per_area: float | None = None

    normalized_thickness: float | None = None
    normalized_mass: float | None = None
    normalized_relative_cost: float | None = None

    optimization_score: float | None = None
    rejection_reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.optimization_status not in VALID_OPTIMIZATION_STATUSES:
            raise ValueError(
                "Optimization status must be ELIGIBLE, REJECTED, or FAILED."
            )

        if self.base_candidate.status == "FAILED":
            if self.optimization_status != "FAILED":
                raise ValueError(
                    "A failed V1.08 candidate must remain FAILED in V1.09."
                )

            if self.mass_per_area_g_per_cm2 is not None:
                raise ValueError(
                    "Failed candidates cannot store mass-per-area results."
                )

            if self.relative_cost_index_per_area is not None:
                raise ValueError(
                    "Failed candidates cannot store relative-cost results."
                )

            if len(self.rejection_reasons) > 0:
                raise ValueError(
                    "Failed candidates use the original calculation failure "
                    "reason, not engineering rejection reasons."
                )

        if self.base_candidate.status == "PASS":
            if self.optimization_status == "FAILED":
                raise ValueError(
                    "A passing V1.08 candidate cannot become FAILED in V1.09."
                )

            if self.mass_per_area_g_per_cm2 is None:
                raise ValueError(
                    "Passing candidates must store mass per area."
                )

            if self.relative_cost_index_per_area is None:
                raise ValueError(
                    "Passing candidates must store relative cost per area."
                )

            if self.mass_per_area_g_per_cm2 < 0:
                raise ValueError("Mass per area cannot be negative.")

            if self.relative_cost_index_per_area < 0:
                raise ValueError(
                    "Relative cost index per area cannot be negative."
                )

        if self.optimization_status == "ELIGIBLE":
            if len(self.rejection_reasons) > 0:
                raise ValueError(
                    "Eligible candidates cannot have rejection reasons."
                )

        if self.optimization_status == "REJECTED":
            if len(self.rejection_reasons) == 0:
                raise ValueError(
                    "Rejected candidates must store at least one rejection reason."
                )

            if self.optimization_score is not None:
                raise ValueError(
                    "Rejected candidates cannot receive an optimization score."
                )

        normalized_values = [
            self.normalized_thickness,
            self.normalized_mass,
            self.normalized_relative_cost,
        ]

        for normalized_value in normalized_values:
            if normalized_value is not None:
                if normalized_value < 0 or normalized_value > 1:
                    raise ValueError(
                        "Normalized metrics must be between 0 and 1."
                    )

        if (
            self.optimization_score is not None
            and self.optimization_score < 0
        ):
            raise ValueError("Optimization score cannot be negative.")


@dataclass
class OptimizedDesignResult:
    # Complete V1.09 result.
    #
    # best_candidate is None when no material satisfies all active constraints.

    target_description: str
    apply_buildup: bool
    optimization_mode: OptimizationMode
    constraints: DesignConstraints
    all_candidates: list[OptimizedMaterialCandidate]

    best_candidate: OptimizedMaterialCandidate | None = None
    weights: OptimizationWeights | None = None
    selection_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.target_description.strip() == "":
            raise ValueError(
                "Optimization target description cannot be empty."
            )

        if self.optimization_mode not in VALID_OPTIMIZATION_MODES:
            raise ValueError(
                "Optimization mode must be minimum_thickness, minimum_mass, "
                "minimum_cost, or balanced."
            )

        if len(self.all_candidates) == 0:
            raise ValueError(
                "Optimization result must contain at least one candidate."
            )

        if self.optimization_mode == "balanced":
            if self.weights is None:
                raise ValueError(
                    "Balanced optimization requires optimization weights."
                )

        eligible_candidates = self.eligible_candidates()

        if len(eligible_candidates) > 0:
            if self.best_candidate is None:
                raise ValueError(
                    "A best candidate is required when eligible candidates exist."
                )

        if len(eligible_candidates) == 0:
            if self.best_candidate is not None:
                raise ValueError(
                    "Best candidate must be None when no candidate is eligible."
                )

        if self.best_candidate is not None:
            if self.best_candidate.optimization_status != "ELIGIBLE":
                raise ValueError(
                    "Best candidate must have ELIGIBLE status."
                )

            if self.best_candidate not in self.all_candidates:
                raise ValueError(
                    "Best candidate must appear in all_candidates."
                )

            if (
                self.selection_reason is None
                or self.selection_reason.strip() == ""
            ):
                raise ValueError(
                    "A selected candidate must include a selection reason."
                )

        if self.best_candidate is None:
            if self.selection_reason is not None:
                raise ValueError(
                    "Selection reason must be None when no candidate is selected."
                )

    def eligible_candidates(self) -> list[OptimizedMaterialCandidate]:
        return [
            candidate
            for candidate in self.all_candidates
            if candidate.optimization_status == "ELIGIBLE"
        ]

    def rejected_candidates(self) -> list[OptimizedMaterialCandidate]:
        return [
            candidate
            for candidate in self.all_candidates
            if candidate.optimization_status == "REJECTED"
        ]

    def failed_candidates(self) -> list[OptimizedMaterialCandidate]:
        return [
            candidate
            for candidate in self.all_candidates
            if candidate.optimization_status == "FAILED"
        ]