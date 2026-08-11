# Generate the reproducible V1.14 OpenMC smoke and production settings files.

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from openmc_benchmark_settings import (  # noqa: E402
    create_v114_production_settings,
    create_v114_smoke_settings,
)
from openmc_settings_io import (  # noqa: E402
    load_openmc_settings,
    save_openmc_settings,
)


OUTPUT_DIRECTORY = REPOSITORY_ROOT / "config" / "openmc"
SMOKE_PATH = OUTPUT_DIRECTORY / "v114_smoke.json"
PRODUCTION_PATH = OUTPUT_DIRECTORY / "v114_production.json"


def save_and_round_trip(settings, output_path: Path) -> None:
    save_openmc_settings(settings, output_path)
    loaded_settings = load_openmc_settings(output_path)

    if loaded_settings != settings:
        raise RuntimeError(
            f"OpenMC settings round trip changed profile {settings.profile_name}."
        )


def main() -> None:
    smoke_settings = create_v114_smoke_settings()
    production_settings = create_v114_production_settings()

    if (
        smoke_settings.energy_bin_boundaries_ev
        != production_settings.energy_bin_boundaries_ev
    ):
        raise RuntimeError(
            "V1.14 smoke and production settings must use the same energy grid."
        )

    save_and_round_trip(smoke_settings, SMOKE_PATH)
    save_and_round_trip(production_settings, PRODUCTION_PATH)

    print(f"PASS: {SMOKE_PATH}")
    print(f"PASS: {PRODUCTION_PATH}")
    print(
        "Energy bins: "
        f"{len(smoke_settings.energy_bin_boundaries_ev) - 1}"
    )
    print(
        "Energy range: "
        f"{smoke_settings.minimum_spectrum_energy_ev:.0f} to "
        f"{smoke_settings.maximum_spectrum_energy_ev:.0f} eV"
    )
    print("OpenMC transport executed: No")


if __name__ == "__main__":
    main()
