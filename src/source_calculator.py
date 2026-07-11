from buildup import (
    calculate_buildup_corrected_flux,
    calculate_gp_buildup_factor,
    get_gp_coefficients_at_energy,
)
from buildup_library import get_gp_coefficients_library
from calculator import calculate_shielding_result
from models import Layer, ShieldingResult
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
    PhotonLine,
    SourceCalculationResult,
    SourceLineResult,
)

# Source-level calculation utilities.
# These functions sit above the validated narrow-beam attenuation calculator.
# They do not redo attenuation physics; they convert source definitions into
# one or more photon-line shielding calculations and then collect the results.


def calculate_buildup_for_result(result: ShieldingResult) -> None:
    # Apply G-P exposure buildup correction to a single ShieldingResult.
    # V1.06 only supports G-P buildup for one homogeneous shielding layer.
    # Multilayer buildup requires a more advanced treatment and is not included yet.

    if len(result.layers) != 1:
        raise ValueError("G-P buildup mode currently supports only one shielding layer.")

    gp_library = get_gp_coefficients_library()
    material = result.layers[0].material
    material_key = material.key

    # Only materials with available ANS/ORNL G-P coefficients can use buildup.
    if material_key not in gp_library:
        raise ValueError(
            f"G-P buildup mode does not currently support {material.name}."
        )

    coefficients = get_gp_coefficients_at_energy(
        material_key,
        result.photon_energy,
        gp_library,
    )

    # calculate_gp_buildup_factor() enforces the valid MFP range.
    # This wrapper adds photon energy and material context to the error message.
    try:
        result.buildup_factor = calculate_gp_buildup_factor(
            coefficients,
            result.total_mfp,
        )
    except ValueError as error:
        raise ValueError(
            f"Could not apply G-P buildup to the {result.photon_energy} MeV "
            f"photon line through {material.name}. "
            f"Total MFP = {result.total_mfp:.6g}. {error}"
        ) from error

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
    # Narrow-beam uncollided flux is always calculated.
    # If buildup is requested but invalid, the calculation still returns the
    # uncollided result and stores a warning.

    warnings = []

    photon_line = PhotonLine(source.energy, 1.0)

    shielding_result = calculate_shielding_result(
        layers,
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    if apply_buildup:
        try:
            calculate_buildup_for_result(shielding_result)
        except ValueError as error:
            warnings.append(
                f"Buildup skipped for {source.energy} MeV manual photon source: "
                f"{error} Narrow-beam uncollided flux is still reported."
            )

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
        warnings,
    )


def calculate_isotope_source_result(
    source: IsotopeSource,
    layers: list[Layer],
    detector_distance: float,
    apply_buildup: bool,
) -> SourceCalculationResult:
    # Run one shielding calculation per photon line and sum detector flux.
    # Narrow-beam uncollided flux is always calculated for every photon line.
    # G-P buildup is applied only when valid for that line/material/thickness.
    # If any line cannot receive buildup, the total buildup-corrected flux is
    # marked unavailable because the source total would be only partially corrected.

    line_results = []
    warnings = []

    total_uncollided_flux = 0.0
    total_buildup_corrected_flux = 0.0
    all_buildup_lines_valid = True

    for photon_line in source.photon_lines:
        photon_rate = source.activity_bq * photon_line.intensity

        shielding_result = calculate_shielding_result(
            layers,
            photon_line.energy,
            photon_rate,
            detector_distance,
        )

        if apply_buildup:
            try:
                calculate_buildup_for_result(shielding_result)
            except ValueError as error:
                all_buildup_lines_valid = False
                warnings.append(
                    f"Buildup skipped for {photon_line.energy} MeV line: {error} "
                    "Narrow-beam uncollided flux is still reported for this line."
                )

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

    if not apply_buildup or not all_buildup_lines_valid:
        total_buildup_corrected_flux = None

    return SourceCalculationResult(
        source.name,
        source.activity_bq,
        line_results,
        total_uncollided_flux,
        total_buildup_corrected_flux,
        warnings,
    )