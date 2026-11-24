"""Verification cases migrated from the original validation runner."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from shielding.monte_carlo.models import (
    OpenMCEnergyBinResult,
    OpenMCRunManifest,
)
from shielding.monte_carlo.result_io import (
    openmc_run_manifest_to_dict,
    save_openmc_run_manifest,
)
from shielding.monte_carlo.settings import ElectronTreatment, OpenMCSettings
from shielding.monte_carlo.settings_io import (
    load_openmc_settings,
    openmc_settings_from_dict,
    openmc_settings_to_dict,
    save_openmc_settings,
)
from shielding.monte_carlo.statepoint import (
    validate_statepoint_metadata,
)
from tests.checks import (
    assert_close,
    assert_equal,
    assert_raises,
)


def test_settings_model() -> None:
    test_openmc_settings = OpenMCSettings(
        profile_name="V113_TEST",
        particles_per_batch=2000,
        batches=5,
        random_seed=12345,
        threads=1,
        energy_bin_boundaries_ev=[
            1000.0,
            100000.0,
            700000.0,
        ],
        electron_treatment="ttb",
        atomic_relaxation=True,
        photon_cutoff_energy_ev=1000.0,
        outer_boundary_radius_cm=110.0,
    )

    assert_equal(
        "V1.13 OpenMC settings normalize profile name",
        test_openmc_settings.profile_name,
        "v113_test",
    )

    assert_equal(
        "V1.13 OpenMC settings calculate total particles",
        test_openmc_settings.total_source_particles,
        10000,
    )

    assert_equal(
        "V1.13 OpenMC settings default statepoint to final batch",
        test_openmc_settings.statepoint_batches,
        [5],
    )

    assert_close(
        "V1.13 OpenMC settings preserve minimum spectrum energy",
        test_openmc_settings.minimum_spectrum_energy_ev,
        1000.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 OpenMC settings preserve maximum spectrum energy",
        test_openmc_settings.maximum_spectrum_energy_ev,
        700000.0,
        1.0e-12,
    )

    assert_equal(
        "V1.13 OpenMC settings preserve TTB treatment",
        test_openmc_settings.electron_treatment,
        "ttb",
    )

    assert_equal(
        "V1.13 OpenMC settings preserve atomic relaxation",
        test_openmc_settings.atomic_relaxation,
        True,
    )


def test_run_manifest() -> None:
    # OpenMC run-manifest model

    synthetic_manifest = OpenMCRunManifest(
        scenario_id="synthetic_v113_response",
        settings_profile_name="v113_test",
        openmc_version="0.15.0",
        python_version="3.13.5",
        cross_section_library=("/example/cross_sections.xml"),
        electron_treatment="ttb",
        atomic_relaxation=True,
        photon_cutoff_energy_ev=1000.0,
        particles_per_batch=2000,
        batches=5,
        total_source_particles=10000,
        random_seed=12345,
        threads=1,
        runtime_seconds=2.5,
        statepoint_filename="statepoint.5.h5",
        execution_timestamp_utc=("2026-07-28T18:00:00+00:00"),
        git_commit="abc123",
    )

    assert_equal(
        "V1.13 OpenMC manifest preserves total particles",
        synthetic_manifest.total_source_particles,
        10000,
    )

    assert_equal(
        "V1.13 OpenMC manifest preserves statepoint name",
        synthetic_manifest.statepoint_filename,
        "statepoint.5.h5",
    )


def test_invalid_openmc_models() -> None:
    # Invalid OpenMC model inputs

    assert_raises(
        "V1.13 OpenMC settings reject zero particles",
        ValueError,
        lambda: OpenMCSettings(
            profile_name="invalid_particles",
            particles_per_batch=0,
            batches=5,
            random_seed=12345,
            threads=1,
            energy_bin_boundaries_ev=[
                1000.0,
                700000.0,
            ],
        ),
        "positive integer",
    )

    assert_raises(
        "V1.13 OpenMC settings reject unsupported electron treatment",
        ValueError,
        lambda: OpenMCSettings(
            profile_name="invalid_electron_treatment",
            particles_per_batch=2000,
            batches=5,
            random_seed=12345,
            threads=1,
            energy_bin_boundaries_ev=[
                1000.0,
                700000.0,
            ],
            electron_treatment=cast(
                ElectronTreatment,
                "invalid",
            ),
        ),
        "Unsupported OpenMC electron treatment",
    )

    assert_raises(
        "V1.13 OpenMC settings reject unordered energy boundaries",
        ValueError,
        lambda: OpenMCSettings(
            profile_name="invalid_energy_order",
            particles_per_batch=2000,
            batches=5,
            random_seed=12345,
            threads=1,
            energy_bin_boundaries_ev=[
                1000.0,
                700000.0,
                100000.0,
            ],
        ),
        "strictly increasing",
    )

    assert_raises(
        "V1.13 OpenMC settings reject spectrum below cutoff",
        ValueError,
        lambda: OpenMCSettings(
            profile_name="invalid_cutoff",
            particles_per_batch=2000,
            batches=5,
            random_seed=12345,
            threads=1,
            energy_bin_boundaries_ev=[
                500.0,
                700000.0,
            ],
            photon_cutoff_energy_ev=1000.0,
        ),
        "below the photon cutoff",
    )

    assert_raises(
        "V1.13 OpenMC settings require final statepoint",
        ValueError,
        lambda: OpenMCSettings(
            profile_name="missing_final_statepoint",
            particles_per_batch=2000,
            batches=5,
            random_seed=12345,
            threads=1,
            energy_bin_boundaries_ev=[
                1000.0,
                700000.0,
            ],
            statepoint_batches=[
                2,
                4,
            ],
        ),
        "include the final batch",
    )

    assert_raises(
        "V1.13 OpenMC energy bin rejects inconsistent contribution",
        ValueError,
        lambda: OpenMCEnergyBinResult(
            lower_energy_ev=1000.0,
            upper_energy_ev=700000.0,
            raw_track_length_flux_mean_cm_per_source=1.0,
            raw_track_length_flux_standard_deviation_cm_per_source=0.1,
            volume_normalized_fluence_mean_per_cm2_per_source=0.01,
            volume_normalized_fluence_standard_deviation_per_cm2_per_source=0.001,
            physical_fluence_rate_mean_per_cm2_s=1.0,
            physical_fluence_rate_standard_deviation_per_cm2_s=0.1,
            response_coefficient_gy_cm2_per_photon=0.5,
            air_kerma_rate_contribution_gy_per_s=2.0,
        ),
        "must equal physical fluence rate",
    )

    assert_raises(
        "V1.13 OpenMC manifest rejects inconsistent particle total",
        ValueError,
        lambda: OpenMCRunManifest(
            scenario_id="invalid_manifest",
            settings_profile_name="v113_test",
            openmc_version="0.15.0",
            python_version="3.13.5",
            cross_section_library=("/example/cross_sections.xml"),
            electron_treatment="ttb",
            atomic_relaxation=True,
            photon_cutoff_energy_ev=1000.0,
            particles_per_batch=2000,
            batches=5,
            total_source_particles=9999,
            random_seed=12345,
            threads=1,
            runtime_seconds=2.5,
            statepoint_filename=("statepoint.5.h5"),
            execution_timestamp_utc=("2026-07-28T18:00:00+00:00"),
        ),
        "must equal particles per batch times batches",
    )


def test_settings_profiles() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    development_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_development.json"
    )

    production_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_production.json"
    )

    assert_equal(
        "V1.13 development OpenMC profile exists",
        development_openmc_settings_path.is_file(),
        True,
    )

    assert_equal(
        "V1.13 production OpenMC profile exists",
        production_openmc_settings_path.is_file(),
        True,
    )

    development_openmc_settings = load_openmc_settings(development_openmc_settings_path)

    production_openmc_settings = load_openmc_settings(production_openmc_settings_path)

    assert_equal(
        "V1.13 development OpenMC profile preserves name",
        development_openmc_settings.profile_name,
        "v113_development",
    )

    assert_equal(
        "V1.13 production OpenMC profile preserves name",
        production_openmc_settings.profile_name,
        "v113_production",
    )

    assert_equal(
        "V1.13 development OpenMC profile uses 100000 histories",
        (development_openmc_settings.total_source_particles),
        100000,
    )

    assert_equal(
        "V1.13 production OpenMC profile uses 5000000 histories",
        (production_openmc_settings.total_source_particles),
        5000000,
    )

    assert_equal(
        "V1.13 development OpenMC profile uses one thread",
        development_openmc_settings.threads,
        1,
    )

    assert_equal(
        "V1.13 production OpenMC profile uses four threads",
        production_openmc_settings.threads,
        4,
    )

    assert_equal(
        "V1.13 OpenMC profiles share random seed",
        development_openmc_settings.random_seed,
        production_openmc_settings.random_seed,
    )

    assert_equal(
        "V1.13 OpenMC profiles share electron treatment",
        development_openmc_settings.electron_treatment,
        production_openmc_settings.electron_treatment,
    )

    assert_equal(
        "V1.13 OpenMC profiles use TTB electron treatment",
        production_openmc_settings.electron_treatment,
        "ttb",
    )

    assert_equal(
        "V1.13 OpenMC profiles enable atomic relaxation",
        production_openmc_settings.atomic_relaxation,
        True,
    )

    assert_close(
        "V1.13 OpenMC profiles use 1 keV photon cutoff",
        (production_openmc_settings.photon_cutoff_energy_ev),
        1000.0,
        1.0e-12,
    )

    assert_close(
        "V1.13 OpenMC outer boundary radius",
        (production_openmc_settings.outer_boundary_radius_cm),
        110.0,
        1.0e-12,
    )

    assert_equal(
        "V1.13 OpenMC profiles share spectrum boundaries",
        (development_openmc_settings.energy_bin_boundaries_ev),
        (production_openmc_settings.energy_bin_boundaries_ev),
    )

    assert_equal(
        "V1.13 OpenMC spectrum has 43 boundaries",
        len(production_openmc_settings.energy_bin_boundaries_ev),
        43,
    )

    assert_equal(
        "V1.13 Cs-137 line falls in refined source-energy bin",
        (660000.0 < 661657.0 < 665000.0),
        True,
    )

    assert_equal(
        "V1.13 production OpenMC profile preserves checkpoints",
        (production_openmc_settings.statepoint_batches),
        [
            25,
            50,
            75,
            100,
        ],
    )

    assert_equal(
        "V1.13 development OpenMC profile writes final statepoint",
        (development_openmc_settings.statepoint_batches),
        [
            10,
        ],
    )


def test_settings_serialization() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_development.json"
    )
    production_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_production.json"
    )
    development_openmc_settings = load_openmc_settings(development_openmc_settings_path)
    production_openmc_settings = load_openmc_settings(production_openmc_settings_path)

    # OpenMC settings serialization

    development_openmc_data = openmc_settings_to_dict(development_openmc_settings)

    assert_equal(
        "V1.13 OpenMC settings serialize schema version",
        development_openmc_data["schema_version"],
        "1.0",
    )

    assert_equal(
        "V1.13 OpenMC settings serialize execution group",
        (development_openmc_data["execution"]["particles_per_batch"]),
        10000,
    )

    assert_equal(
        "V1.13 OpenMC settings serialize physics group",
        (development_openmc_data["physics"]["electron_treatment"]),
        "ttb",
    )

    assert_equal(
        "V1.13 OpenMC settings serialize tally boundaries",
        len(development_openmc_data["tallies"]["energy_bin_boundaries_ev"]),
        43,
    )

    reconstructed_openmc_settings = openmc_settings_from_dict(development_openmc_data)

    assert_equal(
        "V1.13 OpenMC settings dictionary round trip",
        reconstructed_openmc_settings,
        development_openmc_settings,
    )

    with TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        settings_roundtrip_path = temporary_path / "v113_openmc_settings.json"

        saved_settings_path = save_openmc_settings(
            production_openmc_settings,
            settings_roundtrip_path,
        )

        assert_equal(
            "V1.13 OpenMC settings save creates file",
            saved_settings_path.is_file(),
            True,
        )

        reloaded_openmc_settings = load_openmc_settings(settings_roundtrip_path)

        assert_equal(
            "V1.13 OpenMC settings file round trip",
            reloaded_openmc_settings,
            production_openmc_settings,
        )


def test_invalid_settings_json() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    development_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_development.json"
    )
    development_openmc_settings = load_openmc_settings(development_openmc_settings_path)
    development_openmc_data = openmc_settings_to_dict(development_openmc_settings)

    # Invalid OpenMC settings JSON

    invalid_schema_openmc_data = dict(development_openmc_data)

    invalid_schema_openmc_data["schema_version"] = "999.0"

    assert_raises(
        "V1.13 OpenMC settings reject unsupported schema",
        ValueError,
        lambda: openmc_settings_from_dict(invalid_schema_openmc_data),
        "Unsupported OpenMC settings schema version",
    )

    invalid_physics_openmc_data = dict(development_openmc_data)

    invalid_physics_openmc_data["physics"] = []

    assert_raises(
        "V1.13 OpenMC settings reject non-object physics settings",
        ValueError,
        lambda: openmc_settings_from_dict(invalid_physics_openmc_data),
        "must be a JSON object",
    )

    invalid_treatment_openmc_data = dict(development_openmc_data)

    invalid_treatment_openmc_data["physics"] = dict(development_openmc_data["physics"])

    invalid_treatment_openmc_data["physics"]["electron_treatment"] = "invalid"

    assert_raises(
        "V1.13 OpenMC settings JSON rejects invalid electron treatment",
        ValueError,
        lambda: openmc_settings_from_dict(invalid_treatment_openmc_data),
        "Unsupported OpenMC electron treatment",
    )

    invalid_boundaries_openmc_data = dict(development_openmc_data)

    invalid_boundaries_openmc_data["tallies"] = {
        "energy_bin_boundaries_ev": [
            1000.0,
            True,
            700000.0,
        ]
    }

    assert_raises(
        "V1.13 OpenMC settings JSON rejects Boolean energy boundary",
        ValueError,
        lambda: openmc_settings_from_dict(invalid_boundaries_openmc_data),
        "must contain only numerical values",
    )

    invalid_statepoints_openmc_data = dict(development_openmc_data)

    invalid_statepoints_openmc_data["output"] = {
        "statepoint_batches": [
            5.0,
            10,
        ]
    }

    assert_raises(
        "V1.13 OpenMC settings JSON rejects noninteger statepoint",
        ValueError,
        lambda: openmc_settings_from_dict(invalid_statepoints_openmc_data),
        "must contain only integers",
    )


def test_checkpoint_and_manifest() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    synthetic_manifest = OpenMCRunManifest(
        scenario_id="synthetic_v113_response",
        settings_profile_name="v113_test",
        openmc_version="0.15.0",
        python_version="3.13.5",
        cross_section_library=("/example/cross_sections.xml"),
        electron_treatment="ttb",
        atomic_relaxation=True,
        photon_cutoff_energy_ev=1000.0,
        particles_per_batch=2000,
        batches=5,
        total_source_particles=10000,
        random_seed=12345,
        threads=1,
        runtime_seconds=2.5,
        statepoint_filename="statepoint.5.h5",
        execution_timestamp_utc=("2026-07-28T18:00:00+00:00"),
        git_commit="abc123",
    )
    production_openmc_settings_path = (
        repository_root / "config" / "openmc" / "v113_production.json"
    )
    production_openmc_settings = load_openmc_settings(production_openmc_settings_path)

    class SyntheticCheckpointStatepoint:
        tallies_present = True
        photon_transport = True
        current_batch = 25
        n_particles = 50000

    validate_statepoint_metadata(
        statepoint=(SyntheticCheckpointStatepoint()),
        settings_profile=(production_openmc_settings),
        expected_batch=25,
    )

    assert_equal(
        "V1.13 statepoint metadata accepts configured checkpoint",
        True,
        True,
    )

    assert_raises(
        "V1.13 statepoint metadata rejects unconfigured checkpoint",
        ValueError,
        lambda: validate_statepoint_metadata(
            statepoint=(SyntheticCheckpointStatepoint()),
            settings_profile=(production_openmc_settings),
            expected_batch=30,
        ),
        "must be listed in the settings profile",
    )

    assert_raises(
        "V1.13 statepoint metadata rejects checkpoint mismatch",
        ValueError,
        lambda: validate_statepoint_metadata(
            statepoint=(SyntheticCheckpointStatepoint()),
            settings_profile=(production_openmc_settings),
            expected_batch=50,
        ),
        "does not match the expected checkpoint",
    )

    synthetic_manifest_data = openmc_run_manifest_to_dict(synthetic_manifest)

    assert_equal(
        "V1.13 run manifest preserves record type",
        synthetic_manifest_data["record_type"],
        "openmc_run_manifest",
    )

    assert_equal(
        "V1.13 run manifest preserves particle total",
        (synthetic_manifest_data["execution"]["total_source_particles"]),
        10000,
    )

    assert_equal(
        "V1.13 run manifest preserves cross-section library",
        (synthetic_manifest_data["nuclear_data"]["cross_section_library"]),
        "/example/cross_sections.xml",
    )

    with TemporaryDirectory() as temporary_directory:
        manifest_path = save_openmc_run_manifest(
            manifest=(synthetic_manifest),
            output_path=(Path(temporary_directory) / "run_manifest.json"),
        )

        assert_equal(
            "V1.13 run manifest JSON is created",
            manifest_path.is_file(),
            True,
        )

        manifest_text = manifest_path.read_text(encoding="utf-8")

        assert_equal(
            "V1.13 run manifest JSON contains OpenMC version",
            ('"openmc_version": "0.15.0"' in manifest_text),
            True,
        )
