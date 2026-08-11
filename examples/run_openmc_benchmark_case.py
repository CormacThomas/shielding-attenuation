# Generic V1.14 OpenMC benchmark command-line entry point.
#
# Modes:
#   export   Build, attach tallies, and export model.xml without transport.
#   run      Execute transport, create a manifest, and process final results.
#   process  Process an existing statepoint without rerunning transport.

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from openmc_benchmark_runner import (  # noqa: E402
    OpenMCBenchmarkAcceptanceCriteria,
    export_openmc_benchmark_model,
    prepare_clean_directory,
    process_openmc_benchmark_result,
    run_openmc_benchmark_case,
)
from openmc_settings_io import load_openmc_settings  # noqa: E402
from scenario_io import load_scenario  # noqa: E402
from unit_conversions import convert_gy_per_s_to_microgy_per_h  # noqa: E402


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export, run, or process one OpenMC benchmark case."
    )

    parser.add_argument(
        "--mode",
        choices=("export", "run", "process"),
        required=True,
    )
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--statepoint", type=Path)
    parser.add_argument(
        "--evaluation-shell-thickness-cm",
        type=float,
        default=1.0,
    )
    parser.add_argument("--overwrite", action="store_true")

    return parser


def print_processed_result(processed_bundle) -> None:
    result = processed_bundle.openmc_result
    comparison = processed_bundle.comparison

    print()
    print("=" * 80)
    print("OPENMC BENCHMARK RESULT")
    print("=" * 80)
    print(f"Scenario ID: {result.scenario_id}")
    print(f"Settings profile: {result.settings_profile_name}")
    print(
        "Direct response: "
        f"{convert_gy_per_s_to_microgy_per_h(result.direct_response_rate_gy_per_s):.10e} "
        "µGy/h"
    )
    print(
        "Relative uncertainty: "
        f"{result.relative_uncertainty:.4%}"
    )
    print(
        "Direct-versus-folded difference: "
        f"{processed_bundle.direct_vs_folded_relative_difference:+.4%}"
    )
    print(
        "Difference from deterministic uncollided: "
        f"{comparison.relative_difference_from_uncollided:+.4%}"
    )

    if comparison.relative_difference_from_gp is not None:
        print(
            "Difference from deterministic G-P: "
            f"{comparison.relative_difference_from_gp:+.4%}"
        )

    print(
        "Observed Monte Carlo buildup ratio: "
        f"{comparison.observed_monte_carlo_buildup_ratio:.6f}"
    )
    print("-" * 80)
    print(
        "Required uncertainty check: "
        f"{'PASS' if processed_bundle.required_uncertainty_pass else 'FAIL'}"
    )
    print(
        "Preferred uncertainty check: "
        f"{'PASS' if processed_bundle.preferred_uncertainty_pass else 'NOT MET'}"
    )
    print(
        "Direct-versus-folded check: "
        f"{'PASS' if processed_bundle.direct_vs_folded_pass else 'FAIL'}"
    )
    print("=" * 80)


def main() -> int:
    args = create_argument_parser().parse_args()

    scenario = load_scenario(args.scenario)
    settings_profile = load_openmc_settings(args.settings)
    acceptance_criteria = OpenMCBenchmarkAcceptanceCriteria()

    if args.mode == "export":
        if args.statepoint is not None:
            raise ValueError("Export mode does not accept --statepoint.")

        model_xml_path = export_openmc_benchmark_model(
            scenario=scenario,
            settings_profile=settings_profile,
            output_directory=args.output_directory,
            evaluation_shell_thickness_cm=(
                args.evaluation_shell_thickness_cm
            ),
            overwrite=args.overwrite,
        )

        print()
        print("PASS: OpenMC benchmark model exported without transport.")
        print(f"Model XML: {model_xml_path}")
        return 0

    if args.mode == "run":
        if args.statepoint is not None:
            raise ValueError("Run mode does not accept --statepoint.")

        run_bundle = run_openmc_benchmark_case(
            scenario=scenario,
            settings_profile=settings_profile,
            run_directory=args.output_directory,
            repository_root=REPOSITORY_ROOT,
            evaluation_shell_thickness_cm=(
                args.evaluation_shell_thickness_cm
            ),
            acceptance_criteria=acceptance_criteria,
            overwrite=args.overwrite,
        )

        print_processed_result(run_bundle.processed_bundle)
        print(f"Statepoint: {run_bundle.final_statepoint_path}")
        print(f"Manifest: {run_bundle.manifest_path}")
        print(f"Runtime: {run_bundle.runtime_seconds:.6f} s")

        if not run_bundle.processed_bundle.required_uncertainty_pass:
            return 2

        if not run_bundle.processed_bundle.direct_vs_folded_pass:
            return 3

        return 0

    if args.statepoint is None:
        raise ValueError("Process mode requires --statepoint.")

    if not args.statepoint.is_file():
        raise FileNotFoundError(
            f"Statepoint file does not exist: {args.statepoint}"
        )

    processed_output_directory = prepare_clean_directory(
        args.output_directory,
        overwrite=args.overwrite,
    )

    processed_bundle = process_openmc_benchmark_result(
        statepoint_path=args.statepoint,
        scenario=scenario,
        settings_profile=settings_profile,
        output_directory=processed_output_directory,
        evaluation_shell_thickness_cm=(
            args.evaluation_shell_thickness_cm
        ),
        expected_batch=settings_profile.batches,
        acceptance_criteria=acceptance_criteria,
    )

    print_processed_result(processed_bundle)

    if not processed_bundle.required_uncertainty_pass:
        return 2

    if not processed_bundle.direct_vs_folded_pass:
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
