# Pure-Python benchmark case models.
#
# These models separate:
#
#   - the requested optical-thickness definition;
#   - the resolved physical thickness in centimeters;
#   - the backend-independent ShieldingScenario used for execution.
#
# This module does not import OpenMC.


from __future__ import annotations

import math
import re
from dataclasses import dataclass

from shielding.scenarios.models import (
    ShieldingScenario,
)

CASE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def require_positive_finite_value(
    value: float,
    description: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
        or not math.isfinite(float(value))
        or value <= 0
    ):
        raise ValueError(f"{description} must be a positive finite value.")


def require_nonnegative_finite_value(
    value: float,
    description: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
        or not math.isfinite(float(value))
        or value < 0
    ):
        raise ValueError(f"{description} must be a nonnegative finite value.")


@dataclass(frozen=True)
class BenchmarkCaseDefinition:
    # Study-level definition of one single-material benchmark case.
    #
    # target_mean_free_paths is converted into a physical thickness using:
    #
    #   thickness_cm = target_mean_free_paths / mu
    #
    # where mu is evaluated at reference_energy_mev using the project's
    # authoritative XCOM interpolation and material density.
    #
    # The reference energy is explicit because an MFP count is incomplete
    # without specifying the energy at which mu is evaluated.

    case_id: str

    isotope_key: str
    activity_bq: float

    material_key: str

    reference_energy_mev: float
    target_mean_free_paths: float

    source_cavity_radius_cm: float = 1.0
    evaluation_radius_cm: float = 100.0

    apply_gp_buildup: bool = True

    def __post_init__(
        self,
    ) -> None:
        normalized_case_id = self.case_id.lower().strip()

        normalized_isotope_key = self.isotope_key.lower().strip()

        normalized_material_key = self.material_key.lower().strip()

        if normalized_case_id == "":
            raise ValueError("Benchmark case ID cannot be empty.")

        if CASE_ID_PATTERN.fullmatch(normalized_case_id) is None:
            raise ValueError(
                "Benchmark case ID may contain only "
                "lowercase letters, numbers, and "
                "single underscores between tokens."
            )

        if normalized_isotope_key == "":
            raise ValueError("Benchmark isotope key cannot be empty.")

        if normalized_material_key == "":
            raise ValueError("Benchmark material key cannot be empty.")

        require_positive_finite_value(
            self.activity_bq,
            "Benchmark activity",
        )

        require_positive_finite_value(
            self.reference_energy_mev,
            "Benchmark reference energy",
        )

        require_positive_finite_value(
            self.target_mean_free_paths,
            "Benchmark target mean free paths",
        )

        require_nonnegative_finite_value(
            self.source_cavity_radius_cm,
            "Benchmark source-cavity radius",
        )

        require_positive_finite_value(
            self.evaluation_radius_cm,
            "Benchmark evaluation radius",
        )

        if self.evaluation_radius_cm <= self.source_cavity_radius_cm:
            raise ValueError(
                "Benchmark evaluation radius must be "
                "greater than the source-cavity radius."
            )

        if not isinstance(
            self.apply_gp_buildup,
            bool,
        ):
            raise ValueError("Benchmark G-P buildup setting must be Boolean.")

        object.__setattr__(
            self,
            "case_id",
            normalized_case_id,
        )

        object.__setattr__(
            self,
            "isotope_key",
            normalized_isotope_key,
        )

        object.__setattr__(
            self,
            "material_key",
            normalized_material_key,
        )


@dataclass(frozen=True)
class ResolvedBenchmarkCase:
    # Fully resolved physical benchmark case.
    #
    # The benchmark definition preserves the requested optical thickness.
    # The ShieldingScenario stores the actual physical thickness in
    # centimeters for deterministic and OpenMC execution.

    definition: BenchmarkCaseDefinition

    material_name: str

    mu_over_rho_cm2_per_g: float
    density_g_per_cm3: float
    linear_attenuation_coefficient_per_cm: float

    physical_thickness_cm: float
    reconstructed_mean_free_paths: float
    outer_shield_radius_cm: float

    scenario: ShieldingScenario

    def __post_init__(
        self,
    ) -> None:
        if self.material_name.strip() == "":
            raise ValueError("Resolved benchmark material name cannot be empty.")

        require_positive_finite_value(
            self.mu_over_rho_cm2_per_g,
            "Resolved mass attenuation coefficient",
        )

        require_positive_finite_value(
            self.density_g_per_cm3,
            "Resolved material density",
        )

        require_positive_finite_value(
            self.linear_attenuation_coefficient_per_cm,
            "Resolved linear attenuation coefficient",
        )

        require_positive_finite_value(
            self.physical_thickness_cm,
            "Resolved physical thickness",
        )

        require_positive_finite_value(
            self.reconstructed_mean_free_paths,
            "Resolved reconstructed mean free paths",
        )

        require_positive_finite_value(
            self.outer_shield_radius_cm,
            "Resolved outer shield radius",
        )

        expected_mu = self.mu_over_rho_cm2_per_g * self.density_g_per_cm3

        if not math.isclose(
            self.linear_attenuation_coefficient_per_cm,
            expected_mu,
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise ValueError(
                "Resolved linear attenuation coefficient "
                "must equal mu/rho times density."
            )

        expected_mean_free_paths = (
            self.linear_attenuation_coefficient_per_cm * self.physical_thickness_cm
        )

        if not math.isclose(
            self.reconstructed_mean_free_paths,
            expected_mean_free_paths,
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "Resolved reconstructed mean free paths "
                "must equal mu times physical thickness."
            )

        if not math.isclose(
            self.reconstructed_mean_free_paths,
            self.definition.target_mean_free_paths,
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "Resolved physical thickness does not "
                "reproduce the requested mean free paths."
            )

        expected_outer_radius = (
            self.definition.source_cavity_radius_cm + self.physical_thickness_cm
        )

        if not math.isclose(
            self.outer_shield_radius_cm,
            expected_outer_radius,
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "Resolved outer shield radius is "
                "inconsistent with the cavity and thickness."
            )

        if self.outer_shield_radius_cm >= self.definition.evaluation_radius_cm:
            raise ValueError(
                "Resolved shield must remain entirely inside the evaluation radius."
            )

        if self.scenario.scenario_id != self.definition.case_id:
            raise ValueError("Resolved scenario ID must match the benchmark case ID.")

        if self.scenario.calculation_mode != "fixed_shield_response":
            raise ValueError(
                "Resolved benchmark scenario must use fixed_shield_response mode."
            )

        if len(self.scenario.geometry.layers) != 1:
            raise ValueError(
                "Resolved single-material benchmark "
                "must contain exactly one shield layer."
            )

        scenario_layer = self.scenario.geometry.layers[0]

        if scenario_layer.material_key != self.definition.material_key:
            raise ValueError(
                "Resolved scenario material does not match the benchmark definition."
            )

        if not math.isclose(
            scenario_layer.thickness_cm,
            self.physical_thickness_cm,
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "Resolved scenario thickness does not "
                "match the benchmark physical thickness."
            )
