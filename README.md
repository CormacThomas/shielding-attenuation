# Shielding Attenuation Simulator (v1.09)

A Python photon-shielding calculator and design tool that combines NIST XCOM attenuation data, Beer-Lambert attenuation, inverse-square geometric spreading, isotope photon-source modeling, optional Geometric Progression (G-P) exposure buildup correction, target-driven minimum-thickness calculations, material comparison, and constraint-based material selection.

## Overview

The Shielding Attenuation Simulator models photon transmission and detector flux from an isotropic point source through shielding materials. It supports multi-layer narrow-beam attenuation, selected isotope photon spectra, single-layer G-P buildup correction for supported materials, minimum shielding thickness calculations for user-defined targets, comparison of candidate materials, and engineering selection using thickness, mass-per-area, and relative-cost constraints.

Version 1.09 adds a decision layer above the validated V1.08 material-comparison workflow. Each material is first evaluated using the same source, detector distance, target, calculation search limit, and buildup setting. Passing designs are then evaluated against optional engineering constraints and ranked by minimum thickness, minimum mass per area, minimum relative cost, or a weighted balanced score.

The project is intended as a nuclear engineering portfolio project focused on radiation shielding, source modeling, numerical methods, optimization, validation, and future comparison with OpenMC photon transport.

## Physics and Design Models

- **Beer-Lambert attenuation:** Calculates narrow-beam transmission through one or more shielding layers.
- **Inverse-square geometric spreading:** Calculates detector flux from an isotropic point source.
- **NIST XCOM interpolation:** Uses log-log interpolation between tabulated mass attenuation coefficients.
- **Linear attenuation conversion:** Converts mass attenuation coefficient to linear attenuation coefficient using material density.
- **Mean free path calculation:** Reports optical thickness for individual layers and the complete shield.
- **G-P buildup correction:** Applies Geometric Progression exposure buildup factors for supported single-layer homogeneous shielding cases.
- **Isotope source calculation:** Converts source activity and photon-line intensity into photon emission rate.
- **Line-by-line isotope summation:** Calculates each selected photon line independently and sums detector flux at the source level.
- **Target-driven shielding design:** Converts transmission, reduction-factor, and detector-flux targets into equivalent flux requirements.
- **Minimum-thickness calculation:** Uses an analytical narrow-beam solution for manual monoenergetic sources and numerical bisection for isotope or buildup-aware cases.
- **Material comparison:** Applies the same shielding problem to multiple single-material candidates.
- **Constraint-based material selection:** Filters and ranks successful candidate designs using engineering constraints and optimization objectives.

## Optimization Model

For each successful single-material candidate, V1.09 calculates mass per unit area:

$$
\frac{m}{A} = \rho x
$$

where density is in g/cm³, required thickness is in cm, and mass per area is reported in g/cm².

The simplified relative-cost metric is:

$$
C_A = \left(\frac{m}{A}\right) I_C
$$

where $I_C$ is a dimensionless comparative cost multiplier interpreted on a relative per-unit-mass basis. Ordinary concrete is assigned the baseline value 1.0. These values are user-editable assumptions and are not market prices or currency.

Balanced optimization first applies min-max normalization among eligible candidates:

$$
N = \frac{x - x_{\min}}{x_{\max} - x_{\min}}
$$

The final weighted score is:

$$
S = \frac{w_tN_t + w_mN_m + w_cN_c}{w_t + w_m + w_c}
$$

where $N_t$, $N_m$, and $N_c$ are normalized thickness, mass-per-area, and relative-cost values. Lower scores are preferred.

## Features

- **Multi-layer narrow-beam support:** Calculates transmission through a stack of shielding layers.
- **Material library:** Includes lead, aluminum, ordinary concrete, barite concrete, water, tungsten, copper, tin, and polyethylene.
- **NIST XCOM-based attenuation data:** Uses tabulated mass attenuation coefficients with exact lookup and interpolation.
- **Expanded single-layer G-P buildup:** Supports lead, aluminum, ordinary concrete, water, tungsten, copper, and tin.
- **Stable material keys:** Separates internal lookup identifiers from human-readable material names.
- **Manual photon source mode:** Accepts photon energy and photon emission rate directly.
- **Isotope source library:** Includes selected major photon lines for Cs-137, Co-60, Am-241, Ba-133, Na-22, Mn-54, Co-57, Zn-65, Eu-152, and Ir-192.
- **Activity conversion:** Supports Bq, kBq, MBq, GBq, Ci, mCi, and uCi.
- **Multi-line isotope handling:** Performs one shielding calculation per photon line and sums source-level flux.
- **Target classes:** Supports transmission, reduction-factor, and detector-flux targets.
- **Minimum shielding thickness mode:** Calculates required thickness for a selected material and design target.
- **Buildup-aware minimum-thickness design:** Uses G-P buildup when valid and falls back to narrow-beam design with a warning when necessary.
- **Material comparison mode:** Compares required thickness across multiple candidate materials.
- **Constraint-based optimization mode:** Applies maximum thickness, maximum mass per area, and maximum relative-cost limits.
- **Four optimization objectives:**
  - minimum required thickness
  - minimum mass per area
  - minimum relative cost index per area
  - balanced weighted score
- **Candidate status classification:** Separates `ELIGIBLE`, `REJECTED`, and `FAILED` designs.
- **Multiple rejection reasons:** Preserves every violated engineering constraint.
- **Failure preservation:** Keeps lower-level calculation failures visible with their original reasons.
- **Deterministic ranking:** Uses secondary metrics and stable material keys to break ties reproducibly.
- **Infeasibility reporting:** Returns no best candidate when no design satisfies all active constraints.
- **Warning preservation:** Retains buildup fallbacks and relative-cost-model warnings.
- **Command-line interface:** Provides fixed-thickness, minimum-thickness, material-comparison, and material-optimization workflows.
- **Validation runner:** Includes regression and V1.09 optimization tests; the current suite produces 215 passing assertions.

## Running the Simulator

The current implementation uses only the Python standard library and requires Python 3.10 or newer.

From the repository:

```bash
cd src
python main.py
```

Run the complete validation suite with:

```bash
cd src
python validation_runner.py
```

## Example Constraint-Based Optimization

Example design problem:

- Source: Cs-137
- Activity: 1 Ci
- Detector distance: 100 cm
- Target: flux ≤ 100 photons/cm²/s
- Calculation search limit: 100 cm
- Buildup requested: yes
- Maximum design thickness: 20 cm
- Maximum mass per area: 120 g/cm²
- Objective: minimum mass per area
- Materials considered: all available materials

```text
Material                    Thickness    Mass/Area      Rel Cost/Area   Buildup     Status
------------------------------------------------------------------------------------------------
Lead                        7.08821      80.3803        241.141         Yes         ELIGIBLE
Tungsten                    4.90817      94.5020        2362.55         Yes         ELIGIBLE
Aluminum                    58.3158      157.453        629.810         Yes         REJECTED
Concrete (Barite, Type BA)  28.7625      100.669        161.070         Fallback    REJECTED
Concrete (Ordinary)         62.0647      148.955        148.955         Yes         REJECTED
Copper                      17.2589      154.640        1237.12         Yes         REJECTED
Polyethylene                94.6039      88.9277        177.855         Fallback    REJECTED
Tin                         18.6007      135.971        951.799         Yes         REJECTED
Water                       91.3324      91.3324        22.8331         Fallback    REJECTED
```

Lead is selected because it has the lowest mass per area among the two eligible designs. Tungsten is thinner, but its higher density produces a greater mass per area. Other materials remain visible with explicit engineering rejection reasons.

The result also demonstrates why feasibility and objective value are separate. Water has the lowest simplified relative-cost value, but it is not eligible because it exceeds the 20 cm design-thickness constraint.

## Current Limitations

- The V1.09 optimizer evaluates homogeneous single-material designs generated by the V1.08 comparison workflow.
- Multilayer narrow-beam attenuation is supported, but multilayer optimization is not yet implemented.
- Mass is compared using mass per unit area rather than total shield mass because a complete three-dimensional geometry is not yet defined.
- Relative-cost indices are simplified, user-editable comparative assumptions. They are not dollars, market prices, supplier quotes, or procurement estimates.
- The relative-cost model does not include machining, fabrication, structural support, installation, shipping, toxicity controls, or regulatory costs.
- Balanced min-max scores depend on the eligible candidate set and the user-selected weights.
- Hard constraints are currently limited to maximum thickness, maximum mass per area, and maximum relative-cost index per area.
- Density, attenuation data, source intensity, calculated thickness, and relative-cost values are treated as deterministic inputs without uncertainty propagation.
- G-P buildup correction supports only single-layer homogeneous shielding and is limited to 40 mean free paths.
- Barite concrete and polyethylene do not currently have implemented G-P coefficient tables.
- A single optimization table may include both valid buildup-aware designs and documented narrow-beam fallback designs.
- The implemented G-P tables are exposure buildup coefficients. The current code does not yet distinguish photon-number flux, exposure response, air kerma, and dose response for final OpenMC comparison.
- The source is modeled as isotropic and point-like, with shielding thickness along a one-dimensional source-to-detector path.
- The isotope library uses selected major photon lines rather than complete emitted decay spectra.
- Source self-attenuation, encapsulation, air attenuation, and detector-response effects are not modeled.
- Dose rate, exposure rate, air kerma, and effective dose are not yet calculated.
- OpenMC benchmarking has not yet been implemented.
- The simulator currently uses a command-line interface.

## Technical Documentation

Detailed validation reports are available in the `docs` folder:

- **Validation Report V1.01:** Legacy Java attenuation, XCOM interpolation, inverse-square flux, and robustness checks.
- **Validation Report V1.02:** Python rewrite, narrow-beam attenuation, interpolation, multilayer transmission, and regression validation.
- **Validation Report V1.04:** Initial lead G-P coefficient interpolation and buildup-factor implementation.
- **Validation Report V1.05:** Expanded single-layer G-P support for seven materials.
- **Validation Report V1.06:** Isotope source modeling, activity conversion, line-by-line source summation, and buildup warnings.
- **Validation Report V1.07:** Target classes, analytical and bisection minimum-thickness calculations, buildup-aware design, and fallback behavior.
- **Validation Report V1.08:** Single-material comparison, candidate pass/fail preservation, sorting, and warning preservation.
- **Validation Report V1.09:** Constraint-based material selection, engineering metrics, hard-constraint filtering, objective ranking, balanced normalization, infeasibility handling, and regression preservation.

**[Validation Reports](https://github.com/CormacThomas/shielding-attenuation/tree/main/docs)**

## Development Roadmap

- **V1.10 — Optimization plots and Pareto tradeoffs:** Visualize required thickness, mass per area, relative cost, flux-versus-thickness behavior, and design tradeoffs.
- **V1.11 — Scenario and geometry specification:** Create reproducible scenario files shared by deterministic and future OpenMC backends.
- **V1.12 — Radiation-response quantity foundation:** Clearly separate uncollided photon flux, exposure-related response, energy fluence, and air-kerma estimates.
- **V1.13 — OpenMC photon benchmark foundation:** Build a reproducible fixed-source photon-transport benchmark for one spherical single-material case.
- **V1.14 — Single-layer OpenMC validation matrix:** Compare deterministic and Monte Carlo results across selected sources, materials, and optical thicknesses.
- **V1.15 — Two-layer narrow-beam optimization:** Generate and rank two-material shielding stacks under engineering constraints.
- **V1.16 — Multilayer transport and buildup study:** Use OpenMC to evaluate layer-order and scattering effects and investigate carefully bounded deterministic approximations.
- **V1.17 — Final engineering design challenge:** Design and evaluate a conceptual shielded Cs-137 source container, benchmark finalist designs with OpenMC, and produce a documented engineering recommendation.
- **V1.18 — GUI and portfolio package:** Add a graphical workflow, final case-study presentation, architecture figures, and recruiter-facing documentation.

## Background

Radiation shielding is essential in reactor design, radiography, nuclear safety, radiation protection, and national-security applications. This project began as a simple attenuation calculator and is evolving into a validated workflow for analyzing photon shielding, comparing candidate materials, applying engineering constraints, and eventually benchmarking deterministic designs against Monte Carlo transport.


## Author

Developed by Cormac Thomas, Nuclear Engineering, University of New Mexico.

Focus areas include radiation effects, electronics hardening, and national security technology.

## References

[1] Y. Harima, Y. Sakamoto, S. Tanaka, and M. Kawai, “Validity of the Geometric-Progression Formula in Approximating Gamma-Ray Buildup Factors,” Nuclear Science and Engineering, vol. 94, no. 1, pp. 24–35, Sep. 1986. doi:10.13182/nse86-a17113

[2] D. K. Trubey, “New gamma-ray buildup factor data for point kernel calculations: ANS-6.4.3 standard reference data,” IAEA, https://inis.iaea.org/records/0arzw-ez976/files/20014493.pdf (accessed Jul. 10, 2026).

[3] Angstrom Sciences, “Density of elements chart – Angstrom Sciences elements density table,” Angstrom Sciences, https://angstromsciences.com/density-elements-chart (accessed Mar. 26, 2026).

[4] J. Colledge, M. Wilczek, and C. Raymond, “Inverse square law | radiology reference article,” Radiopaedia, https://radiopaedia.org/articles/inverse-square-law?lang=us (accessed Mar. 26, 2026).

[5] “Shielding Radiation Alphas, Betas, Gammas and Neutrons,” U.S. NRC, https://www.nrc.gov/docs/ML1122/ML11229A721.pdf (accessed Mar. 26, 2026).

[6] M. J. Berger et al., “XCOM: Photon Cross Sections Database,” NIST, https://dx.doi.org/10.18434/T48G6X (accessed Mar. 26, 2026).

[7] National Nuclear Data Center, “NuDat 3 Glossary,” Brookhaven National Laboratory, https://www.nndc.bnl.gov/nudat3/guide/glossary.html (accessed Jul. 11, 2026).

[8] International Atomic Energy Agency, “LiveChart of the Nuclides,” IAEA Nuclear Data Section, https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html (accessed Jul. 11, 2026).