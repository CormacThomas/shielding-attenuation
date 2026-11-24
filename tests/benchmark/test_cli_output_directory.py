"""An explicit overwrite must still preserve the files used as inputs."""

from pathlib import Path

from shielding.cli.commands import main

ROOT = Path(__file__).resolve().parents[2]


def test_benchmark_process_keeps_statepoint_inside_output_directory(tmp_path, capsys):
    statepoint = tmp_path / "statepoint.100.h5"
    statepoint.touch()

    exit_code = main(
        [
            "benchmark",
            "--mode",
            "process",
            "--scenario",
            str(ROOT / "scenarios/v1.14/cs137_lead_05mfp.json"),
            "--settings",
            str(ROOT / "config/openmc/v114_production.json"),
            "--statepoint",
            str(statepoint),
            "--output-directory",
            str(tmp_path),
            "--overwrite",
        ]
    )

    assert exit_code == 1
    assert "must not contain input file" in capsys.readouterr().err
    assert statepoint.is_file()
