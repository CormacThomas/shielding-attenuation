# V1.13 Cs-137 / Lead Deterministic–OpenMC Benchmark

## Purpose

V1.13 establishes a matched deterministic and Monte Carlo photon-shielding
benchmark for one fixed physical scenario.

The release demonstrates that the same backend-independent scenario can drive:

- a deterministic uncollided collision-air-kerma calculation;
- a deterministic G-P buildup-adjusted collision-air-kerma calculation;
- an OpenMC photon-transport calculation;
- an energy-resolved photon spectrum;
- a direct OpenMC collision-air-kerma response tally;
- an independently spectrum-folded collision-air-kerma result;
- statistical-uncertainty and consistency checks.

V1.13 is a benchmark-foundation release rather than a broad material,
energy, or deep-penetration study.

## Benchmark configuration

### Source

- Isotope: Cs-137
- Activity: 3.70e10 Bq
- Modeled photon energy: 661657 eV
- Photon emission intensity: 0.851 photons per decay
- Physical photon source rate: 3.1487e10 photons/s
- Source position: center of the spherical geometry
- Angular distribution: isotropic

The physical photon source rate is

```text
3.70e10 decays/s × 0.851 photons/decay
= 3.1487e10 photons/s