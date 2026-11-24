# Shielding Attenuation Simulator

A Python project for photon shielding design studies and computational benchmarking. It computes uncollided fluence and dry-air collision kerma for point sources, screens candidate shields against engineering constraints, and compares selected concentric spherical cases with OpenMC photon transport.

## Run a case

From the repository root, use Python 3.10 or newer.

```text
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux or macOS, or `.\.venv\Scripts\Activate.ps1` in PowerShell. Then install and run.

```text
python -m pip install -e .
shielding scenario scenarios/cs137_air_kerma_reference.json
```

The example selects lead from the supplied candidate set for a 1 µGy/h collision-air-kerma target at 100 cm. Use `shielding interactive` for the design menu or `python -m shielding --help` to see the available commands. The deterministic installation uses the Python standard library.

| Workflow | Command from the repository root |
| --- | --- |
| Uncollided fluence optimization | `shielding scenario scenarios/cs137_v110_reference.json` |
| Fixed-shield point response | `shielding scenario scenarios/v1.14/cs137_lead_05mfp.json` |
| Rebuild the historical benchmark table | `python examples/aggregate_v114_core_results.py` |
| Generate benchmark plots | Install `python -m pip install -e ".[plots]"`, then run `python examples/generate_v114_core_figures.py` |
| Run the verification suite | Install `python -m pip install -e ".[test]"`, then run `python -m pytest` |

Generated tables and figures go to `output/`. The [OpenMC guide](docs/OPENMC.md) covers installing the separate backend, configuring photon data, and running or processing a case.

## Models and verification

- The deterministic solver applies inverse-square spreading and Beer–Lambert transmission to each photon line and sums the responses. Material coefficients come from NIST tabulations. An optional G-P exposure buildup factor approximates scatter contributions to collision air kerma for supported homogeneous shields.
- The design solver computes one thickness per material, applies hard constraints on thickness, mass per area, and a relative cost index, and ranks feasible designs. Plotting can show Pareto tradeoffs.
- The test suite checks analytical identities, tabular interpolation and absorption edges, scenario round trips, design regressions, and deterministic replay against an archived eight-case benchmark. OpenMC settings, tally normalization, and processing models also have offline checks. Live transport and archived statepoint processing require the optional OpenMC environment.
- The supplied OpenMC 0.15.3 comparison contains eight Cs-137 cases with five million histories each. The archived direct estimates ran from about **46% below** to **38% above** the G-P estimates, depending on material and optical thickness. The benchmark compares two computational models in a defined geometry. Experimental measurements and qualification for operational shielding or dose assessment are outside the project's scope.

## Repository guide

| Location | Contents |
| --- | --- |
| `src/shielding/physics`, `data` | Point-kernel attenuation, buildup, collision kerma, and reference tables |
| `src/shielding/design`, `scenarios` | Sizing, material ranking, JSON inputs, and deterministic orchestration |
| `src/shielding/benchmark`, `monte_carlo` | Matched shell averages, OpenMC model construction, and tally processing |
| `src/shielding/reporting`, `cli` | Plot data, figures, and terminal commands |
| `scenarios/`, `config/openmc/`, `examples/` | Reusable cases, separate transport profiles, and runnable examples |
| `tests/`, `benchmarks/reference/`, `archive/` | Automated checks, historical evidence, and original release material |

[Architecture, equations, and references](docs/MODELS.md) · [Refactor and verification record](docs/REFACTOR.md) · [Interview guide](docs/INTERVIEW.md) · [License](LICENSE)
