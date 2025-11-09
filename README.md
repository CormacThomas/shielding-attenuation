# Shielding Attenuation Simulator

A Java-based photon attenuation simulator that models radiation shielding using the Beer–Lambert Law and Inverse-Square Law.
Designed for educational and experimental use in radiation transport, multi-layer shielding, and nuclear materials applications.

## Overview

The simulator calculates the intensity of photons after passing through one or more layers of shielding material. It accounts for:
- Attenuation coefficients specific to each material
- Layer thickness in centimeters
- Initial photon intensity
- Distance-based geometric spreading
  
This project aims to evolve into a more advanced shielding analysis tool capable of determining minimum required shielding thickness for specific isotopes and energies.

## Current Features
- Single and multi-layer shielding attenuation
- Support for common materials (lead, concrete, steel, etc.)
- Mass attenuation calculated using log-log interpolation of NIST data and the Beer-Lamber Law
- Geometric attenuation calculated using the Inverse-Square law

## Planned Features
- Add depleted uranium shielding with self-radiation correction
- Create a graphical front end for visualization
- Add dose rate calculation using source activity
- Implement improved / user friendly UI
- Add isotope library with common gamma emitters
- Add uncertainty estimation
- Improve sampling using Monte Carlo techniques
- Let users define material composition
- Build a minimum shielding calculator for given intensity reduction targets

## Background
Radiation shielding is essential in reactor design, radiography, and nuclear safety. This project started as a simple calculator, but is expanding into a more general tool for analyzing how photons behave when interacting with shielding layers.

## Author
Developed by a nuclear engineering student at the University of New Mexico. Focus areas include radiation transport, reactor systems, and defense applications.

## References
NIST XCOM Photon Cross Section Database
https://physics.nist.gov/cgi-bin/Xcom/xcom2?Method=Elem&Output2=Hand
