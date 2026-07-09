from models import Layer
from physics import calculate_mu, calculate_transmission, get_mu_over_p_at_energy


def calculate_layer_transmission(layer: Layer, photon_energy: float) -> float:

    # Transmission fraction through a single shielding layer.
    # Combines mu/rho lookup at photon energy, conversion to mu, and Beer-Lambert attenuation through the layer.

    mu_over_p_at_energy = get_mu_over_p_at_energy(layer.material, photon_energy) # Attenuation coefficient over density (cm^2/g) at given energy of given material.
    mu_value = calculate_mu(mu_over_p_at_energy, layer.material.density) # Attenuation coefficient at given energy of given material 1/cm.
    transmission = calculate_transmission(mu_value, layer.thickness) # Beer-Lambert transmission: exp^(-mu * thickness).
    return transmission


def calculate_total_transmission(layers: list[Layer], photon_energy: float) -> float:

    # Calculates total transmission through multiple shielding layers.

    total_transmission = 1.0 # Starting with 1 because values will be multiplied into transmission.

    for layer in layers:
        layer_transmission = calculate_layer_transmission(layer, photon_energy)
        total_transmission = total_transmission * layer_transmission # Changes transmission running total.
    
    return total_transmission


def calculate_layer_mfp(layer: Layer, photon_energy: float) -> float:
    # Calculates thickness in mean free paths.
    mu_over_p_at_energy = get_mu_over_p_at_energy(layer.material, photon_energy)
    mu_value = calculate_mu(mu_over_p_at_energy, layer.material.density)

    return mu_value * layer.thickness


def calculate_total_mfp(layers: list[Layer], photon_energy: float) -> float:
    # Calculates total shielding thickness in mean free paths.
    total_mfp = 0.0

    for layer in layers:
        layer_mfp = calculate_layer_mfp(layer, photon_energy)
        total_mfp = total_mfp + layer_mfp
    
    return total_mfp


def calculate_total_thickness(layers: list[Layer]) -> float:
    # Calculates total physical shielding in cm.
    total_thickness = 0.0

    for layer in layers:
        layer_thickness = layer.thickness
        total_thickness = total_thickness + layer_thickness
    
    return total_thickness