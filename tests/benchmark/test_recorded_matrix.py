"""Replay the deterministic half of the archived eight-case comparison."""

import csv
from pathlib import Path

import pytest

from shielding.benchmark.comparison import create_deterministic_shell_average_result
from shielding.physics.units import convert_gy_per_s_to_microgy_per_h
from shielding.scenarios.fixed_shield import calculate_fixed_shield_response
from shielding.scenarios.json_io import load_scenario

ROOT = Path(__file__).resolve().parents[2]
with (ROOT / "benchmarks/reference/v1.14/analysis/v114_core_matrix.csv").open(
    encoding="utf-8", newline=""
) as stream:
    RECORDS = list(csv.DictReader(stream))


@pytest.mark.parametrize("record", RECORDS, ids=[row["case_id"] for row in RECORDS])
def test_shell_averaged_deterministic_kerma_matches_record(record):
    scenario = load_scenario(ROOT / "scenarios/v1.14" / f"{record['case_id']}.json")
    result = calculate_fixed_shield_response(scenario)
    matched = create_deterministic_shell_average_result(result, 1.0)

    uncollided = (
        matched.total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
    )
    gp = matched.total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
    assert gp is not None
    assert convert_gy_per_s_to_microgy_per_h(uncollided) == pytest.approx(
        float(record["deterministic_uncollided_microgy_per_h"]), rel=1e-10, abs=0
    )
    assert convert_gy_per_s_to_microgy_per_h(gp) == pytest.approx(
        float(record["deterministic_gp_microgy_per_h"]), rel=1e-10, abs=0
    )
