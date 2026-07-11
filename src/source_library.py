from source_models import IsotopeSource, PhotonLine


# Energy values are stored in MeV.
# Intensities are stored as photons emitted per decay.
# Source definitions use selected major photon lines, not complete decay spectra.


def create_cs137_source(activity_bq: float) -> IsotopeSource:
    # Cs-137 selected major photon line for external shielding estimates.
    return IsotopeSource(
        "Cs-137",
        activity_bq,
        [
            PhotonLine(0.661657, 0.851),
        ],
    )


def create_co60_source(activity_bq: float) -> IsotopeSource:
    # Co-60 emits two major gamma lines per decay.
    return IsotopeSource(
        "Co-60",
        activity_bq,
        [
            PhotonLine(1.173228, 0.9985),
            PhotonLine(1.332492, 0.9998),
        ],
    )


def create_am241_source(activity_bq: float) -> IsotopeSource:
    # Am-241 selected low-energy photon line.
    # The 59.541 keV line is useful for low-energy shielding and calibration examples.
    # Lower-energy X-rays are not included in the default V1.06 source library.
    return IsotopeSource(
        "Am-241",
        activity_bq,
        [
            PhotonLine(0.059541, 0.359),
        ],
    )


def create_ba133_source(activity_bq: float) -> IsotopeSource:
    # Ba-133 selected major photon lines.
    # Very low-energy X-ray clusters are not included in the default V1.06 source library.
    return IsotopeSource(
        "Ba-133",
        activity_bq,
        [
            PhotonLine(0.0809979, 0.329),
            PhotonLine(0.1606120, 0.00638),
            PhotonLine(0.2232368, 0.00453),
            PhotonLine(0.2763989, 0.0716),
            PhotonLine(0.3028508, 0.1834),
            PhotonLine(0.3560129, 0.6205),
            PhotonLine(0.3838485, 0.0894),
        ],
    )


def create_na22_source(activity_bq: float) -> IsotopeSource:
    # Na-22 selected photon lines.
    # Includes annihilation photons at 511 keV and the 1274.537 keV gamma line.
    return IsotopeSource(
        "Na-22",
        activity_bq,
        [
            PhotonLine(0.5110, 1.7991),
            PhotonLine(1.274537, 0.99940),
        ],
    )


def create_mn54_source(activity_bq: float) -> IsotopeSource:
    # Mn-54 selected major photon line.
    return IsotopeSource(
        "Mn-54",
        activity_bq,
        [
            PhotonLine(0.834848, 0.999760),
        ],
    )


def create_co57_source(activity_bq: float) -> IsotopeSource:
    # Co-57 selected low-energy photon lines.
    return IsotopeSource(
        "Co-57",
        activity_bq,
        [
            PhotonLine(0.12206065, 0.8560),
            PhotonLine(0.13647356, 0.1068),
        ],
    )


def create_zn65_source(activity_bq: float) -> IsotopeSource:
    # Zn-65 selected photon lines.
    # Includes a small annihilation photon component and the main gamma line.
    return IsotopeSource(
        "Zn-65",
        activity_bq,
        [
            PhotonLine(0.511, 0.0290),
            PhotonLine(1.115539, 0.5012),
        ],
    )


def create_eu152_source(activity_bq: float) -> IsotopeSource:
    # Eu-152 selected major photon lines.
    # Very low-energy X-ray clusters are not included in the default V1.06 source library.
    return IsotopeSource(
        "Eu-152",
        activity_bq,
        [
            PhotonLine(0.1217817, 0.2853),
            PhotonLine(0.2446974, 0.0755),
            PhotonLine(0.4439606, 0.02827),
            PhotonLine(0.867380, 0.0423),
            PhotonLine(0.964057, 0.1451),
            PhotonLine(1.085837, 0.1011),
            PhotonLine(1.112076, 0.1367),
            PhotonLine(1.212948, 0.01415),
            PhotonLine(1.408013, 0.2087),

        ],
    )


def create_ir192_source(activity_bq: float) -> IsotopeSource:
    # Ir-192 selected major photon lines.
    return IsotopeSource(
        "Ir-192",
        activity_bq,
        [
            PhotonLine(0.65122, 0.0262),
            PhotonLine(0.66831, 0.0444),
            PhotonLine(0.75749, 0.01021),
            PhotonLine(0.29595650, 0.2871),
            PhotonLine(0.30845507, 0.2970),
            PhotonLine(0.31650618, 0.8286),
            PhotonLine(0.46806885, 0.4784),
            PhotonLine(0.5885810, 0.04522),
            PhotonLine(0.60441105, 0.08216),
            PhotonLine(0.61246215, 0.0534),
        ],
    )

def get_available_isotopes() -> list[str]:
    return [
        "cs137",
        "co60",
        "am241",
        "ba133",
        "na22",
        "mn54",
        "co57",
        "zn65",
        "eu152",
        "ir192",
    ]


def create_isotope_source(isotope_key: str, activity_bq: float) -> IsotopeSource:
    key = isotope_key.lower().strip()

    if key == "cs137" or key == "cs-137":
        return create_cs137_source(activity_bq)

    if key == "co60" or key == "co-60":
        return create_co60_source(activity_bq)

    if key == "am241" or key == "am-241":
        return create_am241_source(activity_bq)

    if key == "ba133" or key == "ba-133":
        return create_ba133_source(activity_bq)
    
    if key == "na22" or key == "na-22":
        return create_na22_source(activity_bq)
    
    if key == "mn54" or key == "mn-54":
        return create_mn54_source(activity_bq)
    
    if key == "co57" or key == "co-57":
        return create_co57_source(activity_bq)

    if key == "zn65" or key == "zn-65":
        return create_zn65_source(activity_bq)
    
    if key == "eu152" or key == "eu-152":
        return create_eu152_source(activity_bq)    

    if key == "ir192" or key == "ir-192":
        return create_ir192_source(activity_bq)    
    
    raise ValueError(
        f"Unsupported isotope source: {isotope_key}"
    )