from buildup import calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from buildup_library import get_gp_coefficients_library
from source_library import create_isotope_source
from unit_conversions import convert_activity_to_bq

# Validation runner for benchmark cases.
# This script is intended for validation after code changes.
# It is separate from main.py so validation tests can be repeated without user input.

def assert_close(name: str, actual: float, expected: float, tolerance: float = 1e-6) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")

def assert_greater_than(name: str, actual: float, minimum: float) -> None:
    if actual <= minimum:
        raise AssertionError(f"{name} failed: expected greater than {minimum}, got {actual}")

    print(f"PASS: {name}")

def run_validation_tests() -> None:
    gp_library = get_gp_coefficients_library()
    coefficients = get_gp_coefficients_at_energy("lead", 0.6617, gp_library)

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

    one_ci_bq = convert_activity_to_bq(1.0, "ci")

    assert_close(
        "1 Ci activity conversion",
        one_ci_bq,
        3.7e10,
        1e-6,
    )

    cs137_source = create_isotope_source("cs137", one_ci_bq)

    assert_close(
        "Cs-137 activity stored in Bq",
        cs137_source.activity_bq,
        3.7e10,
        1e-6,
    )

    assert_close(
        "Cs-137 source has one photon line",
        len(cs137_source.photon_lines),
        1,
        0,
    )

    co60_source = create_isotope_source("co60", one_ci_bq)

    assert_close(
        "Co-60 source has two photon lines",
        len(co60_source.photon_lines),
        2,
        0,
    )

    am241_source = create_isotope_source("am241", one_ci_bq)

    assert_close(
        "Am-241 source has one photon line",
        len(am241_source.photon_lines),
        1,
        0,
    )

    print("\nAll validation tests passed.")


run_validation_tests()