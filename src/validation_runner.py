from target_models import FluxTarget, ReductionFactorTarget, TransmissionTarget
from thickness_calculator import calculate_isotope_minimum_thickness, calculate_manual_minimum_thickness
from buildup import calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from buildup_library import get_gp_coefficients_library
from material_library import get_material_library
from models import Layer
from source_calculator import calculate_isotope_source_result, calculate_manual_source_result
from source_library import create_isotope_source, get_available_isotopes
from source_models import ManualPhotonSource
from unit_conversions import convert_activity_to_bq

# Validation runner for benchmark cases.
# This script is intended for validation after code changes.
# It is separate from main.py so validation tests can be repeated without user input.


def assert_close(
    name: str,
    actual: float,
    expected: float,
    tolerance: float = 1e-6,
) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")


def assert_greater_than(name: str, actual: float, minimum: float) -> None:
    if actual <= minimum:
        raise AssertionError(
            f"{name} failed: expected greater than {minimum}, got {actual}"
        )

    print(f"PASS: {name}")


def assert_less_than_or_equal(name: str, actual: float, maximum: float) -> None:
    if actual > maximum:
        raise AssertionError(
            f"{name} failed: expected less than or equal to {maximum}, got {actual}"
        )

    print(f"PASS: {name}")


def assert_equal(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")


def assert_not_none(name: str, value: float | None) -> float:
    if value is None:
        raise AssertionError(f"{name} failed: expected a value, got None")

    return value


def run_validation_tests() -> None:
    
    gp_library = get_gp_coefficients_library()

    # Validate G-P buildup behavior for every material with coefficient data.

    for material_key in gp_library:
        coefficients = get_gp_coefficients_at_energy(
            material_key,
            1.0,
            gp_library,
        )

        assert_close(
            f"{material_key} GP buildup at 0 MFP",
            calculate_gp_buildup_factor(coefficients, 0.0),
            1.0,
            1e-12,
        )

        assert_close(
            f"{material_key} GP buildup at 1 MFP",
            calculate_gp_buildup_factor(coefficients, 1.0),
            coefficients.b,
            1e-8,
        )

        buildup_at_5_mfp = calculate_gp_buildup_factor(coefficients, 5.0)

        assert_greater_than(
            f"{material_key} GP buildup at 5 MFP greater than 1",
            buildup_at_5_mfp,
            1.0,
        )

    # Validate activity-unit conversions used by isotope sources.

    one_ci_bq = convert_activity_to_bq(1.0, "ci")

    assert_close(
        "1 Ci activity conversion",
        one_ci_bq,
        3.7e10,
        1e-6,
    )

    assert_close(
        "1 mCi activity conversion",
        convert_activity_to_bq(1.0, "mci"),
        3.7e7,
        1e-6,
    )

    assert_close(
        "1 uCi activity conversion",
        convert_activity_to_bq(1.0, "uci"),
        3.7e4,
        1e-9,
    )

    # Validate source-library structure and source-line bookkeeping.

    isotope_keys = get_available_isotopes()

    assert_equal(
        "Source library contains 10 isotope keys",
        len(isotope_keys),
        10,
    )

    expected_line_counts = {
        "cs137": 1,
        "co60": 2,
        "am241": 1,
        "ba133": 7,
        "na22": 2,
        "mn54": 1,
        "co57": 2,
        "zn65": 2,
        "eu152": 9,
        "ir192": 10,
    }

    materials = get_material_library()
    lead_layer = Layer(5.0, materials["lead"])
    layers = [lead_layer]
    detector_distance = 100.0

    # Validate that every isotope source can run through the narrow-beam calculator.

    for isotope_key in isotope_keys:
        source = create_isotope_source(isotope_key, one_ci_bq)

        assert_equal(
            f"{isotope_key} source line count",
            len(source.photon_lines),
            expected_line_counts[isotope_key],
        )

        assert_close(
            f"{isotope_key} activity stored in Bq",
            source.activity_bq,
            one_ci_bq,
            1e-6,
        )

        for i, photon_line in enumerate(source.photon_lines):
            assert_greater_than(
                f"{isotope_key} line {i + 1} energy greater than 0",
                photon_line.energy,
                0.0,
            )

            assert_greater_than(
                f"{isotope_key} line {i + 1} intensity greater than 0",
                photon_line.intensity,
                0.0,
            )

        source_result = calculate_isotope_source_result(
            source,
            layers,
            detector_distance,
            apply_buildup=False,
        )

        assert_equal(
            f"{isotope_key} calculation line result count",
            len(source_result.line_results),
            len(source.photon_lines),
        )

        line_flux_sum = 0.0
        photon_rate_sum = 0.0

        for line_result in source_result.line_results:
            line_flux_sum = line_flux_sum + line_result.shielding_result.uncollided_flux
            photon_rate_sum = photon_rate_sum + line_result.photon_rate

        expected_photon_rate_sum = 0.0

        for photon_line in source.photon_lines:
            expected_photon_rate_sum = (
                expected_photon_rate_sum
                + source.activity_bq * photon_line.intensity
            )

        assert_close(
            f"{isotope_key} photon rates equal activity times intensities",
            photon_rate_sum,
            expected_photon_rate_sum,
            1e-3,
        )

        assert_close(
            f"{isotope_key} total uncollided flux equals sum of line fluxes",
            source_result.total_uncollided_flux,
            line_flux_sum,
            1e-6,
        )

    # Regression test: manual source mode should reproduce the V1.05 Cs-137 lead case.

    manual_source = ManualPhotonSource(
        0.6617,
        3.7e10,
    )

    manual_result = calculate_manual_source_result(
        manual_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    assert_close(
        "Manual source V1.05 uncollided flux regression",
        manual_result.total_uncollided_flux,
        5.40662e2,
        1e-2,
    )

    manual_buildup_flux = assert_not_none(
        "Manual source V1.05 buildup-corrected flux regression",
        manual_result.total_buildup_corrected_flux,
    )

    assert_close(
        "Manual source V1.05 buildup-corrected flux regression",
        manual_buildup_flux,
        1.42612e3,
        1e-2,
    )

    # Validate that multi-line buildup totals equal the sum of valid line-by-line results.

    co60_source = create_isotope_source("co60", one_ci_bq)

    co60_result = calculate_isotope_source_result(
        co60_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    co60_buildup_flux_sum = 0.0

    for line_result in co60_result.line_results:
        line_buildup_flux = assert_not_none(
            "Co-60 line buildup-corrected flux",
            line_result.shielding_result.buildup_corrected_flux,
        )

        co60_buildup_flux_sum = co60_buildup_flux_sum + line_buildup_flux

    co60_total_buildup_flux = assert_not_none(
        "Co-60 total buildup-corrected flux",
        co60_result.total_buildup_corrected_flux,
    )

    assert_close(
        "Co-60 total buildup-corrected flux equals sum of line fluxes",
        co60_total_buildup_flux,
        co60_buildup_flux_sum,
        1e-6,
    )

    # Validate warning behavior when buildup is requested outside the valid G-P MFP range.

    am241_source = create_isotope_source("am241", one_ci_bq)

    am241_result = calculate_isotope_source_result(
        am241_source,
        layers,
        detector_distance,
        apply_buildup=True,
    )

    assert_equal(
        "Am-241 total buildup-corrected flux is unavailable above G-P MFP range",
        am241_result.total_buildup_corrected_flux,
        None,
    )

    assert_greater_than(
        "Am-241 buildup warning generated",
        len(am241_result.warnings),
        0,
    )


    # Validate V1.07 minimum shielding thickness calculations.

    manual_transmission_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        TransmissionTarget(0.1),
    )

    assert_close(
        "Manual minimum thickness transmission target",
        manual_transmission_target_result.final_transmission,
        0.1,
        1e-8,
    )

    manual_reduction_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        ReductionFactorTarget(1000.0),
    )

    assert_close(
        "Manual minimum thickness reduction factor target",
        manual_reduction_target_result.final_transmission,
        0.001,
        1e-8,
    )

    manual_flux_target_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
    )

    assert_less_than_or_equal(
        "Manual minimum thickness flux target",
        manual_flux_target_result.final_flux,
        100.000001,
    )

    cs137_source = create_isotope_source("cs137", one_ci_bq)

    cs137_flux_target_result = calculate_isotope_minimum_thickness(
        cs137_source,
        materials["lead"],
        detector_distance,
        FluxTarget(100.0),
        max_thickness=detector_distance,
    )

    assert_less_than_or_equal(
        "Cs-137 isotope minimum thickness flux target",
        cs137_flux_target_result.final_flux,
        100.000001,
    )

    assert_greater_than(
        "Cs-137 isotope required thickness greater than zero",
        cs137_flux_target_result.required_thickness,
        0.0,
    )

    no_shielding_required_result = calculate_manual_minimum_thickness(
        manual_source,
        materials["lead"],
        detector_distance,
        FluxTarget(1.0e12),
    )

    assert_close(
        "No shielding required returns zero thickness",
        no_shielding_required_result.required_thickness,
        0.0,
        1e-12,
    )

    assert_greater_than(
        "No shielding required warning generated",
        len(no_shielding_required_result.warnings),
        0,
    )

    try:
        calculate_manual_minimum_thickness(
            manual_source,
            materials["lead"],
            detector_distance,
            FluxTarget(1.0e-30),
            max_thickness=0.1,
        )
        raise AssertionError("Impossible manual thickness target should have failed.")
    except ValueError:
        print("PASS: Impossible manual thickness target rejected")


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

    print("\nAll validation tests passed.")


if __name__ == "__main__":
    run_validation_tests()