# Shielding Attenuation Calculator

A Java based calculator for photon attenuation in shielding materails using log-log interpolation from NIST mass attenuation data.

## Current Features
- Calculations in linear attenuation coefficient (μ)
- Uses log-log interpolation for photon energies
- Computes photon tranmission using the Beer-Lambert law
- Includes sample dataset for lead (Pb)

## Planned Features
- Material Selection Menu
  - Support for multiple materials (water, concrete, etc.)
  - Combined material calculations for layered shielding
- Energy and Thickness Input
  - User input interface for energy, material, and thickness values
- Expanded data library for common isotopes and photon energies
- Output Calculations
  - Percent transmitted
  - Half-Value Layer and Tenth-Value Layer
  
## References
NIST XCOM Photon Cross Section Database
https://physics.nist.gov/cgi-bin/Xcom/xcom2?Method=Elem&Output2=Hand
