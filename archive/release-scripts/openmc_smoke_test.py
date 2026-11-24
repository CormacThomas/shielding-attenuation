# Minimal OpenMC photon-transport environment test.
#
# This script is intentionally independent of the shielding simulator.
# Its purpose is only to confirm that:
#
#   - OpenMC can access its cross-section library
#   - a fixed-source photon model can be constructed
#   - photon transport runs successfully
#   - a statepoint file is written
#   - tally results can be read through the Python API
#
# Run from the repository root inside the OpenMC Docker container:
#
#   python examples/openmc_smoke_test.py


from pathlib import Path
import shutil

import openmc


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "openmc_smoke_test_output"
)


def prepare_output_directory() -> None:
    # Remove output from an earlier smoke test so the statepoint path and
    # generated files always correspond to the current run.

    if OUTPUT_DIRECTORY.exists():
        shutil.rmtree(
            OUTPUT_DIRECTORY
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def create_model() -> openmc.Model:
    # Confirm that OpenMC knows where its continuous-energy data library is.

    cross_sections_path = openmc.config.get(
        "cross_sections"
    )

    if cross_sections_path is None:
        raise RuntimeError(
            "OpenMC cross-section library is not configured."
        )

    # ------------------------------------------------------------
    # Material
    # ------------------------------------------------------------

    lead = openmc.Material(
        name="Lead"
    )

    lead.set_density(
        "g/cm3",
        11.34,
    )

    lead.add_element(
        "Pb",
        1.0,
    )

    materials = openmc.Materials(
        [lead]
    )

    materials.cross_sections = (
        cross_sections_path
    )

    # ------------------------------------------------------------
    # Concentric spherical geometry
    # ------------------------------------------------------------
    #
    # Region 1:
    #   vacuum source cavity from 0 to 1 cm
    #
    # Region 2:
    #   Lead shield from 1 to 2 cm
    #
    # Region 3:
    #   outer vacuum region from 2 to 10 cm
    #
    # The outer 10 cm sphere is a vacuum boundary.

    cavity_surface = openmc.Sphere(
        r=1.0
    )

    shield_surface = openmc.Sphere(
        r=2.0
    )

    outer_boundary = openmc.Sphere(
        r=10.0,
        boundary_type="vacuum",
    )

    cavity_cell = openmc.Cell(
        name="Source cavity",
        region=-cavity_surface,
    )

    lead_shell_cell = openmc.Cell(
        name="Lead shell",
        fill=lead,
        region=(
            +cavity_surface
            & -shield_surface
        ),
    )

    outer_void_cell = openmc.Cell(
        name="Outer void",
        region=(
            +shield_surface
            & -outer_boundary
        ),
    )

    geometry = openmc.Geometry(
        [
            cavity_cell,
            lead_shell_cell,
            outer_void_cell,
        ]
    )

    # ------------------------------------------------------------
    # Photon source
    # ------------------------------------------------------------
    #
    # OpenMC energy inputs are in electronvolts.
    #
    # 661.657 keV = 661,657 eV

    source = openmc.IndependentSource(
        space=openmc.stats.Point(
            (0.0, 0.0, 0.0)
        ),
        angle=openmc.stats.Isotropic(),
        energy=openmc.stats.Discrete(
            [661_657.0],
            [1.0],
        ),
        particle="photon",
    )

    # ------------------------------------------------------------
    # Fixed-source transport settings
    # ------------------------------------------------------------

    settings = openmc.Settings()

    settings.run_mode = "fixed source"
    settings.source = source
    settings.photon_transport = True

    settings.batches = 5
    settings.particles = 2_000
    settings.seed = 12_345

    # Explicitly request a statepoint after the final batch.

    settings.statepoint = {
        "batches": [
            settings.batches
        ]
    }

    # ------------------------------------------------------------
    # Tally
    # ------------------------------------------------------------
    #
    # This is a raw cell flux tally used only to confirm that photons reach
    # the outer vacuum region and that tally data can be read successfully.
    #
    # It is not yet a detector model, air-kerma result, or benchmark quantity.

    outer_flux_tally = openmc.Tally(
        name="outer_void_photon_flux"
    )

    outer_flux_tally.filters = [
        openmc.CellFilter(
            outer_void_cell
        ),
        openmc.EnergyFilter(
            [
                1.0e3,
                700.0e3,
            ]
        ),
    ]

    outer_flux_tally.scores = [
        "flux"
    ]

    tallies = openmc.Tallies(
        [outer_flux_tally]
    )

    return openmc.Model(
        materials=materials,
        geometry=geometry,
        settings=settings,
        tallies=tallies,
    )


def run_smoke_test() -> None:
    prepare_output_directory()

    model = create_model()

    print()
    print("=" * 72)
    print("OPENMC PHOTON-TRANSPORT SMOKE TEST")
    print("=" * 72)
    print(
        "Output directory: "
        f"{OUTPUT_DIRECTORY}"
    )
    print(
        "OpenMC version:    "
        f"{openmc.__version__}"
    )
    print()

    statepoint_path = model.run(
        cwd=OUTPUT_DIRECTORY,
        threads=1,
    )

    if statepoint_path is None:
        raise RuntimeError(
            "OpenMC completed without returning a statepoint path."
        )

    statepoint_path = Path(
        statepoint_path
    )

    if not statepoint_path.is_file():
        raise RuntimeError(
            "OpenMC statepoint file was not created: "
            f"{statepoint_path}"
        )

    with openmc.StatePoint(
        statepoint_path
    ) as statepoint:
        if statepoint.run_mode != "fixed source":
            raise RuntimeError(
                "Unexpected OpenMC run mode: "
                f"{statepoint.run_mode}"
            )

        if not statepoint.photon_transport:
            raise RuntimeError(
                "Statepoint indicates that photon transport "
                "was not enabled."
            )

        tally = statepoint.get_tally(
            name="outer_void_photon_flux"
        )

        tally_mean = float(
            tally.mean.ravel()[0]
        )

        tally_standard_deviation = float(
            tally.std_dev.ravel()[0]
        )

        if tally_mean <= 0:
            raise RuntimeError(
                "Outer-region photon tally was not positive."
            )

        if tally_standard_deviation < 0:
            raise RuntimeError(
                "Tally standard deviation cannot be negative."
            )

        print()
        print("=" * 72)
        print("OPENMC SMOKE TEST PASSED")
        print("=" * 72)
        print(
            "Statepoint:       "
            f"{statepoint_path}"
        )
        print(
            "Run mode:         "
            f"{statepoint.run_mode}"
        )
        print(
            "Photon transport: "
            f"{statepoint.photon_transport}"
        )
        print(
            "Tally mean:       "
            f"{tally_mean:.8e}"
        )
        print(
            "Tally std. dev.:  "
            f"{tally_standard_deviation:.8e}"
        )
        print(
            "Realizations:     "
            f"{statepoint.n_realizations}"
        )
        print("=" * 72)
        print()


if __name__ == "__main__":
    run_smoke_test()