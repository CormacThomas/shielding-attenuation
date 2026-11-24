# Architecture and physical models

## Follow one calculation

`shielding scenario` loads a JSON document through `scenarios.json_io`. The scenario records the source, concentric geometry, response quantity or target, and calculation settings. `scenarios.sources` resolves source specifications to runtime photon sources. `scenarios.runner` routes a prescribed layer stack to `scenarios.fixed_shield` and a material-selection problem to `design.optimization`. The API entry point is `run_scenario(load_scenario(path))`.

`physics.attenuation` handles coefficient interpolation and point-source spreading. `physics.layers` applies the line energy to each material layer and retains the individual layer results. `physics.air_kerma` converts each line's fluence into collision air kerma and aggregates source responses. `physics.kerma_coefficients` owns the dry-air lookup, including absorption-edge conventions. Tables live in `data`, with units in their field names or docstrings. The response curves in `design` are numerical samples, and `reporting` renders them or converts ranked designs into plot-ready data.

`monte_carlo.runner` is the OpenMC orchestration layer. It uses the same scenario with a separate execution profile, constructs the model and tallies, processes statepoints, and writes a manifest and response files. `benchmark.comparison` supplies the deterministic shell average and comparison metrics without importing OpenMC. The deterministic solver remains usable without a transport installation.

From the repository root after installation, use the same API as the CLI.

```python
from shielding.scenarios.json_io import load_scenario
from shielding.scenarios.runner import run_scenario

scenario = load_scenario("scenarios/v1.14/cs137_lead_05mfp.json")
result = run_scenario(scenario)
print(result.source_air_kerma_result.total_uncollided_collision_air_kerma_rate_gy_per_s)
```

## Deterministic point kernel

For photon line energy $E$, material layer $i$ has density $\rho_i$ in g/cm³, mass attenuation coefficient $(\mu/\rho)_i(E)$ in cm²/g, and thickness $x_i$ in cm. The optical thickness $\tau_i = \rho_i(\mu/\rho)_i(E)x_i$ is dimensionless, measured in mean free paths. A line with emission rate $q(E)$ in photons/s contributes

```math
T(E) = \prod_i \exp[-\tau_i(E)], \qquad
\dot\Phi(E,r) = \frac{q(E)T(E)}{4\pi r^2}.
```

With $r$ in cm, $\dot\Phi$ is in photons/(cm²·s). Manual sources specify the line rate directly. Isotope cases multiply activity in Bq by photons per decay for each selected line. The isotope library omits minor lines and may omit low-energy X-rays. Material attenuation tables use log-log interpolation and select the post-edge value at exactly duplicated absorption-edge energies. Dry-air coefficients likewise use log-log interpolation between adjacent distinct energies, with an explicit side choice at duplicated edge energies.

For each line, multiply fluence rate by photon energy and by the dry-air mass energy-absorption coefficient, $\mu_\mathrm{en}/\rho$. Convert MeV to J and the area and mass terms to SI. The result is a dry-air collision-air-kerma rate in Gy/s, displayed in µGy/h. This quantity estimates collision energy transfer per mass of air. The simulator has no absorbed-dose or dose-equivalent conversion.

## Buildup and design

The optional geometric-progression model evaluates an exposure buildup factor $B(E,x)$ at optical depth $x$ in mean free paths. It linearly interpolates the five tabulated coefficients by energy. With the intermediate $K(E,x)$ from the fit, it evaluates $1+(b-1)(K^x-1)/(K-1)$, using the linear limit at $K=1$ and $B=1$ at zero thickness. The depth cap is 40 MFP within the supported material's energy grid. A single homogeneous shield can use that factor as a proxy for the collision-air-kerma contribution of scattered photons. The result and its applicability are reported separately from the uncollided response. Arbitrary multilayer buildup and spectral redistribution require a transport model.

For a monoenergetic fluence target, the analytical inverse solves $x=-\ln(T)/\mu$. Multiline fluence and uncollided-kerma sizing use a bounded search since each line attenuates at a different rate. G-P-adjusted kerma can be nonmonotonic. The solver scans a finite thickness grid for the first sampled feasible transition, then bisects that bracket. A narrow feasible interval can fall between samples. Sizing evaluates one homogeneous material at a time.

The optimizer applies hard feasibility constraints after sizing. Areal mass is $\rho x$ in g/cm², and relative cost uses a project-provided index. Minimum-thickness, minimum-areal-mass, minimum-cost, and normalized weighted objectives share one ranking implementation. The selected candidate depends on the supplied materials, bounds, objective, and weights. Total fabricated mass, procurement cost, composition uncertainty, and manufacturing constraints are outside the model.

## OpenMC comparison

The benchmark transports photons in concentric spheres with an isotropic point source. OpenMC uses an explicit material composition for each supported shield, and the evaluation shell is void. The code uses that shell as a fluence scoring region and folds fluence with a dry-air response function. It compares a direct track-length response tally against a separately folded energy-bin spectrum. Track length per source particle is divided by shell volume and scaled by the physical photon rate. A point kernel averaged over the same spherical shell replaces $1/(4\pi r^2)$ with $(r_\mathrm{outer}-r_\mathrm{inner})/V_\mathrm{shell}$. This makes the observed quantity and normalization comparable across both methods.

G-P factors and OpenMC transport reflect different material, geometry, cross-section, and scattering assumptions. The direct tally and folded spectrum are diagnostics from the same run. Their consistency is an internal processing check and Monte Carlo uncertainty measures sampling precision. Neither supplies a measurement of physical accuracy. The recorded study covers one radionuclide and single homogeneous shells. The baseline data and commands are in the [OpenMC guide](OPENMC.md).

## Data and references

- Berger, Hubbell, Seltzer et al., NIST Standard Reference Database 8, photon cross sections and attenuation. The inherited shielding tables identify NIST XCOM as their source. [NIST XCOM](https://doi.org/10.18434/T48G6X)
- Hubbell and Seltzer, NIST mass attenuation and mass energy-absorption coefficient tables. The dry-air lookup preserves the tabulated edges, including duplicates. [NIST dry-air table](https://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/air.html)
- ANSI/ANS-6.4.3-1991 and ORNL RSICC DLC-129 are the documented origins of the G-P exposure buildup approach. [ANSI standard](https://webstore.ansi.org/standards/ansi/ansians1991-1534182) · [ORNL RSICC record](https://rsicc.ornl.gov/codes/dlc/dlc1/dlc-129.html)
- Romano et al. and the OpenMC development team, transport code and user documentation. Each archived run manifest records the OpenMC version, cross-section path, and execution settings available in the supplied run. [OpenMC documentation](https://docs.openmc.org/en/stable/)
- The isotope lines and relative costs are inherited tables. The upload supplies incomplete citation-level provenance for individual isotope yields, material transcriptions, and cost indices.
