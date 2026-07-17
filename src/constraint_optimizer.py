# V1.09 constraint-based material optimizer.
#
# V1.08 calculates required shielding thickness for each material.
# This module:
#   - calculates mass per unit area
#   - calculates relative cost index per unit area
#   - applies hard engineering constraints
#   - separates eligible, rejected, and failed materials
#   - ranks eligible materials
#   - selects the best design
#
# Important distinction:
#
# calculation_max_thickness:
#   Upper search bound used by the V1.07/V1.08 thickness solver.
#
# constraints.max_thickness_cm:
#   Engineering design requirement applied after a valid thickness is found.
#
# A candidate that cannot be calculated is FAILED.
# A candidate that calculates successfully but violates a design requirement
# is REJECTED.


from design_optimizer import (
    MaterialDesignCandidate,
    compare_materials_for_target,
)
from material_cost_library import (
    MaterialCostData,
    RELATIVE_COST_BASIS_DESCRIPTION,
    get_material_cost_library,
)
from models import Material
from optimization_models import (
    DesignConstraints,
    OptimizedDesignResult,
    OptimizedMaterialCandidate,
    OptimizationMode,
    OptimizationWeights,
    VALID_OPTIMIZATION_MODES,
)
from source_models import IsotopeSource, ManualPhotonSource
from target_models import (
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)


Source = ManualPhotonSource | IsotopeSource
Target = TransmissionTarget | ReductionFactorTarget | FluxTarget


def calculate_mass_per_area(
    density_g_per_cm3: float,
    thickness_cm: float,
) -> float:
    # mass / area = density * thickness
    #
    # g/cm^3 * cm = g/cm^2

    if density_g_per_cm3 <= 0:
        raise ValueError(
            "Material density must be greater than zero."
        )

    if thickness_cm < 0:
        raise ValueError(
            "Shielding thickness cannot be negative."
        )

    return density_g_per_cm3 * thickness_cm


def calculate_relative_cost_index_per_area(
    mass_per_area_g_per_cm2: float,
    relative_cost_index: float,
) -> float:
    # Comparative cost metric:
    #
    # relative cost index per area
    #     = mass per area * relative material cost index
    #
    # This is not a monetary unit.

    if mass_per_area_g_per_cm2 < 0:
        raise ValueError(
            "Mass per area cannot be negative."
        )

    if relative_cost_index <= 0:
        raise ValueError(
            "Relative material cost index must be greater than zero."
        )

    return mass_per_area_g_per_cm2 * relative_cost_index


def get_required_thickness(
    candidate: MaterialDesignCandidate,
) -> float:
    if candidate.required_thickness is None:
        raise ValueError(
            f"Passing candidate for {candidate.material.name} "
            "is missing required thickness."
        )

    return candidate.required_thickness


def get_candidate_mass_per_area(
    candidate: OptimizedMaterialCandidate,
) -> float:
    if candidate.mass_per_area_g_per_cm2 is None:
        raise ValueError(
            f"Candidate for {candidate.base_candidate.material.name} "
            "is missing mass per area."
        )

    return candidate.mass_per_area_g_per_cm2


def get_candidate_relative_cost(
    candidate: OptimizedMaterialCandidate,
) -> float:
    if candidate.relative_cost_index_per_area is None:
        raise ValueError(
            f"Candidate for {candidate.base_candidate.material.name} "
            "is missing relative cost index per area."
        )

    return candidate.relative_cost_index_per_area


def get_candidate_score(
    candidate: OptimizedMaterialCandidate,
) -> float:
    if candidate.optimization_score is None:
        raise ValueError(
            f"Candidate for {candidate.base_candidate.material.name} "
            "is missing an optimization score."
        )

    return candidate.optimization_score


def create_optimized_candidate(
    base_candidate: MaterialDesignCandidate,
    constraints: DesignConstraints,
    cost_library: dict[str, MaterialCostData],
) -> OptimizedMaterialCandidate:
    # Convert one V1.08 candidate into a V1.09 candidate.

    if base_candidate.status == "FAILED":
        return OptimizedMaterialCandidate(
            base_candidate=base_candidate,
            optimization_status="FAILED",
        )

    required_thickness = get_required_thickness(base_candidate)

    material_key = base_candidate.material.key

    if material_key not in cost_library:
        raise ValueError(
            f"No relative cost data found for {base_candidate.material.name}."
        )

    relative_cost_index = (
        cost_library[material_key].relative_cost_index
    )

    mass_per_area = calculate_mass_per_area(
        base_candidate.material.density,
        required_thickness,
    )

    relative_cost_per_area = calculate_relative_cost_index_per_area(
        mass_per_area,
        relative_cost_index,
    )

    rejection_reasons = []

    if constraints.max_thickness_cm is not None:
        if required_thickness > constraints.max_thickness_cm:
            rejection_reasons.append(
                f"Required thickness {required_thickness:.6g} cm exceeds "
                f"the maximum allowed thickness "
                f"{constraints.max_thickness_cm:.6g} cm."
            )

    if constraints.max_mass_per_area_g_per_cm2 is not None:
        if (
            mass_per_area
            > constraints.max_mass_per_area_g_per_cm2
        ):
            rejection_reasons.append(
                f"Mass per area {mass_per_area:.6g} g/cm^2 exceeds "
                f"the maximum allowed mass per area "
                f"{constraints.max_mass_per_area_g_per_cm2:.6g} g/cm^2."
            )

    if constraints.max_relative_cost_index_per_area is not None:
        if (
            relative_cost_per_area
            > constraints.max_relative_cost_index_per_area
        ):
            rejection_reasons.append(
                f"Relative cost index per area "
                f"{relative_cost_per_area:.6g} exceeds the maximum "
                f"allowed value "
                f"{constraints.max_relative_cost_index_per_area:.6g}."
            )

    if len(rejection_reasons) > 0:
        optimization_status = "REJECTED"
    else:
        optimization_status = "ELIGIBLE"

    return OptimizedMaterialCandidate(
        base_candidate=base_candidate,
        optimization_status=optimization_status,
        mass_per_area_g_per_cm2=mass_per_area,
        relative_cost_index_per_area=relative_cost_per_area,
        rejection_reasons=rejection_reasons,
    )


def normalize_value(
    value: float,
    minimum_value: float,
    maximum_value: float,
) -> float:
    # Min-max normalization:
    #
    # best value = 0
    # worst value = 1
    #
    # If every candidate has the same value, the normalized value is 0.

    if maximum_value < minimum_value:
        raise ValueError(
            "Normalization maximum cannot be less than minimum."
        )

    if value < minimum_value or value > maximum_value:
        raise ValueError(
            "Normalization value must be inside the supplied range."
        )

    if maximum_value == minimum_value:
        return 0.0

    return (
        (value - minimum_value)
        / (maximum_value - minimum_value)
    )


def assign_normalized_metrics(
    candidates: list[OptimizedMaterialCandidate],
) -> None:
    # Normalization is calculated using eligible candidates only.
    #
    # Rejected and failed candidates do not compete in the ranking.

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate.optimization_status == "ELIGIBLE"
    ]

    if len(eligible_candidates) == 0:
        return

    thickness_values = [
        get_required_thickness(candidate.base_candidate)
        for candidate in eligible_candidates
    ]

    mass_values = [
        get_candidate_mass_per_area(candidate)
        for candidate in eligible_candidates
    ]

    cost_values = [
        get_candidate_relative_cost(candidate)
        for candidate in eligible_candidates
    ]

    minimum_thickness = min(thickness_values)
    maximum_thickness = max(thickness_values)

    minimum_mass = min(mass_values)
    maximum_mass = max(mass_values)

    minimum_cost = min(cost_values)
    maximum_cost = max(cost_values)

    for candidate in eligible_candidates:
        candidate.normalized_thickness = normalize_value(
            get_required_thickness(candidate.base_candidate),
            minimum_thickness,
            maximum_thickness,
        )

        candidate.normalized_mass = normalize_value(
            get_candidate_mass_per_area(candidate),
            minimum_mass,
            maximum_mass,
        )

        candidate.normalized_relative_cost = normalize_value(
            get_candidate_relative_cost(candidate),
            minimum_cost,
            maximum_cost,
        )


def assign_optimization_scores(
    candidates: list[OptimizedMaterialCandidate],
    optimization_mode: OptimizationMode,
    weights: OptimizationWeights | None,
) -> None:
    if optimization_mode not in VALID_OPTIMIZATION_MODES:
        raise ValueError("Unsupported optimization mode.")

    if optimization_mode == "balanced" and weights is None:
        raise ValueError(
            "Balanced optimization requires optimization weights."
        )

    for candidate in candidates:
        if candidate.optimization_status != "ELIGIBLE":
            continue

        if optimization_mode == "minimum_thickness":
            candidate.optimization_score = get_required_thickness(
                candidate.base_candidate
            )

        elif optimization_mode == "minimum_mass":
            candidate.optimization_score = (
                get_candidate_mass_per_area(candidate)
            )

        elif optimization_mode == "minimum_cost":
            candidate.optimization_score = (
                get_candidate_relative_cost(candidate)
            )

        elif optimization_mode == "balanced":
            if weights is None:
                raise ValueError(
                    "Balanced optimization requires optimization weights."
                )

            if candidate.normalized_thickness is None:
                raise ValueError(
                    "Balanced candidate is missing normalized thickness."
                )

            if candidate.normalized_mass is None:
                raise ValueError(
                    "Balanced candidate is missing normalized mass."
                )

            if candidate.normalized_relative_cost is None:
                raise ValueError(
                    "Balanced candidate is missing normalized relative cost."
                )

            weighted_score = (
                weights.thickness_weight
                * candidate.normalized_thickness
                + weights.mass_weight
                * candidate.normalized_mass
                + weights.cost_weight
                * candidate.normalized_relative_cost
            )

            candidate.optimization_score = (
                weighted_score / weights.total_weight()
            )


def rank_eligible_candidates(
    candidates: list[OptimizedMaterialCandidate],
    optimization_mode: OptimizationMode,
) -> list[OptimizedMaterialCandidate]:
    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate.optimization_status == "ELIGIBLE"
    ]

    if optimization_mode == "minimum_thickness":
        eligible_candidates.sort(
            key=lambda candidate: (
                get_required_thickness(candidate.base_candidate),
                get_candidate_mass_per_area(candidate),
                get_candidate_relative_cost(candidate),
                candidate.base_candidate.material.key,
            )
        )

    elif optimization_mode == "minimum_mass":
        eligible_candidates.sort(
            key=lambda candidate: (
                get_candidate_mass_per_area(candidate),
                get_required_thickness(candidate.base_candidate),
                get_candidate_relative_cost(candidate),
                candidate.base_candidate.material.key,
            )
        )

    elif optimization_mode == "minimum_cost":
        eligible_candidates.sort(
            key=lambda candidate: (
                get_candidate_relative_cost(candidate),
                get_candidate_mass_per_area(candidate),
                get_required_thickness(candidate.base_candidate),
                candidate.base_candidate.material.key,
            )
        )

    elif optimization_mode == "balanced":
        eligible_candidates.sort(
            key=lambda candidate: (
                get_candidate_score(candidate),
                get_required_thickness(candidate.base_candidate),
                get_candidate_mass_per_area(candidate),
                get_candidate_relative_cost(candidate),
                candidate.base_candidate.material.key,
            )
        )

    else:
        raise ValueError("Unsupported optimization mode.")

    return eligible_candidates


def get_selection_reason(
    best_candidate: OptimizedMaterialCandidate,
    optimization_mode: OptimizationMode,
    eligible_count: int,
) -> str:
    material_name = best_candidate.base_candidate.material.name

    if optimization_mode == "minimum_thickness":
        thickness = get_required_thickness(
            best_candidate.base_candidate
        )

        return (
            f"{material_name} was selected because it has the lowest "
            f"required thickness ({thickness:.6g} cm) among "
            f"{eligible_count} eligible candidates."
        )

    if optimization_mode == "minimum_mass":
        mass_per_area = get_candidate_mass_per_area(
            best_candidate
        )

        return (
            f"{material_name} was selected because it has the lowest "
            f"mass per area ({mass_per_area:.6g} g/cm^2) among "
            f"{eligible_count} eligible candidates."
        )

    if optimization_mode == "minimum_cost":
        relative_cost = get_candidate_relative_cost(
            best_candidate
        )

        return (
            f"{material_name} was selected because it has the lowest "
            f"relative cost index per area ({relative_cost:.6g}) among "
            f"{eligible_count} eligible candidates."
        )

    if optimization_mode == "balanced":
        score = get_candidate_score(best_candidate)

        return (
            f"{material_name} was selected because it has the lowest "
            f"balanced normalized score ({score:.6g}) among "
            f"{eligible_count} eligible candidates."
        )

    raise ValueError("Unsupported optimization mode.")


def optimize_material_selection(
    source: Source,
    materials: list[Material],
    detector_distance: float,
    target: Target,
    constraints: DesignConstraints,
    optimization_mode: OptimizationMode,
    weights: OptimizationWeights | None = None,
    calculation_max_thickness: float | None = None,
    apply_buildup: bool = False,
    cost_library: dict[str, MaterialCostData] | None = None,
) -> OptimizedDesignResult:
    # Main V1.09 workflow.
    #
    # 1. Run the V1.08 material comparison.
    # 2. Calculate engineering metrics.
    # 3. Apply hard constraints.
    # 4. Normalize eligible candidate metrics.
    # 5. Assign optimization scores.
    # 6. Rank eligible candidates.
    # 7. Select the best design.

    if optimization_mode not in VALID_OPTIMIZATION_MODES:
        raise ValueError("Unsupported optimization mode.")

    if optimization_mode == "balanced":
        if weights is None:
            raise ValueError(
                "Balanced optimization requires optimization weights."
            )
    elif weights is not None:
        raise ValueError(
            "Optimization weights should only be supplied for balanced mode."
        )

    if cost_library is None:
        cost_library = get_material_cost_library()

    comparison_result = compare_materials_for_target(
        source=source,
        materials=materials,
        detector_distance=detector_distance,
        target=target,
        max_thickness=calculation_max_thickness,
        apply_buildup=apply_buildup,
    )

    optimized_candidates = []

    for base_candidate in comparison_result.candidates:
        optimized_candidate = create_optimized_candidate(
            base_candidate,
            constraints,
            cost_library,
        )

        optimized_candidates.append(optimized_candidate)

    assign_normalized_metrics(optimized_candidates)

    assign_optimization_scores(
        optimized_candidates,
        optimization_mode,
        weights,
    )

    ranked_eligible_candidates = rank_eligible_candidates(
        optimized_candidates,
        optimization_mode,
    )

    rejected_candidates = [
        candidate
        for candidate in optimized_candidates
        if candidate.optimization_status == "REJECTED"
    ]

    failed_candidates = [
        candidate
        for candidate in optimized_candidates
        if candidate.optimization_status == "FAILED"
    ]

    rejected_candidates.sort(
        key=lambda candidate: candidate.base_candidate.material.name
    )

    failed_candidates.sort(
        key=lambda candidate: candidate.base_candidate.material.name
    )

    all_candidates = (
        ranked_eligible_candidates
        + rejected_candidates
        + failed_candidates
    )

    warnings = []

    uses_relative_cost = (
        optimization_mode in ["minimum_cost", "balanced"]
        or constraints.max_relative_cost_index_per_area is not None
    )

    if uses_relative_cost:
        warnings.append(RELATIVE_COST_BASIS_DESCRIPTION)

    if len(ranked_eligible_candidates) == 0:
        best_candidate = None
        selection_reason = None

        warnings.append(
            "No material candidate satisfied all active design constraints."
        )

    else:
        best_candidate = ranked_eligible_candidates[0]

        selection_reason = get_selection_reason(
            best_candidate,
            optimization_mode,
            len(ranked_eligible_candidates),
        )

    return OptimizedDesignResult(
        target_description=comparison_result.target_description,
        apply_buildup=comparison_result.apply_buildup,
        optimization_mode=optimization_mode,
        constraints=constraints,
        all_candidates=all_candidates,
        best_candidate=best_candidate,
        weights=weights,
        selection_reason=selection_reason,
        warnings=warnings,
    )