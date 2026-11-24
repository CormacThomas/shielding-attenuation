"""Run a scenario, defaulting to the Cs-137 air-kerma reference case."""

import sys
from pathlib import Path

from shielding.cli.scenario import main

if __name__ == "__main__":
    default = (
        Path(__file__).resolve().parents[1] / "scenarios/cs137_air_kerma_reference.json"
    )
    raise SystemExit(main(sys.argv[1:] or [str(default)]))
