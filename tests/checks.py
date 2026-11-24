"""Shared comparisons and result lookups for migrated tests."""

from collections.abc import Callable


def assert_close(
    name: str,
    actual: float,
    expected: float,
    tolerance: float = 1e-6,
) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")


def assert_raises(
    name: str,
    expected_exception: type[Exception],
    function: Callable[[], object],
    expected_message: str | None = None,
) -> None:
    # Confirm that a callable rejects invalid input using the expected
    # exception type and, optionally, a recognizable error message.

    try:
        function()

    except expected_exception as error:
        if expected_message is not None and expected_message not in str(error):
            raise AssertionError(
                f"{name} failed: expected message containing "
                f"{expected_message!r}, got {str(error)!r}"
            ) from error

        print(f"PASS: {name}")
        return

    except Exception as error:
        raise AssertionError(
            f"{name} failed: expected "
            f"{expected_exception.__name__}, got "
            f"{type(error).__name__}: {error}"
        ) from error

    raise AssertionError(
        f"{name} failed: expected "
        f"{expected_exception.__name__}, but no exception was raised"
    )


def get_candidate_by_material_key(comparison_result, material_key: str):
    for candidate in comparison_result.candidates:
        if candidate.material.key == material_key:
            return candidate

    raise AssertionError(f"Candidate not found for material key: {material_key}")


def get_air_kerma_candidate_by_material_key(
    comparison_result,
    material_key: str,
):
    for candidate in comparison_result.candidates:
        if candidate.material.key == material_key:
            return candidate

    raise AssertionError(
        f"Air-kerma candidate not found for material key: {material_key}"
    )


def get_optimized_candidate_by_material_key(
    optimization_result,
    material_key: str,
):
    for candidate in optimization_result.all_candidates:
        if candidate.base_candidate.material.key == material_key:
            return candidate

    raise AssertionError(
        f"Optimized candidate not found for material key: {material_key}"
    )


def get_material_plot_point_by_key(
    plot_data,
    material_key: str,
):
    for candidate in plot_data.candidates:
        if candidate.material_key == material_key:
            return candidate

    raise AssertionError(f"Material plot point not found for key: {material_key}")


def get_feasibility_row_by_material_key(
    feasibility_rows,
    material_key: str,
):
    for row in feasibility_rows:
        if row.material_key == material_key:
            return row

    raise AssertionError(f"Feasibility row not found for material key: {material_key}")


def get_response_curve_point_by_thickness(
    curve_result,
    thickness_cm: float,
    tolerance: float = 1.0e-12,
):
    for point in curve_result.points:
        if abs(point.thickness_cm - thickness_cm) <= tolerance:
            return point

    raise AssertionError(f"Response curve does not contain thickness: {thickness_cm}")


def assert_greater_than(name: str, actual: float, minimum: float) -> None:
    if actual <= minimum:
        raise AssertionError(
            f"{name} failed: expected greater than {minimum}, got {actual}"
        )


def assert_less_than_or_equal(name: str, actual: float, maximum: float) -> None:
    if actual > maximum:
        raise AssertionError(
            f"{name} failed: expected less than or equal to {maximum}, got {actual}"
        )


def assert_equal(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name} failed: expected {expected}, got {actual}")


def assert_not_none(name: str, value: float | None) -> float:
    if value is None:
        raise AssertionError(f"{name} failed: expected a value, got None")

    return value
