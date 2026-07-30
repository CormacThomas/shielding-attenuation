# Uncollided photon source calculation utilities.
#
# This module converts manual and isotope source definitions
# into line-by-line narrow-beam attenuation calculations.
#
# It calculates:
#   - photon emission rate for each line
#   - line-level shielding results
#   - source-level uncollided photon fluence rate
#
# G-P exposure buildup is not applied to photon-number
# fluence. Buildup-adjusted collision air-kerma calculations
# are handled by air_response.py.


from calculator import calculate_shielding_result
from models import Layer
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
    PhotonLine,
    SourceCalculationResult,
    SourceLineResult,
)


def calculate_manual_source_result(
    source: ManualPhotonSource,
    layers: list[Layer],
    detector_distance: float,
) -> SourceCalculationResult:
    # Calculate one monoenergetic manual source.

    photon_line = PhotonLine(
        energy=source.energy,
        intensity=1.0,
    )

    shielding_result = calculate_shielding_result(
        layers=layers,
        photon_energy=source.energy,
        source_strength=source.photon_rate,
        detector_distance=detector_distance,
    )

    line_result = SourceLineResult(
        photon_line=photon_line,
        photon_rate=source.photon_rate,
        shielding_result=shielding_result,
    )

    return SourceCalculationResult(
        source_name="Manual Photon Source",
        activity_bq=None,
        line_results=[
            line_result,
        ],
        total_uncollided_flux=(
            shielding_result.uncollided_flux
        ),
    )


def calculate_isotope_source_result(
    source: IsotopeSource,
    layers: list[Layer],
    detector_distance: float,
) -> SourceCalculationResult:
    # Calculate one shielding result per isotope photon line
    # and sum their uncollided fluence-rate contributions.

    line_results: list[SourceLineResult] = []
    total_uncollided_flux = 0.0

    for photon_line in source.photon_lines:
        photon_rate = (
            source.activity_bq
            * photon_line.intensity
        )

        shielding_result = calculate_shielding_result(
            layers=layers,
            photon_energy=photon_line.energy,
            source_strength=photon_rate,
            detector_distance=detector_distance,
        )

        line_result = SourceLineResult(
            photon_line=photon_line,
            photon_rate=photon_rate,
            shielding_result=shielding_result,
        )

        line_results.append(
            line_result
        )

        total_uncollided_flux += (
            shielding_result.uncollided_flux
        )

    return SourceCalculationResult(
        source_name=source.name,
        activity_bq=source.activity_bq,
        line_results=line_results,
        total_uncollided_flux=total_uncollided_flux,
    )