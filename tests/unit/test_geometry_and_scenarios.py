"""Verification cases migrated from the original validation runner."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from shielding.design.models import DesignConstraints
from shielding.design.targets import (
    AirKermaRateTarget,
    FluxTarget,
)
from shielding.physics.source_models import (
    IsotopeSource,
    ManualPhotonSource,
)
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
    ManualPhotonSourceSpec,
    ShieldingScenario,
)
from shielding.scenarios.runner import (
    resolve_candidate_materials,
)
from shielding.scenarios.sources import create_runtime_source
from tests.checks import (
    assert_close,
    assert_equal,
    assert_raises,
)


def test_concentric_spherical_geometry() -> None:
    lead_layer_spec = ShieldLayerSpec(
        material_key="  LEAD  ",
        thickness_cm=5.0,
    )

    copper_layer_spec = ShieldLayerSpec(
        material_key="copper",
        thickness_cm=1.0,
    )

    assert_equal(
        "V1.11 shield layer normalizes material key",
        lead_layer_spec.material_key,
        "lead",
    )

    layered_geometry = ConcentricSphericalGeometry(
        source_cavity_radius_cm=2.0,
        evaluation_radius_cm=100.0,
        layers=[
            lead_layer_spec,
            copper_layer_spec,
        ],
    )

    assert_close(
        "V1.11 spherical geometry total shield thickness",
        layered_geometry.total_shield_thickness_cm,
        6.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 spherical geometry outer shield radius",
        layered_geometry.outer_shield_radius_cm,
        8.0,
        1.0e-12,
    )

    derived_shells = layered_geometry.create_shells()

    assert_equal(
        "V1.11 spherical geometry creates two shells",
        len(derived_shells),
        2,
    )

    assert_close(
        "V1.11 first shell inner radius",
        derived_shells[0].inner_radius_cm,
        2.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 first shell outer radius",
        derived_shells[0].outer_radius_cm,
        7.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 second shell inner radius",
        derived_shells[1].inner_radius_cm,
        7.0,
        1.0e-12,
    )

    assert_close(
        "V1.11 second shell outer radius",
        derived_shells[1].outer_radius_cm,
        8.0,
        1.0e-12,
    )

    assert_raises(
        "V1.11 nonpositive layer thickness rejected",
        ValueError,
        lambda: ShieldLayerSpec(
            material_key="lead",
            thickness_cm=0.0,
        ),
        "greater than zero",
    )

    assert_raises(
        "V1.11 evaluation radius inside shield rejected",
        ValueError,
        lambda: ConcentricSphericalGeometry(
            source_cavity_radius_cm=2.0,
            evaluation_radius_cm=7.0,
            layers=[
                ShieldLayerSpec(
                    material_key="lead",
                    thickness_cm=5.0,
                )
            ],
        ),
        "beyond the outer shield radius",
    )


def test_source_specs_and_runtime_conversion() -> None:
    # Source specifications and runtime conversion

    isotope_source_spec = IsotopeSourceSpec(
        isotope_key="  CS137  ",
        activity_bq=3.7e10,
    )

    assert_equal(
        "V1.11 isotope source normalizes isotope key",
        isotope_source_spec.isotope_key,
        "cs137",
    )

    manual_source_spec = ManualPhotonSourceSpec(
        photon_energy_mev=0.661657,
        photon_rate_per_s=3.7e10,
    )

    runtime_manual_source = create_runtime_source(manual_source_spec)

    if not isinstance(
        runtime_manual_source,
        ManualPhotonSource,
    ):
        raise AssertionError(
            "V1.11 manual source adapter returned the wrong runtime source type."
        )

    assert_close(
        "V1.11 manual source adapter preserves energy",
        runtime_manual_source.energy,
        0.661657,
        1.0e-12,
    )

    assert_close(
        "V1.11 manual source adapter preserves photon rate",
        runtime_manual_source.photon_rate,
        3.7e10,
        1.0e-6,
    )

    runtime_isotope_source = create_runtime_source(isotope_source_spec)

    if not isinstance(
        runtime_isotope_source,
        IsotopeSource,
    ):
        raise AssertionError(
            "V1.11 isotope source adapter returned the wrong runtime source type."
        )

    assert_equal(
        "V1.11 isotope source adapter creates Cs-137 source",
        runtime_isotope_source.name,
        "Cs-137",
    )

    assert_close(
        "V1.11 isotope source adapter preserves activity",
        runtime_isotope_source.activity_bq,
        3.7e10,
        1.0e-6,
    )

    assert_raises(
        "V1.11 nonpositive calculation search limit rejected",
        ValueError,
        lambda: DeterministicSettings(calculation_max_thickness_cm=0.0),
        "greater than zero",
    )


def test_uncollided_scenario_definition() -> None:
    # Uncollided photon-fluence reference scenario

    repository_root = Path(__file__).resolve().parents[2]

    reference_scenario_path = (
        repository_root / "scenarios" / "cs137_v110_reference.json"
    )

    assert_equal(
        "V1.11 official reference scenario file exists",
        reference_scenario_path.is_file(),
        True,
    )

    reference_scenario = load_scenario(reference_scenario_path)

    assert_equal(
        "V1.11 loaded scenario preserves scenario ID",
        reference_scenario.scenario_id,
        "cs137_v110_reference",
    )

    assert_equal(
        "V1.11 loaded scenario preserves schema version",
        reference_scenario.schema_version,
        "1.0",
    )

    assert_equal(
        "V1.11 loaded scenario preserves nine candidates",
        len(reference_scenario.candidate_material_keys),
        9,
    )

    assert_equal(
        "V1.11 loaded scenario reconstructs spherical geometry",
        isinstance(
            reference_scenario.geometry,
            ConcentricSphericalGeometry,
        ),
        True,
    )

    loaded_target = reference_scenario.target

    if not isinstance(loaded_target, FluxTarget):
        raise AssertionError(
            "V1.11 reference scenario did not reconstruct a FluxTarget."
        )

    assert_close(
        "V1.11 loaded scenario preserves flux target",
        loaded_target.target_flux,
        100.0,
        1.0e-12,
    )

    assert_equal(
        ("V1.11 reference flux scenario uses uncollided photon fluence"),
        (reference_scenario.deterministic_settings.apply_buildup),
        False,
    )


def test_scenario_dictionary_round_trip() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    reference_scenario_path = (
        repository_root / "scenarios" / "cs137_v110_reference.json"
    )
    reference_scenario = load_scenario(reference_scenario_path)

    # Dictionary serialization and reconstruction

    reference_scenario_data = scenario_to_dict(reference_scenario)

    assert_equal(
        "V1.11 serialized source contains explicit type",
        reference_scenario_data["source"]["type"],
        "isotope",
    )

    assert_equal(
        "V1.11 serialized geometry contains explicit type",
        reference_scenario_data["geometry"]["type"],
        "concentric_spherical",
    )

    assert_equal(
        "V1.11 serialized target contains explicit type",
        reference_scenario_data["target"]["type"],
        "flux",
    )

    assert_equal(
        "V1.11 serialized optimization preserves mode",
        reference_scenario_data["optimization"]["mode"],
        "minimum_mass",
    )

    reconstructed_scenario = scenario_from_dict(reference_scenario_data)

    assert_equal(
        "V1.11 dictionary reconstruction preserves scenario",
        reconstructed_scenario,
        reference_scenario,
    )


def test_scenario_file_round_trip() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    reference_scenario_path = (
        repository_root / "scenarios" / "cs137_v110_reference.json"
    )
    reference_scenario = load_scenario(reference_scenario_path)
    reference_scenario_data = scenario_to_dict(reference_scenario)

    # File round-trip and malformed-file behavior

    with TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        roundtrip_path = temporary_path / "roundtrip_scenario.json"

        saved_path = save_scenario(
            reference_scenario,
            roundtrip_path,
        )

        assert_equal(
            "V1.11 scenario save creates JSON file",
            saved_path.is_file(),
            True,
        )

        roundtrip_scenario = load_scenario(roundtrip_path)

        assert_equal(
            "V1.11 scenario JSON round trip preserves object",
            roundtrip_scenario,
            reference_scenario,
        )

        unsupported_schema_data = json.loads(json.dumps(reference_scenario_data))

        unsupported_schema_data["schema_version"] = "99.0"

        assert_raises(
            "V1.11 unsupported schema version rejected",
            ValueError,
            lambda: scenario_from_dict(unsupported_schema_data),
            "Unsupported scenario schema version",
        )

        invalid_json_path = temporary_path / "invalid.json"

        invalid_json_path.write_text(
            '{"scenario_id": ',
            encoding="utf-8",
        )

        assert_raises(
            "V1.11 malformed JSON rejected",
            ValueError,
            lambda: load_scenario(invalid_json_path),
            "invalid JSON",
        )

        missing_field_data = json.loads(json.dumps(reference_scenario_data))

        missing_field_data.pop("source")

        missing_field_path = temporary_path / "missing_source.json"

        with missing_field_path.open(
            mode="w",
            encoding="utf-8",
        ) as missing_field_file:
            json.dump(
                missing_field_data,
                missing_field_file,
                indent=2,
            )

        assert_raises(
            "V1.11 missing required JSON field rejected",
            ValueError,
            lambda: load_scenario(missing_field_path),
            "missing required field",
        )


def test_scenario_validation() -> None:
    # Complete scenario validation

    assert_raises(
        "V1.11 duplicate candidate materials rejected",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="duplicate_material_test",
            description=("Scenario duplicate-material validation test."),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=0.0,
                evaluation_radius_cm=100.0,
            ),
            candidate_material_keys=[
                "lead",
                "  LEAD  ",
            ],
            target=FluxTarget(target_flux=100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
        ),
        "must be unique",
    )

    assert_raises(
        "V1.11 optimization scenario rejects fixed layers",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="fixed_layer_test",
            description=("Scenario fixed-layer validation test."),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=2.0,
                evaluation_radius_cm=100.0,
                layers=[
                    ShieldLayerSpec(
                        material_key="lead",
                        thickness_cm=1.0,
                    )
                ],
            ),
            candidate_material_keys=[
                "lead",
            ],
            target=FluxTarget(target_flux=100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
        ),
        "cannot contain fixed shield layers",
    )

    assert_raises(
        "V1.11 calculation limit beyond radial space rejected",
        ValueError,
        lambda: ShieldingScenario(
            scenario_id="radial_limit_test",
            description=("Scenario radial-space validation test."),
            calculation_mode="material_optimization",
            source=IsotopeSourceSpec(
                isotope_key="cs137",
                activity_bq=3.7e10,
            ),
            geometry=ConcentricSphericalGeometry(
                source_cavity_radius_cm=10.0,
                evaluation_radius_cm=100.0,
            ),
            candidate_material_keys=[
                "lead",
            ],
            target=FluxTarget(target_flux=100.0),
            constraints=DesignConstraints(),
            optimization_mode="minimum_mass",
            deterministic_settings=DeterministicSettings(
                calculation_max_thickness_cm=90.1
            ),
        ),
        "cannot exceed the radial space",
    )


def test_candidate_material_resolution() -> None:
    # Material resolution

    resolved_materials = resolve_candidate_materials(
        [
            "lead",
            "water",
        ]
    )

    assert_equal(
        "V1.11 material resolver preserves candidate count",
        len(resolved_materials),
        2,
    )

    assert_equal(
        "V1.11 material resolver preserves first material order",
        resolved_materials[0].key,
        "lead",
    )

    assert_equal(
        "V1.11 material resolver preserves second material order",
        resolved_materials[1].key,
        "water",
    )

    assert_raises(
        "V1.11 unknown material key rejected",
        ValueError,
        lambda: resolve_candidate_materials(
            [
                "lead",
                "unobtainium",
            ]
        ),
        "unknown material keys",
    )


def test_air_kerma_target_serialization() -> None:
    # Air-kerma scenario target serialization

    air_kerma_scenario = ShieldingScenario(
        scenario_id="cs137_air_kerma_serialization_test",
        description=(
            "V1.12 reproducible Cs-137 collision air-kerma scenario serialization test."
        ),
        calculation_mode="material_optimization",
        source=IsotopeSourceSpec(
            isotope_key="cs137",
            activity_bq=3.7e10,
        ),
        geometry=ConcentricSphericalGeometry(
            source_cavity_radius_cm=0.0,
            evaluation_radius_cm=100.0,
        ),
        candidate_material_keys=[
            "lead",
            "tungsten",
        ],
        target=AirKermaRateTarget(target_air_kerma_rate_microgy_per_h=1.0),
        constraints=DesignConstraints(
            max_thickness_cm=20.0,
            max_mass_per_area_g_per_cm2=120.0,
        ),
        optimization_mode="minimum_mass",
        deterministic_settings=(
            DeterministicSettings(
                apply_buildup=True,
                calculation_max_thickness_cm=20.0,
            )
        ),
    )

    assert_equal(
        "V1.12 scenario model accepts air-kerma target",
        isinstance(
            air_kerma_scenario.target,
            AirKermaRateTarget,
        ),
        True,
    )

    air_kerma_scenario_data = scenario_to_dict(air_kerma_scenario)

    assert_equal(
        "V1.12 scenario serializes explicit air-kerma target type",
        air_kerma_scenario_data["target"]["type"],
        "air_kerma_rate",
    )

    assert_close(
        "V1.12 scenario serializes air-kerma target in microGy per hour",
        air_kerma_scenario_data["target"]["target_air_kerma_rate_microgy_per_h"],
        1.0,
        1.0e-12,
    )

    reconstructed_air_kerma_scenario = scenario_from_dict(air_kerma_scenario_data)

    reconstructed_air_kerma_target = reconstructed_air_kerma_scenario.target

    if not isinstance(
        reconstructed_air_kerma_target,
        AirKermaRateTarget,
    ):
        raise AssertionError(
            "V1.12 scenario reconstruction did not preserve the air-kerma target type."
        )

    assert_close(
        "V1.12 reconstructed scenario preserves air-kerma target value",
        (reconstructed_air_kerma_target.target_air_kerma_rate_microgy_per_h),
        1.0,
        1.0e-12,
    )

    assert_equal(
        "V1.12 air-kerma scenario dictionary round trip preserves object",
        reconstructed_air_kerma_scenario,
        air_kerma_scenario,
    )

    with TemporaryDirectory() as (air_kerma_temporary_directory):
        air_kerma_scenario_path = (
            Path(air_kerma_temporary_directory) / "air_kerma_scenario.json"
        )

        saved_air_kerma_path = save_scenario(
            air_kerma_scenario,
            air_kerma_scenario_path,
        )

        assert_equal(
            "V1.12 air-kerma scenario save creates JSON file",
            saved_air_kerma_path.is_file(),
            True,
        )

        loaded_air_kerma_scenario = load_scenario(saved_air_kerma_path)

        assert_equal(
            "V1.12 air-kerma scenario JSON round trip preserves object",
            loaded_air_kerma_scenario,
            air_kerma_scenario,
        )

    invalid_air_kerma_target_data = json.loads(json.dumps(air_kerma_scenario_data))

    invalid_air_kerma_target_data["target"]["target_air_kerma_rate_microgy_per_h"] = 0.0

    assert_raises(
        "V1.12 scenario rejects nonpositive air-kerma target",
        ValueError,
        lambda: scenario_from_dict(invalid_air_kerma_target_data),
        "must be greater than zero",
    )
