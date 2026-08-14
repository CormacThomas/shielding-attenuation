# Shielding Attenuation Simulator

Photon shielding analysis, engineering optimization, and OpenMC benchmarking in Python.

This project started as a small Java attenuation calculator and has gradually grown into a larger shielding analysis tool. The current version combines deterministic calculations for quick design studies with OpenMC photon transport for higher-fidelity comparison.

**Stable release:** V1.13
**Current development:** V1.14

![Project quad chart](docs/assets/Quad_Plot_Cormac_Thomas.pdf)

## What it does

The simulator is built around a fairly simple idea: deterministic models are useful for quickly screening a large number of shielding designs, while Monte Carlo is better suited for checking selected cases in more detail.

The deterministic side currently supports:

* Beer-Lambert attenuation
* inverse-square spreading
* NIST XCOM attenuation data
* manual and isotope-based photon sources
* single-layer and multilayer attenuation
* G-P exposure buildup for supported materials
* photon fluence and collision-air-kerma calculations
* minimum-thickness calculations
* material comparison
* thickness, mass, and relative-cost constraints
* several optimization objectives
* Pareto trade studies
* JSON-defined scenarios

The OpenMC side adds:

* fixed-source photon transport
* concentric spherical benchmark geometry
* energy-resolved photon tallies
* direct collision-air-kerma response tallies
* physical source-rate scaling
* statistical uncertainty
* deterministic/OpenMC comparison
* convergence and sensitivity studies

The project is mainly intended for shielding design studies, computational benchmarking, and engineering analysis. It is not intended for regulatory or safety-critical calculations.

## Current V1.14 benchmark work

V1.14 expands the single V1.13 OpenMC benchmark into a small matrix of Cs-137 shielding cases.

The current production matrix contains eight cases:

| Material          | Optical thickness |
| ----------------- | ----------------: |
| Lead              |             1 MFP |
| Lead              |             5 MFP |
| Lead              |            10 MFP |
| Tungsten          |             1 MFP |
| Tungsten          |             5 MFP |
| Ordinary Concrete |             1 MFP |
| Ordinary Concrete |             5 MFP |
| Water             |             5 MFP |

Each case uses 50,000 particles per batch for 100 batches, or 5 million photon histories per case.

That gives 40 million histories across the core benchmark matrix.

Monte Carlo statistical uncertainty across the eight production cases ranges from about 0.04% to 3.11%.

Current benchmark checks:

* 8/8 cases pass the required Monte Carlo uncertainty criterion
* 7/8 meet the preferred uncertainty criterion
* 8/8 pass the direct-vs-spectrum-folded consistency check

The one case that misses the preferred uncertainty target is Lead at 10 MFP. It still passes the required criterion and was checked separately with a convergence study.

## A result I found interesting

One of the main things I wanted to learn from the V1.14 work was whether the G-P buildup approximation showed a consistent bias relative to OpenMC. I learned that it does not.

For Lead:

| Optical thickness | OpenMC buildup | G-P buildup | OpenMC vs. G-P response |
| ----------------- | -------------: | ----------: | ----------------------: |
| 1 MFP             |          1.299 |       1.458 |                  -10.9% |
| 5 MFP             |          2.482 |       2.421 |                   +2.5% |
| 10 MFP            |          4.373 |       3.164 |                  +38.2% |

Across the current benchmark set, the G-P/OpenMC response difference ranges from roughly -46% to +38%.

The sign and size of the difference depend on both the material and optical thickness, so I do not treat the deterministic buildup model as having one universal conservative or non-conservative bias.

The 5-MFP cases also show how different materials can behave even when the primary photon attenuation is expressed at the same optical thickness:

| Material          | OpenMC-derived buildup |
| ----------------- | ---------------------: |
| Lead              |                   2.48 |
| Tungsten          |                   2.72 |
| Ordinary Concrete |                   7.03 |
| Water             |                   8.25 |

Matching narrow-beam attenuation does not necessarily mean matching total response after scattered photons are included.

That is one of the main reasons I use the deterministic model for screening and OpenMC for selected verification cases.

## Numerical checks

I have also been using V1.14 to check whether some of the deterministic/OpenMC differences could be caused by numerical choices rather than the underlying models.

### Monte Carlo convergence

For Lead at 10 MFP:

|    Histories | Relative uncertainty |
| -----------: | -------------------: |
| 1.25 million |                7.33% |
| 2.50 million |                4.72% |
| 3.75 million |                3.67% |
| 5.00 million |                3.11% |

The response stayed reasonably stable while the statistical uncertainty decreased.

### Evaluation-shell sensitivity

The OpenMC response is evaluated in a thin spherical shell centered at a 100 cm radius.

I tested shell thicknesses from 0.25 cm through 2.0 cm. The maximum change relative to the canonical shell was about 0.0025%.

The change closely matched the analytical finite-shell inverse-square averaging effect.

### Energy-grid sensitivity

For the Water 5-MFP case:

| Energy grid | Bins | Direct vs. folded |
| ----------- | ---: | ----------------: |
| Coarse      |   38 |          +0.4451% |
| Production  |   76 |          +0.1591% |
| Refined     |  152 |          +0.0399% |

The direct-response tally stayed effectively unchanged while the spectrum-folded calculation converged toward it as the energy grid was refined.

## Engineering design features

The deterministic side of the project is also used as a design tool.

Instead of only asking:

> What is the response behind a fixed thickness of shielding?

the program can also solve problems such as:

> What material and thickness meet a response target while minimizing mass?

Supported targets include:

* transmission
* reduction factor
* photon fluence rate
* collision-air-kerma rate

Designs can be filtered using:

* maximum thickness
* maximum mass per area
* relative-cost limits

Optimization objectives currently include:

* minimum thickness
* minimum mass
* minimum relative cost
* weighted balanced objectives

The tool also distinguishes between designs that are physically valid but violate engineering constraints and designs that cannot be evaluated with the available model or data.

### V1.12 example

One reference problem uses a 1 Ci Cs-137 source at 100 cm with a target collision-air-kerma rate of 1 µGy/h.

Constraints:

* maximum thickness: 20 cm
* maximum mass per area: 120 g/cm²
* objective: minimum mass per area
* nine candidate materials

The optimizer selects Lead:

| Result             |         Value |
| ------------------ | ------------: |
| Required thickness |    7.18065 cm |
| Mass per area      | 81.4286 g/cm² |
| Final response     |  ~1.000 µGy/h |

Of the nine candidate materials:

* 2 are eligible
* 4 are rejected by engineering constraints
* 3 cannot be evaluated under the required buildup model

## V1.13 benchmark

V1.13 established the first complete deterministic/OpenMC comparison pathway.

The reference case uses:

* Cs-137
* 1.00 Ci activity
* 0.661657 MeV photon energy
* 5.0 cm Lead
* 100 cm evaluation radius
* 5 million OpenMC histories
* dry-air collision air kerma as the response quantity

Results:

| Calculation                | Collision air-kerma rate |
| -------------------------- | -----------------------: |
| Deterministic uncollided   |             5.1399 µGy/h |
| Deterministic G-P adjusted |            13.5575 µGy/h |
| OpenMC direct              |            15.0198 µGy/h |
| OpenMC spectrum folded     |            15.0213 µGy/h |

The OpenMC direct result has a relative statistical uncertainty of about 0.58%.

The direct and spectrum-folded OpenMC calculations differ by about 0.01%.

For this case, the G-P-adjusted deterministic result is about 10.8% below the direct OpenMC result.

![V1.13 Cs-137 Lead benchmark](docs/figures/v1.13/cs137_lead_openmc_benchmark.png)

More information on the V1.13 benchmark is available here:

[`results/v1.13/cs137_lead_benchmark/README.md`](results/v1.13/cs137_lead_benchmark/README.md)

## Project history

The project has changed quite a bit since I started it.

### Original Java version

The first version was a basic attenuation calculator using Beer-Lambert attenuation and inverse-square spreading.

That version was useful for learning the basic physics and building the first material calculations, but it was limited to fairly simple shielding problems.

### Python deterministic model

I later rewrote the project in Python and added:

* NIST XCOM data
* isotope photon lines
* energy-dependent attenuation
* multilayer shielding
* G-P buildup
* explicit radiation-response quantities
* collision-air-kerma calculations

### Engineering optimization

The next stage added:

* target-driven minimum thickness
* material comparison
* mass and relative-cost metrics
* engineering constraints
* multiple objectives
* Pareto analysis
* reusable plotting
* JSON scenarios

This was the point where the project became more of an engineering design tool than an attenuation calculator.

### OpenMC benchmarking

The current stage adds OpenMC as a higher-fidelity computational reference.

That work includes:

* shared deterministic/OpenMC scenarios
* photon transport tallies
* response tallies
* uncertainty calculations
* deterministic/OpenMC comparison
* convergence testing
* numerical sensitivity studies

## Radiation-response quantities

The simulator keeps photon-number quantities separate from energy-weighted response quantities.

Current outputs include:

* uncollided photon fluence rate
* photon energy fluence rate
* uncollided collision-air-kerma rate
* G-P-adjusted collision-air-kerma rate
* OpenMC photon fluence rate
* OpenMC direct collision-air-kerma response
* OpenMC spectrum-folded collision-air-kerma response

G-P exposure buildup is only applied to compatible collision-air-kerma calculations. It is not used as a correction to photon-number fluence.

The primary engineering display unit is µGy/h.

## Scenarios

Shielding problems can be stored as JSON files so that deterministic and OpenMC calculations can use the same physical inputs.

A scenario can include:

* source type
* activity
* photon lines
* shielding geometry
* material layers
* evaluation radius
* response target
* candidate materials
* engineering constraints
* optimization objective

OpenMC execution settings are stored separately from the physical scenario. Particle count, batches, random seed, tally settings, and energy bins can therefore be changed without redefining the shielding problem.

Example scenarios are stored in:

```text
scenarios/
```

## Installation

Python 3.10 or newer is recommended.

Clone the repository:

```bash
git clone https://github.com/CormacThomas/shielding-attenuation.git
cd shielding-attenuation
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the interactive deterministic simulator:

```bash
cd src
python main.py
```

OpenMC calculations require a separate OpenMC installation or container with compatible continuous-energy photon data.

## Example commands

Run the V1.12 deterministic design scenario:

```bash
python examples/run_scenario.py scenarios/cs137_air_kerma_reference.json
```

Run the V1.13 production OpenMC benchmark:

```bash
python examples/openmc_v113_production_run.py
```

Process the preserved V1.13 production statepoint:

```bash
python examples/openmc_v113_process_production_recovery.py
```

Run deterministic and regression checks:

```bash
python src/validation_runner.py
```

Generate the V1.13 benchmark figures:

```bash
python examples/generate_v113_benchmark_figure.py
```

## Repository layout

* `src/` — deterministic model, optimization, response calculations, and OpenMC processing
* `scenarios/` — reusable shielding problem definitions
* `examples/` — example calculations and figure-generation scripts
* `config/` — OpenMC execution settings
* `docs/` — figures, architecture notes, reports, and project material
* `results/` — benchmark outputs and release packages
* `CHANGELOG.md` — development history

## Current status

### V1.13

Stable benchmark-foundation release.

V1.13 contains the first matched deterministic/OpenMC benchmark and the supporting response-processing and release workflow.

### V1.14

In progress.

Current work includes:

* eight-case Cs-137 benchmark matrix
* multiple materials and optical thicknesses
* G-P/OpenMC buildup comparison
* Monte Carlo convergence
* evaluation-shell sensitivity
* energy-grid sensitivity
* benchmark report preparation

The core eight-case production matrix is complete.

Some originally planned V1.14 work, including broader isotope and energy coverage, has been deferred.

## Roadmap

| Version | Planned work                                     |
| ------- | ------------------------------------------------ |
| V1.14   | Multi-case single-layer OpenMC benchmark study   |
| V1.15   | Mass-aware and two-layer deterministic screening |
| V1.16   | OpenMC layer-order and finalist verification     |
| V1.17   | Final Cs-137 shield-container design study       |
| V1.18   | Portfolio monograph and release package          |
| V1.19   | Optional GUI and extended research features      |

## Limitations

Current limitations include:

* isotropic point-source geometry
* no extended-source or source self-attenuation model
* deterministic buildup limited to supported materials and optical-thickness ranges
* no deterministic multilayer buildup model
* selected isotope photon lines rather than complete decay spectra
* no detector efficiency or detector-window response
* no source encapsulation model
* no air attenuation
* homogeneous single-material optimization only
* simplified relative-cost indices
* no experimental benchmark data

OpenMC results also depend on the selected nuclear data, transport settings, tally definitions, response coefficients, and statistical convergence.

The current OpenMC work should be described as computational benchmarking or verification.

This software is intended for conceptual engineering analysis, education, and research development. It is not intended for regulatory certification or safety-critical design approval.

## Documentation

More detailed documentation is available in:

* [`docs/`](docs)
* [`results/`](results)
* [`CHANGELOG.md`](CHANGELOG.md)

Recent project milestones:

* **V1.09** — constraint-based material selection
* **V1.10** — engineering visualization and Pareto analysis
* **V1.11** — reproducible scenarios and spherical geometry
* **V1.12** — collision-air-kerma response framework
* **V1.13** — first matched deterministic/OpenMC benchmark
* **V1.14** — multi-case computational benchmarking *(in progress)*

## References

Primary technical references include:

* NIST XCOM Photon Cross Sections Database
* NIST mass energy-absorption coefficients for dry air
* ANS-6.4.3 gamma-ray exposure-buildup data
* OpenMC photon-transport documentation
* NuDat and IAEA nuclear-decay data

## Author

**Cormac Thomas**
B.S. Nuclear Engineering Student
University of New Mexico

Interests: radiation transport, shielding, radiation effects, Monte Carlo methods, nuclear systems, and national-security engineering.

[GitHub](https://github.com/CormacThomas) · [LinkedIn](https://www.linkedin.com/in/cormacthomas/)
