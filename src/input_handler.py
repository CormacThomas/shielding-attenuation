from models import Layer, Material


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