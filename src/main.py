from calculator import calculate_total_mfp, calculate_total_transmission, calculate_total_thickness
from material_library import create_lead, create_aluminum
from models import Layer
from physics import calculate_flux, get_mu_over_p_at_energy
from output import print_results

lead = create_lead() # Create material and shielding layer.
aluminum = create_aluminum()

lead_layer = Layer(5, lead) # Creates a material layer with a material and thickness in cm.
aluminum_layer = Layer(10, aluminum)

layers = [lead_layer]

photon_energy = 0.6617 # Sample photon energy in MeV
source_strength = 3.7e10 # photons/s not activity
detector_distance = 5 # cm

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