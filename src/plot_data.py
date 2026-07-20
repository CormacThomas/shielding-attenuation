# V1.10 optimization plot-data preparation.
#
# This module converts V1.09 optimization result objects into generic,
# plot-ready data.
#
# It also performs Pareto classification without importing Matplotlib.
# This allows the engineering logic to be validated independently from
# figure rendering.


from optimization_models import (
    OptimizedDesignResult,
    OptimizedMaterialCandidate,
)

from plot_models import (
    BuildupDisplay,
    ConstraintCheckStatus,
    MaterialFeasibilityRow,
    MaterialPlotPoint,
    OptimizationPlotData,
    ParetoPoint,
)


def get_candidate_buildup_display(
    candidate: OptimizedMaterialCandidate,
) -> BuildupDisplay:
    # Convert the underlying V1.08 buildup state into a plot label.
    #
    # YES:
    #   G-P buildup was successfully used.
    #
    # FALLBACK:
    #   Buildup was requested, but the candidate used narrow-beam fallback
    #   and preserved one or more warnings.
    #
    # NO:
    #   Buildup was not used and no fallback warning exists.
    #
    # UNAVAILABLE:
    #   The lower-level material calculation failed.

    base_candidate = candidate.base_candidate

    if base_candidate.status == "FAILED":
        return "UNAVAILABLE"

    if base_candidate.buildup_used:
        return "YES"

    if len(base_candidate.warnings) > 0:
        return "FALLBACK"

    return "NO"


def is_selected_candidate(
    result: OptimizedDesignResult,
    candidate: OptimizedMaterialCandidate,
) -> bool:
    if result.best_candidate is None:
        return False

    selected_key = (
        result.best_candidate
        .base_candidate
        .material
        .key
    )

    candidate_key = candidate.base_candidate.material.key

    return candidate_key == selected_key


def create_material_plot_point(
    result: OptimizedDesignResult,
    candidate: OptimizedMaterialCandidate,
) -> MaterialPlotPoint:
    # Convert one V1.09 optimized candidate into a plot-ready point.

    base_candidate = candidate.base_candidate
    material = base_candidate.material

    if candidate.optimization_status == "FAILED":
        return MaterialPlotPoint(
            material_key=material.key,
            material_name=material.name,
            optimization_status="FAILED",
            required_thickness_cm=None,
            mass_per_area_g_per_cm2=None,
            relative_cost_index_per_area=None,
            optimization_score=None,
            buildup_display="UNAVAILABLE",
            is_selected=False,
            rejection_reasons=tuple(),
            warnings=tuple(base_candidate.warnings),
            failure_reason=base_candidate.failure_reason,
        )

    return MaterialPlotPoint(
        material_key=material.key,
        material_name=material.name,
        optimization_status=candidate.optimization_status,
        required_thickness_cm=base_candidate.required_thickness,
        mass_per_area_g_per_cm2=(
            candidate.mass_per_area_g_per_cm2
        ),
        relative_cost_index_per_area=(
            candidate.relative_cost_index_per_area
        ),
        optimization_score=candidate.optimization_score,
        buildup_display=get_candidate_buildup_display(candidate),
        is_selected=is_selected_candidate(result, candidate),
        rejection_reasons=tuple(candidate.rejection_reasons),
        warnings=tuple(base_candidate.warnings),
        failure_reason=None,
    )


def create_optimization_plot_data(
    result: OptimizedDesignResult,
) -> OptimizationPlotData:
    # Convert a complete V1.09 result into reusable plot data.

    candidate_points = tuple(
        create_material_plot_point(result, candidate)
        for candidate in result.all_candidates
    )

    selected_material_key = None

    if result.best_candidate is not None:
        selected_material_key = (
            result.best_candidate
            .base_candidate
            .material
            .key
        )

    return OptimizationPlotData(
        target_description=result.target_description,
        optimization_mode=result.optimization_mode,
        buildup_requested=result.apply_buildup,
        constraints=result.constraints,
        candidates=candidate_points,
        selected_material_key=selected_material_key,
        selection_reason=result.selection_reason,
        warnings=tuple(result.warnings),
    )


def get_successful_plot_candidates(
    plot_data: OptimizationPlotData,
) -> list[MaterialPlotPoint]:
    # Return candidates with valid numerical design results.
    #
    # This includes both ELIGIBLE and REJECTED candidates because both were
    # successfully calculated. FAILED candidates remain available in the
    # parent plot data for notes and captions.

    return [
        candidate
        for candidate in plot_data.candidates
        if candidate.optimization_status != "FAILED"
    ]


def evaluate_maximum_constraint(
    value: float | None,
    maximum_value: float | None,
) -> ConstraintCheckStatus:
    # Evaluate one numerical value against an optional upper limit.
    #
    # None value:
    #   The material calculation did not produce this metric.
    #
    # None maximum:
    #   The metric exists, but no engineering constraint is active.

    if value is None:
        return "UNAVAILABLE"

    if value < 0:
        raise ValueError(
            "Constraint-check values cannot be negative."
        )

    if maximum_value is None:
        return "INACTIVE"

    if maximum_value <= 0:
        raise ValueError(
            "Maximum constraint values must be greater than zero."
        )

    if value <= maximum_value:
        return "PASS"

    return "FAIL"


def create_material_feasibility_row(
    plot_data: OptimizationPlotData,
    candidate: MaterialPlotPoint,
) -> MaterialFeasibilityRow:
    # Convert one material plot point into independent constraint results.

    if candidate.optimization_status == "FAILED":
        return MaterialFeasibilityRow(
            material_key=candidate.material_key,
            material_name=candidate.material_name,
            thickness_status="UNAVAILABLE",
            mass_status="UNAVAILABLE",
            cost_status="UNAVAILABLE",
            optimization_status="FAILED",
            is_selected=False,
        )

    constraints = plot_data.constraints

    thickness_status = evaluate_maximum_constraint(
        candidate.required_thickness_cm,
        constraints.max_thickness_cm,
    )

    mass_status = evaluate_maximum_constraint(
        candidate.mass_per_area_g_per_cm2,
        constraints.max_mass_per_area_g_per_cm2,
    )

    cost_status = evaluate_maximum_constraint(
        candidate.relative_cost_index_per_area,
        constraints.max_relative_cost_index_per_area,
    )

    return MaterialFeasibilityRow(
        material_key=candidate.material_key,
        material_name=candidate.material_name,
        thickness_status=thickness_status,
        mass_status=mass_status,
        cost_status=cost_status,
        optimization_status=candidate.optimization_status,
        is_selected=candidate.is_selected,
    )


def create_constraint_feasibility_rows(
    plot_data: OptimizationPlotData,
) -> tuple[MaterialFeasibilityRow, ...]:
    # Preserve the optimizer's candidate order:
    # ranked eligible candidates first, followed by rejected and failed
    # candidates.

    return tuple(
        create_material_feasibility_row(
            plot_data,
            candidate,
        )
        for candidate in plot_data.candidates
    )


def dominates(
    first: MaterialPlotPoint,
    second: MaterialPlotPoint,
) -> bool:
    # Return True when the first design dominates the second design in the
    # thickness-versus-mass comparison.
    #
    # first dominates second when:
    #   - first is no thicker
    #   - first is no heavier per area
    #   - first is strictly better in at least one metric

    if first.required_thickness_cm is None:
        raise ValueError(
            "First Pareto candidate is missing required thickness."
        )

    if first.mass_per_area_g_per_cm2 is None:
        raise ValueError(
            "First Pareto candidate is missing mass per area."
        )

    if second.required_thickness_cm is None:
        raise ValueError(
            "Second Pareto candidate is missing required thickness."
        )

    if second.mass_per_area_g_per_cm2 is None:
        raise ValueError(
            "Second Pareto candidate is missing mass per area."
        )

    no_thicker = (
        first.required_thickness_cm
        <= second.required_thickness_cm
    )

    no_heavier = (
        first.mass_per_area_g_per_cm2
        <= second.mass_per_area_g_per_cm2
    )

    strictly_better = (
        first.required_thickness_cm
        < second.required_thickness_cm
        or first.mass_per_area_g_per_cm2
        < second.mass_per_area_g_per_cm2
    )

    return no_thicker and no_heavier and strictly_better


def is_pareto_optimal_candidate(
    candidate: MaterialPlotPoint,
    comparison_candidates: list[MaterialPlotPoint],
) -> bool:
    for other_candidate in comparison_candidates:
        if other_candidate.material_key == candidate.material_key:
            continue

        if dominates(other_candidate, candidate):
            return False

    return True


def create_pareto_points(
    plot_data: OptimizationPlotData,
    eligible_only: bool = True,
) -> list[ParetoPoint]:
    # Create thickness-versus-mass Pareto points.
    #
    # All successful designs are returned so the plot can still show rejected
    # candidates.
    #
    # By default, Pareto membership is calculated using eligible candidates
    # only. Rejected designs remain visible, but they do not define the
    # engineering-feasible Pareto front.
    #
    # Setting eligible_only=False calculates the mathematical front across
    # every successfully calculated design.

    successful_candidates = get_successful_plot_candidates(
        plot_data
    )

    if eligible_only:
        pareto_comparison_candidates = [
            candidate
            for candidate in successful_candidates
            if candidate.optimization_status == "ELIGIBLE"
        ]
    else:
        pareto_comparison_candidates = successful_candidates

    pareto_points = []

    for candidate in successful_candidates:
        if candidate.required_thickness_cm is None:
            raise ValueError(
                f"Candidate {candidate.material_name} is missing thickness."
            )

        if candidate.mass_per_area_g_per_cm2 is None:
            raise ValueError(
                f"Candidate {candidate.material_name} is missing mass per area."
            )

        is_on_pareto_front = False

        if candidate in pareto_comparison_candidates:
            is_on_pareto_front = is_pareto_optimal_candidate(
                candidate,
                pareto_comparison_candidates,
            )

        pareto_points.append(
            ParetoPoint(
                material_key=candidate.material_key,
                material_name=candidate.material_name,
                thickness_cm=candidate.required_thickness_cm,
                mass_per_area_g_per_cm2=(
                    candidate.mass_per_area_g_per_cm2
                ),
                optimization_status=candidate.optimization_status,
                is_selected=candidate.is_selected,
                is_pareto_optimal=is_on_pareto_front,
            )
        )

    pareto_points.sort(
        key=lambda point: (
            point.thickness_cm,
            point.mass_per_area_g_per_cm2,
            point.material_key,
        )
    )

    return pareto_points