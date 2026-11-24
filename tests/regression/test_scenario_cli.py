"""Check that packaged commands can report both reference design quantities."""

from pathlib import Path

import pytest

from shielding.cli.commands import main

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("scenario", "summary"),
    [
        (
            "cs137_v110_reference.json",
            "Selected response basis: Uncollided photon fluence rate",
        ),
        ("cs137_air_kerma_reference.json", "collision air-kerma rate"),
    ],
)
def test_reference_designs_are_reported(scenario, summary, capsys):
    assert main(["scenario", str(ROOT / "scenarios" / scenario)]) == 0
    assert summary in capsys.readouterr().out
