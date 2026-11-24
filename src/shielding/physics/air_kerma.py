"""Calculate and aggregate collision air kerma from deterministic photon lines."""

from shielding.data.gp_coefficients import (
    get_gp_coefficients_library,
)
from shielding.physics.buildup import (
    calculate_gp_buildup_factor,
    get_gp_coefficients_at_energy,
)
from shielding.physics.kerma_coefficients import get_air_kerma_coefficient_at_energy
from shielding.physics.layers import (
    calculate_shielding_result,
)
from shielding.physics.models import (
    Layer,
    ShieldingResult,
)
from shielding.physics.response_models import (
    VALID_BUILDUP_STATUSES,
    BuildupStatus,
    PhotonLineAirKermaResult,
    SourceAirKermaResult,
)
from shielding.physics.source_models import (
    IsotopeSource,
    ManualPhotonSource,
    PhotonLine,
)
from shielding.physics.units import (
    convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s,
    convert_gy_per_s_to_microgy_per_h,
    convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg,
)

Source = ManualPhotonSource | IsotopeSource


def calculate_gp_exposure_buildup_factor_for_shielding_result(
    shielding_result: ShieldingResult,
) -> float:
    # Calculate a G-P exposure buildup factor for one completed
    # narrow-beam shielding result.
    #
    # Unlike the legacy calculate_buildup_for_result() function, this
    # helper does not write a "buildup-corrected flux" into
    # ShieldingResult. It returns only the dimensionless exposure
    # buildup factor.
    #
    # The caller applies the returned factor only to the compatible
    # collision-air-kerma response.

    if len(shielding_result.layers) != 1:
        raise ValueError(
            "G-P exposure buildup currently supports only "
            "one homogeneous shielding layer."
        )

    material = shielding_result.layers[0].material

    gp_library = get_gp_coefficients_library()

    if material.key not in gp_library:
        raise ValueError(f"G-P exposure buildup is not available for {material.name}.")

    coefficients = get_gp_coefficients_at_energy(
        material_name=material.key,
        energy=shielding_result.photon_energy,
        gp_library=gp_library,
    )

    try:
        return calculate_gp_buildup_factor(
            coefficients=coefficients,
            mfp=shielding_result.total_mfp,
        )

    except ValueError as error:
        raise ValueError(
            "Could not calculate G-P exposure buildup for "
            f"{shielding_result.photon_energy:.8g} MeV "
            f"through {material.name}. "
            f"Total optical thickness was "
            f"{shielding_result.total_mfp:.6g} MFP. "
            f"{error}"
        ) from error


def calculate_energy_fluence_rate_mev_per_cm2_s(
    photon_energy_mev: float,
    photon_fluence_rate_per_cm2_s: float,
) -> float:
    # Calculate photon energy fluence rate:
    #
    # photon energy
    #     ×
    # photon fluence rate
    #
    # MeV/photon × photons/(cm² s)
    #     =
    # MeV/(cm² s)

    if photon_energy_mev <= 0:
        raise ValueError("Photon energy must be greater than zero.")

    if photon_fluence_rate_per_cm2_s < 0:
        raise ValueError("Photon fluence rate cannot be negative.")

    return photon_energy_mev * photon_fluence_rate_per_cm2_s


def calculate_collision_air_kerma_rate_gy_per_s(
    energy_fluence_rate_mev_per_cm2_s: float,
    mu_en_over_rho_cm2_per_g: float,
) -> float:
    # Calculate collision air-kerma rate from photon energy fluence.
    #
    # Energy fluence rate:
    #   MeV/(cm² s)
    #
    # Dry-air mass energy-absorption coefficient:
    #   cm²/g
    #
    # Both values are converted to SI units before multiplication:
    #
    # J/(m² s) × m²/kg
    #     =
    # J/(kg s)
    #     =
    # Gy/s

    if energy_fluence_rate_mev_per_cm2_s < 0:
        raise ValueError("Energy fluence rate cannot be negative.")

    if mu_en_over_rho_cm2_per_g <= 0:
        raise ValueError(
            "Dry-air mass energy-absorption coefficient must be greater than zero."
        )

    energy_fluence_rate_j_per_m2_s = convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s(
        energy_fluence_rate_mev_per_cm2_s
    )

    coefficient_m2_per_kg = (
        convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg(
            mu_en_over_rho_cm2_per_g
        )
    )

    return energy_fluence_rate_j_per_m2_s * coefficient_m2_per_kg


def calculate_collision_air_kerma_rate_microgy_per_h(
    energy_fluence_rate_mev_per_cm2_s: float,
    mu_en_over_rho_cm2_per_g: float,
) -> float:
    # Convenience wrapper for engineering output in µGy/h.
    #
    # The canonical internal unit remains Gy/s.

    air_kerma_rate_gy_per_s = calculate_collision_air_kerma_rate_gy_per_s(
        energy_fluence_rate_mev_per_cm2_s,
        mu_en_over_rho_cm2_per_g,
    )

    return convert_gy_per_s_to_microgy_per_h(air_kerma_rate_gy_per_s)


def calculate_photon_line_air_kerma_result(
    photon_line: PhotonLine,
    photon_rate_per_s: float,
    uncollided_photon_fluence_rate_per_cm2_s: float,
    buildup_status: BuildupStatus = "not_requested",
    buildup_factor: float | None = None,
    warnings: list[str] | None = None,
) -> PhotonLineAirKermaResult:
    # Convert one transported photon line into an explicit collision
    # air-kerma response result.
    #
    # The caller supplies the uncollided photon fluence rate. This keeps
    # attenuation calculations separate from response-coefficient folding.
    #
    # When buildup is applied, the supplied factor must be a G-P exposure
    # buildup factor compatible with the collision-air-kerma response.

    if photon_rate_per_s < 0:
        raise ValueError("Photon emission rate cannot be negative.")

    if uncollided_photon_fluence_rate_per_cm2_s < 0:
        raise ValueError("Uncollided photon fluence rate cannot be negative.")

    if buildup_status not in VALID_BUILDUP_STATUSES:
        raise ValueError("Unsupported buildup status.")

    if buildup_status == "applied":
        if buildup_factor is None:
            raise ValueError("Applied buildup requires a buildup factor.")

        if buildup_factor < 1:
            raise ValueError("Buildup factor cannot be less than one.")

    elif buildup_factor is not None:
        raise ValueError(
            "A buildup factor may only be supplied when buildup status is applied."
        )

    coefficient = get_air_kerma_coefficient_at_energy(photon_line.energy)

    energy_fluence_rate = calculate_energy_fluence_rate_mev_per_cm2_s(
        photon_energy_mev=photon_line.energy,
        photon_fluence_rate_per_cm2_s=(uncollided_photon_fluence_rate_per_cm2_s),
    )

    uncollided_air_kerma_rate = calculate_collision_air_kerma_rate_gy_per_s(
        energy_fluence_rate_mev_per_cm2_s=(energy_fluence_rate),
        mu_en_over_rho_cm2_per_g=(coefficient.mu_en_over_rho_cm2_per_g),
    )

    buildup_adjusted_air_kerma_rate = None

    if buildup_status == "applied":
        if buildup_factor is None:
            # This condition is already rejected above. The additional
            # check makes the type narrowing explicit.
            raise ValueError("Applied buildup requires a buildup factor.")

        buildup_adjusted_air_kerma_rate = uncollided_air_kerma_rate * buildup_factor

        calculation_method = (
            "Deterministic point-source attenuation with "
            "dry-air response-coefficient folding and "
            "G-P exposure buildup"
        )

    else:
        calculation_method = (
            "Deterministic uncollided point-source attenuation "
            "with dry-air response-coefficient folding"
        )

    line_warnings = [] if warnings is None else list(warnings)

    return PhotonLineAirKermaResult(
        photon_energy_mev=photon_line.energy,
        emission_intensity=photon_line.intensity,
        photon_rate_per_s=photon_rate_per_s,
        uncollided_photon_fluence_rate_per_cm2_s=(
            uncollided_photon_fluence_rate_per_cm2_s
        ),
        energy_fluence_rate_mev_per_cm2_s=(energy_fluence_rate),
        air_mu_en_over_rho_cm2_per_g=(coefficient.mu_en_over_rho_cm2_per_g),
        uncollided_collision_air_kerma_rate_gy_per_s=(uncollided_air_kerma_rate),
        calculation_method=calculation_method,
        coefficient_source=coefficient.source,
        buildup_status=buildup_status,
        buildup_factor=buildup_factor,
        buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
            buildup_adjusted_air_kerma_rate
        ),
        warnings=line_warnings,
    )


def collect_unique_line_warnings(
    line_results: list[PhotonLineAirKermaResult],
) -> list[str]:
    # Combine line-level warnings while preserving their original order.
    #
    # The same warning may occur for multiple photon lines. Source-level
    # output should not repeat identical warning text unnecessarily.

    combined_warnings: list[str] = []

    for line_result in line_results:
        for warning in line_result.warnings:
            if warning not in combined_warnings:
                combined_warnings.append(warning)

    return combined_warnings


def aggregate_source_air_kerma_results(
    source_name: str,
    activity_bq: float | None,
    line_results: list[PhotonLineAirKermaResult],
) -> SourceAirKermaResult:
    # Combine line-by-line collision air-kerma results into one source result.
    #
    # Source-level buildup behavior:
    #
    # all lines applied
    #     -> buildup-adjusted total is available
    #
    # any line unavailable
    #     -> source buildup status is unavailable
    #
    # any line uses fallback
    #     -> source buildup status is fallback
    #
    # all lines not requested
    #     -> only the uncollided response is reported
    #
    # A mixture of not_requested and another buildup status is rejected
    # because buildup is a source-calculation setting, not a per-line user
    # choice.

    if source_name.strip() == "":
        raise ValueError("Source name cannot be empty.")

    if activity_bq is not None and activity_bq < 0:
        raise ValueError("Source activity cannot be negative.")

    if len(line_results) == 0:
        raise ValueError("At least one photon-line air-kerma result is required.")

    total_uncollided_photon_fluence_rate = sum(
        line_result.uncollided_photon_fluence_rate_per_cm2_s
        for line_result in line_results
    )

    total_uncollided_air_kerma_rate = sum(
        line_result.uncollided_collision_air_kerma_rate_gy_per_s
        for line_result in line_results
    )

    buildup_statuses = {line_result.buildup_status for line_result in line_results}

    if "not_requested" in buildup_statuses and len(buildup_statuses) > 1:
        raise ValueError(
            "Source line results cannot mix not-requested buildup "
            "with applied, unavailable, or fallback buildup states."
        )

    total_buildup_adjusted_air_kerma_rate = None

    if buildup_statuses == {"applied"}:
        source_buildup_status: BuildupStatus = "applied"

        adjusted_line_values = []

        for line_result in line_results:
            adjusted_value = (
                line_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s
            )

            if adjusted_value is None:
                raise ValueError(
                    "An applied photon-line buildup result is "
                    "missing its adjusted air-kerma rate."
                )

            adjusted_line_values.append(adjusted_value)

        total_buildup_adjusted_air_kerma_rate = sum(adjusted_line_values)

    elif "unavailable" in buildup_statuses:
        source_buildup_status = "unavailable"

    elif "fallback" in buildup_statuses:
        source_buildup_status = "fallback"

    elif buildup_statuses == {"not_requested"}:
        source_buildup_status = "not_requested"

    else:
        raise ValueError(
            "Unable to determine a consistent source-level buildup status."
        )

    warnings = collect_unique_line_warnings(line_results)

    return SourceAirKermaResult(
        source_name=source_name,
        activity_bq=activity_bq,
        line_results=list(line_results),
        total_uncollided_photon_fluence_rate_per_cm2_s=(
            total_uncollided_photon_fluence_rate
        ),
        total_uncollided_collision_air_kerma_rate_gy_per_s=(
            total_uncollided_air_kerma_rate
        ),
        buildup_status=source_buildup_status,
        total_buildup_adjusted_collision_air_kerma_rate_gy_per_s=(
            total_buildup_adjusted_air_kerma_rate
        ),
        warnings=warnings,
    )


def calculate_shielded_photon_line_air_kerma_result(
    photon_line: PhotonLine,
    photon_rate_per_s: float,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> PhotonLineAirKermaResult:
    # Calculate attenuation and collision air kerma for one photon line.
    #
    # Workflow:
    #
    # photon rate
    #     -> Beer-Lambert shielding result
    #     -> uncollided photon fluence rate
    #     -> energy fluence rate
    #     -> collision air-kerma rate
    #     -> optional G-P exposure buildup adjustment
    #
    # A failed buildup calculation does not discard the valid
    # uncollided response.

    if photon_rate_per_s < 0:
        raise ValueError("Photon emission rate cannot be negative.")

    shielding_result = calculate_shielding_result(
        layers=layers,
        photon_energy=photon_line.energy,
        source_strength=photon_rate_per_s,
        detector_distance=detector_distance_cm,
    )

    return calculate_air_kerma_from_shielding_result(
        photon_line, shielding_result, apply_buildup
    )


def calculate_air_kerma_from_shielding_result(
    photon_line: PhotonLine,
    shielding_result: ShieldingResult,
    apply_buildup: bool,
) -> PhotonLineAirKermaResult:
    """Evaluate collision kerma and report buildup availability for one line."""
    buildup_status: BuildupStatus = "not_requested"

    buildup_factor = None
    warnings: list[str] = []

    if apply_buildup:
        try:
            buildup_factor = calculate_gp_exposure_buildup_factor_for_shielding_result(
                shielding_result
            )

            buildup_status = "applied"

        except ValueError as error:
            buildup_status = "unavailable"

            warnings.append(
                "G-P exposure buildup was unavailable for "
                f"the {photon_line.energy:.8g} MeV photon line. "
                f"{error} "
                "The uncollided collision air-kerma rate "
                "is still reported."
            )

    return calculate_photon_line_air_kerma_result(
        photon_line=photon_line,
        photon_rate_per_s=shielding_result.source_strength,
        uncollided_photon_fluence_rate_per_cm2_s=(shielding_result.uncollided_flux),
        buildup_status=buildup_status,
        buildup_factor=buildup_factor,
        warnings=warnings,
    )


def calculate_manual_source_air_kerma_result(
    source: ManualPhotonSource,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Calculate collision air kerma for a manual monoenergetic source.

    photon_line = PhotonLine(
        energy=source.energy,
        intensity=1.0,
    )

    line_result = calculate_shielded_photon_line_air_kerma_result(
        photon_line=photon_line,
        photon_rate_per_s=source.photon_rate,
        layers=layers,
        detector_distance_cm=detector_distance_cm,
        apply_buildup=apply_buildup,
    )

    return aggregate_source_air_kerma_results(
        source_name="Manual Photon Source",
        activity_bq=None,
        line_results=[line_result],
    )


def calculate_isotope_source_air_kerma_result(
    source: IsotopeSource,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Calculate one collision air-kerma contribution per isotope
    # photon line and sum the complete source response.

    line_results: list[PhotonLineAirKermaResult] = []

    for photon_line in source.photon_lines:
        photon_rate_per_s = source.activity_bq * photon_line.intensity

        line_result = calculate_shielded_photon_line_air_kerma_result(
            photon_line=photon_line,
            photon_rate_per_s=photon_rate_per_s,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )

        line_results.append(line_result)

    return aggregate_source_air_kerma_results(
        source_name=source.name,
        activity_bq=source.activity_bq,
        line_results=line_results,
    )


def calculate_source_air_kerma_result(
    source: Source,
    layers: list[Layer],
    detector_distance_cm: float,
    apply_buildup: bool = False,
) -> SourceAirKermaResult:
    # Route a supported source type into the correct V1.12 response
    # calculation pathway.

    if isinstance(
        source,
        ManualPhotonSource,
    ):
        return calculate_manual_source_air_kerma_result(
            source=source,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )

    if isinstance(
        source,
        IsotopeSource,
    ):
        return calculate_isotope_source_air_kerma_result(
            source=source,
            layers=layers,
            detector_distance_cm=detector_distance_cm,
            apply_buildup=apply_buildup,
        )

    raise ValueError("Unsupported source type for air-kerma calculation.")
