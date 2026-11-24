# V1.13 OpenMC settings profile serialization and file I/O.
#
# OpenMCSettings describes numerical execution choices rather than the
# physical shielding problem. These profiles therefore live under
# config/openmc instead of inside scenario JSON files.
#
# This module contains no OpenMC import.


from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shielding.monte_carlo.settings import (
    VALID_ELECTRON_TREATMENTS,
    ElectronTreatment,
    OpenMCSettings,
)

OPENMC_SETTINGS_SCHEMA_VERSION = "1.0"

SUPPORTED_OPENMC_SETTINGS_SCHEMA_VERSIONS = {
    OPENMC_SETTINGS_SCHEMA_VERSION,
}


def require_json_object(
    value: Any,
    description: str,
) -> dict[str, Any]:
    # Require a nested JSON value to be an object.

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(f"{description} must be a JSON object.")

    return value


def require_json_number_list(
    value: Any,
    description: str,
) -> list[float]:
    # Require a JSON array containing numerical values only.
    #
    # Boolean values are rejected because bool is a subclass of int.

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"{description} must be a list.")

    numbers: list[float] = []

    for item in value:
        if isinstance(item, bool) or not isinstance(
            item,
            (int, float),
        ):
            raise ValueError(f"{description} must contain only numerical values.")

        numbers.append(float(item))

    return numbers


def require_json_integer_list(
    value: Any,
    description: str,
) -> list[int]:
    # Require a JSON array containing integer values only.

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"{description} must be a list.")

    integers: list[int] = []

    for item in value:
        if isinstance(item, bool) or not isinstance(
            item,
            int,
        ):
            raise ValueError(f"{description} must contain only integers.")

        integers.append(item)

    return integers


def openmc_settings_to_dict(
    settings: OpenMCSettings,
) -> dict[str, Any]:
    # Convert validated settings into a structured JSON representation.
    #
    # The dataclass is flat for convenient Python access. The JSON structure
    # groups related values for human readability.

    return {
        "schema_version": (OPENMC_SETTINGS_SCHEMA_VERSION),
        "profile_name": (settings.profile_name),
        "execution": {
            "particles_per_batch": (settings.particles_per_batch),
            "batches": (settings.batches),
            "random_seed": (settings.random_seed),
            "threads": (settings.threads),
        },
        "physics": {
            "electron_treatment": (settings.electron_treatment),
            "atomic_relaxation": (settings.atomic_relaxation),
            "photon_cutoff_energy_ev": (settings.photon_cutoff_energy_ev),
        },
        "geometry": {
            "outer_boundary_radius_cm": (settings.outer_boundary_radius_cm),
        },
        "tallies": {
            "energy_bin_boundaries_ev": list(settings.energy_bin_boundaries_ev),
        },
        "output": {
            "statepoint_batches": list(settings.statepoint_batches),
        },
    }


def openmc_settings_from_dict(
    settings_data: dict[str, Any],
) -> OpenMCSettings:
    # Reconstruct validated OpenMC numerical settings from JSON data.

    schema_version = settings_data["schema_version"]

    if not isinstance(
        schema_version,
        str,
    ):
        raise ValueError("OpenMC settings schema version must be a string.")

    if schema_version not in SUPPORTED_OPENMC_SETTINGS_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported OpenMC settings schema version: {schema_version}"
        )

    execution_data = require_json_object(
        settings_data["execution"],
        "OpenMC execution settings",
    )

    physics_data = require_json_object(
        settings_data["physics"],
        "OpenMC physics settings",
    )

    geometry_data = require_json_object(
        settings_data["geometry"],
        "OpenMC geometry settings",
    )

    tally_data = require_json_object(
        settings_data["tallies"],
        "OpenMC tally settings",
    )

    output_data = require_json_object(
        settings_data["output"],
        "OpenMC output settings",
    )

    electron_treatment_value = physics_data["electron_treatment"]

    if electron_treatment_value not in VALID_ELECTRON_TREATMENTS:
        raise ValueError(
            f"Unsupported OpenMC electron treatment: {electron_treatment_value}"
        )

    electron_treatment = cast(
        ElectronTreatment,
        electron_treatment_value,
    )

    return OpenMCSettings(
        profile_name=settings_data["profile_name"],
        particles_per_batch=(execution_data["particles_per_batch"]),
        batches=execution_data["batches"],
        random_seed=execution_data["random_seed"],
        threads=execution_data["threads"],
        energy_bin_boundaries_ev=(
            require_json_number_list(
                tally_data["energy_bin_boundaries_ev"],
                "OpenMC energy-bin boundaries",
            )
        ),
        electron_treatment=(electron_treatment),
        atomic_relaxation=(physics_data["atomic_relaxation"]),
        photon_cutoff_energy_ev=(physics_data["photon_cutoff_energy_ev"]),
        outer_boundary_radius_cm=(geometry_data["outer_boundary_radius_cm"]),
        statepoint_batches=(
            require_json_integer_list(
                output_data["statepoint_batches"],
                "OpenMC statepoint batches",
            )
        ),
    )


def save_openmc_settings(
    settings: OpenMCSettings,
    file_path: str | Path,
) -> Path:
    # Save one validated settings profile as formatted UTF-8 JSON.

    output_path = Path(file_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        mode="w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            openmc_settings_to_dict(settings),
            output_file,
            indent=2,
            ensure_ascii=False,
        )

        output_file.write("\n")

    return output_path


def load_openmc_settings(
    file_path: str | Path,
) -> OpenMCSettings:
    # Load and validate one OpenMC settings profile.

    input_path = Path(file_path)

    if not input_path.exists():
        raise FileNotFoundError(f"OpenMC settings file does not exist: {input_path}")

    if not input_path.is_file():
        raise ValueError(f"OpenMC settings path is not a file: {input_path}")

    try:
        with input_path.open(
            mode="r",
            encoding="utf-8",
        ) as input_file:
            settings_data = json.load(input_file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"OpenMC settings file contains invalid JSON: {error}"
        ) from error

    if not isinstance(
        settings_data,
        dict,
    ):
        raise ValueError("OpenMC settings JSON root must be an object.")

    try:
        return openmc_settings_from_dict(settings_data)

    except KeyError as error:
        missing_field = error.args[0]

        raise ValueError(
            f"OpenMC settings JSON is missing required field: {missing_field}"
        ) from error
