from buildup_library import get_gp_coefficients_library
from buildup import get_gp_coefficients_at_energy, calculate_gp_buildup_factor, calculate_buildup_corrected_flux
from calculator import calculate_total_mfp, calculate_total_transmission, calculate_total_thickness
from input_handler import get_layers_from_user, get_detector_distance_from_user, get_photon_energy_from_user, get_source_strength_from_user, get_apply_buildup_from_user
from material_library import get_material_library
from physics import calculate_flux
from output import print_results

materials = get_material_library()
layers = get_layers_from_user(materials)

photon_energy = get_photon_energy_from_user() # Sample photon energy in MeV
source_strength = get_source_strength_from_user() # photons/s not activity
detector_distance = get_detector_distance_from_user() # cm

# Run shielding calculation.
total_transmission = calculate_total_transmission(layers, photon_energy)
total_mfp = calculate_total_mfp(layers, photon_energy)
total_thickness = calculate_total_thickness(layers)
flux = calculate_flux(source_strength, total_transmission, detector_distance)

apply_buildup = get_apply_buildup_from_user()

buildup_factor = None
buildup_corrected_flux = None

if apply_buildup:
    if len(layers) != 1:
        raise ValueError("G-P buildup mode currently supports only one shielding layer.")

    if layers[0].material.name.lower() != "lead":
        raise ValueError("G-P buildup mode currently supports only lead.")

    gp_library = get_gp_coefficients_library()
    coefficients = get_gp_coefficients_at_energy("lead", photon_energy, gp_library)

    buildup_factor = calculate_gp_buildup_factor(coefficients, total_mfp)
    buildup_corrected_flux = calculate_buildup_corrected_flux(flux, buildup_factor)


# Print results.
print_results(
    layers,
    photon_energy,
    source_strength,
    detector_distance,
    total_thickness,
    total_mfp,
    total_transmission,
    flux,
    buildup_factor,
    buildup_corrected_flux)