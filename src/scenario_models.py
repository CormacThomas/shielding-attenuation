# Reproducible shielding scenario models.
#
# This module defines serializable specifications for:
#   - manual and isotope photon sources
#   - response targets
#   - concentric spherical geometry
#   - candidate material sets
#   - engineering constraints
#   - optimization objectives and weights
#   - deterministic calculation settings
#
# V1.13 extends the scenario system with a fixed-shield-response mode.
# The physical source and geometry remain backend independent so the same
# completed shield can be evaluated by the deterministic and OpenMC backends.
#
# scenario_runner.py converts these specifications into validated runtime
# calculation objects.


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
    AirKermaRateTarget,
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
    AirKermaRateTarget
    | FluxTarget
    | ReductionFactorTarget
    | TransmissionTarget
)


ScenarioCalculationMode = Literal[
    "material_optimization",
    "fixed_shield_response",
]


VALID_SCENARIO_CALCULATION_MODES = (
    "material_optimization",
    "fixed_shield_response",
)


VALID_SCENARIO_SCHEMA_VERSIONS = (
    "1.0",
    "1.1",
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
    #
    # Fixed-shield-response scenarios do not perform a thickness search, so
    # calculation_max_thickness_cm must remain None for that mode.

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
    # Complete reproducible specification for one shielding problem.
    #
    # The scenario stores physical and engineering inputs but does not perform
    # calculations itself. Mode-specific validation prevents optimization
    # inputs from being mixed with completed fixed-shield inputs.
    #
    # Shared required fields:
    #   scenario_id
    #   description
    #   calculation_mode
    #   source
    #   geometry
    #
    # Material-optimization fields:
    #   candidate_material_keys
    #   target
    #   constraints
    #   optimization_mode
    #   optional optimization_weights
    #
    # Fixed-shield-response fields:
    #   geometry.layers must contain at least one completed shield layer
    #   target is optional
    #   optimization-only fields must be absent or empty
    #
    # schema_version:
    #   Version 1.0 preserves the original material-optimization structure.
    #   Version 1.1 adds fixed_shield_response.

    scenario_id: str
    description: str
    calculation_mode: ScenarioCalculationMode
    source: SourceSpec
    geometry: ConcentricSphericalGeometry

    candidate_material_keys: list[str] = field(
        default_factory=list
    )

    target: TargetSpec | None = None
    constraints: DesignConstraints | None = None
    optimization_mode: OptimizationMode | None = None

    deterministic_settings: DeterministicSettings = field(
        default_factory=DeterministicSettings
    )

    optimization_weights: OptimizationWeights | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        self.scenario_id = self.scenario_id.lower().strip()
        self.description = self.description.strip()
        self.schema_version = self.schema_version.strip()

        self._validate_shared_fields()
        self._normalize_candidate_material_keys()

        if self.calculation_mode == "material_optimization":
            self._validate_material_optimization_mode()

        elif self.calculation_mode == "fixed_shield_response":
            self._validate_fixed_shield_response_mode()

    def _validate_shared_fields(self) -> None:
        # Validate fields required by every calculation mode.

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
            self.schema_version
            not in VALID_SCENARIO_SCHEMA_VERSIONS
        ):
            raise ValueError(
                "Unsupported scenario schema version: "
                f"{self.schema_version}"
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
            self.geometry,
            ConcentricSphericalGeometry,
        ):
            raise ValueError(
                "Scenario geometry must be a concentric spherical geometry."
            )

        if not isinstance(
            self.deterministic_settings,
            DeterministicSettings,
        ):
            raise ValueError(
                "Scenario deterministic settings must use "
                "DeterministicSettings."
            )

        if self.target is not None:
            if not isinstance(
                self.target,
                (
                    AirKermaRateTarget,
                    FluxTarget,
                    ReductionFactorTarget,
                    TransmissionTarget,
                ),
            ):
                raise ValueError(
                    "Scenario target must be a supported target type or None."
                )

    def _normalize_candidate_material_keys(self) -> None:
        # Normalize stable material keys before mode-specific validation.

        if not isinstance(
            self.candidate_material_keys,
            list,
        ):
            raise ValueError(
                "Candidate material keys must be stored in a list."
            )

        normalized_material_keys: list[str] = []

        for material_key in self.candidate_material_keys:
            if not isinstance(material_key, str):
                raise ValueError(
                    "Candidate material keys must be strings."
                )

            normalized_key = material_key.lower().strip()

            if normalized_key == "":
                raise ValueError(
                    "Candidate material keys cannot be empty."
                )

            normalized_material_keys.append(
                normalized_key
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

    def _validate_material_optimization_mode(self) -> None:
        # Validate the original V1.11/V1.12 optimization pathway.

        if len(self.geometry.layers) > 0:
            raise ValueError(
                "Material-optimization scenarios cannot contain "
                "fixed shield layers."
            )

        if len(self.candidate_material_keys) == 0:
            raise ValueError(
                "Material optimization requires at least one "
                "candidate material."
            )

        if self.target is None:
            raise ValueError(
                "Material optimization requires a response target."
            )

        if not isinstance(
            self.constraints,
            DesignConstraints,
        ):
            raise ValueError(
                "Material optimization requires design constraints."
            )

        if (
            self.optimization_mode is None
            or self.optimization_mode
            not in VALID_OPTIMIZATION_MODES
        ):
            raise ValueError(
                "Material optimization requires a supported "
                "optimization mode."
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

    def _validate_fixed_shield_response_mode(self) -> None:
        # Validate a completed physical shield for deterministic and OpenMC
        # response calculations.

        if self.schema_version != "1.1":
            raise ValueError(
                "Fixed-shield-response scenarios require "
                "schema version 1.1."
            )

        if len(self.geometry.layers) == 0:
            raise ValueError(
                "Fixed-shield-response scenarios require at least "
                "one fixed shield layer."
            )

        if len(self.candidate_material_keys) > 0:
            raise ValueError(
                "Fixed-shield-response scenarios cannot contain "
                "candidate material keys."
            )

        if self.constraints is not None:
            raise ValueError(
                "Fixed-shield-response scenarios cannot contain "
                "optimization constraints."
            )

        if self.optimization_mode is not None:
            raise ValueError(
                "Fixed-shield-response scenarios cannot contain "
                "an optimization mode."
            )

        if self.optimization_weights is not None:
            raise ValueError(
                "Fixed-shield-response scenarios cannot contain "
                "optimization weights."
            )

        if (
            self.deterministic_settings
            .calculation_max_thickness_cm
            is not None
        ):
            raise ValueError(
                "Fixed-shield-response scenarios do not use a "
                "calculation maximum thickness."
            )