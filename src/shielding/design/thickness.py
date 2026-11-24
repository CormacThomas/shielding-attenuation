"""Solve homogeneous shielding thickness for uncollided photon fluence targets."""

import math

from shielding.design.targets import (
    FluxTarget,
    MinimumThicknessResult,
    ReductionFactorTarget,
    TransmissionTarget,
)
from shielding.physics.attenuation import (
    calculate_flux,
    calculate_mu,
    get_mu_over_p_at_energy,
)
from shielding.physics.layers import calculate_shielding_result
from shielding.physics.models import Layer, Material
from shielding.physics.source_models import IsotopeSource, ManualPhotonSource
from shielding.physics.source_transport import calculate_isotope_source_result

# Type alias used to show that these functions accept any supported target type.
# This keeps function signatures readable as more target classes are added later.
Target = TransmissionTarget | ReductionFactorTarget | FluxTarget


def get_target_description(
    target: Target,
) -> str:
    # Describe the uncollided photon quantity constrained
    # by a photon minimum-thickness calculation.

    if isinstance(
        target,
        TransmissionTarget,
    ):
        return f"Uncollided transmission target <= {target.target_transmission:.6g}"

    if isinstance(
        target,
        ReductionFactorTarget,
    ):
        return (
            "Uncollided photon fluence-rate "
            "reduction factor >= "
            f"{target.reduction_factor:.6g}"
        )

    if isinstance(
        target,
        FluxTarget,
    ):
        return (
            "Uncollided photon fluence-rate target <= "
            f"{target.target_flux:.6g} photons/cm^2/s"
        )

    raise ValueError("Unsupported target type.")


def calculate_target_flux_from_unshielded_flux(
    target: Target,
    unshielded_flux: float,
) -> float:
    # All target types are converted to the same comparison form:
    #
    # final_flux <= target_flux
    #
    # This allows the rest of the calculator to treat transmission targets,
    # reduction-factor targets, and direct flux targets the same way.

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
    # If the user does not supply a maximum thickness, the detector distance
    # is used as the default upper bound. This matches the current 1D geometry
    # assumption that shielding thickness lies between the source and detector.

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


def calculate_manual_flux_at_thickness(
    source: ManualPhotonSource,
    material: Material,
    thickness: float,
    detector_distance: float,
) -> float:
    # Calculate uncollided manual-source photon fluence
    # rate at one trial shielding thickness.

    shielding_result = calculate_shielding_result(
        [
            Layer(
                thickness=thickness,
                material=material,
            ),
        ],
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    return shielding_result.uncollided_flux


def calculate_isotope_flux_at_thickness(
    source: IsotopeSource,
    material: Material,
    thickness: float,
    detector_distance: float,
) -> float:
    # Calculate total uncollided isotope photon fluence
    # rate at one trial shielding thickness.

    source_result = calculate_isotope_source_result(
        source=source,
        layers=[
            Layer(
                thickness=thickness,
                material=material,
            ),
        ],
        detector_distance=detector_distance,
    )

    return source_result.total_uncollided_flux


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

    # First check whether the target is reachable at the upper search bound.
    # If even the maximum allowed thickness does not reduce flux enough,
    # bisection would never find a valid solution.
    high_flux = evaluate_flux(high_thickness)

    if high_flux > target_flux:
        raise ValueError(
            f"Target cannot be reached within the {high_thickness_description}. "
            f"Flux at that thickness: {high_flux:.6e} photons/cm^2/s. "
            f"Target flux: {target_flux:.6e} photons/cm^2/s."
        )

    low_thickness = 0.0

    # Bisection search:
    #   low_thickness is known to be too thin or equal to zero.
    #   high_thickness is known to satisfy the target.
    # Each iteration cuts the interval in half until the required thickness
    # is found within the requested tolerance.
    for _ in range(max_iterations):
        mid_thickness = (low_thickness + high_thickness) / 2.0
        mid_flux = evaluate_flux(mid_thickness)

        # If the midpoint flux is still too high, more shielding is needed.
        # Otherwise, the midpoint satisfies the target and becomes the new
        # upper bound.
        if mid_flux > target_flux:
            low_thickness = mid_thickness
        else:
            high_thickness = mid_thickness

        if high_thickness - low_thickness <= tolerance:
            break

    return high_thickness


# Manual-source minimum thickness workflow:
#
# 1. Calculate unshielded flux at the detector.
# 2. Convert the user's target into a target flux.
# 3. If no shielding is needed, return zero thickness with a warning.
# 4. If buildup is requested, try buildup-aware bisection.
# 5. If buildup-aware design fails, fall back to narrow-beam design and warn.
# 6. If buildup is not requested, use the analytical narrow-beam solution.
def calculate_manual_minimum_thickness(
    source: ManualPhotonSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
) -> MinimumThicknessResult:
    # Calculate minimum homogeneous shielding thickness
    # for an uncollided monoenergetic photon response.
    #
    # T = exp(-mu * x)
    # x = -ln(T) / mu

    allowed_max_thickness = validate_max_thickness(
        detector_distance,
        max_thickness,
    )

    target_description = get_target_description(target)

    warnings: list[str] = []

    unshielded_flux = calculate_unshielded_manual_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append("Unshielded source flux is zero; no shielding is required.")

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=0.0,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
        )

    target_flux = calculate_target_flux_from_unshielded_flux(
        target,
        unshielded_flux,
    )

    if target_flux >= unshielded_flux:
        warnings.append(
            "Target flux is greater than or equal to "
            "the unshielded flux; no shielding is required."
        )

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=unshielded_flux,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
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
            "Target cannot be reached within the allowed "
            "maximum thickness. "
            f"Required thickness: "
            f"{required_thickness:.6g} cm. "
            f"Allowed maximum thickness: "
            f"{allowed_max_thickness:.6g} cm."
        )

    shielding_result = calculate_shielding_result(
        [
            Layer(
                thickness=required_thickness,
                material=material,
            ),
        ],
        source.energy,
        source.photon_rate,
        detector_distance,
    )

    return MinimumThicknessResult(
        material=material,
        required_thickness=required_thickness,
        final_flux=shielding_result.uncollided_flux,
        final_transmission=(shielding_result.total_transmission),
        target_description=target_description,
        warnings=warnings,
        calculation_mode=("Uncollided photon-fluence minimum thickness design"),
    )


# Isotope-source minimum thickness workflow:
#
# Isotope sources may have multiple photon lines. Each line has a different
# energy, attenuation coefficient, transmission, and flux contribution.
#
# Because the total source flux is a sum of multiple attenuated lines, there is
# no simple one-line analytical thickness solution. Bisection is used instead.
#
# If buildup is requested, every photon line must have valid buildup. If any
# line cannot use buildup, the buildup-aware total is unavailable and the
# function falls back to narrow-beam design with a warning.
def calculate_isotope_minimum_thickness(
    source: IsotopeSource,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
) -> MinimumThicknessResult:
    # Calculate minimum homogeneous shielding thickness
    # for an isotope's summed uncollided photon fluence.
    #
    # Bisection is required because each photon line has
    # a different energy and attenuation coefficient.

    allowed_max_thickness = validate_max_thickness(
        detector_distance,
        max_thickness,
    )

    if tolerance <= 0:
        raise ValueError("Tolerance must be greater than zero.")

    if max_iterations <= 0:
        raise ValueError("Maximum iterations must be greater than zero.")

    target_description = get_target_description(target)

    warnings: list[str] = []

    unshielded_flux = calculate_unshielded_isotope_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append("Unshielded source flux is zero; no shielding is required.")

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=0.0,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
        )

    target_flux = calculate_target_flux_from_unshielded_flux(
        target,
        unshielded_flux,
    )

    if target_flux >= unshielded_flux:
        warnings.append(
            "Target flux is greater than or equal to "
            "the unshielded flux; no shielding is required."
        )

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=unshielded_flux,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
        )

    def evaluate_uncollided_flux(
        thickness: float,
    ) -> float:
        return calculate_isotope_flux_at_thickness(
            source=source,
            material=material,
            thickness=thickness,
            detector_distance=detector_distance,
        )

    required_thickness = find_minimum_thickness_by_bisection(
        evaluate_flux=(evaluate_uncollided_flux),
        target_flux=target_flux,
        high_thickness=allowed_max_thickness,
        tolerance=tolerance,
        max_iterations=max_iterations,
        high_thickness_description=("allowed maximum thickness"),
    )

    final_flux = calculate_isotope_flux_at_thickness(
        source=source,
        material=material,
        thickness=required_thickness,
        detector_distance=detector_distance,
    )

    final_transmission = final_flux / unshielded_flux

    return MinimumThicknessResult(
        material=material,
        required_thickness=required_thickness,
        final_flux=final_flux,
        final_transmission=final_transmission,
        target_description=target_description,
        warnings=warnings,
        calculation_mode=("Uncollided photon-fluence minimum thickness design"),
    )
