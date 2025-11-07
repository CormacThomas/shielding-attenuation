# Shielding Attenuation Calculator

A Java based calculator for photon attenuation in shielding materials using log-log interpolation from NIST mass attenuation data.

## Current Features
- Calculations in linear attenuation coefficient (μ)
- Calculations in geometric attenuation
- Uses log-log interpolation for photon energies
- Computes photon tranmission using the Beer-Lambert law
- Computes geometric attenuation using the Inverse-Square Law
- Includes dataset for Lead, Ordinary Concrete, Barite Concrete, Aluminum, Water, Tungsten, Bismuth, Copper, Tin, Polyethylene, Graphite, and Leaded Glass
- User input for shielding thickness and distance between detector and source
- Displays percent transmitted and linear attenuation coefficient value

## Planned Features
- Material Selection Menu
  - Combined material calculations for layered shielding
- User isotope selection or direct energy input (MeV)
- Expanded data library for common isotopes and photon energies
- Output Calculations
  - Half-Value Layer and Tenth-Value Layer
  
## References
NIST XCOM Photon Cross Section Database
https://physics.nist.gov/cgi-bin/Xcom/xcom2?Method=Elem&Output2=Hand
