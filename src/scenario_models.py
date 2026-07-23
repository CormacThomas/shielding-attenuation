# Reproducible shielding scenario models.
#
# V1.11 introduces serializable input specifications that describe a
# shielding problem independently of the calculation backend.
#
# This module initially defines:
#   - manual photon-source specifications
#   - isotope-source specifications
#   - deterministic calculation settings
#
# Runtime source objects are created later by scenario_runner.py.


from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from geometry_models import ConcentricSphericalGeometry
from optimization_models import (
    DesignConstraints,
    OptimizationMode,
    OptimizationWeights,
    VALID_OPTIMIZATION_MODES,
)
from target_models import (
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)


@dataclass
class ManualPhotonSourceSpec:
    # Serializable specification for a monoenergetic photon source.
    #
    # photon_energy_mev:
    #   Photon energy in MeV.
    #
    # photon_rate_per_s:
    #   Total photon emission rate in photons per second.

    photon_energy_mev: float
    photon_rate_per_s: float

    def __post_init__(self) -> None:
        if self.photon_energy_mev <= 0:
            raise ValueError(
                "Manual photon energy must be greater than zero."
            )

        if self.photon_rate_per_s < 0:
            raise ValueError(
                "Manual photon emission rate cannot be negative."
            )


@dataclass
class IsotopeSourceSpec:
    # Serializable specification for an isotope source.
    #
    # isotope_key:
    #   Stable internal isotope identifier from source_library.py.
    #
    # activity_bq:
    #   Source activity in becquerels.

    isotope_key: str
    activity_bq: float

    def __post_init__(self) -> None:
        self.isotope_key = self.isotope_key.lower().strip()

        if self.isotope_key == "":
            raise ValueError(
                "Isotope source key cannot be empty."
            )

        if self.activity_bq < 0:
            raise ValueError(
                "Isotope source activity cannot be negative."
            )


SourceSpec: TypeAlias = (
    ManualPhotonSourceSpec
    | IsotopeSourceSpec
)


TargetSpec: TypeAlias = (
    FluxTarget
    | ReductionFactorTarget
    | TransmissionTarget
)


ScenarioCalculationMode = Literal[
    "material_optimization",
]


VALID_SCENARIO_CALCULATION_MODES = (
    "material_optimization",
)


@dataclass
class DeterministicSettings:
    # Backend-specific settings for the deterministic calculator.
    #
    # These settings are kept separate from the physical source and geometry.
    #
    # apply_buildup:
    #   Whether G-P exposure buildup should be requested.
    #
    # calculation_max_thickness_cm:
    #   Optional upper search bound for target-driven thickness calculations.
    #   None allows the existing solver to use its default bound.

    apply_buildup: bool = False
    calculation_max_thickness_cm: float | None = None

    def __post_init__(self) -> None:
        if (
            self.calculation_max_thickness_cm is not None
            and self.calculation_max_thickness_cm <= 0
        ):
            raise ValueError(
                "Calculation maximum thickness must be greater than zero."
            )
        

@dataclass
class ShieldingScenario:
    # Complete reproducible specification for one shielding design problem.
    #
    # V1.11 initially supports material-optimization scenarios only.
    # The scenario stores physical and engineering inputs but does not
    # perform calculations itself.
    #
    # scenario_id:
    #   Stable, machine-readable scenario identifier.
    #
    # description:
    #   Human-readable explanation of the engineering problem.
    #
    # calculation_mode:
    #   Workflow requested by the scenario. V1.11 currently supports
    #   material_optimization only.
    #
    # source:
    #   Serializable manual or isotope source specification.
    #
    # geometry:
    #   Concentric spherical source, shielding, and evaluation geometry.
    #
    # candidate_material_keys:
    #   Stable material-library keys evaluated by the optimizer.
    #
    # target:
    #   Existing validated transmission, reduction-factor, or flux target.
    #
    # constraints:
    #   Existing V1.09 engineering design constraints.
    #
    # optimization_mode:
    #   Existing V1.09 ranking objective.
    #
    # deterministic_settings:
    #   Backend-specific buildup and thickness-search settings.
    #
    # optimization_weights:
    #   Required only for balanced optimization.
    #
    # schema_version:
    #   Version of the serialized scenario structure.

    scenario_id: str
    description: str
    calculation_mode: ScenarioCalculationMode
    source: SourceSpec
    geometry: ConcentricSphericalGeometry
    candidate_material_keys: list[str]
    target: TargetSpec
    constraints: DesignConstraints
    optimization_mode: OptimizationMode

    deterministic_settings: DeterministicSettings = field(
        default_factory=DeterministicSettings
    )

    optimization_weights: OptimizationWeights | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        self.scenario_id = self.scenario_id.lower().strip()
        self.description = self.description.strip()
        self.schema_version = self.schema_version.strip()

        if self.scenario_id == "":
            raise ValueError(
                "Scenario ID cannot be empty."
            )

        if self.description == "":
            raise ValueError(
                "Scenario description cannot be empty."
            )

        if self.schema_version == "":
            raise ValueError(
                "Scenario schema version cannot be empty."
            )

        if (
            self.calculation_mode
            not in VALID_SCENARIO_CALCULATION_MODES
        ):
            raise ValueError(
                "Unsupported scenario calculation mode."
            )

        if not isinstance(
            self.source,
            (ManualPhotonSourceSpec, IsotopeSourceSpec),
        ):
            raise ValueError(
                "Scenario source must be a supported source specification."
            )

        if not isinstance(
            self.target,
            (
                FluxTarget,
                ReductionFactorTarget,
                TransmissionTarget,
            ),
        ):
            raise ValueError(
                "Scenario target must be a supported target type."
            )

        if self.optimization_mode not in VALID_OPTIMIZATION_MODES:
            raise ValueError(
                "Unsupported scenario optimization mode."
            )

        normalized_material_keys = []

        for material_key in self.candidate_material_keys:
            normalized_key = material_key.lower().strip()

            if normalized_key == "":
                raise ValueError(
                    "Candidate material keys cannot be empty."
                )

            normalized_material_keys.append(
                normalized_key
            )

        if len(normalized_material_keys) == 0:
            raise ValueError(
                "Material optimization requires at least one "
                "candidate material."
            )

        if (
            len(set(normalized_material_keys))
            != len(normalized_material_keys)
        ):
            raise ValueError(
                "Candidate material keys must be unique."
            )

        self.candidate_material_keys = (
            normalized_material_keys
        )

        if self.calculation_mode == "material_optimization":
            if len(self.geometry.layers) > 0:
                raise ValueError(
                    "Material-optimization scenarios cannot contain "
                    "fixed shield layers."
                )

        if self.optimization_mode == "balanced":
            if self.optimization_weights is None:
                raise ValueError(
                    "Balanced optimization requires "
                    "optimization weights."
                )

        elif self.optimization_weights is not None:
            raise ValueError(
                "Optimization weights should only be supplied "
                "for balanced optimization."
            )

        calculation_limit = (
            self.deterministic_settings
            .calculation_max_thickness_cm
        )

        available_radial_space = (
            self.geometry.evaluation_radius_cm
            - self.geometry.source_cavity_radius_cm
        )

        if (
            calculation_limit is not None
            and calculation_limit > available_radial_space
        ):
            raise ValueError(
                "Calculation maximum thickness cannot exceed "
                "the radial space between the source cavity "
                "and evaluation location."
            )