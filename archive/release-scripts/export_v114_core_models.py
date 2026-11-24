# Export and inspect all eight V1.14 core OpenMC models without transport.

from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


from shielding.monte_carlo.runner import export_openmc_benchmark_model
from shielding.monte_carlo.settings_io import load_openmc_settings
from shielding.scenarios.json_io import load_scenario


METADATA_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "development"
    / "case_generation"
    / "v114_core_case_metadata.json"
)

SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v114_smoke.json"
)

OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "development"
    / "model_exports"
)

SUMMARY_PATH = OUTPUT_ROOT / "v114_core_model_export_summary.json"


def main() -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    cases = metadata.get("cases")

    if not isinstance(cases, list) or len(cases) != 8:
        raise RuntimeError(
            "V1.14 core metadata must contain exactly eight cases."
        )

    settings_profile = load_openmc_settings(SETTINGS_PATH)
    exported_records: list[dict[str, object]] = []

    for case_record in cases:
        if not isinstance(case_record, dict):
            raise RuntimeError("V1.14 case metadata entries must be objects.")

        case_id = case_record["case_id"]
        scenario_relative_path = case_record["scenario_path"]

        if not isinstance(case_id, str) or not isinstance(
            scenario_relative_path,
            str,
        ):
            raise RuntimeError("V1.14 case metadata fields have invalid types.")

        scenario_path = REPOSITORY_ROOT / scenario_relative_path
        scenario = load_scenario(scenario_path)

        output_directory = OUTPUT_ROOT / f"{case_id}__{settings_profile.profile_name}"

        model_xml_path = export_openmc_benchmark_model(
            scenario=scenario,
            settings_profile=settings_profile,
            output_directory=output_directory,
            evaluation_shell_thickness_cm=1.0,
            overwrite=True,
        )

        summary_path = output_directory / "model_export_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

        exported_records.append(
            {
                "case_id": case_id,
                "scenario_path": scenario_relative_path,
                "model_xml_path": model_xml_path.relative_to(
                    REPOSITORY_ROOT
                ).as_posix(),
                "summary_path": summary_path.relative_to(
                    REPOSITORY_ROOT
                ).as_posix(),
                "material_keys": summary["material_keys"],
                "cell_count": summary["cell_count"],
                "surface_count": summary["surface_count"],
                "tally_ids": summary["tally_ids"],
            }
        )

        print(f"PASS: {case_id}")

    aggregate_summary = {
        "record_type": "v114_core_model_export_summary",
        "version": "1.14",
        "transport_executed": False,
        "settings_profile_name": settings_profile.profile_name,
        "case_count": len(exported_records),
        "cases": exported_records,
    }

    SUMMARY_PATH.write_text(
        json.dumps(aggregate_summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "PASS: All eight V1.14 core OpenMC models were exported and "
        "inspected without particle transport."
    )
    print(f"Aggregate summary: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
