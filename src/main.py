# Command-line entry point.
#
# main.py should only coordinate user input, calculation mode selection,
# calculation function calls, and result printing.
#
# It should not contain physics formulas or validation logic.
# The actual calculation work is delegated to:
#   - source_calculator.py for fixed-thickness source calculations
#   - thickness_calculator.py for one-material minimum-thickness calculations
#   - design_optimizer.py for material comparison calculations


from input_handler import (
    get_apply_buildup_from_user,
    get_calculation_mode_from_user,
    get_detector_distance_from_user,
    get_layers_from_user,
    get_optional_max_thickness_from_user,
    get_single_material_from_user,
    get_source_from_user,
    get_target_from_user,
    get_materials_for_comparison_from_user,
)
from material_library import get_material_library
from output import (
    print_material_comparison_result,
    print_minimum_thickness_result,
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
from design_optimizer import compare_materials_for_target


def run_material_comparison_mode() -> None:
    # V1.08 workflow:
    # Compare required shielding thickness across multiple candidate materials
    # for one source, detector distance, target, and buildup setting.
    materials = get_material_library()

    source = get_source_from_user()
    selected_materials = get_materials_for_comparison_from_user(materials)
    detector_distance = get_detector_distance_from_user()
    target = get_target_from_user()
    max_thickness = get_optional_max_thickness_from_user()
    apply_buildup = get_apply_buildup_from_user()

    result = compare_materials_for_target(
        source,
        selected_materials,
        detector_distance,
        target,
        max_thickness,
        apply_buildup,
    )

    print_material_comparison_result(result)


def run_fixed_thickness_mode() -> None:
    # Fixed-thickness workflow:
    # User supplies actual shielding layers and the simulator calculates
    # detector flux through that chosen shield.
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
    # V1.07 workflow:
    # User selects one shielding material and a design target. The simulator
    # calculates the minimum thickness required to satisfy that target.
    materials = get_material_library()

    source = get_source_from_user()
    material = get_single_material_from_user(materials)
    detector_distance = get_detector_distance_from_user()
    target = get_target_from_user()
    max_thickness = get_optional_max_thickness_from_user()
    apply_buildup = get_apply_buildup_from_user()

    if isinstance(source, ManualPhotonSource):
        result = calculate_manual_minimum_thickness(
            source,
            material,
            detector_distance,
            target,
            max_thickness,
            apply_buildup=apply_buildup,
        )

    elif isinstance(source, IsotopeSource):
        result = calculate_isotope_minimum_thickness(
            source,
            material,
            detector_distance,
            target,
            max_thickness,
            apply_buildup=apply_buildup,
        )

    else:
        raise ValueError("Unsupported source type.")

    print_minimum_thickness_result(result)


def main() -> None:
    # Top-level CLI router.
    # Keep this function simple: choose the mode, then delegate to the
    # corresponding workflow function.
    calculation_mode = get_calculation_mode_from_user()

    if calculation_mode == "fixed_thickness":
        run_fixed_thickness_mode()

    elif calculation_mode == "minimum_thickness":
        run_minimum_thickness_mode()

    elif calculation_mode == "material_comparison":
        run_material_comparison_mode()

    else:
        raise ValueError("Unsupported calculation mode.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")