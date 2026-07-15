import math
from calculator import calculate_shielding_result
from models import Layer, Material
from physics import calculate_flux, calculate_mu, get_mu_over_p_at_energy
from source_calculator import calculate_buildup_for_result, calculate_isotope_source_result
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


def calculate_valid_buildup_max_thickness_for_energy(
    material: Material,
    photon_energy: float,
    detector_distance: float,
) -> float:
    # Find the maximum shield thickness that keeps this material and photon
    # energy within the 40 MFP G-P buildup limit.
    # A zero-thickness buildup calculation is used to confirm that the
    # material and energy are supported by the G-P coefficient library.

    zero_thickness_result = calculate_shielding_result(
        [Layer(0.0, material)],
        photon_energy,
        1.0,
        detector_distance,
    )

    calculate_buildup_for_result(zero_thickness_result)

    mu_over_p = get_mu_over_p_at_energy(
        material,
        photon_energy,
    )

    mu_value = calculate_mu(
        mu_over_p,
        material.density,
    )

    max_buildup_mfp = 40.0

    # The small factor prevents floating-point roundoff from producing
    # 40.0000000001 MFP at the upper search boundary.
    return (max_buildup_mfp / mu_value) * (1.0 - 1.0e-12)


def calculate_valid_buildup_max_thickness_for_isotope(
    source: IsotopeSource,
    material: Material,
    detector_distance: float,
) -> float:
    # For isotope buildup-aware design, all photon lines must remain inside
    # the G-P valid range. The usable buildup search limit is therefore the
    # smallest valid thickness among all photon lines.

    valid_thicknesses = []

    for photon_line in source.photon_lines:
        valid_thickness = calculate_valid_buildup_max_thickness_for_energy(
            material,
            photon_line.energy,
            detector_distance,
        )

        valid_thicknesses.append(valid_thickness)

    return min(valid_thicknesses)


def calculate_manual_flux_at_thickness(
    source: ManualPhotonSource,
    material: Material,
    thickness: float,
    detector_distance: float,
    apply_buildup: bool,
) -> tuple[float, float, float | None]:
    # Calculate manual-source flux at a trial thickness.
    # Returns:
    # selected_flux, uncollided_flux, buildup_corrected_flux
    #
    # selected_flux is the flux used for target comparison.
    # If buildup is requested, selected_flux is buildup-corrected flux.
    # Otherwise, selected_flux is narrow-beam uncollided flux.

    shielding_result = calculate_shielding_result(
        [Layer(thickness, material)],
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    if not apply_buildup:
        return (
            shielding_result.uncollided_flux,
            shielding_result.uncollided_flux,
            None,
        )

    calculate_buildup_for_result(shielding_result)

    if shielding_result.buildup_corrected_flux is None:
        raise ValueError("Buildup-corrected flux was not calculated.")

    return (
        shielding_result.buildup_corrected_flux,
        shielding_result.uncollided_flux,
        shielding_result.buildup_corrected_flux,
    )


def calculate_isotope_flux_at_thickness(
    source: IsotopeSource,
    material: Material,
    thickness: float,
    detector_distance: float,
    apply_buildup: bool = False,
) -> tuple[float, float, float | None]:
    # Calculate isotope-source flux at a trial thickness.
    # Returns:
    # selected_flux, uncollided_flux, buildup_corrected_flux
    #
    # If buildup is requested, every photon line must receive valid buildup.
    # Otherwise, the buildup-aware isotope total is considered unavailable.

    layer = Layer(thickness, material)

    source_result = calculate_isotope_source_result(
        source,
        [layer],
        detector_distance,
        apply_buildup=apply_buildup,
    )

    if not apply_buildup:
        return (
            source_result.total_uncollided_flux,
            source_result.total_uncollided_flux,
            None,
        )

    if source_result.total_buildup_corrected_flux is None:
        if len(source_result.warnings) > 0:
            warning_text = " ".join(source_result.warnings)
        else:
            warning_text = "Buildup-corrected isotope flux was not calculated."

        raise ValueError(warning_text)

    return (
        source_result.total_buildup_corrected_flux,
        source_result.total_uncollided_flux,
        source_result.total_buildup_corrected_flux,
    )


def find_minimum_thickness_by_bisection(
    evaluate_flux,
    target_flux: float,
    high_thickness: float,
    tolerance: float,
    max_iterations: int,
    high_thickness_description: str = "allowed maximum thickness",
) -> float:
    # Generic bisection solver for minimum thickness problems.
    # evaluate_flux(thickness) must return the flux used for target comparison.

    if target_flux <= 0:
        raise ValueError("Target flux must be greater than zero.")

    if high_thickness <= 0:
        raise ValueError("High thickness bound must be greater than zero.")

    high_flux = evaluate_flux(high_thickness)

    if high_flux > target_flux:
        raise ValueError(
            f"Target cannot be reached within the {high_thickness_description}. "
            f"Flux at that thickness: {high_flux:.6e} photons/cm^2/s. "
            f"Target flux: {target_flux:.6e} photons/cm^2/s."
        )

    low_thickness = 0.0

    for _ in range(max_iterations):
        mid_thickness = (low_thickness + high_thickness) / 2.0
        mid_flux = evaluate_flux(mid_thickness)

        if mid_flux > target_flux:
            low_thickness = mid_thickness
        else:
            high_thickness = mid_thickness

        if high_thickness - low_thickness <= tolerance:
            break

    return high_thickness

def calculate_manual_minimum_thickness(
    source: ManualPhotonSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    apply_buildup: bool = False,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
) -> MinimumThicknessResult:
    # Calculate the minimum single-material shielding thickness for a manual
    # monoenergetic photon source.
    #
    # Narrow-beam mode uses the analytical solution:
    # T = exp(-mu * x)
    # x = -ln(T) / mu
    #
    # If buildup is requested, the function tries a buildup-aware bisection
    # calculation. If the buildup model is unsupported or cannot reach the
    # target within the valid G-P MFP range, it falls back to narrow-beam mode
    # and reports a warning.

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

    if apply_buildup:
        try:
            buildup_max_thickness = calculate_valid_buildup_max_thickness_for_energy(
                material,
                source.energy,
                detector_distance,
            )

            buildup_high_thickness = min(
                allowed_max_thickness,
                buildup_max_thickness,
            )

            def evaluate_buildup_flux(thickness: float) -> float:
                selected_flux, _, _ = calculate_manual_flux_at_thickness(
                    source,
                    material,
                    thickness,
                    detector_distance,
                    apply_buildup=True,
                )

                return selected_flux

            required_thickness = find_minimum_thickness_by_bisection(
                evaluate_buildup_flux,
                target_flux,
                buildup_high_thickness,
                tolerance,
                max_iterations,
                "valid G-P buildup thickness range",
            )

            final_flux, final_uncollided_flux, final_buildup_flux = (
                calculate_manual_flux_at_thickness(
                    source,
                    material,
                    required_thickness,
                    detector_distance,
                    apply_buildup=True,
                )
            )

            final_transmission = final_flux / unshielded_flux

            return MinimumThicknessResult(
                material,
                required_thickness,
                final_flux,
                final_transmission,
                target_description,
                warnings,
                "Buildup-aware minimum thickness design",
                final_uncollided_flux,
                final_buildup_flux,
                True,
            )

        except ValueError as error:
            warnings.append(
                "G-P buildup was requested for minimum-thickness design, but "
                f"the buildup-aware solution was unavailable: {error} "
                "The result below uses narrow-beam uncollided flux only."
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
        "Narrow-beam minimum thickness design",
        shielding_result.uncollided_flux,
        None,
        False,
    )


def calculate_isotope_minimum_thickness(
    source: IsotopeSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    apply_buildup: bool = False,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
) -> MinimumThicknessResult:
    # Calculate the minimum single-material shielding thickness for an isotope source.
    #
    # Isotope sources may contain multiple photon lines, and each line attenuates
    # differently. Because of that, this function uses bisection.
    #
    # If buildup is requested, every photon line must receive valid buildup at
    # the design thickness. If that is not possible, the function falls back to
    # narrow-beam mode and reports a warning.

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

    if apply_buildup:
        try:
            buildup_max_thickness = calculate_valid_buildup_max_thickness_for_isotope(
                source,
                material,
                detector_distance,
            )

            buildup_high_thickness = min(
                allowed_max_thickness,
                buildup_max_thickness,
            )

            def evaluate_buildup_flux(thickness: float) -> float:
                selected_flux, _, _ = calculate_isotope_flux_at_thickness(
                    source,
                    material,
                    thickness,
                    detector_distance,
                    apply_buildup=True,
                )

                return selected_flux

            required_thickness = find_minimum_thickness_by_bisection(
                evaluate_buildup_flux,
                target_flux,
                buildup_high_thickness,
                tolerance,
                max_iterations,
            )

            final_flux, final_uncollided_flux, final_buildup_flux = (
                calculate_isotope_flux_at_thickness(
                    source,
                    material,
                    required_thickness,
                    detector_distance,
                    apply_buildup=True,
                )
            )

            final_transmission = final_flux / unshielded_flux

            return MinimumThicknessResult(
                material,
                required_thickness,
                final_flux,
                final_transmission,
                target_description,
                warnings,
                "Buildup-aware minimum thickness design",
                final_uncollided_flux,
                final_buildup_flux,
                True,
            )

        except ValueError as error:
            warnings.append(
                "G-P buildup was requested for minimum-thickness design, but "
                f"the buildup-aware solution was unavailable: {error} "
                "The result below uses narrow-beam uncollided flux only."
            )

    def evaluate_narrow_beam_flux(thickness: float) -> float:
        selected_flux, _, _ = calculate_isotope_flux_at_thickness(
            source,
            material,
            thickness,
            detector_distance,
            apply_buildup=False,
        )

        return selected_flux

    required_thickness = find_minimum_thickness_by_bisection(
        evaluate_narrow_beam_flux,
        target_flux,
        allowed_max_thickness,
        tolerance,
        max_iterations,
        "allowed maximum thickness",
    )

    final_flux, final_uncollided_flux, _ = calculate_isotope_flux_at_thickness(
        source,
        material,
        required_thickness,
        detector_distance,
        apply_buildup=False,
    )

    final_transmission = final_flux / unshielded_flux

    return MinimumThicknessResult(
        material,
        required_thickness,
        final_flux,
        final_transmission,
        target_description,
        warnings,
        "Narrow-beam minimum thickness design",
        final_uncollided_flux,
        None,
        False,
    )