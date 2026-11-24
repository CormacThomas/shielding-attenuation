"""Verification cases migrated from the original validation runner."""

from shielding.data.dry_air import (
    NIST_DRY_AIR_COEFFICIENT_SOURCE,
    get_dry_air_mu_en_over_rho_library,
)
from shielding.data.gp_coefficients import get_gp_coefficients_library
from shielding.physics.air_kerma import (
    aggregate_source_air_kerma_results,
    calculate_collision_air_kerma_rate_gy_per_s,
    calculate_collision_air_kerma_rate_microgy_per_h,
    calculate_energy_fluence_rate_mev_per_cm2_s,
    calculate_photon_line_air_kerma_result,
)
from shielding.physics.buildup import (
    calculate_gp_buildup_factor,
    get_gp_coefficients_at_energy,
)
from shielding.physics.kerma_coefficients import (
    get_air_kerma_coefficient_at_energy,
    get_exact_air_kerma_coefficient,
    log_log_interpolate_positive_value,
)
from shielding.physics.source_models import PhotonLine
from shielding.physics.units import (
    convert_activity_to_bq,
    convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s,
    convert_gy_per_s_to_microgy_per_h,
    convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg,
    convert_mev_to_joules,
    convert_microgy_per_h_to_gy_per_s,
)
from tests.checks import (
    assert_close,
    assert_equal,
    assert_greater_than,
    assert_not_none,
    assert_raises,
)


def test_gp_buildup_identities() -> None:
    gp_library = get_gp_coefficients_library()

    # Validate G-P buildup behavior for every material with coefficient data.

    for material_key in gp_library:
        coefficients = get_gp_coefficients_at_energy(
            material_key,
            1.0,
            gp_library,
        )

        assert_close(
            f"{material_key} GP buildup at 0 MFP",
            calculate_gp_buildup_factor(coefficients, 0.0),
            1.0,
            1e-12,
        )

        assert_close(
            f"{material_key} GP buildup at 1 MFP",
            calculate_gp_buildup_factor(coefficients, 1.0),
            coefficients.b,
            1e-8,
        )

        buildup_at_5_mfp = calculate_gp_buildup_factor(coefficients, 5.0)

        assert_greater_than(
            f"{material_key} GP buildup at 5 MFP greater than 1",
            buildup_at_5_mfp,
            1.0,
        )


def test_activity_conversion() -> None:
    # Validate activity-unit conversions used by isotope sources.

    one_ci_bq = convert_activity_to_bq(1.0, "ci")

    assert_close(
        "1 Ci activity conversion",
        one_ci_bq,
        3.7e10,
        1e-6,
    )

    assert_close(
        "1 mCi activity conversion",
        convert_activity_to_bq(1.0, "mci"),
        3.7e7,
        1e-6,
    )

    assert_close(
        "1 uCi activity conversion",
        convert_activity_to_bq(1.0, "uci"),
        3.7e4,
        1e-9,
    )


def test_dry_air_data_and_interpolation() -> None:
    air_library = get_dry_air_mu_en_over_rho_library()

    assert_equal(
        "V1.12 dry-air coefficient library contains 38 entries",
        len(air_library),
        38,
    )

    assert_equal(
        "V1.12 dry-air coefficient energies are nondecreasing",
        all(
            air_library[index].photon_energy_mev
            <= air_library[index + 1].photon_energy_mev
            for index in range(len(air_library) - 1)
        ),
        True,
    )

    exact_006_coefficient = get_exact_air_kerma_coefficient(0.06)

    assert_close(
        "V1.12 exact dry-air coefficient lookup",
        exact_006_coefficient.mu_en_over_rho_cm2_per_g,
        0.03041,
        1.0e-12,
    )

    assert_equal(
        "V1.12 dry-air coefficient preserves source metadata",
        exact_006_coefficient.source,
        NIST_DRY_AIR_COEFFICIENT_SOURCE,
    )

    cs137_coefficient = get_air_kerma_coefficient_at_energy(0.661657)

    assert_close(
        "V1.12 Cs-137 dry-air coefficient interpolation",
        cs137_coefficient.mu_en_over_rho_cm2_per_g,
        0.02928664455391956,
        1.0e-12,
    )

    below_edge = get_exact_air_kerma_coefficient(
        0.0032029,
        edge_side="below",
    )

    above_edge = get_exact_air_kerma_coefficient(
        0.0032029,
        edge_side="above",
    )

    assert_close(
        "V1.12 argon edge below-edge coefficient",
        below_edge.mu_en_over_rho_cm2_per_g,
        133.0,
        1.0e-12,
    )

    assert_close(
        "V1.12 argon edge above-edge coefficient",
        above_edge.mu_en_over_rho_cm2_per_g,
        146.0,
        1.0e-12,
    )

    assert_raises(
        "V1.12 ambiguous absorption-edge lookup rejected",
        ValueError,
        lambda: get_exact_air_kerma_coefficient(0.0032029),
        "absorption edge",
    )

    assert_raises(
        "V1.12 out-of-range dry-air coefficient rejected",
        ValueError,
        lambda: get_air_kerma_coefficient_at_energy(25.0),
        "outside the dry-air coefficient range",
    )

    logarithmic_midpoint = log_log_interpolate_positive_value(
        x=(0.1 * 0.2) ** 0.5,
        x1=0.1,
        y1=0.02325,
        x2=0.2,
        y2=0.02672,
    )

    assert_close(
        "V1.12 log-log interpolation geometric midpoint",
        logarithmic_midpoint,
        (0.02325 * 0.02672) ** 0.5,
        1.0e-12,
    )


def test_air_kerma_unit_conversions() -> None:
    # Unit-conversion foundation

    assert_close(
        "V1.12 one MeV converts to joules",
        convert_mev_to_joules(1.0),
        1.602176634e-13,
        1.0e-25,
    )

    assert_close(
        "V1.12 energy-fluence SI conversion",
        convert_energy_fluence_mev_per_cm2_s_to_j_per_m2_s(1.0),
        1.602176634e-9,
        1.0e-21,
    )

    assert_close(
        "V1.12 mass energy-absorption coefficient SI conversion",
        convert_mass_energy_absorption_coefficient_cm2_per_g_to_m2_per_kg(1.0),
        0.1,
        1.0e-12,
    )

    assert_close(
        "V1.12 Gy per second converts to microGy per hour",
        convert_gy_per_s_to_microgy_per_h(1.0),
        3.6e9,
        1.0e-3,
    )

    assert_close(
        "V1.12 microGy per hour converts to Gy per second",
        convert_microgy_per_h_to_gy_per_s(3.6e9),
        1.0,
        1.0e-12,
    )


def test_energy_fluence_and_collision_air_kerma() -> None:
    cs137_coefficient = get_air_kerma_coefficient_at_energy(0.661657)

    # Energy fluence and collision air kerma

    cs137_energy_fluence = calculate_energy_fluence_rate_mev_per_cm2_s(
        photon_energy_mev=0.661657,
        photon_fluence_rate_per_cm2_s=100.0,
    )

    assert_close(
        "V1.12 Cs-137 energy-fluence calculation",
        cs137_energy_fluence,
        66.1657,
        1.0e-12,
    )

    cs137_air_kerma_gy_per_s = calculate_collision_air_kerma_rate_gy_per_s(
        energy_fluence_rate_mev_per_cm2_s=(cs137_energy_fluence),
        mu_en_over_rho_cm2_per_g=(cs137_coefficient.mu_en_over_rho_cm2_per_g),
    )

    assert_close(
        "V1.12 Cs-137 collision air-kerma rate in Gy per second",
        cs137_air_kerma_gy_per_s,
        3.1046519590756025e-10,
        1.0e-20,
    )

    assert_close(
        "V1.12 Cs-137 collision air-kerma rate in microGy per hour",
        calculate_collision_air_kerma_rate_microgy_per_h(
            cs137_energy_fluence,
            cs137_coefficient.mu_en_over_rho_cm2_per_g,
        ),
        1.117674705267217,
        1.0e-10,
    )

    assert_close(
        "V1.12 zero energy fluence produces zero air kerma",
        calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=0.0,
            mu_en_over_rho_cm2_per_g=(cs137_coefficient.mu_en_over_rho_cm2_per_g),
        ),
        0.0,
        1.0e-20,
    )

    assert_raises(
        "V1.12 nonpositive response coefficient rejected",
        ValueError,
        lambda: calculate_collision_air_kerma_rate_gy_per_s(
            energy_fluence_rate_mev_per_cm2_s=1.0,
            mu_en_over_rho_cm2_per_g=0.0,
        ),
        "must be greater than zero",
    )


def test_line_response() -> None:
    # Photon-line response model

    cs137_line = PhotonLine(
        energy=0.661657,
        intensity=0.851,
    )

    cs137_line_result = calculate_photon_line_air_kerma_result(
        photon_line=cs137_line,
        photon_rate_per_s=3.1487e10,
        uncollided_photon_fluence_rate_per_cm2_s=100.0,
    )

    assert_equal(
        "V1.12 photon line defaults to no buildup requested",
        cs137_line_result.buildup_status,
        "not_requested",
    )

    assert_close(
        "V1.12 photon line stores interpolated response coefficient",
        cs137_line_result.air_mu_en_over_rho_cm2_per_g,
        0.02928664455391956,
        1.0e-12,
    )

    assert_close(
        "V1.12 photon line stores uncollided air-kerma response",
        (cs137_line_result.uncollided_collision_air_kerma_rate_gy_per_s),
        3.1046519590756025e-10,
        1.0e-20,
    )

    assert_equal(
        "V1.12 unrequested line buildup has no adjusted response",
        (cs137_line_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s),
        None,
    )

    cs137_buildup_line_result = calculate_photon_line_air_kerma_result(
        photon_line=cs137_line,
        photon_rate_per_s=3.1487e10,
        uncollided_photon_fluence_rate_per_cm2_s=100.0,
        buildup_status="applied",
        buildup_factor=2.5,
    )

    assert_equal(
        "V1.12 photon line stores applied buildup status",
        cs137_buildup_line_result.buildup_status,
        "applied",
    )

    assert_close(
        "V1.12 photon line stores buildup factor",
        assert_not_none(
            "V1.12 buildup factor exists",
            cs137_buildup_line_result.buildup_factor,
        ),
        2.5,
        1.0e-12,
    )

    assert_close(
        "V1.12 buildup-adjusted line response uses supplied factor",
        assert_not_none(
            "V1.12 adjusted line response exists",
            (
                cs137_buildup_line_result.buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        (cs137_buildup_line_result.uncollided_collision_air_kerma_rate_gy_per_s * 2.5),
        1.0e-20,
    )

    assert_raises(
        "V1.12 buildup factor rejected when buildup not requested",
        ValueError,
        lambda: calculate_photon_line_air_kerma_result(
            photon_line=cs137_line,
            photon_rate_per_s=1.0,
            uncollided_photon_fluence_rate_per_cm2_s=1.0,
            buildup_status="not_requested",
            buildup_factor=2.0,
        ),
        "may only be supplied",
    )


def test_source_air_kerma_aggregation() -> None:
    # Source-level aggregation

    co60_line_1 = PhotonLine(
        energy=1.173228,
        intensity=0.9985,
    )

    co60_line_2 = PhotonLine(
        energy=1.332492,
        intensity=0.9998,
    )

    co60_line_result_1 = calculate_photon_line_air_kerma_result(
        photon_line=co60_line_1,
        photon_rate_per_s=1.0,
        uncollided_photon_fluence_rate_per_cm2_s=100.0,
    )

    co60_line_result_2 = calculate_photon_line_air_kerma_result(
        photon_line=co60_line_2,
        photon_rate_per_s=1.0,
        uncollided_photon_fluence_rate_per_cm2_s=80.0,
    )

    co60_aggregate = aggregate_source_air_kerma_results(
        source_name="Co-60",
        activity_bq=3.7e10,
        line_results=[
            co60_line_result_1,
            co60_line_result_2,
        ],
    )

    assert_close(
        "V1.12 source aggregation sums photon fluence",
        (co60_aggregate.total_uncollided_photon_fluence_rate_per_cm2_s),
        180.0,
        1.0e-12,
    )

    assert_close(
        "V1.12 source aggregation sums uncollided air kerma",
        (co60_aggregate.total_uncollided_collision_air_kerma_rate_gy_per_s),
        (
            co60_line_result_1.uncollided_collision_air_kerma_rate_gy_per_s
            + co60_line_result_2.uncollided_collision_air_kerma_rate_gy_per_s
        ),
        1.0e-20,
    )

    assert_equal(
        "V1.12 uncollided source aggregation preserves buildup status",
        co60_aggregate.buildup_status,
        "not_requested",
    )

    co60_buildup_line_1 = calculate_photon_line_air_kerma_result(
        photon_line=co60_line_1,
        photon_rate_per_s=1.0,
        uncollided_photon_fluence_rate_per_cm2_s=100.0,
        buildup_status="applied",
        buildup_factor=2.0,
    )

    co60_buildup_line_2 = calculate_photon_line_air_kerma_result(
        photon_line=co60_line_2,
        photon_rate_per_s=1.0,
        uncollided_photon_fluence_rate_per_cm2_s=80.0,
        buildup_status="applied",
        buildup_factor=2.5,
    )

    co60_buildup_aggregate = aggregate_source_air_kerma_results(
        source_name="Co-60",
        activity_bq=3.7e10,
        line_results=[
            co60_buildup_line_1,
            co60_buildup_line_2,
        ],
    )

    assert_equal(
        "V1.12 buildup source aggregation stores applied status",
        co60_buildup_aggregate.buildup_status,
        "applied",
    )

    expected_co60_adjusted_total = assert_not_none(
        "V1.12 first Co-60 adjusted response exists",
        (co60_buildup_line_1.buildup_adjusted_collision_air_kerma_rate_gy_per_s),
    ) + assert_not_none(
        "V1.12 second Co-60 adjusted response exists",
        (co60_buildup_line_2.buildup_adjusted_collision_air_kerma_rate_gy_per_s),
    )

    assert_close(
        "V1.12 source aggregation sums buildup-adjusted air kerma",
        assert_not_none(
            "V1.12 Co-60 adjusted source total exists",
            (
                co60_buildup_aggregate.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        expected_co60_adjusted_total,
        1.0e-20,
    )

    assert_raises(
        "V1.12 mixed source buildup settings rejected",
        ValueError,
        lambda: aggregate_source_air_kerma_results(
            source_name="Co-60",
            activity_bq=3.7e10,
            line_results=[
                co60_line_result_1,
                co60_buildup_line_2,
            ],
        ),
        "cannot mix",
    )
