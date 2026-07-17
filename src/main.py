# Command-line entry point.
#
# main.py coordinates input, calculation workflows, and output.
# Physics and optimization logic remain in their dedicated modules.


from constraint_optimizer import optimize_material_selection
from design_optimizer import compare_materials_for_target
from input_handler import (
    get_apply_buildup_from_user,
    get_calculation_mode_from_user,
    get_design_constraints_from_user,
    get_detector_distance_from_user,
    get_layers_from_user,
    get_materials_for_comparison_from_user,
    get_optimization_mode_from_user,
    get_optimization_weights_from_user,
    get_optional_calculation_max_thickness_from_user,
    get_single_material_from_user,
    get_source_from_user,
    get_target_from_user,
)
from material_library import get_material_library
from output import (
    print_material_comparison_result,
    print_minimum_thickness_result,
    print_optimized_design_result,
    print_source_results,
)
from source_calculator import (
    calculate_isotope_source_result,
    calculate_manual_source_result,
)
from source_models import IsotopeSource, ManualPhotonSource
from thickness_calculator import (
    calculate_isotope_minimum_thickness,
    calculate_manual_minimum_thickness,
)
from optimization_models import OptimizationWeights


def run_fixed_thickness_mode() -> None:
    materials = get_material_library()

    source = get_source_from_user()
    layers = get_layers_from_user(materials)
    detector_distance = get_detector_distance_from_user()
    apply_buildup = get_apply_buildup_from_user()

    if isinstance(source, ManualPhotonSource):
        result = calculate_manual_source_result(
            source,
            layers,
            detector_distance,
            apply_buildup,
        )

    elif isinstance(source, IsotopeSource):
        result = calculate_isotope_source_result(
            source,
            layers,
            detector_distance,
            apply_buildup,
        )

    else:
        raise ValueError("Unsupported source type.")

    print_source_results(result)


def run_minimum_thickness_mode() -> None:
    materials = get_material_library()

    source = get_source_from_user()
    material = get_single_material_from_user(materials)
    detector_distance = get_detector_distance_from_user()
    target = get_target_from_user()

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    apply_buildup = get_apply_buildup_from_user()

    if isinstance(source, ManualPhotonSource):
        result = calculate_manual_minimum_thickness(
            source,
            material,
            detector_distance,
            target,
            calculation_max_thickness,
            apply_buildup=apply_buildup,
        )

    elif isinstance(source, IsotopeSource):
        result = calculate_isotope_minimum_thickness(
            source,
            material,
            detector_distance,
            target,
            calculation_max_thickness,
            apply_buildup=apply_buildup,
        )

    else:
        raise ValueError("Unsupported source type.")

    print_minimum_thickness_result(result)


def run_material_comparison_mode() -> None:
    materials = get_material_library()

    source = get_source_from_user()

    selected_materials = (
        get_materials_for_comparison_from_user(materials)
    )

    detector_distance = get_detector_distance_from_user()
    target = get_target_from_user()

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    apply_buildup = get_apply_buildup_from_user()

    result = compare_materials_for_target(
        source=source,
        materials=selected_materials,
        detector_distance=detector_distance,
        target=target,
        max_thickness=calculation_max_thickness,
        apply_buildup=apply_buildup,
    )

    print_material_comparison_result(result)


def run_material_optimization_mode() -> None:
    # V1.09 workflow:
    #
    # 1. Calculate required thickness for each material.
    # 2. Calculate mass and relative-cost metrics.
    # 3. Apply engineering constraints.
    # 4. Rank eligible candidates.
    # 5. Select and explain the best design.

    materials = get_material_library()

    source = get_source_from_user()

    selected_materials = (
        get_materials_for_comparison_from_user(materials)
    )

    detector_distance = get_detector_distance_from_user()
    target = get_target_from_user()

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    constraints = get_design_constraints_from_user()
    optimization_mode = get_optimization_mode_from_user()

    weights: OptimizationWeights | None = None

    if optimization_mode == "balanced":
        weights = get_optimization_weights_from_user()

    apply_buildup = get_apply_buildup_from_user()

    result = optimize_material_selection(
        source=source,
        materials=selected_materials,
        detector_distance=detector_distance,
        target=target,
        constraints=constraints,
        optimization_mode=optimization_mode,
        weights=weights,
        calculation_max_thickness=calculation_max_thickness,
        apply_buildup=apply_buildup,
    )

    print_optimized_design_result(result)


def main() -> None:
    calculation_mode = get_calculation_mode_from_user()

    if calculation_mode == "fixed_thickness":
        run_fixed_thickness_mode()

    elif calculation_mode == "minimum_thickness":
        run_minimum_thickness_mode()

    elif calculation_mode == "material_comparison":
        run_material_comparison_mode()

    elif calculation_mode == "material_optimization":
        run_material_optimization_mode()

    else:
        raise ValueError("Unsupported calculation mode.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")