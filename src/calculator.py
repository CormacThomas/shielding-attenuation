# Core shielding calculator.
#
# This module contains the validated narrow-beam attenuation engine.
# It handles:
#   - mu/rho lookup at photon energy
#   - conversion from mass attenuation coefficient to linear attenuation coefficient
#   - Beer-Lambert transmission through each layer
#   - total transmission through one or more layers
#   - mean-free-path calculations
#   - point-source detector flux
#
# Higher-level modules such as source_calculator.py, thickness_calculator.py,
# and design_optimizer.py depend on this file. Therefore, this module should stay
# simple, stable, and physics-focused.


from models import Layer, LayerResult, ShieldingResult
from physics import calculate_mu, calculate_transmission, get_mu_over_p_at_energy, calculate_flux


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


def calculate_layer_result(layer: Layer, photon_energy: float) -> LayerResult:

    mu_over_p_at_energy = get_mu_over_p_at_energy(layer.material, photon_energy)
    mu_value = calculate_mu(mu_over_p_at_energy, layer.material.density)
    mfp = mu_value * layer.thickness
    transmission = calculate_transmission(mu_value, layer.thickness)

    return LayerResult(
        layer,
        mu_over_p_at_energy,
        mu_value,
        mfp,
        transmission,
    )


def calculate_shielding_result(
    layers: list[Layer],
    photon_energy: float,
    source_strength: float,
    detector_distance: float,
) -> ShieldingResult:
    
    # Calculates the complete narrow-beam shielding result for a list of layers.
    
    layer_results = []

    total_transmission = 1.0
    total_mfp = 0.0
    total_thickness = 0.0

    for layer in layers:
        layer_result = calculate_layer_result(layer, photon_energy)
        layer_results.append(layer_result)

        total_transmission = total_transmission * layer_result.transmission
        total_mfp = total_mfp + layer_result.mfp
        total_thickness = total_thickness + layer.thickness

    if total_thickness > detector_distance:
        raise ValueError(
        "Total shielding thickness cannot be greater than the source-to-detector distance."
        )

    uncollided_flux = calculate_flux(source_strength, total_transmission, detector_distance)

    return ShieldingResult(
        layers,
        layer_results,
        photon_energy,
        source_strength,
        detector_distance,
        total_thickness,
        total_mfp,
        total_transmission,
        uncollided_flux,
    )