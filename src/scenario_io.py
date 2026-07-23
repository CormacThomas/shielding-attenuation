# V1.11 scenario serialization and file I/O.
#
# This module converts validated ShieldingScenario objects into a stable,
# human-readable JSON structure.
#
# Deserialization will be added after the output structure has been reviewed
# and tested.
#
# The JSON format uses explicit type fields for sources, geometry, and targets.
# This prevents the loader from having to guess which dataclass should be
# reconstructed from a group of numerical fields.


import json
from pathlib import Path
from typing import Any

from geometry_models import ConcentricSphericalGeometry
from scenario_models import (
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ShieldingScenario,
)
from target_models import (
    FluxTarget,
    ReductionFactorTarget,
    TransmissionTarget,
)
from geometry_models import (
    ConcentricSphericalGeometry,
    ShieldLayerSpec,
)
from optimization_models import (
    DesignConstraints,
    OptimizationWeights,
)
from scenario_models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ShieldingScenario,
)
SUPPORTED_SCHEMA_VERSIONS = {
    "1.0",
}


def source_spec_to_dict(
    source_spec: ManualPhotonSourceSpec | IsotopeSourceSpec,
) -> dict[str, Any]:
    # Convert a source specification into an explicitly typed JSON object.

    if isinstance(source_spec, ManualPhotonSourceSpec):
        return {
            "type": "manual",
            "photon_energy_mev": source_spec.photon_energy_mev,
            "photon_rate_per_s": source_spec.photon_rate_per_s,
        }

    if isinstance(source_spec, IsotopeSourceSpec):
        return {
            "type": "isotope",
            "isotope_key": source_spec.isotope_key,
            "activity_bq": source_spec.activity_bq,
        }

    raise ValueError(
        "Unsupported source specification for serialization."
    )


def source_spec_from_dict(
    source_data: dict[str, Any],
) -> ManualPhotonSourceSpec | IsotopeSourceSpec:
    # Reconstruct a validated source specification from JSON data.

    source_type = source_data.get("type")

    if source_type == "manual":
        return ManualPhotonSourceSpec(
            photon_energy_mev=source_data[
                "photon_energy_mev"
            ],
            photon_rate_per_s=source_data[
                "photon_rate_per_s"
            ],
        )

    if source_type == "isotope":
        return IsotopeSourceSpec(
            isotope_key=source_data[
                "isotope_key"
            ],
            activity_bq=source_data[
                "activity_bq"
            ],
        )

    raise ValueError(
        f"Unsupported scenario source type: {source_type}"
    )


def geometry_to_dict(
    geometry: ConcentricSphericalGeometry,
) -> dict[str, Any]:
    # Serialize physical geometry inputs only.
    #
    # Derived shell radii are not stored because they can be reconstructed
    # deterministically from the cavity radius and ordered layer thicknesses.

    return {
        "type": "concentric_spherical",
        "source_cavity_radius_cm": (
            geometry.source_cavity_radius_cm
        ),
        "evaluation_radius_cm": (
            geometry.evaluation_radius_cm
        ),
        "layers": [
            {
                "material_key": layer.material_key,
                "thickness_cm": layer.thickness_cm,
            }
            for layer in geometry.layers
        ],
    }


def geometry_from_dict(
    geometry_data: dict[str, Any],
) -> ConcentricSphericalGeometry:
    # Reconstruct the supported V1.11 geometry from physical JSON inputs.

    geometry_type = geometry_data.get("type")

    if geometry_type != "concentric_spherical":
        raise ValueError(
            "Unsupported scenario geometry type: "
            f"{geometry_type}"
        )

    layer_data_list = geometry_data.get(
        "layers",
        [],
    )

    if not isinstance(layer_data_list, list):
        raise ValueError(
            "Scenario geometry layers must be a list."
        )

    layers = [
        ShieldLayerSpec(
            material_key=layer_data[
                "material_key"
            ],
            thickness_cm=layer_data[
                "thickness_cm"
            ],
        )
        for layer_data in layer_data_list
    ]

    return ConcentricSphericalGeometry(
        source_cavity_radius_cm=geometry_data[
            "source_cavity_radius_cm"
        ],
        evaluation_radius_cm=geometry_data[
            "evaluation_radius_cm"
        ],
        layers=layers,
    )


def target_to_dict(
    target: (
        FluxTarget
        | ReductionFactorTarget
        | TransmissionTarget
    ),
) -> dict[str, Any]:
    # Convert a validated target object into an explicitly typed JSON object.

    if isinstance(target, FluxTarget):
        return {
            "type": "flux",
            "target_flux": target.target_flux,
        }

    if isinstance(target, ReductionFactorTarget):
        return {
            "type": "reduction_factor",
            "reduction_factor": target.reduction_factor,
        }

    if isinstance(target, TransmissionTarget):
        return {
            "type": "transmission",
            "target_transmission": (
                target.target_transmission
            ),
        }

    raise ValueError(
        "Unsupported target type for serialization."
    )


def target_from_dict(
    target_data: dict[str, Any],
) -> (
    FluxTarget
    | ReductionFactorTarget
    | TransmissionTarget
):
    # Reconstruct one validated target from its explicit JSON type.

    target_type = target_data.get("type")

    if target_type == "flux":
        return FluxTarget(
            target_flux=target_data[
                "target_flux"
            ]
        )

    if target_type == "reduction_factor":
        return ReductionFactorTarget(
            reduction_factor=target_data[
                "reduction_factor"
            ]
        )

    if target_type == "transmission":
        return TransmissionTarget(
            target_transmission=target_data[
                "target_transmission"
            ]
        )

    raise ValueError(
        f"Unsupported scenario target type: {target_type}"
    )


def scenario_to_dict(
    scenario: ShieldingScenario,
) -> dict[str, Any]:
    # Convert one validated scenario into the complete V1.11 JSON schema.

    constraints = scenario.constraints
    settings = scenario.deterministic_settings
    weights = scenario.optimization_weights

    optimization_data: dict[str, Any] = {
        "mode": scenario.optimization_mode,
        "weights": None,
    }

    if weights is not None:
        optimization_data["weights"] = {
            "thickness_weight": weights.thickness_weight,
            "mass_weight": weights.mass_weight,
            "cost_weight": weights.cost_weight,
        }

    return {
        "schema_version": scenario.schema_version,
        "scenario_id": scenario.scenario_id,
        "description": scenario.description,
        "calculation_mode": scenario.calculation_mode,
        "source": source_spec_to_dict(
            scenario.source
        ),
        "geometry": geometry_to_dict(
            scenario.geometry
        ),
        "candidate_material_keys": list(
            scenario.candidate_material_keys
        ),
        "target": target_to_dict(
            scenario.target
        ),
        "constraints": {
            "max_thickness_cm": (
                constraints.max_thickness_cm
            ),
            "max_mass_per_area_g_per_cm2": (
                constraints
                .max_mass_per_area_g_per_cm2
            ),
            "max_relative_cost_index_per_area": (
                constraints
                .max_relative_cost_index_per_area
            ),
        },
        "optimization": optimization_data,
        "deterministic_settings": {
            "apply_buildup": settings.apply_buildup,
            "calculation_max_thickness_cm": (
                settings.calculation_max_thickness_cm
            ),
        },
    }


def scenario_from_dict(
    scenario_data: dict[str, Any],
) -> ShieldingScenario:
    # Reconstruct a complete validated ShieldingScenario from JSON data.
    #
    # Nested models perform their own domain validation after reconstruction.

    schema_version = scenario_data.get(
        "schema_version"
    )

    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            "Unsupported scenario schema version: "
            f"{schema_version}"
        )

    source_data = scenario_data[
        "source"
    ]

    geometry_data = scenario_data[
        "geometry"
    ]

    target_data = scenario_data[
        "target"
    ]

    constraints_data = scenario_data[
        "constraints"
    ]

    optimization_data = scenario_data[
        "optimization"
    ]

    settings_data = scenario_data[
        "deterministic_settings"
    ]

    if not isinstance(source_data, dict):
        raise ValueError(
            "Scenario source must be a JSON object."
        )

    if not isinstance(geometry_data, dict):
        raise ValueError(
            "Scenario geometry must be a JSON object."
        )

    if not isinstance(target_data, dict):
        raise ValueError(
            "Scenario target must be a JSON object."
        )

    if not isinstance(constraints_data, dict):
        raise ValueError(
            "Scenario constraints must be a JSON object."
        )

    if not isinstance(optimization_data, dict):
        raise ValueError(
            "Scenario optimization settings must be a JSON object."
        )

    if not isinstance(settings_data, dict):
        raise ValueError(
            "Deterministic settings must be a JSON object."
        )

    weights_data = optimization_data.get(
        "weights"
    )

    optimization_weights = None

    if weights_data is not None:
        if not isinstance(weights_data, dict):
            raise ValueError(
                "Optimization weights must be a JSON object or null."
            )

        optimization_weights = OptimizationWeights(
            thickness_weight=weights_data[
                "thickness_weight"
            ],
            mass_weight=weights_data[
                "mass_weight"
            ],
            cost_weight=weights_data[
                "cost_weight"
            ],
        )

    return ShieldingScenario(
        schema_version=schema_version,
        scenario_id=scenario_data[
            "scenario_id"
        ],
        description=scenario_data[
            "description"
        ],
        calculation_mode=scenario_data[
            "calculation_mode"
        ],
        source=source_spec_from_dict(
            source_data
        ),
        geometry=geometry_from_dict(
            geometry_data
        ),
        candidate_material_keys=list(
            scenario_data[
                "candidate_material_keys"
            ]
        ),
        target=target_from_dict(
            target_data
        ),
        constraints=DesignConstraints(
            max_thickness_cm=constraints_data.get(
                "max_thickness_cm"
            ),
            max_mass_per_area_g_per_cm2=(
                constraints_data.get(
                    "max_mass_per_area_g_per_cm2"
                )
            ),
            max_relative_cost_index_per_area=(
                constraints_data.get(
                    "max_relative_cost_index_per_area"
                )
            ),
        ),
        optimization_mode=optimization_data[
            "mode"
        ],
        optimization_weights=optimization_weights,
        deterministic_settings=DeterministicSettings(
            apply_buildup=settings_data.get(
                "apply_buildup",
                False,
            ),
            calculation_max_thickness_cm=(
                settings_data.get(
                    "calculation_max_thickness_cm"
                )
            ),
        ),
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

    scenario_data = scenario_to_dict(
        scenario
    )

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
        raise FileNotFoundError(
            f"Scenario file does not exist: {input_path}"
        )

    if not input_path.is_file():
        raise ValueError(
            f"Scenario path is not a file: {input_path}"
        )

    try:
        with input_path.open(
            mode="r",
            encoding="utf-8",
        ) as input_file:
            scenario_data = json.load(
                input_file
            )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Scenario file contains invalid JSON: "
            f"{error}"
        ) from error

    if not isinstance(scenario_data, dict):
        raise ValueError(
            "Scenario JSON root must be an object."
        )

    try:
        return scenario_from_dict(
            scenario_data
        )

    except KeyError as error:
        missing_field = error.args[0]

        raise ValueError(
            "Scenario JSON is missing required field: "
            f"{missing_field}"
        ) from error