import math
from calculator import calculate_shielding_result
from models import Layer, Material
from physics import calculate_flux, calculate_mu, get_mu_over_p_at_energy
from source_calculator import calculate_isotope_source_result
from source_models import IsotopeSource, ManualPhotonSource
from target_models import (
    FluxTarget,
    MinimumThicknessResult,
    ReductionFactorTarget,
    TransmissionTarget,
)


Target = TransmissionTarget | ReductionFactorTarget | FluxTarget


def get_target_description(target: Target) -> str:
    # Convert a target object into a readable description for output/reporting.

    if isinstance(target, TransmissionTarget):
        return f"Transmission target <= {target.target_transmission:.6g}"

    if isinstance(target, ReductionFactorTarget):
        return f"Reduction factor target >= {target.reduction_factor:.6g}"

    if isinstance(target, FluxTarget):
        return f"Flux target <= {target.target_flux:.6g} photons/cm^2/s"

    raise ValueError("Unsupported target type.")


def calculate_target_flux_from_unshielded_flux(
    target: Target,
    unshielded_flux: float,
) -> float:
    # Convert any supported target type into an equivalent target flux.
    # This lets the thickness calculator use one common comparison:
    # final_flux <= target_flux.

    if unshielded_flux < 0:
        raise ValueError("Unshielded flux cannot be negative.")

    if isinstance(target, TransmissionTarget):
        return unshielded_flux * target.target_transmission

    if isinstance(target, ReductionFactorTarget):
        return unshielded_flux / target.reduction_factor

    if isinstance(target, FluxTarget):
        return target.target_flux

    raise ValueError("Unsupported target type.")


def validate_max_thickness(
    detector_distance: float,
    max_thickness: float | None,
) -> float:
    # Determine the largest allowed shield thickness for a thickness search.
    # The current simulator geometry requires shield thickness to be less than
    # or equal to the source-to-detector distance.

    if detector_distance <= 0:
        raise ValueError("Detector distance must be greater than zero.")

    if max_thickness is None:
        return detector_distance

    if max_thickness <= 0:
        raise ValueError("Maximum thickness must be greater than zero.")

    if max_thickness > detector_distance:
        raise ValueError(
            "Maximum thickness cannot be greater than detector distance "
            "under the current 1D geometry model."
        )

    return max_thickness


def calculate_unshielded_manual_flux(
    source: ManualPhotonSource,
    detector_distance: float,
) -> float:
    # Calculate detector flux with no shielding for a manual photon source.

    return calculate_flux(
        source.photon_rate,
        1.0,
        detector_distance,
    )


def calculate_unshielded_isotope_flux(
    source: IsotopeSource,
    detector_distance: float,
) -> float:
    # Calculate detector flux with no shielding for an isotope source.
    # Each photon line contributes activity * intensity photons/s.

    total_flux = 0.0

    for photon_line in source.photon_lines:
        photon_rate = source.activity_bq * photon_line.intensity

        line_flux = calculate_flux(
            photon_rate,
            1.0,
            detector_distance,
        )

        total_flux = total_flux + line_flux

    return total_flux


def calculate_manual_minimum_thickness(
    source: ManualPhotonSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
) -> MinimumThicknessResult:
    # Calculate the minimum single-material shielding thickness for a manual
    # monoenergetic photon source.
    #
    # This uses the analytical narrow-beam solution:
    # T = exp(-mu * x)
    # x = -ln(T) / mu
    #
    # G-P buildup is intentionally not used in V1.07 thickness design mode.

    allowed_max_thickness = validate_max_thickness(
        detector_distance,
        max_thickness,
    )

    target_description = get_target_description(target)
    warnings = []

    unshielded_flux = calculate_unshielded_manual_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append("Unshielded source flux is zero; no shielding is required.")

        return MinimumThicknessResult(
            material,
            0.0,
            0.0,
            1.0,
            target_description,
            warnings,
        )

    target_flux = calculate_target_flux_from_unshielded_flux(
        target,
        unshielded_flux,
    )

    if target_flux >= unshielded_flux:
        warnings.append(
            "Target flux is greater than or equal to the unshielded flux; "
            "no shielding is required."
        )

        return MinimumThicknessResult(
            material,
            0.0,
            unshielded_flux,
            1.0,
            target_description,
            warnings,
        )

    target_transmission = target_flux / unshielded_flux

    mu_over_p = get_mu_over_p_at_energy(
        material,
        source.energy,
    )

    mu_value = calculate_mu(
        mu_over_p,
        material.density,
    )

    required_thickness = -math.log(target_transmission) / mu_value

    if required_thickness > allowed_max_thickness:
        raise ValueError(
            "Target cannot be reached within the allowed maximum thickness. "
            f"Required thickness: {required_thickness:.6g} cm. "
            f"Allowed maximum thickness: {allowed_max_thickness:.6g} cm."
        )

    shielding_result = calculate_shielding_result(
        [Layer(required_thickness, material)],
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    return MinimumThicknessResult(
        material,
        required_thickness,
        shielding_result.uncollided_flux,
        shielding_result.total_transmission,
        target_description,
        warnings,
    )


def calculate_isotope_flux_at_thickness(
    source: IsotopeSource,
    material: Material,
    thickness: float,
    detector_distance: float,
) -> float:
    # Calculate total narrow-beam uncollided flux for an isotope source
    # through one layer of a selected material at a given thickness.

    layer = Layer(thickness, material)

    source_result = calculate_isotope_source_result(
        source,
        [layer],
        detector_distance,
        apply_buildup=False,
    )

    return source_result.total_uncollided_flux


def calculate_isotope_minimum_thickness(
    source: IsotopeSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
) -> MinimumThicknessResult:
    # Calculate the minimum single-material shielding thickness for an isotope source.
    #
    # Isotope sources may contain multiple photon lines, and each line attenuates
    # differently. Because of that, this function uses bisection instead of a
    # single analytical attenuation equation.
    #
    # G-P buildup is intentionally not used in V1.07 thickness design mode.

    allowed_max_thickness = validate_max_thickness(
        detector_distance,
        max_thickness,
    )

    if tolerance <= 0:
        raise ValueError("Tolerance must be greater than zero.")

    if max_iterations <= 0:
        raise ValueError("Maximum iterations must be greater than zero.")

    target_description = get_target_description(target)
    warnings = []

    unshielded_flux = calculate_unshielded_isotope_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append("Unshielded source flux is zero; no shielding is required.")

        return MinimumThicknessResult(
            material,
            0.0,
            0.0,
            1.0,
            target_description,
            warnings,
        )

    target_flux = calculate_target_flux_from_unshielded_flux(
        target,
        unshielded_flux,
    )

    if target_flux >= unshielded_flux:
        warnings.append(
            "Target flux is greater than or equal to the unshielded flux; "
            "no shielding is required."
        )

        return MinimumThicknessResult(
            material,
            0.0,
            unshielded_flux,
            1.0,
            target_description,
            warnings,
        )

    high_flux = calculate_isotope_flux_at_thickness(
        source,
        material,
        allowed_max_thickness,
        detector_distance,
    )

    if high_flux > target_flux:
        raise ValueError(
            "Target cannot be reached within the allowed maximum thickness. "
            f"Flux at maximum thickness: {high_flux:.6e} photons/cm^2/s. "
            f"Target flux: {target_flux:.6e} photons/cm^2/s."
        )

    low_thickness = 0.0
    high_thickness = allowed_max_thickness

    for _ in range(max_iterations):
        mid_thickness = (low_thickness + high_thickness) / 2.0

        mid_flux = calculate_isotope_flux_at_thickness(
            source,
            material,
            mid_thickness,
            detector_distance,
        )

        if mid_flux > target_flux:
            low_thickness = mid_thickness
        else:
            high_thickness = mid_thickness

        if high_thickness - low_thickness <= tolerance:
            break

    final_flux = calculate_isotope_flux_at_thickness(
        source,
        material,
        high_thickness,
        detector_distance,
    )

    final_transmission = final_flux / unshielded_flux

    return MinimumThicknessResult(
        material,
        high_thickness,
        final_flux,
        final_transmission,
        target_description,
        warnings,
    )