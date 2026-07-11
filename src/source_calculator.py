from buildup import (calculate_buildup_corrected_flux, calculate_gp_buildup_factor, get_gp_coefficients_at_energy)
from buildup_library import get_gp_coefficients_library
from calculator import calculate_shielding_result
from models import Layer
from source_models import (IsotopeSource, ManualPhotonSource, PhotonLine, SourceCalculationResult, SourceLineResult)

# Given a source, shielding layers, detector distance, and buildup choice, what is total flux?
# Note: This calculator does not "redo" already validated attenuation physics.

def calculate_buildup_for_result(
    result,
) -> None:
    # Apply G-P buildup correction to a single ShieldingResult.
    # This uses the same single-layer homogeneous material restriction as V1.05.

    if len(result.layers) != 1:
        raise ValueError("G-P buildup mode currently supports only one shielding layer.")

    gp_library = get_gp_coefficients_library()
    material_key = result.layers[0].material.key

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


def calculate_manual_source_result(
    source: ManualPhotonSource,
    layers: list[Layer],
    detector_distance: float,
    apply_buildup: bool,
) -> SourceCalculationResult:
    # Run the shielding calculation for a manually defined monoenergetic photon source.

    photon_line = PhotonLine(source.energy, 1.0)

    shielding_result = calculate_shielding_result(
        layers,
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    if apply_buildup:
        calculate_buildup_for_result(shielding_result)

    line_result = SourceLineResult(
        photon_line,
        source.photon_rate,
        shielding_result,
    )

    total_buildup_corrected_flux = None

    if shielding_result.buildup_corrected_flux is not None:
        total_buildup_corrected_flux = shielding_result.buildup_corrected_flux

    return SourceCalculationResult(
        "Manual Photon Source",
        None,
        [line_result],
        shielding_result.uncollided_flux,
        total_buildup_corrected_flux,
    )


def calculate_isotope_source_result(
    source: IsotopeSource,
    layers: list[Layer],
    detector_distance: float,
    apply_buildup: bool,
) -> SourceCalculationResult:
    # Run one shielding calculation per photon line and sum the detector flux.

    line_results = []
    total_uncollided_flux = 0.0
    total_buildup_corrected_flux = 0.0

    for photon_line in source.photon_lines:
        photon_rate = source.activity_bq * photon_line.intensity

        shielding_result = calculate_shielding_result(
            layers,
            photon_line.energy,
            photon_rate,
            detector_distance,
        )

        if apply_buildup:
            calculate_buildup_for_result(shielding_result)

        line_result = SourceLineResult(
            photon_line,
            photon_rate,
            shielding_result,
        )

        line_results.append(line_result)
        total_uncollided_flux = total_uncollided_flux + shielding_result.uncollided_flux

        if shielding_result.buildup_corrected_flux is not None:
            total_buildup_corrected_flux = (
                total_buildup_corrected_flux
                + shielding_result.buildup_corrected_flux
            )

    if not apply_buildup:
        total_buildup_corrected_flux = None

    return SourceCalculationResult(
        source.name,
        source.activity_bq,
        line_results,
        total_uncollided_flux,
        total_buildup_corrected_flux,
    )