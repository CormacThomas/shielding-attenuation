from buildup import calculate_gp_buildup_factor, get_gp_coefficients_at_energy
from buildup_library import get_gp_coefficients_library
from calculator import calculate_shielding_result
from material_library import get_material_library
from models import Layer

# Validation runner for benchmark cases.
# This script is inteded for validation after code changes.
# It is separate from main.py so validation tests can be repeated without user input.

def assert_close(name: str, actual: float, expected: float, tolerance: float = 1e-6) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")

    print(f"PASS: {name}")


def run_validation_tests() -> None:
    materials = get_material_library()

    lead_layer = Layer(5.0, materials["lead"])
    result = calculate_shielding_result(
        [lead_layer],
        0.6617,
        3.7e10,
        100.0,
    )

    assert_close(
        "Lead 5 cm transmission at 0.6617 MeV",
        result.total_transmission,
        0.0018362592,
        1e-8,
    )

    gp_library = get_gp_coefficients_library()
    coefficients = get_gp_coefficients_at_energy("lead", 0.6617, gp_library)

    assert_close(
        "Lead GP buildup at 0 MFP",
        calculate_gp_buildup_factor(coefficients, 0.0),
        1.0,
        1e-12,
    )

    assert_close(
        "Lead GP buildup at 1 MFP",
        calculate_gp_buildup_factor(coefficients, 1.0),
        coefficients.b,
        1e-8,
    )

    print("\nAll validation tests passed.")


run_validation_tests()