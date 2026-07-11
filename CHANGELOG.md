# Changelog

All major development milestones for the Shielding Attenuation Simulator are documented here.

## v1.06 - Isotope Source Library and Source-Level Flux Calculation

Added isotope source modeling, activity unit conversion, line-by-line photon source calculations, and warning behavior for buildup requests outside the valid G-P mean-free-path range.

Changes:
- Added source model dataclasses:
  - `PhotonLine`
  - `IsotopeSource`
  - `ManualPhotonSource`
  - `SourceLineResult`
  - `SourceCalculationResult`
- Added isotope photon source library with selected major photon lines for:
  - Cs-137
  - Co-60
  - Am-241
  - Ba-133
  - Na-22
  - Mn-54
  - Co-57
  - Zn-65
  - Eu-152
  - Ir-192
- Added activity unit conversion to Bq for:
  - Bq
  - kBq
  - MBq
  - GBq
  - Ci
  - mCi
  - uCi
- Added isotope source mode to the command-line interface.
- Preserved manual monoenergetic photon source mode from previous versions.
- Added line-by-line source calculation for multi-line isotope sources.
- Added source-level summation of uncollided detector flux.
- Added source-level summation of buildup-corrected flux when buildup is valid for all photon lines.
- Added warning behavior when G-P buildup is requested outside the supported 40 MFP range.
- Updated output formatting to show source name, activity, photon line results, total flux, buildup results, and warnings.
- Added validation checks for source-library structure, activity conversion, photon emission rates, source flux summation, and invalid buildup range handling.
- Added V1.06 validation report for isotope source modeling and source-level calculation behavior.

Validated behavior:
- Activity conversion for Ci, mCi, and uCi.
- Creation of all 10 isotope sources.
- Correct photon line counts for each isotope source.
- Positive photon energy and intensity values for all source-library entries.
- Photon emission rate calculation using activity multiplied by emission intensity.
- Total uncollided source flux equals the sum of line-by-line uncollided flux values.
- Co-60 buildup-corrected source flux equals the sum of valid line-by-line buildup-corrected flux values.
- Manual source mode reproduces the V1.05 single-energy lead shielding regression case.
- Am-241 through 5 cm of lead correctly reports narrow-beam flux while skipping buildup above the valid G-P MFP range.
- Unsupported activity units are rejected.
- Unsupported isotope source names are rejected.
- Negative activity values are rejected.

Notes:
- The isotope library uses selected major photon lines, not complete decay spectra.
- Photon intensities are treated as emitted photons per decay before source self-attenuation, encapsulation, air attenuation, or detector-window effects.
- G-P buildup correction remains limited to single-layer homogeneous shielding.
- Buildup correction is only applied through 40 mean free paths. Above this range, narrow-beam flux is still reported but buildup is skipped with a warning.
- V1.06 reports photon flux, not dose rate, exposure rate, air kerma, or effective dose.

## v1.05 - Expanded Single-Layer G-P Buildup Material Support

Expanded Geometric Progression (G-P) gamma-ray buildup correction from lead-only support to multiple single-layer shielding materials.

Changes:
- Added G-P exposure buildup coefficient tables for:
  - Lead
  - Aluminum
  - Ordinary Concrete
  - Water
  - Tungsten
  - Copper
  - Tin
- Added a `key` field to the `Material` dataclass for stable internal material lookup.
- Updated buildup lookup to use `Material.key` instead of display names.
- Updated output text so buildup mode displays the selected material.
- Added validation runner checks for all supported buildup materials.
- Added validation checks confirming:
  - `B(0 MFP) = 1`
  - `B(1 MFP) = b`
  - `B(5 MFP) > 1`
- Added geometry validation preventing total shielding thickness from exceeding source-to-detector distance.
- Added V1.05 validation report for expanded buildup material support.

Validated behavior:
- Supported buildup material lookup.
- G-P buildup behavior for lead, aluminum, ordinary concrete, water, tungsten, copper, and tin.
- Material key lookup for display names such as `Concrete (Ordinary)`.
- Rejection of unsupported buildup materials.
- Rejection of multilayer buildup cases.
- Rejection of physically invalid source-to-detector geometry.

Notes:
- G-P buildup remains limited to single-layer homogeneous shielding.
- Barite concrete and polyethylene remain available for narrow-beam attenuation but do not currently support buildup correction.

## v1.04 - G-P Buildup Factor Support for Lead

Added the first implementation of Geometric Progression gamma-ray buildup correction.

Changes:
- Added `GPCoefficients` dataclass.
- Added G-P coefficient library structure.
- Added lead exposure buildup coefficients from ANS-6.4.3 reference data.
- Added exact and interpolated G-P coefficient lookup.
- Added G-P buildup factor calculation.
- Added buildup-corrected flux calculation.
- Added optional user prompt for G-P buildup correction.
- Restricted buildup mode to single-layer lead shielding.
- Added V1.04 validation report for G-P buildup behavior.

Validated behavior:
- Coefficient interpolation for lead.
- Buildup factor calculation at 0, 1, 5, and 10 mean free paths.
- Buildup-corrected flux calculation.
- Rejection of unsupported materials.
- Rejection of multilayer buildup cases.

## v1.03 - Python CLI and Code Organization Improvements

Intermediate development version after the Python rewrite.

Changes:
- Added user input for materials, layer thicknesses, photon energy, source strength, and detector distance.
- Added material selection from a dictionary-based material library.
- Added support for multiple shielding materials in the Python version.
- Improved file organization into separate modules:
  - `main.py`
  - `models.py`
  - `material_library.py`
  - `physics.py`
  - `calculator.py`
  - `input_handler.py`
  - `output.py`
- Improved command-line usability.

Notes:
- No major new physics model was added in this version.
- This version served as a cleanup and usability bridge between v1.02 and v1.04.

## v1.02 - Python Rewrite and Validation

Python rewrite of the original Java photon attenuation simulator.

Changes:
- Reimplemented the photon attenuation simulator in Python.
- Added dataclass-based `Material` and `Layer` models.
- Added NIST XCOM mass attenuation coefficient lookup.
- Added log-log interpolation for attenuation coefficients.
- Added narrow-beam Beer-Lambert attenuation through one or more layers.
- Added inverse-square point-source flux calculation.
- Added validation checks for:
  - Lead attenuation
  - Aluminum attenuation
  - Multilayer transmission
  - Exact table lookup
  - Duplicate-edge handling
  - Zero-thickness shielding
  - Invalid distance handling
  - HVL and TVL behavior

Documentation:
- Added V1.02 validation report.

## v1.01 - Original Java Version

Original Java implementation of the photon attenuation simulator.

Features:
- Modeled photon attenuation through shielding materials.
- Used NIST XCOM mass attenuation coefficient data.
- Converted mass attenuation coefficients to linear attenuation coefficients using material density.
- Calculated Beer-Lambert transmission.
- Included multilayer attenuation support.
- Included inverse-square geometric spreading.
- Included early material library and validation work.

Notes:
- This version established the original project concept and physics foundation.
- Later rewritten in Python to improve organization, readability, and future compatibility with scientific Python tools and possible OpenMC integration.