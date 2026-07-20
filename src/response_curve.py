# V1.10 detector-response curve generation.
#
# This module evaluates the existing deterministic shielding model across a
# range of single-material shield thicknesses.
#
# It does not perform Matplotlib rendering. It produces structured numerical
# data that plotting.py can later display.
#
# Important behavior:
#   - Narrow-beam uncollided flux is calculated at every thickness.
#   - G-P buildup-adjusted values are calculated separately when requested.
#   - Invalid buildup values are never extrapolated or replaced.
#   - Once the increasing-thickness curve leaves the valid buildup range,
#     the buildup series stops while the narrow-beam series continues.
#   - An exact optimized thickness can be inserted into the sampling grid.


from models import Material
from plot_models import (
    ResponseCurvePoint,
    ResponseCurveResult,
)
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
)
from target_models import (
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from thickness_calculator import (
    calculate_isotope_flux_at_thickness,
    calculate_manual_flux_at_thickness,
    calculate_target_flux_from_unshielded_flux,
    calculate_unshielded_isotope_flux,
    calculate_unshielded_manual_flux,
)


Source = ManualPhotonSource | IsotopeSource

Target = (
    TransmissionTarget
    | ReductionFactorTarget
    | FluxTarget
)


def validate_response_curve_range(
    minimum_thickness_cm: float,
    maximum_thickness_cm: float,
    detector_distance_cm: float,
    number_of_points: int,
) -> None:
    # Validate the requested response-curve sampling range.

    if detector_distance_cm <= 0:
        raise ValueError(
            "Detector distance must be greater than zero."
        )

    if minimum_thickness_cm < 0:
        raise ValueError(
            "Minimum plotted thickness cannot be negative."
        )

    if maximum_thickness_cm <= minimum_thickness_cm:
        raise ValueError(
            "Maximum plotted thickness must be greater than "
            "minimum plotted thickness."
        )

    if maximum_thickness_cm > detector_distance_cm:
        raise ValueError(
            "Maximum plotted thickness cannot exceed detector distance "
            "under the current one-dimensional geometry model."
        )

    if number_of_points < 2:
        raise ValueError(
            "A response curve requires at least two sampling points."
        )


def create_thickness_samples(
    minimum_thickness_cm: float,
    maximum_thickness_cm: float,
    number_of_points: int,
    required_thickness_cm: float | None = None,
) -> list[float]:
    # Create evenly spaced shielding-thickness samples.
    #
    # number_of_points controls the regular sampling grid, including both
    # endpoints.
    #
    # If required_thickness_cm is supplied, the exact value is included even
    # when it does not fall on the regular grid. This may make the returned
    # list contain number_of_points + 1 values.

    if minimum_thickness_cm < 0:
        raise ValueError(
            "Minimum thickness cannot be negative."
        )

    if maximum_thickness_cm <= minimum_thickness_cm:
        raise ValueError(
            "Maximum thickness must be greater than minimum thickness."
        )

    if number_of_points < 2:
        raise ValueError(
            "At least two thickness samples are required."
        )

    if required_thickness_cm is not None:
        if required_thickness_cm < minimum_thickness_cm:
            raise ValueError(
                "Required thickness cannot be below the plotted range."
            )

        if required_thickness_cm > maximum_thickness_cm:
            raise ValueError(
                "Required thickness cannot exceed the plotted range."
            )

    step_size = (
        maximum_thickness_cm - minimum_thickness_cm
    ) / (number_of_points - 1)

    thickness_values = [
        minimum_thickness_cm + index * step_size
        for index in range(number_of_points)
    ]

    # Set the endpoints explicitly to avoid small floating-point differences.
    thickness_values[0] = minimum_thickness_cm
    thickness_values[-1] = maximum_thickness_cm

    if required_thickness_cm is not None:
        matching_index = None

        for index, thickness in enumerate(thickness_values):
            if abs(thickness - required_thickness_cm) <= 1.0e-12:
                matching_index = index
                break

        if matching_index is None:
            thickness_values.append(required_thickness_cm)
        else:
            # Replace a nearly identical grid value with the exact optimized
            # thickness so later validation can compare it directly.
            thickness_values[matching_index] = required_thickness_cm

    thickness_values.sort()

    return thickness_values


def get_response_curve_source_name(
    source: Source,
) -> str:
    if isinstance(source, ManualPhotonSource):
        return "Manual Photon Source"

    if isinstance(source, IsotopeSource):
        return source.name

    raise ValueError("Unsupported source type.")


def calculate_curve_unshielded_flux(
    source: Source,
    detector_distance_cm: float,
) -> float:
    # Calculate the no-shielding flux used to convert transmission and
    # reduction-factor targets into target flux.

    if isinstance(source, ManualPhotonSource):
        return calculate_unshielded_manual_flux(
            source,
            detector_distance_cm,
        )

    if isinstance(source, IsotopeSource):
        return calculate_unshielded_isotope_flux(
            source,
            detector_distance_cm,
        )

    raise ValueError("Unsupported source type.")


def calculate_uncollided_curve_flux(
    source: Source,
    material: Material,
    thickness_cm: float,
    detector_distance_cm: float,
) -> float:
    # Evaluate narrow-beam uncollided flux at one thickness.
    #
    # This function deliberately calls the existing V1.07 calculation helpers
    # rather than reproducing Beer-Lambert or isotope summation logic.

    if isinstance(source, ManualPhotonSource):
        _, uncollided_flux, _ = (
            calculate_manual_flux_at_thickness(
                source=source,
                material=material,
                thickness=thickness_cm,
                detector_distance=detector_distance_cm,
                apply_buildup=False,
            )
        )

        return uncollided_flux

    if isinstance(source, IsotopeSource):
        _, uncollided_flux, _ = (
            calculate_isotope_flux_at_thickness(
                source=source,
                material=material,
                thickness=thickness_cm,
                detector_distance=detector_distance_cm,
                apply_buildup=False,
            )
        )

        return uncollided_flux

    raise ValueError("Unsupported source type.")


def calculate_buildup_curve_flux(
    source: Source,
    material: Material,
    thickness_cm: float,
    detector_distance_cm: float,
) -> float:
    # Evaluate the current G-P buildup-adjusted result at one thickness.
    #
    # This function does not perform fallback. A buildup curve must contain
    # actual buildup-aware values or None.
    #
    # If buildup is unsupported or outside its valid range, the existing
    # calculation helper raises ValueError. The curve generator catches that
    # error and ends the buildup series.

    if isinstance(source, ManualPhotonSource):
        _, _, buildup_corrected_flux = (
            calculate_manual_flux_at_thickness(
                source=source,
                material=material,
                thickness=thickness_cm,
                detector_distance=detector_distance_cm,
                apply_buildup=True,
            )
        )

    elif isinstance(source, IsotopeSource):
        _, _, buildup_corrected_flux = (
            calculate_isotope_flux_at_thickness(
                source=source,
                material=material,
                thickness=thickness_cm,
                detector_distance=detector_distance_cm,
                apply_buildup=True,
            )
        )

    else:
        raise ValueError("Unsupported source type.")

    if buildup_corrected_flux is None:
        raise ValueError(
            "Buildup-adjusted curve value was not calculated."
        )

    return buildup_corrected_flux


def calculate_response_curve_target_flux(
    source: Source,
    detector_distance_cm: float,
    target: Target | None,
) -> float | None:
    # Convert any supported shielding target into a target detector flux.
    #
    # A direct FluxTarget already contains the needed value.
    # Transmission and reduction-factor targets require the unshielded flux.

    if target is None:
        return None

    unshielded_flux = calculate_curve_unshielded_flux(
        source,
        detector_distance_cm,
    )

    return calculate_target_flux_from_unshielded_flux(
        target,
        unshielded_flux,
    )


def create_response_curve(
    source: Source,
    material: Material,
    detector_distance_cm: float,
    maximum_thickness_cm: float,
    number_of_points: int = 101,
    minimum_thickness_cm: float = 0.0,
    apply_buildup: bool = False,
    target: Target | None = None,
    required_thickness_cm: float | None = None,
) -> ResponseCurveResult:
    # Generate deterministic flux-versus-thickness data.
    #
    # Workflow:
    #
    # 1. Validate the requested range.
    # 2. Generate an evenly spaced thickness grid.
    # 3. Insert the exact optimized thickness when supplied.
    # 4. Calculate narrow-beam uncollided flux at every thickness.
    # 5. Calculate buildup-adjusted values separately when requested.
    # 6. Stop the buildup series when it becomes unavailable.
    # 7. Return structured plot data.
    #
    # The buildup series is not allowed to silently fall back to uncollided
    # flux. That distinction is essential for an honest comparison plot.

    validate_response_curve_range(
        minimum_thickness_cm=minimum_thickness_cm,
        maximum_thickness_cm=maximum_thickness_cm,
        detector_distance_cm=detector_distance_cm,
        number_of_points=number_of_points,
    )

    thickness_values = create_thickness_samples(
        minimum_thickness_cm=minimum_thickness_cm,
        maximum_thickness_cm=maximum_thickness_cm,
        number_of_points=number_of_points,
        required_thickness_cm=required_thickness_cm,
    )

    target_flux = calculate_response_curve_target_flux(
        source=source,
        detector_distance_cm=detector_distance_cm,
        target=target,
    )

    points = []
    warnings = []

    # Because thickness values are increasing, exceeding the 40-MFP limit is
    # permanent for all later points. Unsupported material or energy data is
    # also permanent. Once buildup fails, the series therefore remains None.
    buildup_series_active = apply_buildup

    for thickness_cm in thickness_values:
        uncollided_flux = calculate_uncollided_curve_flux(
            source=source,
            material=material,
            thickness_cm=thickness_cm,
            detector_distance_cm=detector_distance_cm,
        )

        buildup_corrected_flux = None

        if buildup_series_active:
            try:
                buildup_corrected_flux = (
                    calculate_buildup_curve_flux(
                        source=source,
                        material=material,
                        thickness_cm=thickness_cm,
                        detector_distance_cm=detector_distance_cm,
                    )
                )

            except ValueError as error:
                warnings.append(
                    f"G-P buildup curve became unavailable at "
                    f"{thickness_cm:.6g} cm for {material.name}: "
                    f"{error}"
                )

                buildup_series_active = False
                buildup_corrected_flux = None

        points.append(
            ResponseCurvePoint(
                thickness_cm=thickness_cm,
                uncollided_flux=uncollided_flux,
                buildup_corrected_flux=buildup_corrected_flux,
            )
        )

    return ResponseCurveResult(
        backend_name="Deterministic",
        quantity_name="Photon flux",
        quantity_units="photons/cm^2/s",
        source_name=get_response_curve_source_name(source),
        material_key=material.key,
        material_name=material.name,
        detector_distance_cm=detector_distance_cm,
        points=tuple(points),
        buildup_requested=apply_buildup,
        target_flux=target_flux,
        required_thickness_cm=required_thickness_cm,
        warnings=tuple(warnings),
    )