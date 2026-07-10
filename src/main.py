from buildup_library import get_gp_coefficients_library
from buildup import calculate_buildup_corrected_flux, calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from calculator import calculate_shielding_result
from input_handler import get_apply_buildup_from_user,get_detector_distance_from_user, get_layers_from_user, get_photon_energy_from_user, get_source_strength_from_user
from material_library import get_material_library
from output import print_results


materials = get_material_library()
layers = get_layers_from_user(materials)

photon_energy = get_photon_energy_from_user()
source_strength = get_source_strength_from_user()
detector_distance = get_detector_distance_from_user()

# Run narrow-beam shielding calculation.
result = calculate_shielding_result(layers, photon_energy, source_strength, detector_distance)

apply_buildup = get_apply_buildup_from_user()

if apply_buildup:
    if len(result.layers) != 1:
        raise ValueError("G-P buildup mode currently supports only one shielding layer.")

    gp_library = get_gp_coefficients_library()
    material_key = result.layers[0].material.name.lower().strip()

    if material_key not in gp_library:
        raise ValueError(
            f"G-P buildup mode does not currently support {result.layers[0].material.name}."
        )

    coefficients = get_gp_coefficients_at_energy(
        material_key,
        result.photon_energy,
        gp_library,
    )

    result.buildup_factor = calculate_gp_buildup_factor(
        coefficients,
        result.total_mfp,
    )

    result.buildup_corrected_flux = calculate_buildup_corrected_flux(
        result.uncollided_flux,
        result.buildup_factor,
    )

# Print results.
print_results(result)