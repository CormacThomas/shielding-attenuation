# V1.07 target-driven minimum-thickness calculator.
#
# This module converts shielding requirements into required material thickness.
# It does not introduce new attenuation physics. Instead, it uses the validated
# narrow-beam attenuation engine and source-calculation tools from earlier versions.
#
# Supported design targets:
#   - TransmissionTarget: final flux is a fraction of unshielded flux.
#   - ReductionFactorTarget: final flux is reduced by a chosen factor.
#   - FluxTarget: final detector flux is supplied directly by the user.
#
# Manual monoenergetic sources can use an analytical narrow-beam solution:
#   x = -ln(T) / mu
#
# Isotope sources use bisection because each photon line attenuates differently,
# and total source flux is calculated by summing all line contributions.
#
# Buildup-aware design also uses bisection because the G-P buildup factor depends
# on shield thickness in mean free paths.


import math
from calculator import calculate_shielding_result
from models import Layer, Material
from physics import calculate_flux, calculate_mu, get_mu_over_p_at_energy
from source_calculator import calculate_isotope_source_result
from source_models import IsotopeSource, ManualPhotonSource
from air_response import (
    calculate_source_air_kerma_result,
)

from air_response_models import (
    SourceAirKermaResult,
)

from target_models import (
    AirKermaMinimumThicknessResult,
    AirKermaRateTarget,
    FluxTarget,
    MinimumThicknessResult,
    ReductionFactorTarget,
    TransmissionTarget,
)

# Type alias used to show that these functions accept any supported target type.
# This keeps function signatures readable as more target classes are added later.
Target = TransmissionTarget | ReductionFactorTarget | FluxTarget

AirKermaSource = (
    ManualPhotonSource
    | IsotopeSource
)

def get_target_description(
    target: Target,
) -> str:
    # Describe the uncollided photon quantity constrained
    # by a photon minimum-thickness calculation.

    if isinstance(
        target,
        TransmissionTarget,
    ):
        return (
            "Uncollided transmission target <= "
            f"{target.target_transmission:.6g}"
        )

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

    raise ValueError(
        "Unsupported target type."
    )

def get_air_kerma_target_description(
    target: AirKermaRateTarget,
    apply_buildup: bool,
) -> str:
    # Describe the exact physical response constrained by the solver.

    if apply_buildup:
        response_name = (
            "G-P buildup-adjusted collision air-kerma rate"
        )
    else:
        response_name = (
            "Uncollided collision air-kerma rate"
        )

    return (
        f"{response_name} <= "
        f"{target.target_air_kerma_rate_microgy_per_h:.6g} µGy/h"
    )


def get_source_photon_energies_mev(
    source: AirKermaSource,
) -> list[float]:
    # Return every photon energy contributing to a supported source.

    if isinstance(
        source,
        ManualPhotonSource,
    ):
        return [
            source.energy
        ]

    if isinstance(
        source,
        IsotopeSource,
    ):
        return [
            photon_line.energy
            for photon_line in source.photon_lines
        ]

    raise ValueError(
        "Unsupported source type for air-kerma design."
    )


def calculate_maximum_gp_valid_thickness_cm(
    source: AirKermaSource,
    material: Material,
) -> float:
    # Calculate the largest homogeneous shield thickness that keeps every
    # source photon line at or below the 40-MFP G-P validity limit.
    #
    # For each line:
    #
    #     MFP = mu(E) * thickness
    #
    # Therefore:
    #
    #     thickness_max = 40 / mu(E)
    #
    # A multi-line source is limited by the smallest permitted thickness.

    maximum_gp_mfp = 40.0

    valid_thickness_limits = []

    for photon_energy_mev in (
        get_source_photon_energies_mev(
            source
        )
    ):
        mu_over_rho = get_mu_over_p_at_energy(
            material,
            photon_energy_mev,
        )

        mu = calculate_mu(
            mu_over_rho,
            material.density,
        )

        if mu <= 0:
            raise ValueError(
                "Linear attenuation coefficient must be "
                "greater than zero."
            )

        valid_thickness_limits.append(
            maximum_gp_mfp / mu
        )

    if len(valid_thickness_limits) == 0:
        raise ValueError(
            "At least one photon energy is required for "
            "G-P buildup design."
        )

    return min(
        valid_thickness_limits
    )


def get_selected_air_kerma_rate_gy_per_s(
    response: SourceAirKermaResult,
    apply_buildup: bool,
) -> float:
    # Return the exact source response constrained by the design solver.
    #
    # Buildup-aware designs are strict. They do not silently use the
    # uncollided response when G-P buildup is unavailable.

    if not apply_buildup:
        return (
            response
            .total_uncollided_collision_air_kerma_rate_gy_per_s
        )

    if response.buildup_status != "applied":
        warning_text = " ".join(
            response.warnings
        )

        if warning_text == "":
            warning_text = (
                "No detailed buildup warning was provided."
            )

        raise ValueError(
            "A buildup-aware air-kerma design requires valid "
            "G-P exposure buildup for every photon line. "
            f"{warning_text}"
        )

    adjusted_rate = (
        response
        .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    )

    if adjusted_rate is None:
        raise ValueError(
            "The buildup-adjusted source air-kerma rate "
            "is unavailable."
        )

    return adjusted_rate


def calculate_air_kerma_response_at_thickness(
    source: AirKermaSource,
    material: Material,
    detector_distance_cm: float,
    thickness_cm: float,
    apply_buildup: bool,
) -> tuple[
    SourceAirKermaResult,
    float,
]:
    # Calculate the complete source response and return the exact
    # air-kerma rate used by the design target.

    if detector_distance_cm <= 0:
        raise ValueError(
            "Detector distance must be greater than zero."
        )

    if thickness_cm < 0:
        raise ValueError(
            "Trial shielding thickness cannot be negative."
        )

    if thickness_cm > detector_distance_cm:
        raise ValueError(
            "Trial shielding thickness cannot exceed "
            "the source-to-detector distance."
        )

    layers = [
        Layer(
            thickness=thickness_cm,
            material=material,
        )
    ]

    response = calculate_source_air_kerma_result(
        source=source,
        layers=layers,
        detector_distance_cm=detector_distance_cm,
        apply_buildup=apply_buildup,
    )

    selected_rate = (
        get_selected_air_kerma_rate_gy_per_s(
            response=response,
            apply_buildup=apply_buildup,
        )
    )

    return (
        response,
        selected_rate,
    )


def calculate_air_kerma_minimum_thickness(
    source: AirKermaSource,
    material: Material,
    detector_distance_cm: float,
    target: AirKermaRateTarget,
    max_thickness_cm: float | None = None,
    apply_buildup: bool = False,
    thickness_tolerance_cm: float = 1.0e-8,
    maximum_iterations: int = 200,
    bracket_scan_intervals: int = 200,
) -> AirKermaMinimumThicknessResult:
    # Solve for the minimum homogeneous shielding thickness satisfying:
    #
    #     selected air-kerma rate <= target air-kerma rate
    #
    # Selected response:
    #
    #   apply_buildup=False
    #       -> uncollided collision air-kerma rate
    #
    #   apply_buildup=True
    #       -> G-P exposure-buildup-adjusted collision
    #          air-kerma-rate estimate
    #
    # Search method:
    #
    #   1. Evaluate the unshielded response.
    #   2. For buildup-aware calculations, scan the valid thickness range
    #      in ascending order.
    #   3. Find the first sampled interval whose lower endpoint fails
    #      the target and whose upper endpoint passes.
    #   4. Apply bisection only inside that local bracket.
    #
    # The preliminary scan avoids assuming that the buildup-adjusted
    # response decreases monotonically over the entire search range.

    if detector_distance_cm <= 0:
        raise ValueError(
            "Detector distance must be greater than zero."
        )

    if thickness_tolerance_cm <= 0:
        raise ValueError(
            "Thickness tolerance must be greater than zero."
        )

    if maximum_iterations <= 0:
        raise ValueError(
            "Maximum iteration count must be greater than zero."
        )

    if bracket_scan_intervals <= 0:
        raise ValueError(
            "Bracket scan interval count must be greater than zero."
        )

    if max_thickness_cm is None:
        search_upper_bound_cm = detector_distance_cm

    else:
        if max_thickness_cm <= 0:
            raise ValueError(
                "Maximum search thickness must be "
                "greater than zero."
            )

        search_upper_bound_cm = max_thickness_cm

    if search_upper_bound_cm > detector_distance_cm:
        raise ValueError(
            "Maximum search thickness cannot exceed "
            "the source-to-detector distance."
        )

    # A buildup-aware search must remain within the G-P validity range
    # for every contributing photon line.
    if apply_buildup:
        maximum_gp_thickness_cm = (
            calculate_maximum_gp_valid_thickness_cm(
                source=source,
                material=material,
            )
        )

        search_upper_bound_cm = min(
            search_upper_bound_cm,
            maximum_gp_thickness_cm,
        )

    target_rate_gy_per_s = (
        target.target_air_kerma_rate_gy_per_s
    )

    target_description = (
        get_air_kerma_target_description(
            target=target,
            apply_buildup=apply_buildup,
        )
    )

    calculation_mode = (
        "G-P exposure-buildup-adjusted collision "
        "air-kerma minimum thickness design"
        if apply_buildup
        else
        "Uncollided collision air-kerma "
        "minimum thickness design"
    )

    warnings: list[str] = []

    unshielded_response, unshielded_rate = (
        calculate_air_kerma_response_at_thickness(
            source=source,
            material=material,
            detector_distance_cm=detector_distance_cm,
            thickness_cm=0.0,
            apply_buildup=apply_buildup,
        )
    )

    # The unshielded source already satisfies the target.
    if unshielded_rate <= target_rate_gy_per_s:
        warnings.append(
            "The unshielded source response already satisfies "
            "the requested air-kerma-rate target."
        )

        return AirKermaMinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_source_response=unshielded_response,
            final_response_ratio=1.0,
            target_description=target_description,
            warnings=warnings,
            calculation_mode=calculation_mode,
            buildup_used=apply_buildup,
        )

    # Uncollided attenuation is monotonic, so only the two search
    # endpoints are needed to establish a bracket.
    #
    # A buildup-adjusted response can initially increase. In that case,
    # scan the range in ascending order to locate the first sampled
    # failed-to-passed target interval.
    scan_interval_count = (
        bracket_scan_intervals
        if apply_buildup
        else 1
    )

    previous_thickness_cm = 0.0
    previous_rate = unshielded_rate

    lower_thickness_cm: float | None = None
    lower_rate: float | None = None

    upper_thickness_cm: float | None = None
    upper_rate: float | None = None
    upper_response: SourceAirKermaResult | None = None

    for scan_index in range(
        1,
        scan_interval_count + 1,
    ):
        trial_thickness_cm = (
            search_upper_bound_cm
            * scan_index
            / scan_interval_count
        )

        trial_response, trial_rate = (
            calculate_air_kerma_response_at_thickness(
                source=source,
                material=material,
                detector_distance_cm=detector_distance_cm,
                thickness_cm=trial_thickness_cm,
                apply_buildup=apply_buildup,
            )
        )

        if trial_rate <= target_rate_gy_per_s:
            lower_thickness_cm = (
                previous_thickness_cm
            )

            lower_rate = previous_rate

            upper_thickness_cm = (
                trial_thickness_cm
            )

            upper_rate = trial_rate
            upper_response = trial_response

            break

        previous_thickness_cm = (
            trial_thickness_cm
        )

        previous_rate = trial_rate

    if (
        lower_thickness_cm is None
        or lower_rate is None
        or upper_thickness_cm is None
        or upper_rate is None
        or upper_response is None
    ):
        raise ValueError(
            f"{material.name} cannot reach the requested "
            "air-kerma-rate target within the valid search range. "
            f"Maximum evaluated thickness: "
            f"{search_upper_bound_cm:.6g} cm."
        )

    # The scan must produce a failed lower boundary and a passing upper
    # boundary before bisection begins.
    if lower_rate <= target_rate_gy_per_s:
        raise ValueError(
            "Air-kerma target bracketing failed because the lower "
            "boundary already satisfies the target."
        )

    if upper_rate > target_rate_gy_per_s:
        raise ValueError(
            "Air-kerma target bracketing failed because the upper "
            "boundary does not satisfy the target."
        )

    final_response = upper_response
    final_rate = upper_rate

    for _ in range(maximum_iterations):
        if (
            upper_thickness_cm
            - lower_thickness_cm
            <= thickness_tolerance_cm
        ):
            break

        midpoint_thickness_cm = (
            0.5
            * (
                lower_thickness_cm
                + upper_thickness_cm
            )
        )

        midpoint_response, midpoint_rate = (
            calculate_air_kerma_response_at_thickness(
                source=source,
                material=material,
                detector_distance_cm=detector_distance_cm,
                thickness_cm=midpoint_thickness_cm,
                apply_buildup=apply_buildup,
            )
        )

        if midpoint_rate <= target_rate_gy_per_s:
            upper_thickness_cm = (
                midpoint_thickness_cm
            )

            upper_rate = midpoint_rate
            final_response = midpoint_response
            final_rate = midpoint_rate

        else:
            lower_thickness_cm = (
                midpoint_thickness_cm
            )

            lower_rate = midpoint_rate

    else:
        raise ValueError(
            "Air-kerma minimum-thickness bisection did "
            "not converge within the iteration limit."
        )

    # Final solver invariants:
    #
    # lower boundary -> target failed
    # upper boundary -> target satisfied
    # bracket width  -> within requested thickness tolerance

    if lower_rate <= target_rate_gy_per_s:
        raise ValueError(
            "Air-kerma solver lost its failing lower boundary."
        )

    if final_rate > target_rate_gy_per_s:
        raise ValueError(
            "Air-kerma solver returned a design that does not "
            "satisfy the target."
        )

    if (
        upper_thickness_cm
        - lower_thickness_cm
        > thickness_tolerance_cm
    ):
        raise ValueError(
            "Air-kerma solver stopped before reaching the "
            "requested thickness tolerance."
        )

    final_response_ratio = (
        final_rate
        / unshielded_rate
    )

    return AirKermaMinimumThicknessResult(
        material=material,
        required_thickness=upper_thickness_cm,
        final_source_response=final_response,
        final_response_ratio=final_response_ratio,
        target_description=target_description,
        warnings=warnings,
        calculation_mode=calculation_mode,
        buildup_used=apply_buildup,
    )


def calculate_target_flux_from_unshielded_flux(
    target: Target,
    unshielded_flux: float,
) -> float:
    # All target types are converted to the same comparison form:
    #
    #final_flux <= target_flux
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

    target_description = get_target_description(
        target
    )

    warnings: list[str] = []

    unshielded_flux = calculate_unshielded_manual_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append(
            "Unshielded source flux is zero; "
            "no shielding is required."
        )

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=0.0,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
        )

    target_flux = (
        calculate_target_flux_from_unshielded_flux(
            target,
            unshielded_flux,
        )
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

    target_transmission = (
        target_flux
        / unshielded_flux
    )

    mu_over_p = get_mu_over_p_at_energy(
        material,
        source.energy,
    )

    mu_value = calculate_mu(
        mu_over_p,
        material.density,
    )

    required_thickness = (
        -math.log(
            target_transmission
        )
        / mu_value
    )

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
        final_transmission=(
            shielding_result.total_transmission
        ),
        target_description=target_description,
        warnings=warnings,
        calculation_mode=(
            "Uncollided photon-fluence "
            "minimum thickness design"
        ),
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
        raise ValueError(
            "Tolerance must be greater than zero."
        )

    if max_iterations <= 0:
        raise ValueError(
            "Maximum iterations must be greater than zero."
        )

    target_description = get_target_description(
        target
    )

    warnings: list[str] = []

    unshielded_flux = calculate_unshielded_isotope_flux(
        source,
        detector_distance,
    )

    if unshielded_flux == 0:
        warnings.append(
            "Unshielded source flux is zero; "
            "no shielding is required."
        )

        return MinimumThicknessResult(
            material=material,
            required_thickness=0.0,
            final_flux=0.0,
            final_transmission=1.0,
            target_description=target_description,
            warnings=warnings,
        )

    target_flux = (
        calculate_target_flux_from_unshielded_flux(
            target,
            unshielded_flux,
        )
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

    required_thickness = (
        find_minimum_thickness_by_bisection(
            evaluate_flux=(
                evaluate_uncollided_flux
            ),
            target_flux=target_flux,
            high_thickness=allowed_max_thickness,
            tolerance=tolerance,
            max_iterations=max_iterations,
            high_thickness_description=(
                "allowed maximum thickness"
            ),
        )
    )

    final_flux = calculate_isotope_flux_at_thickness(
        source=source,
        material=material,
        thickness=required_thickness,
        detector_distance=detector_distance,
    )

    final_transmission = (
        final_flux
        / unshielded_flux
    )

    return MinimumThicknessResult(
        material=material,
        required_thickness=required_thickness,
        final_flux=final_flux,
        final_transmission=final_transmission,
        target_description=target_description,
        warnings=warnings,
        calculation_mode=(
            "Uncollided photon-fluence "
            "minimum thickness design"
        ),
    )