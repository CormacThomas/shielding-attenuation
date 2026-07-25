# Command-line entry point.
#
# main.py coordinates input, calculation workflows, and output.
# Physics and optimization logic remain in their dedicated modules.


from constraint_optimizer import (
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from design_optimizer import (
    compare_materials_for_air_kerma_target,
    compare_materials_for_target,
)
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
    get_response_quantity_from_user,
)
from material_library import get_material_library
from output import (
    print_air_kerma_material_comparison_result,
    print_air_kerma_minimum_thickness_result,
    print_material_comparison_result,
    print_minimum_thickness_result,
    print_optimized_design_result,
    print_source_air_kerma_result,
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
    calculate_air_kerma_minimum_thickness,
)
from optimization_models import OptimizationWeights
from air_response import (
    calculate_source_air_kerma_result,
)
from target_models import AirKermaRateTarget

def run_fixed_thickness_mode() -> None:
    # Calculate the response through user-specified shielding layers.
    #
    # Collision air kerma:
    #   Uses dry-air response-coefficient folding and may optionally
    #   use compatible G-P exposure buildup.
    #
    # Photon fluence rate:
    #   Uses the narrow-beam photon-number pathway. Exposure buildup
    #   is intentionally not applied to this response quantity.

    materials = get_material_library()

    source = get_source_from_user()

    response_quantity = (
        get_response_quantity_from_user()
    )

    layers = get_layers_from_user(
        materials
    )

    detector_distance = (
        get_detector_distance_from_user()
    )

    if (
        response_quantity
        == "collision_air_kerma_rate"
    ):
        apply_buildup = (
            get_apply_buildup_from_user()
        )

        air_kerma_result = (
            calculate_source_air_kerma_result(
                source=source,
                layers=layers,
                detector_distance_cm=(
                    detector_distance
                ),
                apply_buildup=apply_buildup,
            )
        )

        print_source_air_kerma_result(
            air_kerma_result
        )

        return

    if (
        response_quantity
        != "photon_fluence_rate"
    ):
        raise ValueError(
            "Unsupported response quantity."
        )

    # The revised photon pathway is explicitly uncollided.
    # G-P exposure buildup is not applied to photon-number fluence.
    if isinstance(
        source,
        ManualPhotonSource,
    ):
        photon_result = (
            calculate_manual_source_result(
                source,
                layers,
                detector_distance,
                apply_buildup=False,
            )
        )

    elif isinstance(
        source,
        IsotopeSource,
    ):
        photon_result = (
            calculate_isotope_source_result(
                source,
                layers,
                detector_distance,
                apply_buildup=False,
            )
        )

    else:
        raise ValueError(
            "Unsupported source type."
        )

    print_source_results(
        photon_result
    )


def run_minimum_thickness_mode() -> None:
    # Calculate the minimum homogeneous shielding thickness required
    # to satisfy the selected response target.

    materials = get_material_library()

    source = get_source_from_user()

    response_quantity = (
        get_response_quantity_from_user()
    )

    material = get_single_material_from_user(
        materials
    )

    detector_distance = (
        get_detector_distance_from_user()
    )

    target = get_target_from_user(
        response_quantity
    )

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    if (
        response_quantity
        == "collision_air_kerma_rate"
    ):
        if not isinstance(
            target,
            AirKermaRateTarget,
        ):
            raise ValueError(
                "Collision-air-kerma response requires "
                "an air-kerma-rate target."
            )

        apply_buildup = (
            get_apply_buildup_from_user()
        )

        air_kerma_result = (
            calculate_air_kerma_minimum_thickness(
                source=source,
                material=material,
                detector_distance_cm=(
                    detector_distance
                ),
                target=target,
                max_thickness_cm=(
                    calculation_max_thickness
                ),
                apply_buildup=apply_buildup,
            )
        )

        print_air_kerma_minimum_thickness_result(
            air_kerma_result
        )

        return

    if (
        response_quantity
        != "photon_fluence_rate"
    ):
        raise ValueError(
            "Unsupported response quantity."
        )

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        raise ValueError(
            "Photon-fluence-rate response cannot use "
            "an air-kerma-rate target."
        )

    # The revised photon pathway is explicitly uncollided.
    if isinstance(
        source,
        ManualPhotonSource,
    ):
        photon_result = (
            calculate_manual_minimum_thickness(
                source,
                material,
                detector_distance,
                target,
                calculation_max_thickness,
                apply_buildup=False,
            )
        )

    elif isinstance(
        source,
        IsotopeSource,
    ):
        photon_result = (
            calculate_isotope_minimum_thickness(
                source,
                material,
                detector_distance,
                target,
                calculation_max_thickness,
                apply_buildup=False,
            )
        )

    else:
        raise ValueError(
            "Unsupported source type."
        )

    print_minimum_thickness_result(
        photon_result
    )

def run_material_comparison_mode() -> None:
    # Compare the required homogeneous shielding thickness across
    # multiple candidate materials.
    #
    # Collision air kerma:
    #   Uses the V1.12 response-specific solver and may optionally
    #   require compatible G-P exposure buildup.
    #
    # Photon fluence rate:
    #   Uses the legacy target models through an explicitly
    #   uncollided photon-number pathway.

    materials = get_material_library()

    source = get_source_from_user()

    response_quantity = (
        get_response_quantity_from_user()
    )

    selected_materials = (
        get_materials_for_comparison_from_user(
            materials
        )
    )

    detector_distance = (
        get_detector_distance_from_user()
    )

    target = get_target_from_user(
        response_quantity
    )

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    if (
        response_quantity
        == "collision_air_kerma_rate"
    ):
        if not isinstance(
            target,
            AirKermaRateTarget,
        ):
            raise ValueError(
                "Collision-air-kerma comparison requires "
                "an air-kerma-rate target."
            )

        apply_buildup = (
            get_apply_buildup_from_user()
        )

        air_kerma_result = (
            compare_materials_for_air_kerma_target(
                source=source,
                materials=selected_materials,
                detector_distance_cm=(
                    detector_distance
                ),
                target=target,
                max_thickness_cm=(
                    calculation_max_thickness
                ),
                apply_buildup=apply_buildup,
            )
        )

        print_air_kerma_material_comparison_result(
            air_kerma_result
        )

        return

    if (
        response_quantity
        != "photon_fluence_rate"
    ):
        raise ValueError(
            "Unsupported response quantity."
        )

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        raise ValueError(
            "Photon-fluence-rate comparison cannot use "
            "an air-kerma-rate target."
        )

    photon_result = compare_materials_for_target(
        source=source,
        materials=selected_materials,
        detector_distance=detector_distance,
        target=target,
        max_thickness=calculation_max_thickness,
        apply_buildup=False,
    )

    print_material_comparison_result(
        photon_result
    )


def run_material_optimization_mode() -> None:
    # Optimize homogeneous shielding-material selection using
    # response-specific deterministic calculations and shared
    # engineering constraints.
    #
    # Collision air kerma:
    #   Uses the V1.12 air-kerma optimizer and may optionally
    #   require compatible G-P exposure buildup.
    #
    # Photon fluence rate:
    #   Uses the legacy target models through an explicitly
    #   uncollided photon-number pathway.

    materials = get_material_library()

    source = get_source_from_user()

    response_quantity = (
        get_response_quantity_from_user()
    )

    selected_materials = (
        get_materials_for_comparison_from_user(
            materials
        )
    )

    detector_distance = (
        get_detector_distance_from_user()
    )

    target = get_target_from_user(
        response_quantity
    )

    calculation_max_thickness = (
        get_optional_calculation_max_thickness_from_user()
    )

    constraints = (
        get_design_constraints_from_user()
    )

    optimization_mode = (
        get_optimization_mode_from_user()
    )

    weights: OptimizationWeights | None = None

    if optimization_mode == "balanced":
        weights = (
            get_optimization_weights_from_user()
        )

    if (
        response_quantity
        == "collision_air_kerma_rate"
    ):
        if not isinstance(
            target,
            AirKermaRateTarget,
        ):
            raise ValueError(
                "Collision-air-kerma optimization "
                "requires an air-kerma-rate target."
            )

        apply_buildup = (
            get_apply_buildup_from_user()
        )

        air_kerma_result = (
            optimize_air_kerma_material_selection(
                source=source,
                materials=selected_materials,
                detector_distance=(
                    detector_distance
                ),
                target=target,
                constraints=constraints,
                optimization_mode=(
                    optimization_mode
                ),
                weights=weights,
                calculation_max_thickness=(
                    calculation_max_thickness
                ),
                apply_buildup=apply_buildup,
            )
        )

        print_optimized_design_result(
            air_kerma_result
        )

        return

    if (
        response_quantity
        != "photon_fluence_rate"
    ):
        raise ValueError(
            "Unsupported response quantity."
        )

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        raise ValueError(
            "Photon-fluence-rate optimization "
            "cannot use an air-kerma-rate target."
        )

    photon_result = optimize_material_selection(
        source=source,
        materials=selected_materials,
        detector_distance=detector_distance,
        target=target,
        constraints=constraints,
        optimization_mode=optimization_mode,
        weights=weights,
        calculation_max_thickness=(
            calculation_max_thickness
        ),
        apply_buildup=False,
    )

    print_optimized_design_result(
        photon_result
    )


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