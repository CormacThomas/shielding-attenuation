# V1.11/V1.13 scenario serialization and file I/O.
#
# This module converts validated ShieldingScenario objects into stable,
# human-readable JSON and reconstructs them from JSON data.
#
# Schema 1.0:
#   - material_optimization only
#
# Schema 1.1:
#   - material_optimization
#   - fixed_shield_response
#
# The JSON format uses explicit type fields for sources, geometry, and targets.
# Optimization-only fields are omitted from fixed-shield-response scenarios.


from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shielding.design.models import (
    VALID_OPTIMIZATION_MODES,
    DesignConstraints,
    OptimizationMode,
    OptimizationWeights,
)
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from shielding.scenarios.geometry import (
    ConcentricSphericalGeometry,
    ShieldLayerSpec,
)
from shielding.scenarios.models import (
    VALID_SCENARIO_CALCULATION_MODES,
    VALID_SCENARIO_SCHEMA_VERSIONS,
    DeterministicSettings,
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ScenarioCalculationMode,
    ShieldingScenario,
    TargetSpec,
)

SUPPORTED_SCHEMA_VERSIONS = set(VALID_SCENARIO_SCHEMA_VERSIONS)


def require_json_object(
    value: Any,
    description: str,
) -> dict[str, Any]:
    # Require one nested JSON value to be an object.

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(f"{description} must be a JSON object.")

    return value


def require_json_string_list(
    value: Any,
    description: str,
) -> list[str]:
    # Require a JSON array containing strings only.

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"{description} must be a list.")

    string_values: list[str] = []

    for item in value:
        if not isinstance(
            item,
            str,
        ):
            raise ValueError(f"{description} must contain only strings.")

        string_values.append(item)

    return string_values


def source_spec_to_dict(
    source_spec: (ManualPhotonSourceSpec | IsotopeSourceSpec),
) -> dict[str, Any]:
    # Convert a source specification into an explicitly typed JSON object.

    if isinstance(
        source_spec,
        ManualPhotonSourceSpec,
    ):
        return {
            "type": "manual",
            "photon_energy_mev": (source_spec.photon_energy_mev),
            "photon_rate_per_s": (source_spec.photon_rate_per_s),
        }

    if isinstance(
        source_spec,
        IsotopeSourceSpec,
    ):
        return {
            "type": "isotope",
            "isotope_key": (source_spec.isotope_key),
            "activity_bq": (source_spec.activity_bq),
        }

    raise ValueError("Unsupported source specification for serialization.")


def source_spec_from_dict(
    source_data: dict[str, Any],
) -> ManualPhotonSourceSpec | IsotopeSourceSpec:
    # Reconstruct a validated source specification from JSON data.

    source_type = source_data.get("type")

    if source_type == "manual":
        return ManualPhotonSourceSpec(
            photon_energy_mev=source_data["photon_energy_mev"],
            photon_rate_per_s=source_data["photon_rate_per_s"],
        )

    if source_type == "isotope":
        return IsotopeSourceSpec(
            isotope_key=source_data["isotope_key"],
            activity_bq=source_data["activity_bq"],
        )

    raise ValueError(f"Unsupported scenario source type: {source_type}")


def geometry_to_dict(
    geometry: ConcentricSphericalGeometry,
) -> dict[str, Any]:
    # Serialize physical geometry inputs only.
    #
    # Derived shell radii are reconstructed deterministically from the source
    # cavity radius and ordered layer thicknesses.

    return {
        "type": "concentric_spherical",
        "source_cavity_radius_cm": (geometry.source_cavity_radius_cm),
        "evaluation_radius_cm": (geometry.evaluation_radius_cm),
        "layers": [
            {
                "material_key": (layer.material_key),
                "thickness_cm": (layer.thickness_cm),
            }
            for layer in geometry.layers
        ],
    }


def geometry_from_dict(
    geometry_data: dict[str, Any],
) -> ConcentricSphericalGeometry:
    # Reconstruct the supported concentric spherical geometry.

    geometry_type = geometry_data.get("type")

    if geometry_type != "concentric_spherical":
        raise ValueError(f"Unsupported scenario geometry type: {geometry_type}")

    layer_data_list = geometry_data.get(
        "layers",
        [],
    )

    if not isinstance(
        layer_data_list,
        list,
    ):
        raise ValueError("Scenario geometry layers must be a list.")

    layers: list[ShieldLayerSpec] = []

    for layer_data_value in layer_data_list:
        layer_data = require_json_object(
            layer_data_value,
            "Scenario geometry layer",
        )

        layers.append(
            ShieldLayerSpec(
                material_key=layer_data["material_key"],
                thickness_cm=layer_data["thickness_cm"],
            )
        )

    return ConcentricSphericalGeometry(
        source_cavity_radius_cm=(geometry_data["source_cavity_radius_cm"]),
        evaluation_radius_cm=(geometry_data["evaluation_radius_cm"]),
        layers=layers,
    )


def target_to_dict(
    target: TargetSpec,
) -> dict[str, Any]:
    # Convert one validated target into an explicitly typed JSON object.

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        return {
            "type": "air_kerma_rate",
            "target_air_kerma_rate_microgy_per_h": (
                target.target_air_kerma_rate_microgy_per_h
            ),
        }

    if isinstance(
        target,
        FluxTarget,
    ):
        return {
            "type": "flux",
            "target_flux": (target.target_flux),
        }

    if isinstance(
        target,
        ReductionFactorTarget,
    ):
        return {
            "type": "reduction_factor",
            "reduction_factor": (target.reduction_factor),
        }

    if isinstance(
        target,
        TransmissionTarget,
    ):
        return {
            "type": "transmission",
            "target_transmission": (target.target_transmission),
        }

    raise ValueError("Unsupported target type for serialization.")


def target_from_dict(
    target_data: dict[str, Any],
) -> TargetSpec:
    # Reconstruct one validated target from its explicit JSON type.

    target_type = target_data.get("type")

    if target_type == "air_kerma_rate":
        return AirKermaRateTarget(
            target_air_kerma_rate_microgy_per_h=(
                target_data["target_air_kerma_rate_microgy_per_h"]
            )
        )

    if target_type == "flux":
        return FluxTarget(target_flux=target_data["target_flux"])

    if target_type == "reduction_factor":
        return ReductionFactorTarget(reduction_factor=target_data["reduction_factor"])

    if target_type == "transmission":
        return TransmissionTarget(
            target_transmission=target_data["target_transmission"]
        )

    raise ValueError(f"Unsupported scenario target type: {target_type}")


def constraints_to_dict(
    constraints: DesignConstraints,
) -> dict[str, Any]:
    # Serialize engineering constraints used by optimization mode.

    return {
        "max_thickness_cm": (constraints.max_thickness_cm),
        "max_mass_per_area_g_per_cm2": (constraints.max_mass_per_area_g_per_cm2),
        "max_relative_cost_index_per_area": (
            constraints.max_relative_cost_index_per_area
        ),
    }


def constraints_from_dict(
    constraints_data: dict[str, Any],
) -> DesignConstraints:
    # Reconstruct validated engineering constraints.

    return DesignConstraints(
        max_thickness_cm=(constraints_data.get("max_thickness_cm")),
        max_mass_per_area_g_per_cm2=(
            constraints_data.get("max_mass_per_area_g_per_cm2")
        ),
        max_relative_cost_index_per_area=(
            constraints_data.get("max_relative_cost_index_per_area")
        ),
    )


def optimization_to_dict(
    optimization_mode: OptimizationMode,
    optimization_weights: (OptimizationWeights | None),
) -> dict[str, Any]:
    # Serialize one optimization objective and its optional weights.

    optimization_data: dict[
        str,
        Any,
    ] = {
        "mode": optimization_mode,
        "weights": None,
    }

    if optimization_weights is not None:
        optimization_data["weights"] = {
            "thickness_weight": (optimization_weights.thickness_weight),
            "mass_weight": (optimization_weights.mass_weight),
            "cost_weight": (optimization_weights.cost_weight),
        }

    return optimization_data


def optimization_from_dict(
    optimization_data: dict[str, Any],
) -> tuple[
    OptimizationMode,
    OptimizationWeights | None,
]:
    # Reconstruct a validated optimization objective and optional weights.

    mode_value = optimization_data["mode"]

    if mode_value not in VALID_OPTIMIZATION_MODES:
        raise ValueError(f"Unsupported scenario optimization mode: {mode_value}")

    optimization_mode = cast(
        OptimizationMode,
        mode_value,
    )

    weights_data_value = optimization_data.get("weights")

    optimization_weights = None

    if weights_data_value is not None:
        weights_data = require_json_object(
            weights_data_value,
            "Optimization weights",
        )

        optimization_weights = OptimizationWeights(
            thickness_weight=weights_data["thickness_weight"],
            mass_weight=weights_data["mass_weight"],
            cost_weight=weights_data["cost_weight"],
        )

    return (
        optimization_mode,
        optimization_weights,
    )


def deterministic_settings_to_dict(
    settings: DeterministicSettings,
) -> dict[str, Any]:
    # Serialize deterministic backend settings.

    return {
        "apply_buildup": (settings.apply_buildup),
        "calculation_max_thickness_cm": (settings.calculation_max_thickness_cm),
    }


def deterministic_settings_from_dict(
    settings_data: dict[str, Any],
) -> DeterministicSettings:
    # Reconstruct deterministic backend settings.

    return DeterministicSettings(
        apply_buildup=(
            settings_data.get(
                "apply_buildup",
                False,
            )
        ),
        calculation_max_thickness_cm=(
            settings_data.get("calculation_max_thickness_cm")
        ),
    )


def require_material_optimization_fields(
    scenario: ShieldingScenario,
) -> tuple[
    TargetSpec,
    DesignConstraints,
    OptimizationMode,
]:
    # Narrow fields that are optional on the shared scenario model but are
    # required by material-optimization mode.

    if scenario.calculation_mode != "material_optimization":
        raise ValueError("Scenario serialization expected material_optimization mode.")

    target = scenario.target
    constraints = scenario.constraints
    optimization_mode = scenario.optimization_mode

    if target is None:
        raise ValueError("Material-optimization scenario is missing its target.")

    if constraints is None:
        raise ValueError("Material-optimization scenario is missing its constraints.")

    if optimization_mode is None:
        raise ValueError(
            "Material-optimization scenario is missing its optimization mode."
        )

    return (
        target,
        constraints,
        optimization_mode,
    )


def scenario_to_dict(
    scenario: ShieldingScenario,
) -> dict[str, Any]:
    # Convert one validated scenario into its mode-specific JSON structure.

    scenario_data: dict[
        str,
        Any,
    ] = {
        "schema_version": (scenario.schema_version),
        "scenario_id": (scenario.scenario_id),
        "description": (scenario.description),
        "calculation_mode": (scenario.calculation_mode),
        "source": source_spec_to_dict(scenario.source),
        "geometry": geometry_to_dict(scenario.geometry),
    }

    if scenario.calculation_mode == "material_optimization":
        (
            target,
            constraints,
            optimization_mode,
        ) = require_material_optimization_fields(scenario)

        scenario_data.update(
            {
                "candidate_material_keys": list(scenario.candidate_material_keys),
                "target": target_to_dict(target),
                "constraints": constraints_to_dict(constraints),
                "optimization": optimization_to_dict(
                    optimization_mode,
                    scenario.optimization_weights,
                ),
            }
        )

    elif scenario.calculation_mode == "fixed_shield_response":
        scenario_data["target"] = (
            None if scenario.target is None else target_to_dict(scenario.target)
        )

    else:
        raise ValueError("Unsupported scenario calculation mode for serialization.")

    scenario_data["deterministic_settings"] = deterministic_settings_to_dict(
        scenario.deterministic_settings
    )

    return scenario_data


def scenario_from_dict(
    scenario_data: dict[str, Any],
) -> ShieldingScenario:
    # Reconstruct a complete validated ShieldingScenario from JSON data.
    #
    # Nested models perform their own domain validation after reconstruction.

    schema_version_value = scenario_data["schema_version"]

    if not isinstance(
        schema_version_value,
        str,
    ):
        raise ValueError("Scenario schema version must be a string.")

    if schema_version_value not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported scenario schema version: {schema_version_value}")

    calculation_mode_value = scenario_data["calculation_mode"]

    if calculation_mode_value not in VALID_SCENARIO_CALCULATION_MODES:
        raise ValueError(
            f"Unsupported scenario calculation mode: {calculation_mode_value}"
        )

    calculation_mode = cast(
        ScenarioCalculationMode,
        calculation_mode_value,
    )

    source_data = require_json_object(
        scenario_data["source"],
        "Scenario source",
    )

    geometry_data = require_json_object(
        scenario_data["geometry"],
        "Scenario geometry",
    )

    settings_data = require_json_object(
        scenario_data["deterministic_settings"],
        "Deterministic settings",
    )

    source = source_spec_from_dict(source_data)

    geometry = geometry_from_dict(geometry_data)

    deterministic_settings = deterministic_settings_from_dict(settings_data)

    if calculation_mode == "material_optimization":
        target_data_value = scenario_data["target"]

    else:
        target_data_value = scenario_data.get("target")

    target = None

    if target_data_value is not None:
        target_data = require_json_object(
            target_data_value,
            "Scenario target",
        )

        target = target_from_dict(target_data)

    if calculation_mode == "material_optimization":
        candidate_material_keys = require_json_string_list(
            scenario_data["candidate_material_keys"],
            "Candidate material keys",
        )

        constraints_data = require_json_object(
            scenario_data["constraints"],
            "Scenario constraints",
        )

        optimization_data = require_json_object(
            scenario_data["optimization"],
            "Scenario optimization settings",
        )

        (
            optimization_mode,
            optimization_weights,
        ) = optimization_from_dict(optimization_data)

        return ShieldingScenario(
            schema_version=(schema_version_value),
            scenario_id=scenario_data["scenario_id"],
            description=scenario_data["description"],
            calculation_mode=(calculation_mode),
            source=source,
            geometry=geometry,
            candidate_material_keys=(candidate_material_keys),
            target=target,
            constraints=constraints_from_dict(constraints_data),
            optimization_mode=(optimization_mode),
            optimization_weights=(optimization_weights),
            deterministic_settings=(deterministic_settings),
        )

    candidate_material_keys = require_json_string_list(
        scenario_data.get(
            "candidate_material_keys",
            [],
        ),
        "Candidate material keys",
    )

    constraints = None

    constraints_data_value = scenario_data.get("constraints")

    if constraints_data_value is not None:
        constraints_data = require_json_object(
            constraints_data_value,
            "Scenario constraints",
        )

        constraints = constraints_from_dict(constraints_data)

    optimization_mode = None
    optimization_weights = None

    optimization_data_value = scenario_data.get("optimization")

    if optimization_data_value is not None:
        optimization_data = require_json_object(
            optimization_data_value,
            "Scenario optimization settings",
        )

        if len(optimization_data) > 0:
            (
                optimization_mode,
                optimization_weights,
            ) = optimization_from_dict(optimization_data)

    return ShieldingScenario(
        schema_version=(schema_version_value),
        scenario_id=scenario_data["scenario_id"],
        description=scenario_data["description"],
        calculation_mode=(calculation_mode),
        source=source,
        geometry=geometry,
        candidate_material_keys=(candidate_material_keys),
        target=target,
        constraints=constraints,
        optimization_mode=(optimization_mode),
        optimization_weights=(optimization_weights),
        deterministic_settings=(deterministic_settings),
    )


def save_scenario(
    scenario: ShieldingScenario,
    file_path: str | Path,
) -> Path:
    # Save a validated scenario as formatted UTF-8 JSON.
    #
    # Parent directories are created automatically so callers can write
    # directly to paths such as scenarios/cs137_reference.json.

    output_path = Path(file_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenario_data = scenario_to_dict(scenario)

    with output_path.open(
        mode="w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            scenario_data,
            output_file,
            indent=2,
            ensure_ascii=False,
        )

        # End text files with a newline for cleaner Git diffs.
        output_file.write("\n")

    return output_path


def load_scenario(
    file_path: str | Path,
) -> ShieldingScenario:
    # Load and validate one scenario from a UTF-8 JSON file.

    input_path = Path(file_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Scenario file does not exist: {input_path}")

    if not input_path.is_file():
        raise ValueError(f"Scenario path is not a file: {input_path}")

    try:
        with input_path.open(
            mode="r",
            encoding="utf-8",
        ) as input_file:
            scenario_data = json.load(input_file)

    except json.JSONDecodeError as error:
        raise ValueError(f"Scenario file contains invalid JSON: {error}") from error

    if not isinstance(
        scenario_data,
        dict,
    ):
        raise ValueError("Scenario JSON root must be an object.")

    try:
        return scenario_from_dict(scenario_data)

    except KeyError as error:
        missing_field = error.args[0]

        raise ValueError(
            f"Scenario JSON is missing required field: {missing_field}"
        ) from error
