# Shielding Attenuation Simulator (v1.04)

A Python-based photon shielding calculator designed to model attenuation through shielding materials using NIST XCOM data, Beer-Lambert attenuation, inverse-square geometric spreading, and optional Geometric Progression (G-P) buildup correction for single-layer lead shielding.

## Overview

This project provides a framework for calculating photon transmission and detector flux from an isotropic point source. The simulator supports multi-layer narrow-beam attenuation calculations and includes an initial implementation of G-P buildup correction for single-layer lead shielding.

The project is intended as a nuclear engineering portfolio project focused on radiation shielding, attenuation modeling, interpolation, validation, and future shielding optimization.

## Physics Models

- **Beer-Lambert attenuation:** Calculates narrow-beam transmission through shielding layers.
- **Inverse-square geometric spreading:** Calculates uncollided photon flux at a detector distance from a point source.
- **NIST XCOM interpolation:** Uses log-log interpolation for mass attenuation coefficients between tabulated photon energy values.
- **G-P buildup correction:** Applies Geometric Progression gamma-ray buildup factors for supported single-layer lead cases.
- **Mean free path calculation:** Reports optical thickness in mean free paths for individual layers and total shielding thickness.


## Features

- **Multi-layer narrow-beam support:** Calculates transmission through a stack of shielding layers.
- **Material library:** Includes attenuation data for lead, aluminum, ordinary concrete, barite concrete, water, tungsten, copper, tin, and polyethylene.
- **NIST XCOM-based data:** Uses tabulated mass attenuation coefficients with interpolation between energy points.
- **Single-layer lead G-P buildup:** Supports optional buildup-corrected flux estimates for homogeneous lead shielding.
- **Input validation:** Checks for invalid energies, negative thicknesses, invalid source strength, invalid detector distance, data list mismatches, and unsupported buildup cases.
- **Command-line interface:** Allows users to select materials, thicknesses, photon energy, source strength, detector distance, and buildup mode.


## Current Limitations

- G-P buildup correction currently supports single-layer lead shielding only.
- Multilayer buildup correction is not implemented.
- The source is modeled as an isotropic point source.
- The simulator currently models monoenergetic photon sources.
- Dose-rate conversion and isotope libraries are not yet implemented.
- G-P coefficients are currently implemented for exposure buildup factors only.


## Technical Documentation

Detailed physics models and validation benchmarks can be found in the following folder:

- **Validation Report V1.01:** Validation of legacy Java simulator, Beer-Lambert attenuation, NIST XCOM interpolation, inverse-square flux calculation, and robustness checks.
- **Validation Report V1.02:** Validates the Python rewrite, Beer-Lambert attenuation, NIST XCOM interpolation, inverse-square flux calculation, and robustness checks.
- **Validation Report V1.04:** Validates G-P buildup coefficient interpolation, buildup factor calculation, buildup-corrected flux, and unsupported-case handling for single-layer lead buildup.

**[VALIDATION REPORTS)](https://github.com/CormacThomas/shielding-attenuation/tree/main/docs)**


## Planned Features

- Implement G-P fitting parameters (ORNL standard) to account for collided flux
- Create a graphical front end for visualization
- Add dose rate calculation using source activity
- Implement improved / user friendly UI
- Add isotope library with common gamma emitters
- Add uncertainty estimation
- Let users define material composition
- Build a minimum shielding calculator for given intensity reduction targets

## Background

Radiation shielding is essential in reactor design, radiography, and nuclear safety. This project started as a simple calculator, but is expanding into a more general tool for analyzing how photons behave when interacting with shielding layers.

## Author

Developed by Cormac Thomas, Nuclear Engineering, University of New Mexico.
Focus areas include radiation effects, electronics hardening, and national security technology.

## References

[1] Y. Harima, Y. Sakamoto, S. Tanaka, and M. Kawai, “Validity of the Geometric-Progression Formula in Approximating Gamma-Ray Buildup Factors,” Nuclear Science and Engineering, vol. 94, no. 1, pp. 24–35, Sep. 1986. doi:10.13182/nse86-a17113

[2] D. K. Trubey, “New gamma-ray buildup factor data for point kernel calculations: ANS-6.4.3 standard reference data,” IAEA, https://inis.iaea.org/records/0arzw-ez976/files/20014493.pdf (accessed Jul. 10, 2026).

[3] Angstrom Sciences, “Density of elements chart – Angstrom Sciences elements density table,” Angstrom Sciences, https://angstromsciences.com/density-elements-chart (accessed Mar. 26, 2026).

[4] J. Colledge, M. Wilczek, and C. Raymond, “Inverse square law | radiology reference article,” Radiopaedia, https://radiopaedia.org/articles/inverse-square-law?lang=us (accessed Mar. 26, 2026).

[5] “Shielding Radiation Alphas, Betas, Gammas and Neutrons,” U.S.NRC, https://www.nrc.gov/docs/ML1122/ML11229A721.pdf (accessed Mar. 26, 2026).

[6] M. J. Berger et al., “XCOM: Photon Cross Sections Database,” NIST,https://dx.doi.org/10.18434/T48G6X (accessed Mar. 26, 2026).
