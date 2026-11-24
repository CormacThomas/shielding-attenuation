"""Verification cases migrated from the original validation runner."""

from shielding.data.isotopes import create_isotope_source
from shielding.data.materials import get_material_library
from shielding.design.response_curves import (
    calculate_response_curve_target_flux,
    create_response_curve,
    create_thickness_samples,
)
from shielding.design.targets import (
    ReductionFactorTarget,
    TransmissionTarget,
)
from shielding.design.thickness import calculate_unshielded_manual_flux
from shielding.physics.source_models import ManualPhotonSource
from shielding.physics.units import convert_activity_to_bq
from tests.checks import (
    assert_close,
    assert_equal,
    assert_not_none,
)


def test_thickness_sampling() -> None:
    # Validate V1.10 thickness sampling.

    inserted_required_thickness = 7.08821

    thickness_samples = create_thickness_samples(
        minimum_thickness_cm=0.0,
        maximum_thickness_cm=10.0,
        number_of_points=11,
        required_thickness_cm=inserted_required_thickness,
    )

    assert_equal(
        "V1.10 exact required thickness adds one sampling point",
        len(thickness_samples),
        12,
    )

    assert_close(
        "V1.10 thickness samples preserve lower endpoint",
        thickness_samples[0],
        0.0,
        1.0e-12,
    )

    assert_close(
        "V1.10 thickness samples preserve upper endpoint",
        thickness_samples[-1],
        10.0,
        1.0e-12,
    )

    exact_thickness_is_present = any(
        abs(value - inserted_required_thickness) <= 1.0e-12
        for value in thickness_samples
    )

    assert_equal(
        "V1.10 exact required thickness is included",
        exact_thickness_is_present,
        True,
    )

    samples_are_strictly_increasing = all(
        thickness_samples[index] < thickness_samples[index + 1]
        for index in range(len(thickness_samples) - 1)
    )

    assert_equal(
        "V1.10 thickness samples are strictly increasing",
        samples_are_strictly_increasing,
        True,
    )


def test_response_curve_target_conversion() -> None:
    detector_distance = 100.0
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )

    # Validate target conversion for response curves.

    manual_unshielded_flux = calculate_unshielded_manual_flux(
        manual_source,
        detector_distance,
    )

    transmission_curve_target = calculate_response_curve_target_flux(
        source=manual_source,
        detector_distance_cm=detector_distance,
        target=TransmissionTarget(0.1),
    )

    transmission_curve_target_value = assert_not_none(
        "V1.10 transmission curve target",
        transmission_curve_target,
    )

    assert_close(
        "V1.10 transmission target converts to target flux",
        transmission_curve_target_value,
        manual_unshielded_flux * 0.1,
        1.0e-8,
    )

    reduction_curve_target = calculate_response_curve_target_flux(
        source=manual_source,
        detector_distance_cm=detector_distance,
        target=ReductionFactorTarget(1000.0),
    )

    reduction_curve_target_value = assert_not_none(
        "V1.10 reduction curve target",
        reduction_curve_target,
    )

    assert_close(
        "V1.10 reduction factor converts to target flux",
        reduction_curve_target_value,
        manual_unshielded_flux / 1000.0,
        1.0e-8,
    )


def test_response_curve_rejects_invalid_input() -> None:
    materials = get_material_library()
    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )

    # Validate response-curve input rejection.

    try:
        create_response_curve(
            source=manual_source,
            material=materials["lead"],
            detector_distance_cm=100.0,
            minimum_thickness_cm=0.0,
            maximum_thickness_cm=101.0,
            number_of_points=10,
        )

        raise AssertionError(
            "Response curve beyond detector distance should have failed."
        )

    except ValueError:
        print("PASS: V1.10 response curve beyond detector distance rejected")

    try:
        create_thickness_samples(
            minimum_thickness_cm=0.0,
            maximum_thickness_cm=10.0,
            number_of_points=1,
        )

        raise AssertionError("Response curve with one sample should have failed.")

    except ValueError:
        print("PASS: V1.10 response curve with insufficient samples rejected")


def test_invalid_source_inputs() -> None:
    one_ci_bq = convert_activity_to_bq(1.0, "ci")

    # Validate expected error handling for invalid user inputs.

    try:
        convert_activity_to_bq(1.0, "banana")
        raise AssertionError("Unsupported activity unit should have failed.")
    except ValueError:
        print("PASS: Unsupported activity unit rejected")

    try:
        create_isotope_source("fake_isotope", one_ci_bq)
        raise AssertionError("Unsupported isotope source should have failed.")
    except ValueError:
        print("PASS: Unsupported isotope source rejected")

    try:
        convert_activity_to_bq(-1.0, "ci")
        raise AssertionError("Negative activity should have failed.")
    except ValueError:
        print("PASS: Negative activity rejected")
