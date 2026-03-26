# Shielding Attenuation Simulator (v1.01)

A Java-based radiation transport tool designed to model photon attenuation through multi-layer shielding geometries. This simulator uses the Beer-Lambert Law for material interactions and the Inverse-Square Law for geometric spreading.

## Overview

This project provides a framework for calculating uncollided photon flux from a point source. It is designed for nuclear engineering students and researchers to evaluate shielding effectiveness across various materials using NIST data.

Physics Models
- Attenuation: Calculated using the Beer-Lambert Law
- Geometric Spreading: Flux at a distance modeled via Inverse-Square Law.
- Data Interpolation: Since pohotn cross-sections are non-linear, the simulator uses log-log interpolation for NIST XCOM mass attenuation coefficients to keep accuracy between tabulated energy points.

## Features
- Multi-Layer Support: Calculates transmission through an unlimited stack of diferrent materials.
- NIST-Integrated Library: Includes attenuation data for common materials like Lead, Tungsten, Barite Concrete, and Polyethylene.
- Error Handling: Validates energy bounds (0.0001-10.0 MeV) and handles duplicate NIST data entries or physical inconsistencies.

## Technical Documentation

Detailed physics models and validation benchmarks can be found in the following document:

**[VALIDATION REPORT: PHOTON ATTENUATION SIMULATOR (V1.01)](./docs/VALIDATION_REPORT_PHOTON_ATTENUATION_SIMULATOR_(V1.01).pdf)**

## Planned Features
- Implement G-P fitting parameters (ORNL standard) to account for collided flux
- Add depleted uranium shielding with self-radiation correction
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

Developed by Cormac Thomas, Nuclear Engineering, Univeristy of New Mexico.
Focus areas include radiation transport, reactor systems, and defense applications.

## References
NIST XCOM Photon Cross Section Database
https://physics.nist.gov/cgi-bin/Xcom/xcom2?Method=Elem&Output2=Hand
