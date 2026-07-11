from input_handler import (
    get_apply_buildup_from_user,
    get_detector_distance_from_user,
    get_layers_from_user,
    get_source_from_user,
)
from material_library import get_material_library
from output import print_source_results
from source_calculator import (
    calculate_isotope_source_result,
    calculate_manual_source_result,
)
from source_models import IsotopeSource, ManualPhotonSource


def main() -> None:
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


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"\nError: {error}")