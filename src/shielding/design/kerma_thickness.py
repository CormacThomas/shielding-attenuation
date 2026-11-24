"""Solve homogeneous shielding thickness for collision air-kerma targets."""

from shielding.design.targets import (
    AirKermaMinimumThicknessResult,
    AirKermaRateTarget,
)
from shielding.physics.air_kerma import (
    calculate_source_air_kerma_result,
)
from shielding.physics.attenuation import calculate_mu, get_mu_over_p_at_energy
from shielding.physics.buildup import MAX_GP_MEAN_FREE_PATHS
from shielding.physics.models import Layer, Material
from shielding.physics.response_models import (
    SourceAirKermaResult,
)
from shielding.physics.source_models import IsotopeSource, ManualPhotonSource

AirKermaSource = ManualPhotonSource | IsotopeSource


def get_air_kerma_target_description(
    target: AirKermaRateTarget,
    apply_buildup: bool,
) -> str:
    # Describe the exact physical response constrained by the solver.

    if apply_buildup:
        response_name = "G-P buildup-adjusted collision air-kerma rate"
    else:
        response_name = "Uncollided collision air-kerma rate"

    return f"{response_name} <= {target.target_air_kerma_rate_microgy_per_h:.6g} µGy/h"


def get_source_photon_energies_mev(
    source: AirKermaSource,
) -> list[float]:
    # Return every photon energy contributing to a supported source.

    if isinstance(
        source,
        ManualPhotonSource,
    ):
        return [source.energy]

    if isinstance(
        source,
        IsotopeSource,
    ):
        return [photon_line.energy for photon_line in source.photon_lines]

    raise ValueError("Unsupported source type for air-kerma design.")


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

    valid_thickness_limits = []

    for photon_energy_mev in get_source_photon_energies_mev(source):
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
                "Linear attenuation coefficient must be greater than zero."
            )

        valid_thickness_limits.append(MAX_GP_MEAN_FREE_PATHS / mu)

    if len(valid_thickness_limits) == 0:
        raise ValueError(
            "At least one photon energy is required for G-P buildup design."
        )

    return min(valid_thickness_limits)


def get_selected_air_kerma_rate_gy_per_s(
    response: SourceAirKermaResult,
    apply_buildup: bool,
) -> float:
    # Return the exact source response constrained by the design solver.
    #
    # Buildup-aware designs are strict. They do not silently use the
    # uncollided response when G-P buildup is unavailable.

    if not apply_buildup:
        return response.total_uncollided_collision_air_kerma_rate_gy_per_s

    if response.buildup_status != "applied":
        warning_text = " ".join(response.warnings)

        if warning_text == "":
            warning_text = "No detailed buildup warning was provided."

        raise ValueError(
            "A buildup-aware air-kerma design requires valid "
            "G-P exposure buildup for every photon line. "
            f"{warning_text}"
        )

    adjusted_rate = response.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s

    if adjusted_rate is None:
        raise ValueError("The buildup-adjusted source air-kerma rate is unavailable.")

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
        raise ValueError("Detector distance must be greater than zero.")

    if thickness_cm < 0:
        raise ValueError("Trial shielding thickness cannot be negative.")

    if thickness_cm > detector_distance_cm:
        raise ValueError(
            "Trial shielding thickness cannot exceed the source-to-detector distance."
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

    selected_rate = get_selected_air_kerma_rate_gy_per_s(
        response=response,
        apply_buildup=apply_buildup,
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
        raise ValueError("Detector distance must be greater than zero.")

    if thickness_tolerance_cm <= 0:
        raise ValueError("Thickness tolerance must be greater than zero.")

    if maximum_iterations <= 0:
        raise ValueError("Maximum iteration count must be greater than zero.")

    if bracket_scan_intervals <= 0:
        raise ValueError("Bracket scan interval count must be greater than zero.")

    if max_thickness_cm is None:
        search_upper_bound_cm = detector_distance_cm

    else:
        if max_thickness_cm <= 0:
            raise ValueError("Maximum search thickness must be greater than zero.")

        search_upper_bound_cm = max_thickness_cm

    if search_upper_bound_cm > detector_distance_cm:
        raise ValueError(
            "Maximum search thickness cannot exceed the source-to-detector distance."
        )

    # A buildup-aware search must remain within the G-P validity range
    # for every contributing photon line.
    if apply_buildup:
        maximum_gp_thickness_cm = calculate_maximum_gp_valid_thickness_cm(
            source=source,
            material=material,
        )

        search_upper_bound_cm = min(
            search_upper_bound_cm,
            maximum_gp_thickness_cm,
        )

    target_rate_gy_per_s = target.target_air_kerma_rate_gy_per_s

    target_description = get_air_kerma_target_description(
        target=target,
        apply_buildup=apply_buildup,
    )

    calculation_mode = (
        "G-P exposure-buildup-adjusted collision air-kerma minimum thickness design"
        if apply_buildup
        else "Uncollided collision air-kerma minimum thickness design"
    )

    warnings: list[str] = []

    unshielded_response, unshielded_rate = calculate_air_kerma_response_at_thickness(
        source=source,
        material=material,
        detector_distance_cm=detector_distance_cm,
        thickness_cm=0.0,
        apply_buildup=apply_buildup,
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
    scan_interval_count = bracket_scan_intervals if apply_buildup else 1

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
        trial_thickness_cm = search_upper_bound_cm * scan_index / scan_interval_count

        trial_response, trial_rate = calculate_air_kerma_response_at_thickness(
            source=source,
            material=material,
            detector_distance_cm=detector_distance_cm,
            thickness_cm=trial_thickness_cm,
            apply_buildup=apply_buildup,
        )

        if trial_rate <= target_rate_gy_per_s:
            lower_thickness_cm = previous_thickness_cm

            lower_rate = previous_rate

            upper_thickness_cm = trial_thickness_cm

            upper_rate = trial_rate
            upper_response = trial_response

            break

        previous_thickness_cm = trial_thickness_cm

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
        if upper_thickness_cm - lower_thickness_cm <= thickness_tolerance_cm:
            break

        midpoint_thickness_cm = 0.5 * (lower_thickness_cm + upper_thickness_cm)

        midpoint_response, midpoint_rate = calculate_air_kerma_response_at_thickness(
            source=source,
            material=material,
            detector_distance_cm=detector_distance_cm,
            thickness_cm=midpoint_thickness_cm,
            apply_buildup=apply_buildup,
        )

        if midpoint_rate <= target_rate_gy_per_s:
            upper_thickness_cm = midpoint_thickness_cm

            upper_rate = midpoint_rate
            final_response = midpoint_response
            final_rate = midpoint_rate

        else:
            lower_thickness_cm = midpoint_thickness_cm

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
        raise ValueError("Air-kerma solver lost its failing lower boundary.")

    if final_rate > target_rate_gy_per_s:
        raise ValueError(
            "Air-kerma solver returned a design that does not satisfy the target."
        )

    if upper_thickness_cm - lower_thickness_cm > thickness_tolerance_cm:
        raise ValueError(
            "Air-kerma solver stopped before reaching the "
            "requested thickness tolerance."
        )

    final_response_ratio = final_rate / unshielded_rate

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
