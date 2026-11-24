"""Verification cases migrated from the original validation runner."""

from pathlib import Path
from tempfile import TemporaryDirectory

from shielding.design.models import (
    DesignConstraints,
    OptimizationWeights,
)
from shielding.design.targets import AirKermaRateTarget
from shielding.scenarios.fixed_shield import calculate_fixed_shield_response
from shielding.scenarios.fixed_shield_models import FixedShieldDeterministicResult
from shielding.scenarios.geometry import (
    ConcentricSphericalGeometry,
    ShieldLayerSpec,
)
from shielding.scenarios.json_io import (
    load_scenario,
    save_scenario,
    scenario_from_dict,
    scenario_to_dict,
)
from shielding.scenarios.models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ShieldingScenario,
)
from shielding.scenarios.runner import run_scenario
from tests.checks import (
    assert_close,
    assert_equal,
    assert_not_none,
    assert_raises,
)


def test_historical_benchmark_scenarios() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )

    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )

    # Official scenario files

    assert_equal(
        "V1.13 development scenario file exists",
        development_scenario_path.is_file(),
        True,
    )

    assert_equal(
        "V1.13 production scenario file exists",
        production_scenario_path.is_file(),
        True,
    )

    development_scenario = load_scenario(development_scenario_path)

    production_scenario = load_scenario(production_scenario_path)

    assert_equal(
        "V1.13 development scenario preserves ID",
        development_scenario.scenario_id,
        "cs137_v113_development",
    )

    assert_equal(
        "V1.13 production scenario preserves ID",
        production_scenario.scenario_id,
        "cs137_v113_production",
    )

    assert_equal(
        "V1.13 development scenario uses schema 1.1",
        development_scenario.schema_version,
        "1.1",
    )

    assert_equal(
        "V1.13 production scenario uses schema 1.1",
        production_scenario.schema_version,
        "1.1",
    )

    assert_equal(
        "V1.13 development scenario uses fixed-shield mode",
        development_scenario.calculation_mode,
        "fixed_shield_response",
    )

    assert_equal(
        "V1.13 production scenario uses fixed-shield mode",
        production_scenario.calculation_mode,
        "fixed_shield_response",
    )

    assert_close(
        "V1.13 development source cavity radius",
        (development_scenario.geometry.source_cavity_radius_cm),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production source cavity radius",
        (production_scenario.geometry.source_cavity_radius_cm),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 development evaluation radius",
        (development_scenario.geometry.evaluation_radius_cm),
        100.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production evaluation radius",
        (production_scenario.geometry.evaluation_radius_cm),
        100.0,
        1.0e-12,
    )

    assert_equal(
        "V1.13 development scenario contains one layer",
        len(development_scenario.geometry.layers),
        1,
    )

    assert_equal(
        "V1.13 production scenario contains one layer",
        len(production_scenario.geometry.layers),
        1,
    )

    assert_equal(
        "V1.13 development layer uses Lead",
        (development_scenario.geometry.layers[0].material_key),
        "lead",
    )

    assert_equal(
        "V1.13 production layer uses Lead",
        (production_scenario.geometry.layers[0].material_key),
        "lead",
    )

    assert_close(
        "V1.13 development Lead thickness",
        (development_scenario.geometry.layers[0].thickness_cm),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production Lead thickness",
        (production_scenario.geometry.layers[0].thickness_cm),
        5.0,
        1.0e-12,
    )

    development_shells = development_scenario.geometry.create_shells()

    production_shells = production_scenario.geometry.create_shells()

    assert_close(
        "V1.13 development Lead inner radius",
        development_shells[0].inner_radius_cm,
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 development Lead outer radius",
        development_shells[0].outer_radius_cm,
        2.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production Lead inner radius",
        production_shells[0].inner_radius_cm,
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production Lead outer radius",
        production_shells[0].outer_radius_cm,
        6.0,
        1.0e-12,
    )

    assert_equal(
        "V1.13 development scenario has no target",
        development_scenario.target,
        None,
    )

    assert_equal(
        "V1.13 production scenario has no target",
        production_scenario.target,
        None,
    )

    assert_equal(
        "V1.13 development scenario requests buildup",
        (development_scenario.deterministic_settings.apply_buildup),
        True,
    )

    assert_equal(
        "V1.13 production scenario requests buildup",
        (production_scenario.deterministic_settings.apply_buildup),
        True,
    )


def test_fixed_shield_serialization() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    development_scenario = load_scenario(development_scenario_path)

    # Fixed-shield serialization

    development_data = scenario_to_dict(development_scenario)

    assert_equal(
        "V1.13 fixed-shield serialization preserves mode",
        development_data["calculation_mode"],
        "fixed_shield_response",
    )

    assert_equal(
        "V1.13 fixed-shield serialization preserves null target",
        development_data["target"],
        None,
    )

    assert_equal(
        "V1.13 fixed-shield serialization omits candidate materials",
        ("candidate_material_keys" in development_data),
        False,
    )

    assert_equal(
        "V1.13 fixed-shield serialization omits constraints",
        ("constraints" in development_data),
        False,
    )

    assert_equal(
        "V1.13 fixed-shield serialization omits optimization",
        ("optimization" in development_data),
        False,
    )

    reconstructed_development_scenario = scenario_from_dict(development_data)

    assert_equal(
        "V1.13 dictionary reconstruction preserves fixed scenario",
        reconstructed_development_scenario,
        development_scenario,
    )


def test_fixed_shield_file_round_trip() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    production_scenario = load_scenario(production_scenario_path)

    # Fixed-shield file round trip

    with TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        roundtrip_path = temporary_path / "v113_fixed_roundtrip.json"

        saved_path = save_scenario(
            production_scenario,
            roundtrip_path,
        )

        assert_equal(
            "V1.13 fixed-shield save creates JSON file",
            saved_path.is_file(),
            True,
        )

        roundtrip_scenario = load_scenario(roundtrip_path)

        assert_equal(
            "V1.13 fixed-shield JSON round trip preserves object",
            roundtrip_scenario,
            production_scenario,
        )


def test_scenario_schema_compatibility() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    # Schema backward and forward compatibility

    v110_reference_path = repository_root / "scenarios" / "cs137_v110_reference.json"

    schema_10_scenario = load_scenario(v110_reference_path)

    assert_equal(
        "V1.13 schema 1.0 scenario remains supported",
        schema_10_scenario.schema_version,
        "1.0",
    )

    schema_11_optimization_data = scenario_to_dict(schema_10_scenario)

    schema_11_optimization_data["schema_version"] = "1.1"

    schema_11_optimization_scenario = scenario_from_dict(schema_11_optimization_data)

    assert_equal(
        "V1.13 schema 1.1 supports optimization scenarios",
        (schema_11_optimization_scenario.calculation_mode),
        "material_optimization",
    )

    assert_equal(
        "V1.13 schema 1.1 optimization preserves candidate count",
        len(schema_11_optimization_scenario.candidate_material_keys),
        9,
    )


def test_optional_fixed_shield_target() -> None:
    # Optional fixed-shield target

    targeted_fixed_scenario = ShieldingScenario(
        schema_version="1.1",
        scenario_id=("v113_targeted_fixed_test"),
        description=("Fixed-shield scenario with an optional response target."),
        calculation_mode=("fixed_shield_response"),
        source=IsotopeSourceSpec(
            isotope_key="cs137",
            activity_bq=3.7e10,
        ),
        geometry=(
            ConcentricSphericalGeometry(
                source_cavity_radius_cm=1.0,
                evaluation_radius_cm=100.0,
                layers=[
                    ShieldLayerSpec(
                        material_key="lead",
                        thickness_cm=5.0,
                    )
                ],
            )
        ),
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=(1.0)),
        deterministic_settings=(DeterministicSettings(apply_buildup=True)),
    )

    targeted_fixed_data = scenario_to_dict(targeted_fixed_scenario)

    assert_equal(
        "V1.13 fixed-shield optional target serializes",
        targeted_fixed_data["target"]["type"],
        "air_kerma_rate",
    )

    reconstructed_targeted_scenario = scenario_from_dict(targeted_fixed_data)

    assert_equal(
        "V1.13 fixed-shield optional target round trips",
        reconstructed_targeted_scenario,
        targeted_fixed_scenario,
    )


def test_invalid_fixed_shield_combinations() -> None:
    # Invalid fixed-shield combinations

    def create_fixed_geometry() -> ConcentricSphericalGeometry:
        return ConcentricSphericalGeometry(
            source_cavity_radius_cm=1.0,
            evaluation_radius_cm=100.0,
            layers=[
                ShieldLayerSpec(
                    material_key="lead",
                    thickness_cm=5.0,
                )
            ],
        )

    def create_fixed_source() -> IsotopeSourceSpec:
        return IsotopeSourceSpec(
            isotope_key="cs137",
            activity_bq=3.7e10,
        )

    assert_raises(
        "V1.13 schema 1.0 rejects fixed-shield mode",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.0",
            scenario_id=("schema_10_fixed_test"),
            description=("Invalid schema 1.0 fixed-shield test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
        ),
        "require schema version 1.1",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects empty layers",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("empty_fixed_layers_test"),
            description=("Invalid empty fixed-shield test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=(
                ConcentricSphericalGeometry(
                    source_cavity_radius_cm=1.0,
                    evaluation_radius_cm=100.0,
                    layers=[],
                )
            ),
        ),
        "require at least one fixed shield layer",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects candidate materials",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("fixed_candidates_test"),
            description=("Invalid fixed-shield candidate test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
            candidate_material_keys=[
                "lead",
            ],
        ),
        "cannot contain candidate material keys",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects constraints",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("fixed_constraints_test"),
            description=("Invalid fixed-shield constraints test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
            constraints=DesignConstraints(max_thickness_cm=10.0),
        ),
        "cannot contain optimization constraints",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects optimization mode",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("fixed_optimization_test"),
            description=("Invalid fixed-shield optimization test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
            optimization_mode="minimum_mass",
        ),
        "cannot contain an optimization mode",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects optimization weights",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("fixed_weights_test"),
            description=("Invalid fixed-shield weights test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
            optimization_weights=(
                OptimizationWeights(
                    thickness_weight=1.0,
                    mass_weight=1.0,
                    cost_weight=1.0,
                )
            ),
        ),
        "cannot contain optimization weights",
    )

    assert_raises(
        "V1.13 fixed-shield mode rejects calculation search limit",
        ValueError,
        lambda: ShieldingScenario(
            schema_version="1.1",
            scenario_id=("fixed_search_limit_test"),
            description=("Invalid fixed-shield calculation search-limit test."),
            calculation_mode=("fixed_shield_response"),
            source=create_fixed_source(),
            geometry=create_fixed_geometry(),
            deterministic_settings=(
                DeterministicSettings(
                    apply_buildup=True,
                    calculation_max_thickness_cm=10.0,
                )
            ),
        ),
        "do not use a calculation maximum thickness",
    )


def test_fixed_shield_deterministic_calculation() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    development_scenario = load_scenario(development_scenario_path)
    production_scenario = load_scenario(production_scenario_path)

    development_fixed_result = calculate_fixed_shield_response(development_scenario)

    production_fixed_result = calculate_fixed_shield_response(production_scenario)

    assert_equal(
        "V1.13 development calculation returns fixed-shield result",
        isinstance(
            development_fixed_result,
            FixedShieldDeterministicResult,
        ),
        True,
    )

    assert_equal(
        "V1.13 production calculation returns fixed-shield result",
        isinstance(
            production_fixed_result,
            FixedShieldDeterministicResult,
        ),
        True,
    )

    assert_equal(
        "V1.13 development result preserves scenario ID",
        development_fixed_result.scenario_id,
        "cs137_v113_development",
    )

    assert_equal(
        "V1.13 production result preserves scenario ID",
        production_fixed_result.scenario_id,
        "cs137_v113_production",
    )

    assert_equal(
        "V1.13 fixed-shield result preserves source name",
        production_fixed_result.source_name,
        "Cs-137",
    )

    assert_close(
        "V1.13 fixed-shield result preserves activity",
        assert_not_none(
            "V1.13 fixed-shield activity exists",
            production_fixed_result.activity_bq,
        ),
        3.7e10,
        1.0e-3,
    )

    assert_equal(
        "V1.13 development result contains one photon line",
        len(development_fixed_result.line_results),
        1,
    )

    assert_equal(
        "V1.13 production result contains one photon line",
        len(production_fixed_result.line_results),
        1,
    )

    development_fixed_line = development_fixed_result.line_results[0]

    production_fixed_line = production_fixed_result.line_results[0]

    assert_close(
        "V1.13 development photon-line energy",
        (development_fixed_line.photon_line.energy),
        0.661657,
        1.0e-12,
    )

    assert_close(
        "V1.13 production photon emission rate",
        (production_fixed_line.photon_rate_per_s),
        3.1487e10,
        1.0e-3,
    )

    assert_equal(
        "V1.13 fixed-shield runtime material is Lead",
        (production_fixed_result.layers[0].material.key),
        "lead",
    )

    assert_close(
        "V1.13 development total shield thickness",
        (development_fixed_result.total_shield_thickness_cm),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 production total shield thickness",
        (production_fixed_result.total_shield_thickness_cm),
        5.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 development Lead optical thickness",
        (development_fixed_line.shielding_result.total_mfp),
        1.260102158391917,
        1.0e-12,
    )

    assert_close(
        "V1.13 production Lead optical thickness",
        (production_fixed_line.shielding_result.total_mfp),
        6.300510791959585,
        1.0e-12,
    )

    assert_close(
        "V1.13 development Lead transmission",
        (development_fixed_line.shielding_result.total_transmission),
        0.2836250503406665,
        1.0e-15,
    )

    assert_close(
        "V1.13 production Lead transmission",
        (production_fixed_line.shielding_result.total_transmission),
        0.0018353670468263651,
        1.0e-15,
    )

    assert_close(
        "V1.13 development point uncollided fluence",
        (development_fixed_result.total_uncollided_photon_fluence_rate_per_cm2_s),
        71066.67656190228,
        1.0e-8,
    )

    assert_close(
        "V1.13 production point uncollided fluence",
        (production_fixed_result.total_uncollided_photon_fluence_rate_per_cm2_s),
        459.8798171477357,
        1.0e-10,
    )

    assert_close(
        "V1.13 development point uncollided air kerma",
        (development_fixed_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        2.206372966129021e-7,
        1.0e-18,
    )

    assert_close(
        "V1.13 production point uncollided air kerma",
        (production_fixed_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        1.4277667752470475e-9,
        1.0e-20,
    )

    assert_equal(
        "V1.13 development buildup status is applied",
        development_fixed_result.buildup_status,
        "applied",
    )

    assert_equal(
        "V1.13 production buildup status is applied",
        production_fixed_result.buildup_status,
        "applied",
    )

    assert_close(
        "V1.13 development G-P buildup factor",
        assert_not_none(
            "V1.13 development buildup factor exists",
            (development_fixed_line.air_kerma_result.buildup_factor),
        ),
        1.5482056569655493,
        1.0e-12,
    )

    assert_close(
        "V1.13 production G-P buildup factor",
        assert_not_none(
            "V1.13 production buildup factor exists",
            (production_fixed_line.air_kerma_result.buildup_factor),
        ),
        2.6376806705294165,
        1.0e-12,
    )

    assert_close(
        "V1.13 development point G-P-adjusted air kerma",
        assert_not_none(
            "V1.13 development adjusted response exists",
            (
                development_fixed_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        3.4159191075368083e-7,
        1.0e-18,
    )

    assert_close(
        "V1.13 production point G-P-adjusted air kerma",
        assert_not_none(
            "V1.13 production adjusted response exists",
            (
                production_fixed_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s
            ),
        ),
        3.765992825093255e-9,
        1.0e-20,
    )

    assert_equal(
        "V1.13 fixed-shield source and line response match",
        (
            production_fixed_line.air_kerma_result
            == production_fixed_result.source_air_kerma_result.line_results[0]
        ),
        True,
    )

    assert_equal(
        "V1.13 fixed-shield calculation has no warnings",
        production_fixed_result.warnings,
        [],
    )


def test_fixed_shield_calculation_failures() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    v110_reference_path = repository_root / "scenarios" / "cs137_v110_reference.json"
    schema_10_scenario = load_scenario(v110_reference_path)

    # Fixed-shield calculation failures

    assert_raises(
        "V1.13 fixed-shield calculator rejects optimization scenario",
        ValueError,
        lambda: calculate_fixed_shield_response(schema_10_scenario),
        "requires fixed_shield_response mode",
    )

    unknown_material_scenario = ShieldingScenario(
        schema_version="1.1",
        scenario_id=("v113_unknown_fixed_material"),
        description=("Fixed-shield scenario with an unknown material key."),
        calculation_mode=("fixed_shield_response"),
        source=IsotopeSourceSpec(
            isotope_key="cs137",
            activity_bq=3.7e10,
        ),
        geometry=(
            ConcentricSphericalGeometry(
                source_cavity_radius_cm=1.0,
                evaluation_radius_cm=100.0,
                layers=[
                    ShieldLayerSpec(
                        material_key=("not_a_material"),
                        thickness_cm=1.0,
                    )
                ],
            )
        ),
        deterministic_settings=(DeterministicSettings(apply_buildup=False)),
    )

    assert_raises(
        "V1.13 fixed-shield calculator rejects unknown material",
        ValueError,
        lambda: calculate_fixed_shield_response(unknown_material_scenario),
        "unknown material keys",
    )


def test_fixed_shield_scenario_routing() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_development.json"
    )
    production_scenario_path = (
        repository_root / "scenarios" / "cs137_v113_production.json"
    )
    development_scenario = load_scenario(development_scenario_path)
    production_scenario = load_scenario(production_scenario_path)
    development_fixed_result = calculate_fixed_shield_response(development_scenario)
    production_fixed_result = calculate_fixed_shield_response(production_scenario)

    routed_development_result = run_scenario(development_scenario)

    assert_equal(
        "V1.13 scenario runner returns fixed-shield result",
        isinstance(
            routed_development_result,
            FixedShieldDeterministicResult,
        ),
        True,
    )

    if not isinstance(
        routed_development_result,
        FixedShieldDeterministicResult,
    ):
        raise AssertionError(
            "V1.13 scenario runner did not return a FixedShieldDeterministicResult."
        )

    assert_equal(
        "V1.13 scenario runner matches direct fixed-shield calculation",
        routed_development_result,
        development_fixed_result,
    )

    routed_production_result = run_scenario(production_scenario)

    assert_equal(
        "V1.13 production scenario routes through general runner",
        isinstance(
            routed_production_result,
            FixedShieldDeterministicResult,
        ),
        True,
    )

    if not isinstance(
        routed_production_result,
        FixedShieldDeterministicResult,
    ):
        raise AssertionError(
            "V1.13 production scenario did not return a FixedShieldDeterministicResult."
        )

    assert_equal(
        "V1.13 production runner preserves point response",
        (routed_production_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
        (production_fixed_result.total_uncollided_collision_air_kerma_rate_gy_per_s),
    )
