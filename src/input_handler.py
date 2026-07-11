from models import Layer, Material
from source_library import create_isotope_source, get_available_isotopes
from source_models import IsotopeSource, ManualPhotonSource
from unit_conversions import convert_activity_to_bq


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