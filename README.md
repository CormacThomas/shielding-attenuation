# Shielding Attenuation Simulator

A validated Python photon-shielding analysis and engineering design tool using NIST XCOM attenuation data, isotope photon-source models, dry-air collision-air-kerma response coefficients, G-P exposure buildup factors, engineering constraints, Pareto analysis, reproducible JSON scenarios, and OpenMC-ready spherical geometry.

## Overview

The Shielding Attenuation Simulator models photon attenuation and radiation-response quantities from an isotropic point source through shielding materials.

The project began as a Java Beer-Lambert attenuation calculator and has developed into a modular Python shielding-design workflow capable of:

- calculating narrow-beam photon attenuation;
- modeling selected isotope photon lines;
- reporting explicit photon fluence and collision-air-kerma quantities;
- estimating single-layer exposure buildup;
- solving for minimum shielding thickness;
- comparing candidate materials;
- applying thickness, mass, and relative-cost constraints;
- ranking feasible designs under multiple objectives;
- visualizing engineering tradeoffs and photon-line contributions;
- loading complete design scenarios from JSON;
- defining concentric spherical shielding geometry;
- preparing quantity-matched inputs for future OpenMC benchmarking.

The current release is **V1.12**.

## Current Capabilities

### Deterministic Photon Transport

- Beer-Lambert narrow-beam attenuation
- Single-layer and multilayer transmission
- NIST XCOM mass attenuation data
- Log-log attenuation-coefficient interpolation
- Linear attenuation coefficients
- Mean-free-path calculations
- Inverse-square point-source spreading
- Manual monoenergetic photon sources
- Selected isotope photon spectra
- Line-by-line isotope calculations
- G-P exposure buildup for supported homogeneous shields

### Radiation-Response Quantities

V1.12 separates quantities that were previously represented through legacy flux-named fields.

The simulator now reports:

- uncollided photon fluence rate in photons/cm²/s;
- photon energy fluence rate in MeV/(cm²·s);
- uncollided collision air-kerma rate in Gy/s and µGy/h;
- G-P exposure-buildup-adjusted collision air-kerma rate in Gy/s and µGy/h.

The response calculation follows the line-by-line sequence:

```text
Activity and emission intensity
            ↓
Photon emission rate
            ↓
Beer-Lambert transmission
            ↓
Uncollided photon fluence rate
            ↓
Photon energy fluence rate
            ↓
Dry-air μen/ρ response folding
            ↓
Uncollided collision air-kerma rate
            ↓
Optional G-P exposure-buildup adjustment
```

The canonical internal air-kerma-rate unit is:

```text
Gy/s
```

The primary engineering display unit is:

```text
µGy/h
```

The dry-air response calculation uses a 38-entry NIST mass energy-absorption coefficient table from 0.001 to 20 MeV. The implementation preserves the duplicate argon K-edge entries and prevents interpolation across the zero-width absorption-edge interval.

### Shielding Design

Supported design targets include:

- transmission targets;
- reduction-factor targets;
- uncollided photon-fluence-rate targets;
- collision-air-kerma-rate targets.

Design capabilities include:

- analytical and numerical minimum-thickness solutions;
- bracket scanning and bisection;
- support for initially nonmonotonic buildup-adjusted responses;
- single-material comparison;
- engineering constraint filtering;
- minimum-thickness optimization;
- minimum-mass optimization;
- minimum-relative-cost optimization;
- weighted balanced optimization;
- explicit `ELIGIBLE`, `REJECTED`, and `FAILED` design states;
- thickness-mass Pareto classification.

Air-kerma target calculations use strict buildup behavior. When G-P exposure buildup is required, every contributing photon line must have a valid buildup result. Unsupported materials or out-of-domain optical thicknesses are reported as `FAILED` rather than silently substituted with an uncollided design.

### Reproducible Scenarios

The shared scenario layer allows complete shielding problems to be stored as human-readable JSON:

```text
Scenario JSON
      ↓
Validated ShieldingScenario
      ↓
scenario_runner.py
      ↓
Response-specific deterministic optimizer
```

A scenario can define:

- source type and activity;
- concentric spherical geometry;
- source-cavity radius;
- evaluation radius;
- candidate materials;
- response target;
- engineering constraints;
- optimization objective;
- optional balanced weights;
- deterministic calculation settings.

The scenario runner routes air-kerma targets through the V1.12 air-response optimizer and retains the earlier photon-response pathway for backward compatibility.

The same scenario foundation is planned to support the OpenMC backend beginning in V1.13.

## Official V1.12 Engineering Case

The official V1.12 reference scenario models:

- Source: Cs-137
- Activity: 1.00 Ci, or 3.70 × 10¹⁰ Bq
- Selected photon line: 0.661657 MeV
- Emission intensity: 0.851 photons/decay
- Source-cavity radius: 0 cm
- Evaluation radius: 100 cm
- Target: G-P exposure-buildup-adjusted collision air-kerma rate ≤ 1 µGy/h
- Maximum shielding thickness: 20 cm
- Maximum mass per area: 120 g/cm²
- Objective: minimum mass per area
- Candidate materials: nine
- G-P exposure buildup: required
- Numerical search limit: 100 cm

The optimizer selects **Lead**:

```text
Required thickness: 7.180648660 cm
Mass per area:      81.428555808 g/cm²
Final adjusted K:   0.999999991 µGy/h
Response ratio:     3.570781 × 10⁻⁴
Eligible designs:   Lead and Tungsten
Selected objective: Minimum mass per area
```

The complete candidate accounting is:

```text
2 eligible + 4 rejected + 3 failed = 9 materials
```

- Lead and Tungsten are eligible.
- Aluminum and Ordinary Concrete exceed both active engineering limits.
- Copper and Tin exceed the mass-per-area limit.
- Barite Concrete and Polyethylene lack validated G-P exposure buildup data.
- Water cannot reach the required response within the 100 cm calculation range.

The official scenario file is:

```text
scenarios/cs137_air_kerma_reference.json
```

The earlier V1.10 photon-response reference scenario remains available for regression testing:

```text
scenarios/cs137_v110_reference.json
```

## Co-60 Photon-Line Contribution Figure

V1.12 includes a reproducible line-contribution figure for:

- 1.00 Ci Co-60;
- 5.00 cm Lead;
- 100 cm evaluation distance;
- two modeled photon lines;
- uncollided and G-P-adjusted collision-air-kerma contributions.

The validated source totals are approximately:

```text
Uncollided collision air-kerma rate: 402.829 µGy/h
G-P-adjusted collision air-kerma rate: 1086.362 µGy/h
```

![Co-60 photon-line contributions](docs/figures/v1.12/co60_photon_line_air_kerma_contributions.png)

The figure demonstrates that photon-line contributions depend on energy, attenuation, dry-air response coefficient, emission intensity, and buildup factor. Contribution cannot be inferred from emission intensity alone.

## Installation

Python 3.10 or newer is recommended.

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

Install project dependencies:

```bash
python -m pip install -r requirements.txt
```

## Running the Simulator

From the repository root:

```bash
cd src
python main.py
```

The command-line interface supports:

1. fixed-thickness shielding calculations;
2. minimum-thickness shielding design;
3. material comparison;
4. constraint-based material optimization.

Each mode allows the user to select the intended response quantity:

- uncollided photon fluence rate;
- collision air-kerma rate.

Exposure buildup is not applied to photon-number fluence. The G-P prompt is shown only for compatible collision-air-kerma calculations.

## Running Reproducible Scenarios

Run the official V1.12 air-kerma scenario:

```bash
python examples/run_scenario.py
```

Run a specific scenario:

```bash
python examples/run_scenario.py scenarios/cs137_air_kerma_reference.json
```

Run the historical V1.10 regression scenario:

```bash
python examples/run_scenario.py scenarios/cs137_v110_reference.json
```

The scenario output reports:

- scenario metadata;
- target quantity and units;
- buildup treatment;
- candidate counts;
- selected material;
- required thickness;
- mass per area;
- final response;
- response ratio;
- selection reason;
- failed-candidate explanations;
- warnings.

## Running Validation

From the repository root:

```bash
python src/validation_runner.py
```

Expected final message:

```text
All validation tests passed.
```

The complete V1.12 suite contains:

```text
684 total PASS assertions
365 assertions focused on V1.12
319 retained V1.11 and earlier regression assertions
```

V1.12 coverage includes:

- dry-air coefficient-library structure;
- exact coefficient lookup;
- log-log interpolation;
- absorption-edge behavior;
- coefficient range rejection;
- MeV, joule, area, coefficient, and air-kerma unit conversions;
- monoenergetic collision-air-kerma hand calculations;
- photon-line metadata;
- source-level response aggregation;
- Cs-137 line behavior;
- Co-60 two-line summation;
- Am-241 low-energy applicability handling;
- zero-thickness buildup behavior;
- the 40-MFP G-P boundary;
- strict unavailable-buildup handling;
- air-kerma targets and result models;
- minimum-thickness calculations;
- nonmonotonic bracket scanning;
- material comparison;
- constrained optimization;
- scenario serialization and execution;
- CLI response routing;
- public output terminology;
- V1.10 and V1.11 backward compatibility.

## Generating Engineering Figures

Generate the V1.10 engineering-design figure set:

```bash
python examples/generate_v110_figures.py
```

This creates four PNG and four SVG files under:

```text
docs/figures/v1.10/
```

The figures cover:

- material thickness, mass, and relative cost;
- engineering constraint feasibility;
- thickness-mass Pareto tradeoffs;
- detector response versus Lead thickness.

Generate the V1.12 Co-60 line-contribution figure:

```bash
python examples/generate_v112_line_contribution_figure.py
```

This creates PNG and SVG files under:

```text
docs/figures/v1.12/
```

## OpenMC Environment Test

The repository includes a Docker-based OpenMC photon-transport smoke test.

Launch the official OpenMC image with the repository mounted:

```powershell
docker run --rm -it `
    -v "${PWD}:/workspace" `
    -w /workspace `
    openmc/openmc:latest
```

Inside the container:

```bash
python examples/openmc_smoke_test.py
```

The verified test used OpenMC 0.15.3 and confirmed:

- access to continuous-energy photon data;
- fixed-source photon transport;
- concentric spherical Lead-shell geometry;
- statepoint generation;
- named tally extraction through Python.

This smoke test verifies environment readiness only. Its raw cell-flux tally is not an air-kerma result and is not a matched deterministic-versus-OpenMC benchmark.

## Project Structure

```text
shielding-attenuation/
├── docs/
│   ├── architecture/
│   ├── figures/
│   │   ├── v1.10/
│   │   └── v1.12/
│   └── validation reports/
├── examples/
│   ├── generate_v110_figures.py
│   ├── generate_v112_line_contribution_figure.py
│   ├── openmc_smoke_test.py
│   └── run_scenario.py
├── scenarios/
│   ├── cs137_air_kerma_reference.json
│   └── cs137_v110_reference.json
├── src/
│   ├── air_response.py
│   ├── air_response_library.py
│   ├── air_response_models.py
│   ├── air_response_plots.py
│   ├── buildup modules
│   ├── attenuation and source modules
│   ├── optimization modules
│   ├── plotting modules
│   ├── geometry_models.py
│   ├── scenario_models.py
│   ├── scenario_io.py
│   ├── scenario_runner.py
│   ├── target_models.py
│   ├── thickness_calculator.py
│   ├── unit_conversions.py
│   └── validation_runner.py
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt
```

## Current Limitations

- Photon emission is modeled as an isotropic point source.
- Extended-source geometry and source self-attenuation are not modeled.
- Beer-Lambert attenuation represents the narrow-beam uncollided component.
- G-P exposure buildup is an engineering response approximation rather than explicit scattered-particle transport.
- G-P exposure buildup currently supports one homogeneous shielding material at a time.
- Deterministic multilayer attenuation is supported, but deterministic multilayer buildup is not claimed.
- G-P calculations are limited to supported materials and optical thicknesses no greater than 40 MFP.
- Barite Concrete and Polyethylene do not currently have validated G-P coefficient tables.
- Dry-air μen/ρ folding produces a collision air-kerma-rate estimate, not effective dose, organ dose, ambient dose equivalent, or a regulatory dose quantity.
- The isotope library contains selected useful photon lines rather than complete decay spectra.
- Source encapsulation, air attenuation, and detector response are not modeled.
- The current deterministic optimizer evaluates homogeneous single-material designs.
- The spherical geometry layer defines physical shell radii, but total spherical shield mass is not yet used by the current optimizer.
- Relative-cost indices are simplified comparative assumptions rather than market prices.
- OpenMC has been environment-tested but has not yet been compared against the deterministic model using a matched response quantity.
- The software is intended for conceptual engineering analysis and education, not regulatory certification or safety-critical design approval.

## Documentation

Formal validation reports are available in the [`docs`](docs) directory.

Recent reports include:

- **V1.09:** Constraint-based material selection
- **V1.10:** Engineering visualization and Pareto analysis
- **V1.11:** Reproducible scenarios, spherical geometry, JSON validation, and OpenMC environment verification
- **V1.12:** Radiation-response quantities, dry-air collision-air-kerma calculations, strict buildup semantics, and OpenMC benchmark readiness

The complete development history is recorded in [`CHANGELOG.md`](CHANGELOG.md).

## Roadmap

Planned major milestones:

```text
V1.13  Matched OpenMC photon benchmark
V1.14  Compact single-layer OpenMC benchmark study
V1.15  Two-layer spherical optimization
V1.16  Multilayer OpenMC verification
V1.17  Final Cs-137 shield-container design study
V1.18  Portfolio package and optional GUI
```

## Author

Developed by **Cormac Thomas**, B.S. Nuclear Engineering student at the University of New Mexico.

Primary interests include radiation effects, radiation-hardened electronics, shielding analysis, Monte Carlo transport, and national-security technology.

## Primary Technical References

- NIST XCOM Photon Cross Sections Database
- NIST X-Ray Mass Attenuation Coefficients for Dry Air
- ANS-6.4.3 gamma-ray exposure-buildup reference data
- OpenMC photon-transport documentation
- NuDat and IAEA nuclear-decay data resources