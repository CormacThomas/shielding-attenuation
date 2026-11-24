"""Apply narrow-beam attenuation to ordered material layers."""

from shielding.physics.attenuation import (
    calculate_flux,
    calculate_mu,
    calculate_transmission,
    get_mu_over_p_at_energy,
)
from shielding.physics.models import Layer, LayerResult, ShieldingResult


def calculate_layer_result(layer: Layer, photon_energy: float) -> LayerResult:
    """Evaluate attenuation at photon_energy in MeV for one layer."""
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
    """Return the uncollided point-source response through a layer stack.

    Energy is in MeV, distances and thicknesses are in cm, and source strength
    is in photons/s. The uncollided fluence rate is in photons/(cm² s).
    """

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

    uncollided_flux = calculate_flux(
        source_strength, total_transmission, detector_distance
    )

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
