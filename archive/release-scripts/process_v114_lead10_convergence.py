# Process the existing V1.14 Cs-137 / Lead / 10-MFP production
# statepoint checkpoints as a cumulative Monte Carlo convergence study.
#
# IMPORTANT:
#   - This script does not run OpenMC transport.
#   - It reads the already-preserved production statepoints at batches
#     25, 50, 75, and 100.
#   - It writes only under results/v1.14/analysis/convergence/.
#   - It never modifies or deletes the production run directory.
#
# Run inside the same OpenMC environment used for the V1.14 production runs:
#
#   python examples/process_v114_lead10_convergence.py
#
# To replace an earlier analysis output:
#
#   python examples/process_v114_lead10_convergence.py --overwrite

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from openmc_benchmark_runner import (  # noqa: E402
    OpenMCBenchmarkAcceptanceCriteria,
    process_openmc_benchmark_result,
)
from openmc_settings_io import load_openmc_settings  # noqa: E402
from scenario_io import load_scenario  # noqa: E402
from unit_conversions import convert_gy_per_s_to_microgy_per_h  # noqa: E402


SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "v1.14"
    / "cs137_lead_10mfp.json"
)

SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v114_production.json"
)

PRODUCTION_RUN_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "production"
    / "cs137_lead_10mfp__v114_production"
)

ANALYSIS_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "analysis"
    / "convergence"
    / "cs137_lead_10mfp"
)

CHECKPOINT_OUTPUT_DIRECTORY = (
    ANALYSIS_DIRECTORY
    / "checkpoints"
)

CONVERGENCE_CSV_PATH = (
    ANALYSIS_DIRECTORY
    / "convergence.csv"
)

CONVERGENCE_JSON_PATH = (
    ANALYSIS_DIRECTORY
    / "convergence.json"
)

CONVERGENCE_SUMMARY_PATH = (
    ANALYSIS_DIRECTORY
    / "convergence_summary.txt"
)

EXPECTED_BATCHES = (
    25,
    50,
    75,
    100,
)

EXPECTED_PARTICLES_PER_BATCH = 50_000

PREFERRED_RELATIVE_UNCERTAINTY = 0.02


CSV_FIELDNAMES = [
    "batch",
    "total_histories",
    "direct_response_microgy_per_h",
    "standard_deviation_microgy_per_h",
    "relative_uncertainty",
    "relative_difference_from_final_response",
    "expected_relative_uncertainty_from_final_inverse_sqrt_n",
    "uncertainty_scaling_ratio_to_final",
    "direct_vs_folded_relative_difference",
    "relative_difference_from_deterministic_uncollided",
    "relative_difference_from_deterministic_gp",
    "observed_monte_carlo_buildup_ratio",
    "required_uncertainty_pass",
    "preferred_uncertainty_pass",
    "direct_vs_folded_pass",
]


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(
            message
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process the preserved V1.14 Lead 10-MFP statepoints "
            "as a cumulative convergence study without rerunning transport."
        )
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Replace only the dedicated analysis/convergence output. "
            "The production run directory is never modified."
        ),
    )

    return parser.parse_args()


def prepare_analysis_directory(
    *,
    overwrite: bool,
) -> None:
    production_resolved = (
        PRODUCTION_RUN_DIRECTORY
        .resolve()
    )

    analysis_resolved = (
        ANALYSIS_DIRECTORY
        .resolve()
    )

    require(
        production_resolved
        != analysis_resolved,
        (
            "Safety check failed: analysis directory "
            "cannot be the production run directory."
        ),
    )

    require(
        production_resolved
        not in analysis_resolved.parents,
        (
            "Safety check failed: analysis output "
            "cannot be inside the production run directory."
        ),
    )

    if ANALYSIS_DIRECTORY.exists():
        if not overwrite:
            raise FileExistsError(
                "V1.14 Lead 10-MFP convergence analysis already exists: "
                f"{ANALYSIS_DIRECTORY}\n"
                "Rerun with --overwrite to replace only this analysis output."
            )

        shutil.rmtree(
            ANALYSIS_DIRECTORY
        )

    CHECKPOINT_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def resolve_statepoint_path(
    batch: int,
) -> Path:
    candidates = (
        PRODUCTION_RUN_DIRECTORY
        / f"statepoint.{batch:03d}.h5",
        PRODUCTION_RUN_DIRECTORY
        / f"statepoint.{batch}.h5",
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "Required V1.14 production statepoint was not found for "
        f"batch {batch}. Checked: "
        + ", ".join(
            str(candidate)
            for candidate in candidates
        )
    )


def calculate_relative_difference(
    *,
    comparison_value: float,
    reference_value: float,
) -> float:
    if not math.isfinite(
        comparison_value
    ):
        raise ValueError(
            "Convergence comparison value must be finite."
        )

    if (
        not math.isfinite(
            reference_value
        )
        or reference_value == 0.0
    ):
        raise ValueError(
            "Convergence reference value must be finite and nonzero."
        )

    return (
        comparison_value
        - reference_value
    ) / reference_value


def create_raw_checkpoint_record(
    *,
    batch: int,
    particles_per_batch: int,
    processed_bundle: Any,
) -> dict[str, Any]:
    result = (
        processed_bundle
        .openmc_result
    )

    comparison = (
        processed_bundle
        .comparison
    )

    direct_response_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .direct_response_rate_gy_per_s
        )
    )

    standard_deviation_microgy_per_h = (
        convert_gy_per_s_to_microgy_per_h(
            result
            .direct_response_rate_standard_deviation_gy_per_s
        )
    )

    return {
        "batch": batch,
        "total_histories": (
            batch
            * particles_per_batch
        ),
        "direct_response_microgy_per_h": (
            direct_response_microgy_per_h
        ),
        "standard_deviation_microgy_per_h": (
            standard_deviation_microgy_per_h
        ),
        "relative_uncertainty": (
            result.relative_uncertainty
        ),
        "direct_vs_folded_relative_difference": (
            processed_bundle
            .direct_vs_folded_relative_difference
        ),
        "relative_difference_from_deterministic_uncollided": (
            comparison
            .relative_difference_from_uncollided
        ),
        "relative_difference_from_deterministic_gp": (
            comparison
            .relative_difference_from_gp
        ),
        "observed_monte_carlo_buildup_ratio": (
            comparison
            .observed_monte_carlo_buildup_ratio
        ),
        "required_uncertainty_pass": (
            processed_bundle
            .required_uncertainty_pass
        ),
        "preferred_uncertainty_pass": (
            processed_bundle
            .preferred_uncertainty_pass
        ),
        "direct_vs_folded_pass": (
            processed_bundle
            .direct_vs_folded_pass
        ),
    }


def finalize_checkpoint_records(
    raw_records: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    require(
        len(raw_records)
        == len(EXPECTED_BATCHES),
        (
            "Lead 10-MFP convergence analysis "
            "requires four checkpoint records."
        ),
    )

    final_record = (
        raw_records[-1]
    )

    final_histories = int(
        final_record[
            "total_histories"
        ]
    )

    final_response = float(
        final_record[
            "direct_response_microgy_per_h"
        ]
    )

    final_relative_uncertainty = float(
        final_record[
            "relative_uncertainty"
        ]
    )

    require(
        final_histories > 0,
        (
            "Final convergence history count "
            "must be positive."
        ),
    )

    require(
        final_response > 0.0,
        (
            "Final convergence response "
            "must be positive."
        ),
    )

    require(
        final_relative_uncertainty > 0.0,
        (
            "Final convergence relative "
            "uncertainty must be positive."
        ),
    )

    finalized_records: list[
        dict[str, Any]
    ] = []

    for raw_record in raw_records:
        record = dict(
            raw_record
        )

        histories = int(
            record[
                "total_histories"
            ]
        )

        response = float(
            record[
                "direct_response_microgy_per_h"
            ]
        )

        relative_uncertainty = float(
            record[
                "relative_uncertainty"
            ]
        )

        expected_relative_uncertainty = (
            final_relative_uncertainty
            * math.sqrt(
                final_histories
                / histories
            )
        )

        scaled_uncertainty_ratio = (
            relative_uncertainty
            / expected_relative_uncertainty
        )

        record[
            "relative_difference_from_final_response"
        ] = (
            calculate_relative_difference(
                comparison_value=response,
                reference_value=(
                    final_response
                ),
            )
        )

        record[
            "expected_relative_uncertainty_from_final_inverse_sqrt_n"
        ] = (
            expected_relative_uncertainty
        )

        record[
            "uncertainty_scaling_ratio_to_final"
        ] = (
            scaled_uncertainty_ratio
        )

        finalized_records.append(
            record
        )

    return finalized_records


def create_summary_metrics(
    records: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    final_record = (
        records[-1]
    )

    final_histories = int(
        final_record[
            "total_histories"
        ]
    )

    final_relative_uncertainty = float(
        final_record[
            "relative_uncertainty"
        ]
    )

    projected_histories_for_preferred = (
        final_histories
        * (
            final_relative_uncertainty
            / PREFERRED_RELATIVE_UNCERTAINTY
        )
        ** 2
    )

    projected_additional_histories = max(
        0.0,
        projected_histories_for_preferred
        - final_histories,
    )

    uncertainty_values = [
        float(
            record[
                "relative_uncertainty"
            ]
        )
        for record in records
    ]

    response_values = [
        float(
            record[
                "direct_response_microgy_per_h"
            ]
        )
        for record in records
    ]

    uncertainty_monotonically_decreases = all(
        later <= earlier
        for earlier, later
        in zip(
            uncertainty_values[:-1],
            uncertainty_values[1:],
            strict=True,
        )
    )

    maximum_absolute_difference_from_final = max(
        abs(
            float(
                record[
                    "relative_difference_from_final_response"
                ]
            )
        )
        for record in records[:-1]
    )

    scaling_ratios = [
        float(
            record[
                "uncertainty_scaling_ratio_to_final"
            ]
        )
        for record in records
    ]

    return {
        "final_histories": (
            final_histories
        ),
        "final_response_microgy_per_h": (
            response_values[-1]
        ),
        "final_relative_uncertainty": (
            final_relative_uncertainty
        ),
        "final_preferred_uncertainty_pass": (
            bool(
                final_record[
                    "preferred_uncertainty_pass"
                ]
            )
        ),
        "uncertainty_monotonically_decreases": (
            uncertainty_monotonically_decreases
        ),
        "maximum_absolute_checkpoint_difference_from_final": (
            maximum_absolute_difference_from_final
        ),
        "minimum_uncertainty_scaling_ratio_to_final": (
            min(
                scaling_ratios
            )
        ),
        "maximum_uncertainty_scaling_ratio_to_final": (
            max(
                scaling_ratios
            )
        ),
        "projected_histories_for_2_percent_uncertainty_if_inverse_sqrt_n": (
            projected_histories_for_preferred
        ),
        "projected_additional_histories_for_2_percent_uncertainty_if_inverse_sqrt_n": (
            projected_additional_histories
        ),
        "projection_note": (
            "History projection assumes the final observed relative "
            "uncertainty continues to scale as 1/sqrt(N). It is an "
            "engineering projection, not a guarantee."
        ),
        "correlation_note": (
            "Checkpoint statepoints are cumulative and therefore correlated. "
            "Differences from the final response are descriptive stability "
            "metrics and must not be interpreted as independent-sample "
            "significance tests."
        ),
    }


def save_csv(
    records: list[
        dict[str, Any]
    ],
) -> None:
    with CONVERGENCE_CSV_PATH.open(
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

        for record in records:
            writer.writerow(
                {
                    fieldname: (
                        record[
                            fieldname
                        ]
                    )
                    for fieldname
                    in CSV_FIELDNAMES
                }
            )


def create_summary_text(
    *,
    records: list[
        dict[str, Any]
    ],
    metrics: dict[str, Any],
) -> str:
    lines = [
        "=" * 92,
        "V1.14 Cs-137 / LEAD / 10-MFP OPENMC CONVERGENCE STUDY",
        "=" * 92,
        (
            "Scenario: "
            "cs137_lead_10mfp"
        ),
        (
            "Settings profile: "
            "v114_production"
        ),
        (
            "Checkpoint statepoints: "
            "25, 50, 75, 100"
        ),
        (
            "Particles per batch: "
            f"{EXPECTED_PARTICLES_PER_BATCH:,}"
        ),
        (
            "Transport rerun: No"
        ),
        "-" * 92,
        (
            f"{'Batch':>7}"
            f"{'Histories':>13}"
            f"{'Response µGy/h':>19}"
            f"{'Rel. unc.':>13}"
            f"{'From final':>13}"
            f"{'1/sqrt(N) ratio':>18}"
            f"{'MC vs G-P':>13}"
        ),
        "-" * 92,
    ]

    for record in records:
        lines.append(
            f"{record['batch']:>7d}"
            f"{record['total_histories']:>13,d}"
            f"{record['direct_response_microgy_per_h']:>19.8g}"
            f"{record['relative_uncertainty']:>13.4%}"
            f"{record['relative_difference_from_final_response']:>+13.4%}"
            f"{record['uncertainty_scaling_ratio_to_final']:>18.4f}"
            f"{record['relative_difference_from_deterministic_gp']:>+13.4%}"
        )

    lines.extend(
        [
            "-" * 92,
            (
                "Final response: "
                f"{metrics['final_response_microgy_per_h']:.10e} µGy/h"
            ),
            (
                "Final relative uncertainty: "
                f"{metrics['final_relative_uncertainty']:.4%}"
            ),
            (
                "Preferred <= 2% uncertainty: "
                + (
                    "PASS"
                    if metrics[
                        "final_preferred_uncertainty_pass"
                    ]
                    else "NOT MET"
                )
            ),
            (
                "Uncertainty decreases monotonically: "
                + (
                    "Yes"
                    if metrics[
                        "uncertainty_monotonically_decreases"
                    ]
                    else "No"
                )
            ),
            (
                "Largest pre-final checkpoint difference "
                "from final response: "
                f"{metrics['maximum_absolute_checkpoint_difference_from_final']:.4%}"
            ),
            (
                "Observed 1/sqrt(N) scaling-ratio range: "
                f"{metrics['minimum_uncertainty_scaling_ratio_to_final']:.4f}"
                " to "
                f"{metrics['maximum_uncertainty_scaling_ratio_to_final']:.4f}"
                " (1.0000 = ideal relative to final statepoint)"
            ),
            (
                "Projected histories for 2% uncertainty "
                "if 1/sqrt(N) scaling continues: "
                f"{metrics['projected_histories_for_2_percent_uncertainty_if_inverse_sqrt_n']:,.0f}"
            ),
            (
                "Projected additional histories beyond current run: "
                f"{metrics['projected_additional_histories_for_2_percent_uncertainty_if_inverse_sqrt_n']:,.0f}"
            ),
            "",
            (
                "NOTE: Checkpoint statepoints are cumulative and correlated. "
                "Differences from the final result describe numerical stability; "
                "they are not independent-sample significance tests."
            ),
            (
                "NOTE: The 2% history estimate is a 1/sqrt(N) projection from "
                "the observed final uncertainty and is not a guaranteed runtime target."
            ),
            "=" * 92,
            "",
        ]
    )

    return "\n".join(
        lines
    )


def main() -> int:
    arguments = (
        parse_arguments()
    )

    require(
        SCENARIO_PATH.is_file(),
        (
            "V1.14 Lead 10-MFP scenario "
            f"does not exist: {SCENARIO_PATH}"
        ),
    )

    require(
        SETTINGS_PATH.is_file(),
        (
            "V1.14 production settings "
            f"do not exist: {SETTINGS_PATH}"
        ),
    )

    require(
        PRODUCTION_RUN_DIRECTORY.is_dir(),
        (
            "V1.14 Lead 10-MFP production "
            f"run does not exist: {PRODUCTION_RUN_DIRECTORY}"
        ),
    )

    scenario = load_scenario(
        SCENARIO_PATH
    )

    settings_profile = (
        load_openmc_settings(
            SETTINGS_PATH
        )
    )

    require(
        scenario.scenario_id
        == "cs137_lead_10mfp",
        (
            "Unexpected convergence scenario ID: "
            f"{scenario.scenario_id}"
        ),
    )

    require(
        settings_profile.profile_name
        == "v114_production",
        (
            "Unexpected convergence settings profile: "
            f"{settings_profile.profile_name}"
        ),
    )

    require(
        settings_profile
        .particles_per_batch
        == EXPECTED_PARTICLES_PER_BATCH,
        (
            "Unexpected V1.14 production "
            "particles-per-batch value."
        ),
    )

    require(
        tuple(
            settings_profile
            .statepoint_batches
        )
        == EXPECTED_BATCHES,
        (
            "V1.14 production statepoint batches "
            "do not match 25, 50, 75, 100."
        ),
    )

    statepoint_paths = {
        batch: (
            resolve_statepoint_path(
                batch
            )
        )
        for batch in EXPECTED_BATCHES
    }

    prepare_analysis_directory(
        overwrite=(
            arguments.overwrite
        )
    )

    acceptance_criteria = (
        OpenMCBenchmarkAcceptanceCriteria()
    )

    raw_records: list[
        dict[str, Any]
    ] = []

    print()
    print("=" * 92)
    print("V1.14 LEAD 10-MFP CONVERGENCE STATEPOINT PROCESSING")
    print("=" * 92)
    print(
        "Transport rerun: No"
    )
    print(
        "Reading preserved production statepoints:"
    )

    for batch in EXPECTED_BATCHES:
        statepoint_path = (
            statepoint_paths[
                batch
            ]
        )

        checkpoint_output = (
            CHECKPOINT_OUTPUT_DIRECTORY
            / f"batch_{batch:03d}"
        )

        checkpoint_output.mkdir(
            parents=True,
            exist_ok=False,
        )

        processed_bundle = (
            process_openmc_benchmark_result(
                statepoint_path=(
                    statepoint_path
                ),
                scenario=scenario,
                settings_profile=(
                    settings_profile
                ),
                output_directory=(
                    checkpoint_output
                ),
                evaluation_shell_thickness_cm=1.0,
                expected_batch=batch,
                acceptance_criteria=(
                    acceptance_criteria
                ),
            )
        )

        record = (
            create_raw_checkpoint_record(
                batch=batch,
                particles_per_batch=(
                    settings_profile
                    .particles_per_batch
                ),
                processed_bundle=(
                    processed_bundle
                ),
            )
        )

        raw_records.append(
            record
        )

        print(
            f"  Batch {batch:03d} | "
            f"{record['total_histories']:,} histories | "
            f"{record['direct_response_microgy_per_h']:.8e} µGy/h | "
            f"rel. unc. {record['relative_uncertainty']:.4%}"
        )

    records = (
        finalize_checkpoint_records(
            raw_records
        )
    )

    metrics = (
        create_summary_metrics(
            records
        )
    )

    save_csv(
        records
    )

    convergence_document = {
        "schema_version": "1.0",
        "record_type": (
            "v114_openmc_convergence_study"
        ),
        "version": "1.14",
        "scenario_id": (
            scenario.scenario_id
        ),
        "settings_profile_name": (
            settings_profile
            .profile_name
        ),
        "transport_rerun": False,
        "statepoints_are_cumulative": True,
        "statepoint_batches": list(
            EXPECTED_BATCHES
        ),
        "particles_per_batch": (
            settings_profile
            .particles_per_batch
        ),
        "metrics": metrics,
        "checkpoints": records,
        "source_statepoints": {
            str(batch): (
                statepoint_paths[
                    batch
                ]
                .relative_to(
                    REPOSITORY_ROOT
                )
                .as_posix()
            )
            for batch in EXPECTED_BATCHES
        },
    }

    CONVERGENCE_JSON_PATH.write_text(
        json.dumps(
            convergence_document,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    CONVERGENCE_SUMMARY_PATH.write_text(
        create_summary_text(
            records=records,
            metrics=metrics,
        ),
        encoding="utf-8",
    )

    print("-" * 92)
    print(
        "Created:"
    )

    for path in (
        CONVERGENCE_CSV_PATH,
        CONVERGENCE_JSON_PATH,
        CONVERGENCE_SUMMARY_PATH,
    ):
        print(
            f"  {path}"
        )

    print(
        "Checkpoint processed outputs:"
    )

    print(
        f"  {CHECKPOINT_OUTPUT_DIRECTORY}"
    )

    print("-" * 92)
    print(
        "PASS: Existing Lead 10-MFP production statepoints "
        "were processed without rerunning transport."
    )
    print("=" * 92)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
