# Aggregate the completed V1.14 core deterministic-versus-OpenMC matrix.
#
# This script has no OpenMC dependency. It reads the authoritative case
# metadata plus the processed production records, verifies consistency, and
# writes compact JSON/CSV/text outputs for plotting and reporting.
#
# Run from the repository root:
#
#   python examples/aggregate_v114_core_results.py

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

CASE_METADATA_PATH = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "development"
    / "case_generation"
    / "v114_core_case_metadata.json"
)

PRODUCTION_ROOT = REPOSITORY_ROOT / "results" / "v1.14" / "production"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "results" / "v1.14" / "analysis"
OUTPUT_JSON_PATH = OUTPUT_DIRECTORY / "v114_core_matrix.json"
OUTPUT_CSV_PATH = OUTPUT_DIRECTORY / "v114_core_matrix.csv"
OUTPUT_SUMMARY_PATH = OUTPUT_DIRECTORY / "v114_core_matrix_summary.txt"

EXPECTED_CASE_COUNT = 8
EXPECTED_SETTINGS_PROFILE = "v114_production"
EXPECTED_TOTAL_SOURCE_HISTORIES = 5_000_000

CSV_FIELDNAMES = [
    "case_id",
    "isotope_key",
    "material_key",
    "material_name",
    "reference_energy_mev",
    "target_mean_free_paths",
    "physical_thickness_cm",
    "density_g_per_cm3",
    "deterministic_uncollided_microgy_per_h",
    "deterministic_gp_microgy_per_h",
    "gp_buildup_factor",
    "openmc_direct_microgy_per_h",
    "openmc_standard_deviation_microgy_per_h",
    "openmc_relative_uncertainty",
    "openmc_buildup_ratio",
    "openmc_vs_uncollided_relative_difference",
    "openmc_vs_gp_relative_difference",
    "spectrum_folded_microgy_per_h",
    "direct_vs_folded_relative_difference",
    "required_uncertainty_pass",
    "preferred_uncertainty_pass",
    "direct_vs_folded_pass",
    "total_source_histories",
    "runtime_seconds",
    "openmc_version",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required V1.14 analysis input does not exist: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}.")

    return value


def number(value: Any, description: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{description} must be numerical.")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{description} must be finite.")

    return result


def require_close(actual: float, expected: float, description: str) -> None:
    if not math.isclose(
        actual,
        expected,
        rel_tol=1.0e-10,
        abs_tol=1.0e-20,
    ):
        raise RuntimeError(
            f"{description} mismatch: {actual:.17g} versus {expected:.17g}."
        )


def case_paths(case_id: str) -> dict[str, Path]:
    run_directory = (
        PRODUCTION_ROOT
        / f"{case_id}__{EXPECTED_SETTINGS_PROFILE}"
    )
    processed_directory = run_directory / "processed" / "final"

    return {
        "response": processed_directory / "openmc_response.json",
        "comparison": processed_directory / "deterministic_openmc_comparison.json",
        "manifest": run_directory / "run_manifest.json",
    }


def create_case_record(metadata: dict[str, Any]) -> dict[str, Any]:
    case_id = metadata.get("case_id")
    require(isinstance(case_id, str) and case_id.strip() != "", "Invalid case ID.")
    case_id = case_id.strip()

    paths = case_paths(case_id)
    response = load_json_object(paths["response"])
    comparison = load_json_object(paths["comparison"])
    manifest = load_json_object(paths["manifest"])

    require(response.get("record_type") == "openmc_response", f"{case_id}: bad response record type.")
    require(comparison.get("record_type") == "deterministic_openmc_comparison", f"{case_id}: bad comparison record type.")
    require(manifest.get("record_type") == "openmc_run_manifest", f"{case_id}: bad manifest record type.")

    for record_name, record in (
        ("response", response),
        ("comparison", comparison),
        ("manifest", manifest),
    ):
        require(record.get("scenario_id") == case_id, f"{case_id}: {record_name} scenario mismatch.")
        require(
            record.get("settings_profile_name") == EXPECTED_SETTINGS_PROFILE,
            f"{case_id}: {record_name} settings-profile mismatch.",
        )

    deterministic = comparison["deterministic"]
    openmc = comparison["openmc"]
    comparison_values = comparison["comparison"]
    acceptance = comparison["acceptance_checks"]
    direct_response = response["direct_response"]
    spectrum_summary = response["spectrum_summary"]
    manifest_execution = manifest["execution"]
    manifest_software = manifest["software"]

    deterministic_uncollided = number(
        deterministic["uncollided_response_rate_microgy_per_h"],
        f"{case_id}: deterministic uncollided response",
    )
    deterministic_gp = number(
        deterministic["gp_adjusted_response_rate_microgy_per_h"],
        f"{case_id}: deterministic G-P response",
    )
    require(deterministic.get("buildup_status") == "applied", f"{case_id}: G-P buildup was not applied.")
    require(deterministic_uncollided > 0.0 and deterministic_gp > 0.0, f"{case_id}: deterministic responses must be positive.")

    openmc_direct = number(openmc["direct_response_rate_microgy_per_h"], f"{case_id}: OpenMC direct response")
    openmc_std = number(openmc["direct_response_standard_deviation_microgy_per_h"], f"{case_id}: OpenMC standard deviation")
    openmc_uncertainty = number(openmc["relative_uncertainty"], f"{case_id}: OpenMC uncertainty")
    folded = number(openmc["spectrum_folded_response_rate_microgy_per_h"], f"{case_id}: folded response")

    require_close(
        number(direct_response["rate_microgy_per_h"], f"{case_id}: response JSON direct response"),
        openmc_direct,
        f"{case_id}: direct response cross-file check",
    )
    require_close(
        number(direct_response["relative_uncertainty"], f"{case_id}: response JSON uncertainty"),
        openmc_uncertainty,
        f"{case_id}: uncertainty cross-file check",
    )
    require_close(
        number(spectrum_summary["spectrum_folded_response_rate_microgy_per_h"], f"{case_id}: response JSON folded response"),
        folded,
        f"{case_id}: folded response cross-file check",
    )

    vs_uncollided = number(comparison_values["relative_difference_from_uncollided"], f"{case_id}: difference from uncollided")
    vs_gp = number(comparison_values["relative_difference_from_gp"], f"{case_id}: difference from G-P")
    mc_buildup = number(comparison_values["observed_monte_carlo_buildup_ratio"], f"{case_id}: MC buildup")
    direct_vs_folded = number(comparison_values["direct_vs_folded_relative_difference"], f"{case_id}: direct-vs-folded difference")

    require_close(vs_uncollided, (openmc_direct - deterministic_uncollided) / deterministic_uncollided, f"{case_id}: uncollided comparison")
    require_close(vs_gp, (openmc_direct - deterministic_gp) / deterministic_gp, f"{case_id}: G-P comparison")
    require_close(mc_buildup, openmc_direct / deterministic_uncollided, f"{case_id}: MC buildup")
    require_close(direct_vs_folded, (folded - openmc_direct) / openmc_direct, f"{case_id}: direct-vs-folded comparison")

    total_histories = manifest_execution["total_source_particles"]
    require(
        isinstance(total_histories, int) and not isinstance(total_histories, bool),
        f"{case_id}: total histories must be an integer.",
    )
    require(total_histories == EXPECTED_TOTAL_SOURCE_HISTORIES, f"{case_id}: expected {EXPECTED_TOTAL_SOURCE_HISTORIES} histories, found {total_histories}.")

    openmc_version = manifest_software.get("openmc_version")
    require(isinstance(openmc_version, str) and openmc_version.strip() != "", f"{case_id}: OpenMC version is missing.")

    required_pass = acceptance["required_uncertainty_pass"]
    preferred_pass = acceptance["preferred_uncertainty_pass"]
    folded_pass = acceptance["direct_vs_folded_pass"]
    require(all(isinstance(value, bool) for value in (required_pass, preferred_pass, folded_pass)), f"{case_id}: acceptance results must be Boolean.")

    # IMPORTANT: case-generation metadata stores deterministic point-response
    # values at the nominal 100 cm radius. The production comparison record
    # stores the matched 99.5–100.5 cm shell-volume-average deterministic
    # values, which are authoritative for this matrix.

    return {
        "case_id": case_id,
        "isotope_key": metadata["isotope_key"],
        "material_key": metadata["material_key"],
        "material_name": metadata["material_name"],
        "reference_energy_mev": number(metadata["reference_energy_mev"], f"{case_id}: reference energy"),
        "target_mean_free_paths": number(metadata["target_mean_free_paths"], f"{case_id}: target MFP"),
        "physical_thickness_cm": number(metadata["physical_thickness_cm"], f"{case_id}: thickness"),
        "density_g_per_cm3": number(metadata["density_g_per_cm3"], f"{case_id}: density"),
        "deterministic_uncollided_microgy_per_h": deterministic_uncollided,
        "deterministic_gp_microgy_per_h": deterministic_gp,
        "gp_buildup_factor": deterministic_gp / deterministic_uncollided,
        "openmc_direct_microgy_per_h": openmc_direct,
        "openmc_standard_deviation_microgy_per_h": openmc_std,
        "openmc_relative_uncertainty": openmc_uncertainty,
        "openmc_buildup_ratio": mc_buildup,
        "openmc_vs_uncollided_relative_difference": vs_uncollided,
        "openmc_vs_gp_relative_difference": vs_gp,
        "spectrum_folded_microgy_per_h": folded,
        "direct_vs_folded_relative_difference": direct_vs_folded,
        "required_uncertainty_pass": required_pass,
        "preferred_uncertainty_pass": preferred_pass,
        "direct_vs_folded_pass": folded_pass,
        "total_source_histories": total_histories,
        "runtime_seconds": number(manifest_execution["runtime_seconds"], f"{case_id}: runtime"),
        "openmc_version": openmc_version.strip(),
        "source_paths": {
            key: path.relative_to(REPOSITORY_ROOT).as_posix()
            for key, path in paths.items()
        },
    }


def create_summary(case_records: list[dict[str, Any]]) -> dict[str, Any]:
    largest_gp_error = max(
        case_records,
        key=lambda record: abs(record["openmc_vs_gp_relative_difference"]),
    )
    largest_buildup = max(case_records, key=lambda record: record["openmc_buildup_ratio"])

    five_mfp = [
        record
        for record in case_records
        if math.isclose(record["target_mean_free_paths"], 5.0, rel_tol=0.0, abs_tol=1.0e-12)
    ]
    five_mfp.sort(key=lambda record: record["openmc_buildup_ratio"])

    lead_series = [record for record in case_records if record["material_key"] == "lead"]
    lead_series.sort(key=lambda record: record["target_mean_free_paths"])

    return {
        "required_uncertainty_pass_count": sum(record["required_uncertainty_pass"] for record in case_records),
        "preferred_uncertainty_pass_count": sum(record["preferred_uncertainty_pass"] for record in case_records),
        "direct_vs_folded_pass_count": sum(record["direct_vs_folded_pass"] for record in case_records),
        "largest_absolute_openmc_vs_gp_difference": {
            "case_id": largest_gp_error["case_id"],
            "relative_difference": largest_gp_error["openmc_vs_gp_relative_difference"],
            "absolute_relative_difference": abs(largest_gp_error["openmc_vs_gp_relative_difference"]),
        },
        "largest_openmc_buildup_ratio": {
            "case_id": largest_buildup["case_id"],
            "buildup_ratio": largest_buildup["openmc_buildup_ratio"],
        },
        "five_mfp_openmc_buildup_order": [
            {
                "case_id": record["case_id"],
                "material_name": record["material_name"],
                "buildup_ratio": record["openmc_buildup_ratio"],
                "openmc_vs_gp_relative_difference": record["openmc_vs_gp_relative_difference"],
            }
            for record in five_mfp
        ],
        "lead_optical_thickness_series": [
            {
                "target_mean_free_paths": record["target_mean_free_paths"],
                "openmc_buildup_ratio": record["openmc_buildup_ratio"],
                "gp_buildup_factor": record["gp_buildup_factor"],
                "openmc_vs_gp_relative_difference": record["openmc_vs_gp_relative_difference"],
                "openmc_relative_uncertainty": record["openmc_relative_uncertainty"],
            }
            for record in lead_series
        ],
    }


def save_csv(case_records: list[dict[str, Any]]) -> None:
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for record in case_records:
            writer.writerow({field: record[field] for field in CSV_FIELDNAMES})


def create_summary_text(case_records: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "=" * 88,
        "V1.14 CORE DETERMINISTIC-VERSUS-OPENMC MATRIX SUMMARY",
        "=" * 88,
        f"Cases aggregated: {len(case_records)}",
        f"Settings profile: {EXPECTED_SETTINGS_PROFILE}",
        f"Histories per case: {EXPECTED_TOTAL_SOURCE_HISTORIES:,}",
        f"Required uncertainty checks: {summary['required_uncertainty_pass_count']}/{len(case_records)} PASS",
        f"Preferred uncertainty checks: {summary['preferred_uncertainty_pass_count']}/{len(case_records)} PASS",
        f"Direct-versus-folded checks: {summary['direct_vs_folded_pass_count']}/{len(case_records)} PASS",
        "-" * 88,
        f"{'Case':<38}{'MFP':>7}{'OpenMC µGy/h':>17}{'MC B':>11}{'G-P B':>11}{'MC vs G-P':>13}{'MC unc.':>10}",
        "-" * 88,
    ]

    for record in case_records:
        lines.append(
            f"{record['case_id']:<38}"
            f"{record['target_mean_free_paths']:>7.1f}"
            f"{record['openmc_direct_microgy_per_h']:>17.6g}"
            f"{record['openmc_buildup_ratio']:>11.4f}"
            f"{record['gp_buildup_factor']:>11.4f}"
            f"{record['openmc_vs_gp_relative_difference']:>+13.2%}"
            f"{record['openmc_relative_uncertainty']:>10.2%}"
        )

    largest_gp = summary["largest_absolute_openmc_vs_gp_difference"]
    largest_buildup = summary["largest_openmc_buildup_ratio"]

    lines.extend([
        "-" * 88,
        f"Largest absolute OpenMC-vs-G-P difference: {largest_gp['case_id']} | {largest_gp['relative_difference']:+.4%}",
        f"Largest observed Monte Carlo buildup ratio: {largest_buildup['case_id']} | {largest_buildup['buildup_ratio']:.6f}",
        "",
        "5-MFP OpenMC buildup ordering:",
    ])

    for index, record in enumerate(summary["five_mfp_openmc_buildup_order"], start=1):
        lines.append(
            f"  {index}. {record['material_name']}: "
            f"B_MC = {record['buildup_ratio']:.6f}, "
            f"OpenMC vs G-P = {record['openmc_vs_gp_relative_difference']:+.4%}"
        )

    lines.extend(["", "Lead optical-thickness series:"])

    for record in summary["lead_optical_thickness_series"]:
        lines.append(
            f"  {record['target_mean_free_paths']:.0f} MFP | "
            f"B_MC = {record['openmc_buildup_ratio']:.6f} | "
            f"B_GP = {record['gp_buildup_factor']:.6f} | "
            f"OpenMC vs G-P = {record['openmc_vs_gp_relative_difference']:+.4%} | "
            f"MC uncertainty = {record['openmc_relative_uncertainty']:.4%}"
        )

    lines.extend([
        "",
        (
            "Deterministic values in this matrix are the matched evaluation-shell averages "
            "from each production comparison record, not the nominal-radius point values "
            "stored in the case-generation metadata."
        ),
        "=" * 88,
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    metadata_document = load_json_object(CASE_METADATA_PATH)
    require(
        metadata_document.get("record_type") == "v114_core_benchmark_case_metadata",
        "Unexpected V1.14 case-metadata record type.",
    )

    cases = metadata_document.get("cases")
    require(isinstance(cases, list), "V1.14 core metadata must contain a case list.")
    require(len(cases) == EXPECTED_CASE_COUNT, f"Expected {EXPECTED_CASE_COUNT} core cases, found {len(cases)}.")

    case_records: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()

    for metadata in cases:
        require(isinstance(metadata, dict), "Each V1.14 metadata entry must be an object.")
        record = create_case_record(metadata)
        require(record["case_id"] not in seen_case_ids, f"Duplicate case ID: {record['case_id']}")
        seen_case_ids.add(record["case_id"])
        case_records.append(record)

    openmc_versions = {record["openmc_version"] for record in case_records}
    require(len(openmc_versions) == 1, "Core production runs do not all use the same OpenMC version.")

    summary = create_summary(case_records)
    require(summary["required_uncertainty_pass_count"] == EXPECTED_CASE_COUNT, "At least one core case failed the required uncertainty check.")
    require(summary["direct_vs_folded_pass_count"] == EXPECTED_CASE_COUNT, "At least one core case failed the direct-versus-folded check.")

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    matrix_document = {
        "schema_version": "1.0",
        "record_type": "v114_core_deterministic_openmc_matrix",
        "version": "1.14",
        "response_quantity": "shell-volume-averaged dry-air collision air-kerma rate",
        "settings_profile_name": EXPECTED_SETTINGS_PROFILE,
        "case_count": len(case_records),
        "openmc_version": next(iter(openmc_versions)),
        "histories_per_case": EXPECTED_TOTAL_SOURCE_HISTORIES,
        "case_metadata_path": CASE_METADATA_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
        "summary": summary,
        "cases": case_records,
    }

    OUTPUT_JSON_PATH.write_text(json.dumps(matrix_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    save_csv(case_records)
    OUTPUT_SUMMARY_PATH.write_text(create_summary_text(case_records, summary), encoding="utf-8")

    print()
    print("=" * 88)
    print("V1.14 CORE MATRIX AGGREGATION PASSED")
    print("=" * 88)
    print(f"Cases: {len(case_records)}")
    print(f"OpenMC version: {next(iter(openmc_versions))}")
    print(f"Required uncertainty checks: {summary['required_uncertainty_pass_count']}/{len(case_records)} PASS")
    print(f"Preferred uncertainty checks: {summary['preferred_uncertainty_pass_count']}/{len(case_records)} PASS")
    print(f"Direct-versus-folded checks: {summary['direct_vs_folded_pass_count']}/{len(case_records)} PASS")
    print("-" * 88)
    print("Created:")
    for path in (OUTPUT_JSON_PATH, OUTPUT_CSV_PATH, OUTPUT_SUMMARY_PATH):
        print(f"  {path}")
    print("=" * 88)
    print()


if __name__ == "__main__":
    main()
