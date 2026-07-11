from source_models import IsotopeSource, PhotonLine


def create_cs137_source(activity_bq: float) -> IsotopeSource:
    # Cs-137 primary gamma emission through Ba-137m.
    # PhotonLine intensity is photons per decay.
    # 661.657 keV = 0.661657 MeV.
    return IsotopeSource(
        "Cs-137",
        activity_bq,
        [
            PhotonLine(0.661657, 0.851),
        ],
    )


def create_co60_source(activity_bq: float) -> IsotopeSource:
    # Co-60 emits two major gamma lines per decay.
    # 1173.228 keV = 1.173228 MeV.
    # 1332.492 keV = 1.332492 MeV.
    return IsotopeSource(
        "Co-60",
        activity_bq,
        [
            PhotonLine(1.173228, 0.9985),
            PhotonLine(1.332492, 0.9998),
        ],
    )


def create_am241_source(activity_bq: float) -> IsotopeSource:
    # Am-241 common low-energy gamma line.
    # 59.541 keV = 0.059541 MeV.
    return IsotopeSource(
        "Am-241",
        activity_bq,
        [
            PhotonLine(0.059541, 0.359),
        ],
    )


def get_available_isotopes() -> list[str]:
    return [
        "cs137",
        "co60",
        "am241",
    ]


def create_isotope_source(isotope_key: str, activity_bq: float) -> IsotopeSource:
    key = isotope_key.lower().strip()

    if key == "cs137" or key == "cs-137":
        return create_cs137_source(activity_bq)

    if key == "co60" or key == "co-60":
        return create_co60_source(activity_bq)

    if key == "am241" or key == "am-241":
        return create_am241_source(activity_bq)

    raise ValueError(
        f"Unsupported isotope source: {isotope_key}"
    )