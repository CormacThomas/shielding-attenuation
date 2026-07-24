# V1.12 dry-air mass energy-absorption coefficient library.
#
# The values in this module are used to convert photon energy fluence into
# collision air-kerma rate.
#
# Data source:
#   NIST X-Ray Mass Attenuation Coefficients
#   Air, Dry (Near Sea Level)
#
# Stored columns:
#   photon energy: MeV
#   dry-air mu_en/rho: cm^2/g
#
# Important:
# NIST lists the argon K absorption edge twice at 0.00320290 MeV:
#   - the first entry is immediately below the edge
#   - the second entry is immediately above the edge
#
# Both values are preserved in their published order. Later interpolation
# code must avoid interpolating across a zero-width duplicate-energy interval.


from air_response_models import AirKermaCoefficient


NIST_DRY_AIR_COEFFICIENT_SOURCE = (
    "NIST X-Ray Mass Attenuation Coefficients: "
    "Air, Dry (Near Sea Level)"
)


def get_dry_air_mu_en_over_rho_library() -> list[AirKermaCoefficient]:
    # Return the NIST dry-air mass energy-absorption coefficient table.
    #
    # A new list is returned on every call so callers cannot accidentally
    # modify a shared global coefficient table.

    source = NIST_DRY_AIR_COEFFICIENT_SOURCE

    return [
        AirKermaCoefficient(
            photon_energy_mev=0.00100000,
            mu_en_over_rho_cm2_per_g=3.599e3,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00150000,
            mu_en_over_rho_cm2_per_g=1.188e3,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00200000,
            mu_en_over_rho_cm2_per_g=5.262e2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00300000,
            mu_en_over_rho_cm2_per_g=1.614e2,
            source=source,
        ),

        # Argon K edge: value immediately below the edge.
        AirKermaCoefficient(
            photon_energy_mev=0.00320290,
            mu_en_over_rho_cm2_per_g=1.330e2,
            source=source,
        ),

        # Argon K edge: value immediately above the edge.
        AirKermaCoefficient(
            photon_energy_mev=0.00320290,
            mu_en_over_rho_cm2_per_g=1.460e2,
            source=source,
        ),

        AirKermaCoefficient(
            photon_energy_mev=0.00400000,
            mu_en_over_rho_cm2_per_g=7.636e1,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00500000,
            mu_en_over_rho_cm2_per_g=3.931e1,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00600000,
            mu_en_over_rho_cm2_per_g=2.270e1,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.00800000,
            mu_en_over_rho_cm2_per_g=9.446,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.01000000,
            mu_en_over_rho_cm2_per_g=4.742,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.01500000,
            mu_en_over_rho_cm2_per_g=1.334,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.02000000,
            mu_en_over_rho_cm2_per_g=5.389e-1,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.03000000,
            mu_en_over_rho_cm2_per_g=1.537e-1,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.04000000,
            mu_en_over_rho_cm2_per_g=6.833e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.05000000,
            mu_en_over_rho_cm2_per_g=4.098e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.06000000,
            mu_en_over_rho_cm2_per_g=3.041e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.08000000,
            mu_en_over_rho_cm2_per_g=2.407e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.10000000,
            mu_en_over_rho_cm2_per_g=2.325e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.15000000,
            mu_en_over_rho_cm2_per_g=2.496e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.20000000,
            mu_en_over_rho_cm2_per_g=2.672e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.30000000,
            mu_en_over_rho_cm2_per_g=2.872e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.40000000,
            mu_en_over_rho_cm2_per_g=2.949e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.50000000,
            mu_en_over_rho_cm2_per_g=2.966e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.60000000,
            mu_en_over_rho_cm2_per_g=2.953e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=0.80000000,
            mu_en_over_rho_cm2_per_g=2.882e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=1.00000000,
            mu_en_over_rho_cm2_per_g=2.789e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=1.25000000,
            mu_en_over_rho_cm2_per_g=2.666e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=1.50000000,
            mu_en_over_rho_cm2_per_g=2.547e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=2.00000000,
            mu_en_over_rho_cm2_per_g=2.345e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=3.00000000,
            mu_en_over_rho_cm2_per_g=2.057e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=4.00000000,
            mu_en_over_rho_cm2_per_g=1.870e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=5.00000000,
            mu_en_over_rho_cm2_per_g=1.740e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=6.00000000,
            mu_en_over_rho_cm2_per_g=1.647e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=8.00000000,
            mu_en_over_rho_cm2_per_g=1.525e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=10.00000000,
            mu_en_over_rho_cm2_per_g=1.450e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=15.00000000,
            mu_en_over_rho_cm2_per_g=1.353e-2,
            source=source,
        ),
        AirKermaCoefficient(
            photon_energy_mev=20.00000000,
            mu_en_over_rho_cm2_per_g=1.311e-2,
            source=source,
        ),
    ]