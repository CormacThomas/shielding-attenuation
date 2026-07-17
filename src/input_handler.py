# Command-line input utilities.
#
# This module gathers and converts user input for the CLI.
# It should not perform physics calculations.
#
# Current limitation:
# Invalid input generally raises ValueError and exits the program.
# Future CLI polish should replace this with repeated prompts.
from target_models import FluxTarget, ReductionFactorTarget, TransmissionTarget
from models import Layer, Material
from source_library import create_isotope_source, get_available_isotopes
from source_models import IsotopeSource, ManualPhotonSource
from unit_conversions import convert_activity_to_bq
from optimization_models import (
    DesignConstraints,
    OptimizationMode,
    OptimizationWeights,
)

def get_layers_from_user(materials: dict[str, Material]) -> list[Layer]:
    print("Available materials:")
    for material_name in materials:
        print(f"- {material_name}")
    
    num_layers = int(input("Enter number of shielding layers: "))

    layers = []
    for i in range(num_layers):
        print(f"\nLayer {i+1}")

        material_name = input("Enter material name: ").lower().strip()

        if material_name not in materials:
            raise ValueError("Material not found.")

        thickness = float(input("Enter layer thickness in cm: "))

        layer = Layer(thickness, materials[material_name])
        layers.append(layer)

    return layers


def get_detector_distance_from_user() -> float:
    detector_distance = float(input("Enter detector distance in cm: "))
    return detector_distance


def get_photon_energy_from_user() -> float:
    photon_energy = float(input("Enter photon energy in MeV "))
    return photon_energy


def get_source_strength_from_user() -> float:
    source_strength = float(input("Enter source strength in photons/s "))
    return source_strength


def get_apply_buildup_from_user() -> bool:
    answer = input("Apply G-P buildup correction? (y/n): ").lower().strip()

    if answer == "y" or answer == "yes":
        return True

    if answer == "n" or answer == "no":
        return False

    raise ValueError("Please enter y or n.")


# Gets user choice between V1.05 monoenergetic photon source or Isotope source
def get_source_mode_from_user() -> str:
    print("\nSource modes:")
    print("1. Manual monoenergetic photon source")
    print("2. Isotope source from library")

    source_mode = input("Select source mode (1/2): ").strip()

    if source_mode == "1":
        return "manual"

    if source_mode == "2":
        return "isotope"

    raise ValueError("Please enter 1 or 2.")


# If manual photon source is selected, perform the V1.05 method of photon_energy and source_strength
def get_manual_photon_source_from_user() -> ManualPhotonSource:
    photon_energy = float(input("Enter photon energy in MeV: "))
    photon_rate = float(input("Enter photon emission rate in photons/s: "))

    return ManualPhotonSource(
        photon_energy,
        photon_rate,
    )


# If isotope source is selected, prompt user to choose an isotope, enter activity, and enter unit.
def get_isotope_source_from_user() -> IsotopeSource:
    print("\nAvailable isotope sources:")
    for isotope_key in get_available_isotopes():
        print(f"- {isotope_key}")

    isotope_key = input("Enter isotope source: ").lower().strip()

    activity_value = float(input("Enter source activity value: "))
    activity_unit = input("Enter activity unit (bq, kbq, mbq, gbq, ci, mci, uci): ")

    activity_bq = convert_activity_to_bq(
        activity_value,
        activity_unit,
    )

    return create_isotope_source(
        isotope_key,
        activity_bq,
    )


def get_source_from_user() -> ManualPhotonSource | IsotopeSource:
    source_mode = get_source_mode_from_user()

    if source_mode == "manual":
        return get_manual_photon_source_from_user()

    if source_mode == "isotope":
        return get_isotope_source_from_user()

    raise ValueError("Invalid source mode.")


def get_calculation_mode_from_user() -> str:
    print("\nCalculation modes:")
    print("1. Calculate shielded flux for a chosen thickness")
    print("2. Calculate required shielding thickness for a target")
    print("3. Compare required shielding thickness across materials")
    print("4. Optimize material selection using engineering constraints")

    calculation_mode = input(
        "Select calculation mode (1/2/3/4): "
    ).strip()

    if calculation_mode == "1":
        return "fixed_thickness"

    if calculation_mode == "2":
        return "minimum_thickness"

    if calculation_mode == "3":
        return "material_comparison"

    if calculation_mode == "4":
        return "material_optimization"

    raise ValueError("Please enter 1, 2, 3, or 4.")


def get_single_material_from_user(materials: dict[str, Material]) -> Material:
    print("Available materials:")
    for material_name in materials:
        print(f"- {material_name}")

    material_name = input("Enter shielding material name: ").lower().strip()

    if material_name not in materials:
        raise ValueError("Material not found.")

    return materials[material_name]


def get_target_from_user() -> TransmissionTarget | ReductionFactorTarget | FluxTarget:
    print("\nTarget types:")
    print("1. Transmission target")
    print("2. Reduction factor target")
    print("3. Flux target")

    target_mode = input("Select target type (1/2/3): ").strip()

    if target_mode == "1":
        target_transmission = float(
            input("Enter target transmission fraction, ex: 0.01 for 1%: ")
        )

        return TransmissionTarget(target_transmission)

    if target_mode == "2":
        reduction_factor = float(
            input("Enter reduction factor, ex: 1000 for 1000x reduction: ")
        )

        return ReductionFactorTarget(reduction_factor)

    if target_mode == "3":
        target_flux = float(
            input("Enter target uncollided flux in photons/cm^2/s: ")
        )

        return FluxTarget(target_flux)

    raise ValueError("Please enter 1, 2, or 3.")


def get_optional_calculation_max_thickness_from_user() -> float | None:
    # Calculation search limit used by the minimum-thickness solver.
    #
    # This is different from the V1.09 engineering design thickness constraint.
    # Pressing Enter allows the solver to search up to the detector distance.

    answer = input(
        "Enter calculation thickness search limit in cm, "
        "or press Enter to use detector distance: "
    ).strip()

    if answer == "":
        return None

    value = float(answer)

    if value <= 0:
        raise ValueError(
            "Calculation thickness search limit must be greater than zero."
        )

    return value

def get_materials_for_comparison_from_user(
    materials: dict[str, Material],
) -> list[Material]:
    # Get the list of materials to compare in V1.08 material comparison mode.
    #
    # Pressing Enter compares every material in the material library.
    # Otherwise, the user can enter comma-separated material keys such as:
    #   lead, concrete_ordinary, water
    #
    # Material keys are used instead of display names because they are stable
    # and match the dictionary keys in material_library.py.
    print("Available materials:")
    for material_name in materials:
        print(f"- {material_name}")

    answer = input(
        "Enter material names separated by commas, or press Enter to compare all materials: "
    ).lower().strip()

    if answer == "":
        return list(materials.values())

    selected_materials = []
    material_names = answer.split(",")

    for material_name in material_names:
        key = material_name.strip()

        if key not in materials:
            raise ValueError(f"Material not found: {key}")

        selected_materials.append(materials[key])

    if len(selected_materials) == 0:
        raise ValueError("At least one material must be selected.")

    return selected_materials


def get_optional_positive_float_from_user(
    prompt: str,
) -> float | None:
    answer = input(prompt).strip()

    if answer == "":
        return None

    value = float(answer)

    if value <= 0:
        raise ValueError(
            "Optional design constraint values must be greater than zero."
        )

    return value


def get_design_constraints_from_user() -> DesignConstraints:
    # Collect optional V1.09 hard engineering constraints.
    #
    # Pressing Enter skips a constraint.

    print("\nOptional engineering design constraints:")
    print("Press Enter to leave a constraint inactive.")

    max_thickness_cm = get_optional_positive_float_from_user(
        "Maximum design thickness in cm: "
    )

    max_mass_per_area = get_optional_positive_float_from_user(
        "Maximum mass per area in g/cm^2: "
    )

    max_relative_cost = get_optional_positive_float_from_user(
        "Maximum relative cost index per area: "
    )

    return DesignConstraints(
        max_thickness_cm=max_thickness_cm,
        max_mass_per_area_g_per_cm2=max_mass_per_area,
        max_relative_cost_index_per_area=max_relative_cost,
    )


def get_optimization_mode_from_user() -> OptimizationMode:
    print("\nOptimization objectives:")
    print("1. Minimum required thickness")
    print("2. Minimum mass per area")
    print("3. Minimum relative cost index per area")
    print("4. Balanced thickness, mass, and relative cost score")

    answer = input(
        "Select optimization objective (1/2/3/4): "
    ).strip()

    if answer == "1":
        return "minimum_thickness"

    if answer == "2":
        return "minimum_mass"

    if answer == "3":
        return "minimum_cost"

    if answer == "4":
        return "balanced"

    raise ValueError("Please enter 1, 2, 3, or 4.")


def get_optimization_weights_from_user() -> OptimizationWeights:
    print("\nBalanced optimization weights:")
    print(
        "Weights do not need to add to 1. "
        "Larger values give a metric more influence."
    )

    thickness_weight = float(
        input("Thickness weight: ")
    )

    mass_weight = float(
        input("Mass weight: ")
    )

    cost_weight = float(
        input("Relative cost weight: ")
    )

    return OptimizationWeights(
        thickness_weight=thickness_weight,
        mass_weight=mass_weight,
        cost_weight=cost_weight,
    )