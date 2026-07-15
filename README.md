# Shielding Attenuation Simulator (v1.07)

A Python-based photon shielding calculator and design tool for modeling attenuation through shielding materials using NIST XCOM data, Beer-Lambert attenuation, inverse-square geometric spreading, isotope source photon emission data, optional Geometric Progression (G-P) buildup correction, and target-driven minimum shielding thickness calculations.

## Overview

This project provides a framework for calculating photon transmission and detector flux from an isotropic point source. The simulator supports multi-layer narrow-beam attenuation calculations, single-layer G-P buildup correction for selected homogeneous shielding materials, manual monoenergetic photon sources, isotope source calculations using selected major photon emission lines, and minimum shielding thickness calculations for user-defined design targets.

The project is intended as a nuclear engineering portfolio project focused on radiation shielding, attenuation modeling, interpolation, source modeling, validation, shielding design, and future shielding optimization.

## Physics Models

- **Beer-Lambert attenuation:** Calculates narrow-beam transmission through shielding layers.
- **Inverse-square geometric spreading:** Calculates uncollided photon flux at a detector distance from a point source.
- **NIST XCOM interpolation:** Uses log-log interpolation for mass attenuation coefficients between tabulated photon energy values.
- **G-P buildup correction:** Applies Geometric Progression gamma-ray exposure buildup factors for supported single-layer homogeneous shielding cases.
- **Mean free path calculation:** Reports optical thickness in mean free paths for individual layers and total shielding thickness.
- **Isotope source calculation:** Converts source activity to photon emission rate using selected photon line intensities.
- **Line-by-line source summation:** Calculates each isotope photon line independently and sums detector flux at the source level.
- **Target-driven shielding design:** Converts transmission, reduction-factor, and flux targets into detector flux requirements.
- **Minimum thickness calculation:** Calculates required single-material shielding thickness using analytical narrow-beam solutions for manual monoenergetic sources and bisection for isotope sources.

## Features

- **Multi-layer narrow-beam support:** Calculates transmission through a stack of shielding layers.
- **Material library:** Includes attenuation data for lead, aluminum, ordinary concrete, barite concrete, water, tungsten, copper, tin, and polyethylene.
- **NIST XCOM-based data:** Uses tabulated mass attenuation coefficients with interpolation between energy points.
- **Expanded single-layer G-P buildup:** Supports optional buildup-corrected flux estimates for lead, aluminum, ordinary concrete, water, tungsten, copper, and tin.
- **Material key lookup:** Uses stable internal material keys while preserving readable material display names.
- **Manual photon source mode:** Allows users to enter photon energy and photon emission rate directly.
- **Isotope source library:** Includes selected major photon lines for Cs-137, Co-60, Am-241, Ba-133, Na-22, Mn-54, Co-57, Zn-65, Eu-152, and Ir-192.
- **Activity unit conversion:** Supports Bq, kBq, MBq, GBq, Ci, mCi, and uCi.
- **Photon emission rate calculation:** Converts isotope activity and photon emission intensity into photons/s for each line.
- **Multi-line source handling:** Performs one shielding calculation per photon line and sums total uncollided flux.
- **Target classes:** Supports transmission targets, reduction-factor targets, and detector flux targets.
- **Minimum shielding thickness mode:** Calculates required shielding thickness for a selected material and design target.
- **Analytical manual-source design:** Uses the closed-form narrow-beam attenuation solution for monoenergetic manual photon sources.
- **Isotope-source design by bisection:** Uses numerical bisection to solve minimum-thickness problems for multi-line isotope sources.
- **Buildup-aware minimum-thickness design:** Attempts to solve target-driven design problems using buildup-corrected flux when the G-P model is valid.
- **Buildup fallback behavior:** Falls back to narrow-beam minimum-thickness design with a warning when buildup is unsupported or unavailable within the valid G-P range.
- **Buildup warning behavior:** Reports warnings when buildup is requested outside the valid G-P mean-free-path range while preserving narrow-beam results.
- **Input validation:** Checks for invalid energies, negative thicknesses, invalid source strength, invalid activity, invalid detector distance, data list mismatches, unsupported buildup cases, impossible design targets, and physically invalid shield geometry.
- **Command-line interface:** Allows users to select calculation mode, source mode, isotope source, activity, shielding materials, thicknesses or design targets, detector distance, and buildup mode.
- **Validation runner:** Includes repeatable validation tests for supported buildup materials, source-library behavior, source flux summation, activity conversion, minimum-thickness design, buildup-aware design, fallback behavior, and important edge cases.

## Current Limitations

- Minimum-thickness design currently evaluates one shielding material at a time.
- Minimum-thickness design does not yet perform material optimization, cost optimization, or mass optimization.
- G-P buildup correction currently supports single-layer homogeneous shielding only.
- Buildup-aware minimum-thickness design is limited to single-layer homogeneous shielding.
- Multilayer buildup correction is not implemented.
- Multilayer shielding optimization is not implemented.
- Barite concrete and polyethylene are available for narrow-beam attenuation but do not currently support G-P buildup correction.
- Buildup correction is only applied through 40 mean free paths. If a photon line exceeds this range, narrow-beam flux is reported but buildup is skipped or design mode falls back to narrow-beam calculation with a warning.
- The source is modeled as an isotropic point source.
- The isotope library uses selected major photon lines, not complete emitted decay spectra.
- Photon intensities are treated as emitted photons per decay before source self-attenuation, encapsulation, air attenuation, or detector-window effects.
- Dose-rate conversion, exposure-rate conversion, air kerma, and effective dose are not yet implemented.
- G-P coefficients are currently implemented for exposure buildup factors only.
- The simulator currently uses a command-line interface.

## Technical Documentation

Detailed physics models and validation benchmarks can be found in the following folder:

- **Validation Report V1.01:** Validation of legacy Java simulator, Beer-Lambert attenuation, NIST XCOM interpolation, inverse-square flux calculation, and robustness checks.
- **Validation Report V1.02:** Validates the Python rewrite, Beer-Lambert attenuation, NIST XCOM interpolation, inverse-square flux calculation, and robustness checks.
- **Validation Report V1.04:** Validates G-P buildup coefficient interpolation, buildup factor calculation, buildup-corrected flux, and unsupported-case handling for single-layer lead buildup.
- **Validation Report V1.05:** Validates expanded single-layer G-P buildup support for lead, aluminum, ordinary concrete, water, tungsten, copper, and tin.
- **Validation Report V1.06:** Validates isotope source modeling, activity conversion, photon emission rate calculation, line-by-line source summation, manual source regression, and buildup warning behavior outside the valid G-P MFP range.
- **Validation Report V1.07:** Validates target classes, minimum shielding thickness calculations, analytical manual-source design, isotope-source bisection, buildup-aware design, fallback-to-narrow-beam behavior, and manual source regression preservation.

**[Validation Reports](https://github.com/CormacThomas/shielding-attenuation/tree/main/docs)**

## Planned Features

- Add single-material design optimization comparing required thickness across materials.
- Add constraint-based material selection using target flux, maximum thickness, mass, and cost constraints.
- Add material cost and mass-per-area estimates.
- Add plotting for attenuation curves, flux versus thickness, required thickness by material, and optimization tradeoffs.
- Add scenario runner / batch study support for repeatable shielding design cases.
- Add example case studies for common sources and materials.
- Add improved user input handling with repeated prompts instead of immediate program termination.
- Create a graphical front end for visualization.
- Add dose-rate calculation using appropriate photon flux-to-dose conversion coefficients.
- Add uncertainty estimation.
- Let users define custom material compositions.
- Expand isotope source library options and possibly add detailed spectrum modes.
- Add two-layer narrow-beam optimization.
- Explore OpenMC integration for Monte Carlo comparison and validation.
- Investigate more rigorous multilayer buildup treatment.

## Background

Radiation shielding is essential in reactor design, radiography, nuclear safety, and radiation protection. This project started as a simple calculator, but is expanding into a more general tool for analyzing how photons behave when interacting with shielding layers and estimating how much shielding is required to satisfy design targets.

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