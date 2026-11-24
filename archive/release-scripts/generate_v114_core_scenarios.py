# Generate and deterministically verify the eight V1.14 core benchmark cases.
#
# This script:
#
#   - resolves requested MFP values into physical centimeter thicknesses;
#   - writes eight schema-1.1 fixed-shield scenario files;
#   - round-trips every scenario through scenario_io;
#   - runs every deterministic fixed-shield calculation;
#   - verifies that G-P buildup is available for every core case;
#   - writes JSON and CSV case metadata;
#   - performs no OpenMC transport.


from __future__ import annotations


import csv
import json
from pathlib import Path


REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)




from shielding.benchmark.cases import (
    create_v114_core_case_definitions,
    resolve_benchmark_cases,
    resolved_benchmark_case_to_dict,
)
from shielding.scenarios.fixed_shield import (
    calculate_fixed_shield_response,
)
from shielding.scenarios.json_io import (
    load_scenario,
    save_scenario,
)


SCENARIO_DIRECTORY = (
    REPOSITORY_ROOT
    / "scenarios"
    / "v1.14"
)

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "development"
    / "case_generation"
)

METADATA_JSON_PATH = (
    OUTPUT_DIRECTORY
    / "v114_core_case_metadata.json"
)

METADATA_CSV_PATH = (
    OUTPUT_DIRECTORY
    / "v114_core_case_metadata.csv"
)


CSV_FIELDNAMES = [
    "case_id",
    "isotope_key",
    "activity_bq",
    "material_key",
    "material_name",
    "reference_energy_mev",
    "target_mean_free_paths",
    "mu_over_rho_cm2_per_g",
    "density_g_per_cm3",
    "linear_attenuation_coefficient_per_cm",
    "physical_thickness_cm",
    "reconstructed_mean_free_paths",
    "source_cavity_radius_cm",
    "outer_shield_radius_cm",
    "evaluation_radius_cm",
    "apply_gp_buildup",
    "scenario_path",
    "deterministic_buildup_status",
    "deterministic_uncollided_air_kerma_rate_gy_per_s",
    "deterministic_gp_air_kerma_rate_gy_per_s",
]


def main() -> None:
    definitions = (
        create_v114_core_case_definitions()
    )

    resolved_cases = (
        resolve_benchmark_cases(
            definitions
        )
    )

    if len(
        resolved_cases
    ) != 8:
        raise RuntimeError(
            "V1.14 core matrix must contain "
            "exactly eight cases."
        )

    SCENARIO_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata_rows: list[
        dict[str, object]
    ] = []

    for resolved_case in (
        resolved_cases
    ):
        scenario_path = (
            SCENARIO_DIRECTORY
            / (
                resolved_case
                .definition
                .case_id
                + ".json"
            )
        )

        save_scenario(
            resolved_case.scenario,
            scenario_path,
        )

        loaded_scenario = (
            load_scenario(
                scenario_path
            )
        )

        if (
            loaded_scenario
            != resolved_case.scenario
        ):
            raise RuntimeError(
                "Scenario JSON round trip changed "
                f"{resolved_case.definition.case_id}."
            )

        deterministic_result = (
            calculate_fixed_shield_response(
                loaded_scenario
            )
        )

        source_response = (
            deterministic_result
            .source_air_kerma_result
        )

        if (
            resolved_case
            .definition
            .apply_gp_buildup
            and source_response.buildup_status
            != "applied"
        ):
            raise RuntimeError(
                "V1.14 core case requires an applied "
                "G-P response, but it was unavailable "
                f"for {resolved_case.definition.case_id}."
            )

        metadata_row = (
            resolved_benchmark_case_to_dict(
                resolved_case
            )
        )

        metadata_row.update(
            {
                "scenario_path": (
                    scenario_path
                    .relative_to(
                        REPOSITORY_ROOT
                    )
                    .as_posix()
                ),
                "deterministic_buildup_status": (
                    source_response
                    .buildup_status
                ),
                "deterministic_uncollided_air_kerma_rate_gy_per_s": (
                    source_response
                    .total_uncollided_collision_air_kerma_rate_gy_per_s
                ),
                "deterministic_gp_air_kerma_rate_gy_per_s": (
                    source_response
                    .total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
                ),
            }
        )

        metadata_rows.append(
            metadata_row
        )

    metadata_document = {
        "record_type": (
            "v114_core_benchmark_case_metadata"
        ),
        "version": "1.14",
        "transport_executed": False,
        "case_count": len(
            metadata_rows
        ),
        "reference_energy_basis": (
            "Explicit case-level photon energy "
            "used to calculate physical MFP thickness."
        ),
        "cases": metadata_rows,
    }

    METADATA_JSON_PATH.write_text(
        json.dumps(
            metadata_document,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with METADATA_CSV_PATH.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=(
                CSV_FIELDNAMES
            ),
        )

        writer.writeheader()

        for metadata_row in (
            metadata_rows
        ):
            writer.writerow(
                metadata_row
            )

    print()
    print("=" * 88)
    print("V1.14 CORE BENCHMARK CASE GENERATION")
    print("=" * 88)

    for metadata_row in (
        metadata_rows
    ):
        print(
            f"{metadata_row['case_id']:<38} "
            f"{metadata_row['physical_thickness_cm']:>14.8f} cm  "
            f"{metadata_row['reconstructed_mean_free_paths']:>8.4f} MFP  "
            f"G-P {metadata_row['deterministic_buildup_status']}"
        )

    print("-" * 88)

    print(
        "Scenario files: "
        f"{SCENARIO_DIRECTORY}"
    )

    print(
        "Metadata JSON: "
        f"{METADATA_JSON_PATH}"
    )

    print(
        "Metadata CSV: "
        f"{METADATA_CSV_PATH}"
    )

    print(
        "OpenMC transport executed: No"
    )

    print(
        "PASS: Eight V1.14 core cases were "
        "resolved, serialized, round-tripped, "
        "and evaluated deterministically."
    )


if __name__ == "__main__":
    main()