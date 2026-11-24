# Generate the two additional OpenMC settings profiles used by the V1.14
# energy-discretization sensitivity study.
#
# The existing v114_production profile is the canonical grid and is not
# modified. This script derives two nested alternatives from that exact grid:
#
#   coarse:
#       every second canonical boundary
#       -> 38 spectrum bins
#
#   refined:
#       one geometric midpoint inserted into every canonical bin
#       -> 152 spectrum bins
#
# All transport settings remain identical to v114_production, including the
# random seed. Only the profile name and spectrum tally discretization change.
#
# Run from the repository root:
#
#   python examples/generate_v114_energy_grid_sensitivity_settings.py

from __future__ import annotations

import math
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from openmc_models import OpenMCSettings  # noqa: E402
from openmc_settings_io import (  # noqa: E402
    load_openmc_settings,
    save_openmc_settings,
)


CANONICAL_SETTINGS_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "v114_production.json"
)

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "config"
    / "openmc"
    / "sensitivity"
)

COARSE_SETTINGS_PATH = (
    OUTPUT_DIRECTORY
    / "v114_energy_coarse.json"
)

REFINED_SETTINGS_PATH = (
    OUTPUT_DIRECTORY
    / "v114_energy_refined.json"
)

EXPECTED_CANONICAL_PROFILE_NAME = (
    "v114_production"
)

EXPECTED_CANONICAL_BOUNDARY_COUNT = 77
EXPECTED_CANONICAL_BIN_COUNT = 76
EXPECTED_COARSE_BIN_COUNT = 38
EXPECTED_REFINED_BIN_COUNT = 152

CS137_SOURCE_ENERGY_EV = 661_657.0


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(
            message
        )


def create_coarse_boundaries(
    canonical_boundaries: list[float],
) -> list[float]:
    # With 77 canonical boundaries, taking indices 0, 2, 4, ..., 76
    # preserves both endpoints and merges each adjacent pair of canonical
    # bins into one coarse bin.

    coarse_boundaries = list(
        canonical_boundaries[
            ::2
        ]
    )

    require(
        coarse_boundaries[0]
        == canonical_boundaries[0],
        (
            "Coarse V1.14 energy grid did not "
            "preserve the lower endpoint."
        ),
    )

    require(
        coarse_boundaries[-1]
        == canonical_boundaries[-1],
        (
            "Coarse V1.14 energy grid did not "
            "preserve the upper endpoint."
        ),
    )

    return coarse_boundaries


def create_refined_boundaries(
    canonical_boundaries: list[float],
) -> list[float]:
    # Split every canonical bin into two logarithmically balanced bins by
    # inserting the geometric midpoint. The project's spectrum folding also
    # uses geometric representative energies, so this is a natural nested
    # refinement for the sensitivity study.

    refined_boundaries: list[
        float
    ] = []

    for (
        lower_energy_ev,
        upper_energy_ev,
    ) in zip(
        canonical_boundaries[:-1],
        canonical_boundaries[1:],
        strict=True,
    ):
        refined_boundaries.append(
            lower_energy_ev
        )

        refined_boundaries.append(
            math.sqrt(
                lower_energy_ev
                * upper_energy_ev
            )
        )

    refined_boundaries.append(
        canonical_boundaries[-1]
    )

    return refined_boundaries


def create_sensitivity_settings(
    *,
    canonical_settings: OpenMCSettings,
    profile_name: str,
    energy_bin_boundaries_ev: list[float],
) -> OpenMCSettings:
    return OpenMCSettings(
        profile_name=(
            profile_name
        ),
        particles_per_batch=(
            canonical_settings
            .particles_per_batch
        ),
        batches=(
            canonical_settings
            .batches
        ),
        random_seed=(
            canonical_settings
            .random_seed
        ),
        threads=(
            canonical_settings
            .threads
        ),
        energy_bin_boundaries_ev=(
            energy_bin_boundaries_ev
        ),
        electron_treatment=(
            canonical_settings
            .electron_treatment
        ),
        atomic_relaxation=(
            canonical_settings
            .atomic_relaxation
        ),
        photon_cutoff_energy_ev=(
            canonical_settings
            .photon_cutoff_energy_ev
        ),
        outer_boundary_radius_cm=(
            canonical_settings
            .outer_boundary_radius_cm
        ),
        statepoint_batches=list(
            canonical_settings
            .statepoint_batches
        ),
    )


def find_containing_bin(
    boundaries: list[float],
    energy_ev: float,
) -> tuple[
    float,
    float,
]:
    for (
        lower_energy_ev,
        upper_energy_ev,
    ) in zip(
        boundaries[:-1],
        boundaries[1:],
        strict=True,
    ):
        if (
            lower_energy_ev
            <= energy_ev
            < upper_energy_ev
        ):
            return (
                lower_energy_ev,
                upper_energy_ev,
            )

    raise RuntimeError(
        "Cs-137 source energy is not contained "
        "in the generated sensitivity grid."
    )


def require_identical_transport_settings(
    *,
    canonical: OpenMCSettings,
    candidate: OpenMCSettings,
) -> None:
    attributes = (
        "particles_per_batch",
        "batches",
        "random_seed",
        "threads",
        "electron_treatment",
        "atomic_relaxation",
        "photon_cutoff_energy_ev",
        "outer_boundary_radius_cm",
        "statepoint_batches",
    )

    for attribute_name in attributes:
        require(
            getattr(
                canonical,
                attribute_name,
            )
            == getattr(
                candidate,
                attribute_name,
            ),
            (
                "Energy-grid sensitivity profile "
                "changed transport setting "
                f"{attribute_name}."
            ),
        )


def save_and_round_trip(
    settings: OpenMCSettings,
    output_path: Path,
) -> None:
    save_openmc_settings(
        settings,
        output_path,
    )

    reloaded = (
        load_openmc_settings(
            output_path
        )
    )

    require(
        reloaded == settings,
        (
            "Energy-grid sensitivity settings "
            f"round trip changed {settings.profile_name}."
        ),
    )


def main() -> None:
    canonical_settings = (
        load_openmc_settings(
            CANONICAL_SETTINGS_PATH
        )
    )

    require(
        canonical_settings.profile_name
        == EXPECTED_CANONICAL_PROFILE_NAME,
        (
            "Unexpected canonical V1.14 "
            "production profile name."
        ),
    )

    canonical_boundaries = list(
        canonical_settings
        .energy_bin_boundaries_ev
    )

    require(
        len(
            canonical_boundaries
        )
        == EXPECTED_CANONICAL_BOUNDARY_COUNT,
        (
            "V1.14 canonical energy grid no longer "
            "contains the expected 77 boundaries."
        ),
    )

    require(
        len(
            canonical_boundaries
        )
        - 1
        == EXPECTED_CANONICAL_BIN_COUNT,
        (
            "V1.14 canonical energy grid no longer "
            "contains the expected 76 bins."
        ),
    )

    coarse_boundaries = (
        create_coarse_boundaries(
            canonical_boundaries
        )
    )

    refined_boundaries = (
        create_refined_boundaries(
            canonical_boundaries
        )
    )

    require(
        len(
            coarse_boundaries
        )
        - 1
        == EXPECTED_COARSE_BIN_COUNT,
        (
            "Unexpected coarse V1.14 "
            "energy-bin count."
        ),
    )

    require(
        len(
            refined_boundaries
        )
        - 1
        == EXPECTED_REFINED_BIN_COUNT,
        (
            "Unexpected refined V1.14 "
            "energy-bin count."
        ),
    )

    require(
        coarse_boundaries[0]
        == canonical_boundaries[0]
        == refined_boundaries[0],
        (
            "Energy-grid sensitivity profiles "
            "do not share a common lower bound."
        ),
    )

    require(
        coarse_boundaries[-1]
        == canonical_boundaries[-1]
        == refined_boundaries[-1],
        (
            "Energy-grid sensitivity profiles "
            "do not share a common upper bound."
        ),
    )

    coarse_settings = (
        create_sensitivity_settings(
            canonical_settings=(
                canonical_settings
            ),
            profile_name=(
                "v114_energy_coarse"
            ),
            energy_bin_boundaries_ev=(
                coarse_boundaries
            ),
        )
    )

    refined_settings = (
        create_sensitivity_settings(
            canonical_settings=(
                canonical_settings
            ),
            profile_name=(
                "v114_energy_refined"
            ),
            energy_bin_boundaries_ev=(
                refined_boundaries
            ),
        )
    )

    require_identical_transport_settings(
        canonical=(
            canonical_settings
        ),
        candidate=(
            coarse_settings
        ),
    )

    require_identical_transport_settings(
        canonical=(
            canonical_settings
        ),
        candidate=(
            refined_settings
        ),
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_and_round_trip(
        coarse_settings,
        COARSE_SETTINGS_PATH,
    )

    save_and_round_trip(
        refined_settings,
        REFINED_SETTINGS_PATH,
    )

    canonical_source_bin = (
        find_containing_bin(
            canonical_boundaries,
            CS137_SOURCE_ENERGY_EV,
        )
    )

    coarse_source_bin = (
        find_containing_bin(
            coarse_boundaries,
            CS137_SOURCE_ENERGY_EV,
        )
    )

    refined_source_bin = (
        find_containing_bin(
            refined_boundaries,
            CS137_SOURCE_ENERGY_EV,
        )
    )

    print()
    print("=" * 88)
    print(
        "V1.14 ENERGY-GRID SENSITIVITY SETTINGS CREATED"
    )
    print("=" * 88)

    print(
        "Transport settings changed: No"
    )

    print(
        "Random seed preserved: "
        f"{canonical_settings.random_seed}"
    )

    print(
        "Histories per run: "
        f"{canonical_settings.total_source_particles:,}"
    )

    print(
        "Energy range: "
        f"{canonical_boundaries[0]:.0f} to "
        f"{canonical_boundaries[-1]:.0f} eV"
    )

    print("-" * 88)

    print(
        "Coarse grid:"
    )

    print(
        "  Bins: "
        f"{len(coarse_boundaries) - 1}"
    )

    print(
        "  Cs-137 source bin: "
        f"{coarse_source_bin[0]:.6f} to "
        f"{coarse_source_bin[1]:.6f} eV"
    )

    print(
        "  File: "
        f"{COARSE_SETTINGS_PATH}"
    )

    print()

    print(
        "Canonical grid:"
    )

    print(
        "  Bins: "
        f"{len(canonical_boundaries) - 1}"
    )

    print(
        "  Cs-137 source bin: "
        f"{canonical_source_bin[0]:.6f} to "
        f"{canonical_source_bin[1]:.6f} eV"
    )

    print(
        "  File: "
        f"{CANONICAL_SETTINGS_PATH}"
    )

    print()

    print(
        "Refined grid:"
    )

    print(
        "  Bins: "
        f"{len(refined_boundaries) - 1}"
    )

    print(
        "  Cs-137 source bin: "
        f"{refined_source_bin[0]:.6f} to "
        f"{refined_source_bin[1]:.6f} eV"
    )

    print(
        "  File: "
        f"{REFINED_SETTINGS_PATH}"
    )

    print("-" * 88)

    print(
        "PASS: Coarse and refined spectrum grids were "
        "derived from the canonical production grid "
        "without changing transport settings."
    )

    print("=" * 88)
    print()


if __name__ == "__main__":
    main()
