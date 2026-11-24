# V1.13 matched benchmark observation and deterministic result models.
#
# The physical shielding scenario defines:
#   - source
#   - source cavity
#   - shield layers
#   - central evaluation radius
#
# The benchmark observation model defines:
#   - the finite spherical shell over which a backend reports its response
#
# Keeping these concepts separate allows:
#   - the same physical scenario to use different tally-shell thicknesses;
#   - deterministic and OpenMC calculations to share one observation region;
#   - future shell-thickness sensitivity studies without duplicating scenarios.
#
# This module contains no OpenMC imports.


import math
from dataclasses import dataclass

from shielding.physics.response_models import (
    BuildupStatus,
)
from shielding.scenarios.fixed_shield_models import (
    FixedShieldDeterministicResult,
    FixedShieldPhotonLineResult,
)


def benchmark_values_match(
    first_value: float,
    second_value: float,
) -> bool:
    # Compare quantities that should represent the same calculated value.

    return math.isclose(
        first_value,
        second_value,
        rel_tol=1.0e-12,
        abs_tol=1.0e-18,
    )


@dataclass(frozen=True)
class SphericalEvaluationShell:
    # Finite spherical observation region centered around the scenario's
    # nominal evaluation radius.
    #
    # Example:
    #
    #   center_radius_cm = 100.0
    #   thickness_cm = 1.0
    #
    # produces:
    #
    #   inner_radius_cm = 99.5
    #   outer_radius_cm = 100.5

    center_radius_cm: float
    thickness_cm: float

    def __post_init__(self) -> None:
        if self.center_radius_cm <= 0:
            raise ValueError(
                "Evaluation-shell center radius must be greater than zero."
            )

        if self.thickness_cm <= 0:
            raise ValueError("Evaluation-shell thickness must be greater than zero.")

        if self.inner_radius_cm <= 0:
            raise ValueError("Evaluation-shell inner radius must be greater than zero.")

    @property
    def inner_radius_cm(self) -> float:
        return self.center_radius_cm - self.thickness_cm / 2.0

    @property
    def outer_radius_cm(self) -> float:
        return self.center_radius_cm + self.thickness_cm / 2.0


@dataclass
class DeterministicShellPhotonLineResult:
    # Shell-volume-averaged deterministic response for one photon line.
    #
    # fixed_shield_line_result preserves the original point response and
    # detailed attenuation result.
    #
    # The shell-average values represent the same line and shield averaged
    # throughout the finite SphericalEvaluationShell.

    fixed_shield_line_result: FixedShieldPhotonLineResult

    point_to_shell_average_scale_factor: float

    shell_average_uncollided_photon_fluence_rate_per_cm2_s: float

    shell_average_uncollided_collision_air_kerma_rate_gy_per_s: float

    shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s: float | None = (
        None
    )

    def __post_init__(self) -> None:
        if self.point_to_shell_average_scale_factor <= 0:
            raise ValueError(
                "Point-to-shell-average scale factor must be greater than zero."
            )

        if self.shell_average_uncollided_photon_fluence_rate_per_cm2_s < 0:
            raise ValueError(
                "Shell-average uncollided photon fluence rate cannot be negative."
            )

        if self.shell_average_uncollided_collision_air_kerma_rate_gy_per_s < 0:
            raise ValueError(
                "Shell-average uncollided collision air-kerma rate cannot be negative."
            )

        adjusted_response = (
            self.shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if adjusted_response is not None and adjusted_response < 0:
            raise ValueError(
                "Shell-average buildup-adjusted collision "
                "air-kerma rate cannot be negative."
            )

        fixed_line_result = self.fixed_shield_line_result

        expected_fluence_rate = (
            fixed_line_result.shielding_result.uncollided_flux
            * self.point_to_shell_average_scale_factor
        )

        if not benchmark_values_match(
            (self.shell_average_uncollided_photon_fluence_rate_per_cm2_s),
            expected_fluence_rate,
        ):
            raise ValueError(
                "Shell-average photon fluence rate must match the scaled point result."
            )

        point_air_kerma_rate = fixed_line_result.air_kerma_result.uncollided_collision_air_kerma_rate_gy_per_s

        expected_air_kerma_rate = (
            point_air_kerma_rate * self.point_to_shell_average_scale_factor
        )

        if not benchmark_values_match(
            (self.shell_average_uncollided_collision_air_kerma_rate_gy_per_s),
            expected_air_kerma_rate,
        ):
            raise ValueError(
                "Shell-average uncollided collision "
                "air-kerma rate must match the scaled "
                "point result."
            )

        point_adjusted_response = fixed_line_result.air_kerma_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s

        if point_adjusted_response is None:
            if adjusted_response is not None:
                raise ValueError(
                    "A shell-average buildup-adjusted "
                    "response requires a point buildup-"
                    "adjusted response."
                )

        else:
            if adjusted_response is None:
                raise ValueError(
                    "A point buildup-adjusted response "
                    "requires a shell-average buildup-"
                    "adjusted response."
                )

            expected_adjusted_response = (
                point_adjusted_response * self.point_to_shell_average_scale_factor
            )

            if not benchmark_values_match(
                adjusted_response,
                expected_adjusted_response,
            ):
                raise ValueError(
                    "Shell-average buildup-adjusted "
                    "collision air-kerma rate must match "
                    "the scaled point result."
                )

            if adjusted_response < (
                self.shell_average_uncollided_collision_air_kerma_rate_gy_per_s
            ):
                raise ValueError(
                    "Shell-average buildup-adjusted "
                    "collision air kerma cannot be less "
                    "than the uncollided response."
                )


@dataclass
class DeterministicShellAverageResult:
    # Complete matched deterministic response over one finite spherical
    # evaluation shell.
    #
    # fixed_shield_result:
    #   Original deterministic point-response result.
    #
    # evaluation_shell:
    #   Exact spatial region that OpenMC will also tally.
    #
    # line_results:
    #   Shell-average response for every source photon line.

    fixed_shield_result: FixedShieldDeterministicResult

    evaluation_shell: SphericalEvaluationShell

    point_to_shell_average_scale_factor: float

    line_results: list[DeterministicShellPhotonLineResult]

    total_shell_average_uncollided_photon_fluence_rate_per_cm2_s: float

    total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s: float

    total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s: (
        float | None
    ) = None

    def __post_init__(self) -> None:
        if self.point_to_shell_average_scale_factor <= 0:
            raise ValueError(
                "Point-to-shell-average scale factor must be greater than zero."
            )

        if not benchmark_values_match(
            self.evaluation_shell.center_radius_cm,
            self.fixed_shield_result.evaluation_radius_cm,
        ):
            raise ValueError(
                "Evaluation-shell center must match the scenario evaluation radius."
            )

        if self.evaluation_shell.inner_radius_cm <= (
            self.fixed_shield_result.geometry.outer_shield_radius_cm
        ):
            raise ValueError(
                "Evaluation shell must be entirely beyond the outer shield radius."
            )

        if len(self.line_results) == 0:
            raise ValueError(
                "Deterministic shell-average result must "
                "contain at least one photon-line result."
            )

        if len(self.line_results) != len(self.fixed_shield_result.line_results):
            raise ValueError(
                "Shell-average photon-line count must match "
                "the fixed-shield point result."
            )

        if self.total_shell_average_uncollided_photon_fluence_rate_per_cm2_s < 0:
            raise ValueError(
                "Total shell-average photon fluence rate cannot be negative."
            )

        if self.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s < 0:
            raise ValueError(
                "Total shell-average collision air-kerma rate cannot be negative."
            )

        for (
            shell_line_result,
            fixed_line_result,
        ) in zip(
            self.line_results,
            self.fixed_shield_result.line_results,
            strict=True,
        ):
            if shell_line_result.fixed_shield_line_result != fixed_line_result:
                raise ValueError(
                    "Shell-average line result must match "
                    "the corresponding fixed-shield line."
                )

            if not benchmark_values_match(
                (shell_line_result.point_to_shell_average_scale_factor),
                self.point_to_shell_average_scale_factor,
            ):
                raise ValueError(
                    "Every shell-average photon line must "
                    "use the same spatial scale factor."
                )

        expected_total_fluence_rate = sum(
            line_result.shell_average_uncollided_photon_fluence_rate_per_cm2_s
            for line_result in self.line_results
        )

        if not benchmark_values_match(
            (self.total_shell_average_uncollided_photon_fluence_rate_per_cm2_s),
            expected_total_fluence_rate,
        ):
            raise ValueError(
                "Total shell-average photon fluence rate "
                "must equal the line-result sum."
            )

        expected_total_air_kerma_rate = sum(
            line_result.shell_average_uncollided_collision_air_kerma_rate_gy_per_s
            for line_result in self.line_results
        )

        if not benchmark_values_match(
            (self.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s),
            expected_total_air_kerma_rate,
        ):
            raise ValueError(
                "Total shell-average collision air-kerma "
                "rate must equal the line-result sum."
            )

        adjusted_total = (
            self.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if self.buildup_status == "applied":
            adjusted_line_values: list[float] = []

            for line_result in self.line_results:
                adjusted_line_value = line_result.shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s

                if adjusted_line_value is None:
                    raise ValueError(
                        "Applied shell-average buildup "
                        "requires an adjusted value for "
                        "every photon line."
                    )

                adjusted_line_values.append(adjusted_line_value)

            expected_adjusted_total = sum(adjusted_line_values)

            if adjusted_total is None:
                raise ValueError(
                    "Applied shell-average buildup requires an adjusted source total."
                )

            if not benchmark_values_match(
                adjusted_total,
                expected_adjusted_total,
            ):
                raise ValueError(
                    "Total shell-average buildup-adjusted "
                    "collision air kerma must equal the "
                    "line-result sum."
                )

        elif adjusted_total is not None:
            raise ValueError(
                "A shell-average buildup-adjusted total "
                "may only be stored when buildup status "
                "is applied."
            )

    @property
    def scenario_id(self) -> str:
        return self.fixed_shield_result.scenario_id

    @property
    def source_name(self) -> str:
        return self.fixed_shield_result.source_name

    @property
    def activity_bq(self) -> float | None:
        return self.fixed_shield_result.activity_bq

    @property
    def buildup_status(self) -> BuildupStatus:
        return self.fixed_shield_result.buildup_status

    @property
    def warnings(self) -> list[str]:
        return list(self.fixed_shield_result.warnings)
