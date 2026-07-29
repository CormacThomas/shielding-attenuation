# Construct and export the complete V1.13 OpenMC model with its two benchmark
# tallies, but do not transport particles.
#
# Development check:
#
#   python examples/openmc_v113_tally_check.py
#
# Production configuration check:
#
#   python examples/openmc_v113_tally_check.py \
#       scenarios/cs137_v113_production.json \
#       config/openmc/v113_production.json


from __future__ import annotations


import argparse
from pathlib import Path
import shutil
import sys


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "src"
)


if str(
    SOURCE_DIRECTORY
) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from openmc_model_builder import (
    build_openmc_v113_model,
)
from openmc_settings_io import (
    load_openmc_settings,
)
from openmc_tally_builder import (
    AIR_KERMA_RESPONSE_FILTER_ID,
    DIRECT_RESPONSE_TALLY_ID,
    DIRECT_RESPONSE_TALLY_NAME,
    SPECTRUM_TALLY_ID,
    SPECTRUM_TALLY_NAME,
    attach_v113_benchmark_tallies,
)
from scenario_io import (
    load_scenario,
)


DEFAULT_SCENARIO_PATH = (
    REPOSITORY_ROOT
    / "scenarios"
    / "cs137_v113_development.json"
)

DEFAULT_SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v113_development.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Construct and export the complete V1.13 "
            "OpenMC model and benchmark tallies "
            "without running particles."
        )
    )

    parser.add_argument(
        "scenario_path",
        nargs="?",
        type=Path,
        default=DEFAULT_SCENARIO_PATH,
    )

    parser.add_argument(
        "settings_path",
        nargs="?",
        type=Path,
        default=DEFAULT_SETTINGS_PATH,
    )

    parser.add_argument(
        "--evaluation-shell-thickness-cm",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def prepare_output_directory(
    output_directory: Path,
) -> None:
    if output_directory.exists():
        shutil.rmtree(
            output_directory
        )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


def require_exported_file(
    output_directory: Path,
    filename: str,
) -> Path:
    exported_path = (
        output_directory
        / filename
    )

    if not exported_path.is_file():
        raise RuntimeError(
            "Expected OpenMC XML file was not created: "
            f"{exported_path}"
        )

    return exported_path


def main() -> int:
    arguments = parse_arguments()

    scenario = load_scenario(
        arguments.scenario_path
    )

    settings_profile = (
        load_openmc_settings(
            arguments.settings_path
        )
    )

    model_build_result = (
        build_openmc_v113_model(
            scenario=scenario,
            settings_profile=(
                settings_profile
            ),
            evaluation_shell_thickness_cm=(
                arguments
                .evaluation_shell_thickness_cm
            ),
        )
    )

    tally_build_result = (
        attach_v113_benchmark_tallies(
            model_build_result=(
                model_build_result
            ),
            settings_profile=(
                settings_profile
            ),
        )
    )

    if (
        arguments.output_directory
        is None
    ):
        output_directory = (
            REPOSITORY_ROOT
            / "results"
            / "v1.13"
            / "tally_build"
            / (
                f"{scenario.scenario_id}__"
                f"{settings_profile.profile_name}"
            )
        )

    else:
        output_directory = (
            arguments.output_directory
        )

    prepare_output_directory(
        output_directory
    )

    model_build_result.model.export_to_xml(
        directory=output_directory
    )

    materials_path = require_exported_file(
        output_directory,
        "materials.xml",
    )

    geometry_path = require_exported_file(
        output_directory,
        "geometry.xml",
    )

    settings_path = require_exported_file(
        output_directory,
        "settings.xml",
    )

    tallies_path = require_exported_file(
        output_directory,
        "tallies.xml",
    )

    spectrum_tally = (
        tally_build_result
        .spectrum_tally
    )

    direct_response_tally = (
        tally_build_result
        .direct_response_tally
    )

    spectrum_energy_filter = (
        tally_build_result
        .spectrum_energy_filter
    )

    response_filter = (
        tally_build_result
        .air_kerma_response_filter
    )

    response_function = (
        tally_build_result
        .response_function
    )

    expected_spectrum_bin_count = (
        len(
            settings_profile
            .energy_bin_boundaries_ev
        )
        - 1
    )

    if (
        spectrum_energy_filter.num_bins
        != expected_spectrum_bin_count
    ):
        raise RuntimeError(
            "Unexpected spectrum energy-bin count: "
            f"expected {expected_spectrum_bin_count}, "
            f"found {spectrum_energy_filter.num_bins}."
        )

    if spectrum_tally.id != SPECTRUM_TALLY_ID:
        raise RuntimeError(
            "Unexpected spectrum tally ID."
        )

    if (
        direct_response_tally.id
        != DIRECT_RESPONSE_TALLY_ID
    ):
        raise RuntimeError(
            "Unexpected direct-response tally ID."
        )

    if spectrum_tally.name != SPECTRUM_TALLY_NAME:
        raise RuntimeError(
            "Unexpected spectrum tally name."
        )

    if (
        direct_response_tally.name
        != DIRECT_RESPONSE_TALLY_NAME
    ):
        raise RuntimeError(
            "Unexpected direct-response tally name."
        )

    if (
        response_filter.id
        != AIR_KERMA_RESPONSE_FILTER_ID
    ):
        raise RuntimeError(
            "Unexpected air-kerma response-filter ID."
        )

    if (
        response_filter.interpolation
        != "log-log"
    ):
        raise RuntimeError(
            "Direct-response filter must use "
            "log-log interpolation."
        )

    if (
        spectrum_tally.estimator
        != "tracklength"
    ):
        raise RuntimeError(
            "Spectrum tally is not using the "
            "track-length estimator."
        )

    if (
        direct_response_tally.estimator
        != "tracklength"
    ):
        raise RuntimeError(
            "Direct-response tally is not using "
            "the track-length estimator."
        )

    if len(
        model_build_result.model.tallies
    ) != 2:
        raise RuntimeError(
            "Complete V1.13 model must contain "
            "exactly two tallies."
        )

    print()
    print("=" * 72)
    print("OPENMC V1.13 TALLY-CONSTRUCTION CHECK PASSED")
    print("=" * 72)

    print(
        "OpenMC version: "
        f"{model_build_result.openmc_version}"
    )

    print(
        "Scenario ID: "
        f"{scenario.scenario_id}"
    )

    print(
        "Settings profile: "
        f"{settings_profile.profile_name}"
    )

    print(
        "Evaluation shell: "
        f"{model_build_result.evaluation_shell.inner_radius_cm:.6f} "
        "to "
        f"{model_build_result.evaluation_shell.outer_radius_cm:.6f} cm"
    )

    print(
        "Physical source rate: "
        f"{model_build_result.physical_source_rate_per_s:.8e} "
        "photons/s"
    )

    print("-" * 72)

    print(
        "Tally count: "
        f"{len(model_build_result.model.tallies)}"
    )

    print(
        "Spectrum tally ID: "
        f"{spectrum_tally.id}"
    )

    print(
        "Spectrum tally name: "
        f"{spectrum_tally.name}"
    )

    print(
        "Spectrum score: "
        f"{spectrum_tally.scores}"
    )

    print(
        "Spectrum estimator: "
        f"{spectrum_tally.estimator}"
    )

    print(
        "Spectrum energy boundaries: "
        f"{len(settings_profile.energy_bin_boundaries_ev)}"
    )

    print(
        "Spectrum energy bins: "
        f"{spectrum_energy_filter.num_bins}"
    )

    print(
        "Spectrum range: "
        f"{settings_profile.minimum_spectrum_energy_ev:.6f} "
        "to "
        f"{settings_profile.maximum_spectrum_energy_ev:.6f} eV"
    )

    print("-" * 72)

    print(
        "Direct-response tally ID: "
        f"{direct_response_tally.id}"
    )

    print(
        "Direct-response tally name: "
        f"{direct_response_tally.name}"
    )

    print(
        "Direct-response score: "
        f"{direct_response_tally.scores}"
    )

    print(
        "Direct-response estimator: "
        f"{direct_response_tally.estimator}"
    )

    print(
        "Response-function points: "
        f"{len(response_function.points)}"
    )

    print(
        "Response interpolation: "
        f"{response_filter.interpolation}"
    )

    print(
        "Response range: "
        f"{response_function.minimum_energy_ev:.6f} "
        "to "
        f"{response_function.maximum_energy_ev:.6f} eV"
    )

    print(
        "Response coefficient source: "
        f"{response_function.coefficient_source}"
    )

    print("-" * 72)

    print(
        "Exported materials: "
        f"{materials_path}"
    )

    print(
        "Exported geometry: "
        f"{geometry_path}"
    )

    print(
        "Exported settings: "
        f"{settings_path}"
    )

    print(
        "Exported tallies: "
        f"{tallies_path}"
    )

    print()
    print(
        "No particles were transported and "
        "no statepoint was created."
    )

    print("=" * 72)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )