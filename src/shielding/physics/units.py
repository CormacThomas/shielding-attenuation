# Exact and defined conversion constants used by V1.12 air-response
# calculations.

MEV_TO_JOULES = 1.602176634e-13

SQUARE_CENTIMETERS_PER_SQUARE_METER = 1.0e4

CM2_PER_G_TO_M2_PER_KG = 0.1

SECONDS_PER_HOUR = 3600.0

MICROGY_PER_GY = 1.0e6


def convert_activity_to_bq(activity_value: float, activity_unit: str) -> float:
    # Convert activity units to becquerels.
    # Internally, the simulator uses Bq because 1 Bq = 1 decay/s.

    if activity_value < 0:
        raise ValueError("Activity cannot be negative.")

    unit = activity_unit.lower().strip()

    if unit == "bq":
        return activity_value

    if unit == "kbq":
        return activity_value * 1.0e3

    if unit == "mbq":
        return activity_value * 1.0e6

    if unit == "gbq":
        return activity_value * 1.0e9

    if unit == "ci":
        return activity_value * 3.7e10

    if unit == "mci":
        return activity_value * 3.7e7

    if unit == "uci":
        return activity_value * 3.7e4

    raise ValueError(
        "Unsupported activity unit. Use bq, kbq, mbq, gbq, ci, mci, or uci."
    )


def convert_mev_to_joules(
    energy_mev: float,
) -> float:
    # Convert photon energy from MeV to joules.

    if energy_mev < 0:
        raise ValueError("Energy in MeV cannot be negative.")

    return energy_mev * MEV_TO_JOULES


def convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s(
    energy_fluence_mev_per_cm2_s: float,
) -> float:
    # Convert energy fluence rate:
    #
    # MeV / (cm² s)
    #       ↓
    # J / (m² s)
    #
    # A value expressed per square centimeter becomes 10,000 times
    # larger when expressed per square meter.

    if energy_fluence_mev_per_cm2_s < 0:
        raise ValueError("Energy fluence rate cannot be negative.")

    return (
        energy_fluence_mev_per_cm2_s
        * MEV_TO_JOULES
        * SQUARE_CENTIMETERS_PER_SQUARE_METER
    )


def convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg(
    coefficient_cm2_per_g: float,
) -> float:
    # Convert a mass energy-absorption coefficient:
    #
    # cm²/g
    #   ↓
    # m²/kg
    #
    # 1 cm²/g = 0.1 m²/kg

    if coefficient_cm2_per_g < 0:
        raise ValueError("Mass energy-absorption coefficient cannot be negative.")

    return coefficient_cm2_per_g * CM2_PER_G_TO_M2_PER_KG


def convert_gy_per_s_to_microgy_per_h(
    air_kerma_rate_gy_per_s: float,
) -> float:
    # Convert Gy/s to µGy/h for readable engineering output.

    if air_kerma_rate_gy_per_s < 0:
        raise ValueError("Air-kerma rate cannot be negative.")

    return air_kerma_rate_gy_per_s * MICROGY_PER_GY * SECONDS_PER_HOUR


def convert_microgy_per_h_to_gy_per_s(
    air_kerma_rate_microgy_per_h: float,
) -> float:
    # Convert a user-facing µGy/h value into the canonical internal
    # unit of Gy/s.

    if air_kerma_rate_microgy_per_h < 0:
        raise ValueError("Air-kerma rate cannot be negative.")

    return air_kerma_rate_microgy_per_h / MICROGY_PER_GY / SECONDS_PER_HOUR
