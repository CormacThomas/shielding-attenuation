from calculator import calculate_total_mfp, calculate_total_transmission, calculate_total_thickness
from input_handler import get_layers_from_user, get_detector_distance_from_user, get_photon_energy_from_user, get_source_strength_from_user
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


# Print results.
print_results(
    layers,
    photon_energy,
    source_strength,
    detector_distance,
    total_thickness,
    total_mfp,
    total_transmission,
    flux)