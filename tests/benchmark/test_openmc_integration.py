"""Optional OpenMC API and executable checks."""

from pathlib import Path
from shutil import which

import pytest

from shielding.monte_carlo.runner import run_openmc_benchmark_case
from shielding.monte_carlo.settings_io import load_openmc_settings
from shielding.monte_carlo.statepoint import process_openmc_benchmark_statepoint
from shielding.physics.units import convert_gy_per_s_to_microgy_per_h
from shielding.scenarios.json_io import load_scenario

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "scenarios/v1.14/cs137_lead_05mfp.json"
pytestmark = pytest.mark.openmc


def test_archived_lead_statepoint():
    pytest.importorskip("openmc")
    result = process_openmc_benchmark_statepoint(
        ROOT / "benchmarks/reference/v1.14/statepoints/lead-05mfp.h5",
        load_scenario(SCENARIO),
        load_openmc_settings(ROOT / "config/openmc/v114_production.json"),
        expected_batch=100,
    )
    assert convert_gy_per_s_to_microgy_per_h(result.direct_response_rate_gy_per_s) == (
        pytest.approx(46.82529754118281, rel=1e-9)
    )


def test_live_lead_smoke(tmp_path):
    openmc = pytest.importorskip("openmc")
    cross_sections = openmc.config.get("cross_sections")
    if (
        which("openmc") is None
        or not cross_sections
        or not Path(cross_sections).is_file()
    ):
        pytest.skip("Need the OpenMC executable and configured continuous-energy data")

    bundle = run_openmc_benchmark_case(
        scenario=load_scenario(SCENARIO),
        settings_profile=load_openmc_settings(ROOT / "config/openmc/v114_smoke.json"),
        run_directory=tmp_path / "run",
        repository_root=ROOT,
        output=False,
    )
    assert bundle.final_statepoint_path.is_file()
    assert bundle.processed_bundle.openmc_result.direct_response_rate_gy_per_s > 0
