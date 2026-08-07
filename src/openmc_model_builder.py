# Reusable OpenMC photon model construction.
#
# Introduced for the V1.13 matched benchmark and extended in V1.14 to support
# multiple benchmark materials.
#
# This module is the first project module that creates actual OpenMC Python
# objects. The OpenMC import is delayed until model construction begins so:
#
#   - the normal Windows validation suite remains OpenMC independent;
#   - this module can be imported without OpenMC installed;
#   - an informative error is raised only when the backend is invoked;
#   - Pylance does not report a missing static OpenMC import.
#
# Current V1.13 support:
#   - fixed_shield_response scenarios
#   - centered isotropic photon sources
#   - concentric spherical geometry
#   - natural Lead shielding
#   - vacuum evaluation shell
#   - outer vacuum boundary
#
# Tallies are intentionally added by a later module.


from dataclasses import dataclass
from importlib import import_module
import math
from pathlib import Path
from typing import Any


from benchmark_models import (
    SphericalEvaluationShell,
)
from fixed_shield_response import (
    create_fixed_shield_runtime_source,
    get_runtime_source_lines,
)
from material_library import (
    get_material_library,
)
from openmc_material_library import (
    get_openmc_material_definition,
)
from openmc_models import (
    OpenMCSettings,
)
from scenario_models import (
    ShieldingScenario,
)


EV_PER_MEV = 1.0e6


# Stable IDs make generated XML files and later statepoint parsing easier to
# inspect and reproduce.
SOURCE_CAVITY_SURFACE_ID = 101

FIRST_SHIELD_OUTER_SURFACE_ID = 201

EVALUATION_SHELL_INNER_SURFACE_ID = 301
EVALUATION_SHELL_OUTER_SURFACE_ID = 302
OUTER_BOUNDARY_SURFACE_ID = 303

SOURCE_CAVITY_CELL_ID = 1001
FIRST_SHIELD_CELL_ID = 1101
TRANSPORT_VOID_CELL_ID = 1201
EVALUATION_SHELL_CELL_ID = 1202
EXTERIOR_VOID_CELL_ID = 1203

FIRST_MATERIAL_ID = 2001



@dataclass
class OpenMCModelBuildResult:
    # Complete collection of OpenMC objects and normalization metadata created
    # from one backend-independent shielding scenario.
    #
    # OpenMC objects are typed as Any because OpenMC is dynamically imported
    # only in the Docker/OpenMC environment.

    model: Any

    source: Any

    source_cavity_cell: Any
    shield_cells: list[Any]
    transport_void_cell: Any
    evaluation_shell_cell: Any
    exterior_void_cell: Any

    outer_boundary_surface: Any

    materials_by_key: dict[
        str,
        Any,
    ]

    evaluation_shell: (
        SphericalEvaluationShell
    )

    physical_source_rate_per_s: float

    source_energies_ev: list[float]
    source_probabilities: list[float]

    cross_sections_path: str
    openmc_version: str

    def __post_init__(self) -> None:
        if len(self.shield_cells) == 0:
            raise ValueError(
                "OpenMC model build must contain at least "
                "one shielding cell."
            )

        if len(self.materials_by_key) == 0:
            raise ValueError(
                "OpenMC model build must contain at least "
                "one material."
            )

        if self.physical_source_rate_per_s <= 0:
            raise ValueError(
                "OpenMC model physical source rate must "
                "be greater than zero."
            )

        if len(self.source_energies_ev) == 0:
            raise ValueError(
                "OpenMC model source must contain at least "
                "one photon energy."
            )

        if (
            len(self.source_energies_ev)
            != len(self.source_probabilities)
        ):
            raise ValueError(
                "OpenMC source energies and probabilities "
                "must have equal lengths."
            )

        for energy_ev in self.source_energies_ev:
            if energy_ev <= 0:
                raise ValueError(
                    "OpenMC source energies must be "
                    "greater than zero."
                )

        for probability in self.source_probabilities:
            if probability < 0:
                raise ValueError(
                    "OpenMC source probabilities cannot "
                    "be negative."
                )

        probability_sum = sum(
            self.source_probabilities
        )

        if not math.isclose(
            probability_sum,
            1.0,
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise ValueError(
                "OpenMC source probabilities must sum to one."
            )

        if self.cross_sections_path.strip() == "":
            raise ValueError(
                "OpenMC cross-section path cannot be empty."
            )

        if self.openmc_version.strip() == "":
            raise ValueError(
                "OpenMC version cannot be empty."
            )


def load_openmc_module() -> Any:
    # Import OpenMC only when the backend is actually invoked.

    try:
        return import_module(
            "openmc"
        )

    except ModuleNotFoundError as error:
        raise RuntimeError(
            "OpenMC is not installed in the current Python "
            "environment. Run this model builder inside the "
            "configured OpenMC Docker environment."
        ) from error


def get_configured_cross_sections_path(
    openmc_module: Any,
) -> str:
    # Require the same continuous-energy cross-section configuration already
    # checked by the independent OpenMC smoke test.

    cross_sections_value = (
        openmc_module
        .config
        .get(
            "cross_sections"
        )
    )

    if cross_sections_value is None:
        raise RuntimeError(
            "OpenMC cross-section library is not configured."
        )

    cross_sections_path = Path(
        cross_sections_value
    ).expanduser()

    if not cross_sections_path.is_file():
        raise RuntimeError(
            "Configured OpenMC cross-section file does "
            "not exist: "
            f"{cross_sections_path}"
        )

    return str(
        cross_sections_path
    )


def create_openmc_materials(
    openmc_module: Any,
    scenario: ShieldingScenario,
    cross_sections_path: str,
) -> tuple[
    Any,
    dict[str, Any],
]:
    # Convert each unique scenario material into its explicitly supported
    # OpenMC material composition.
    #
    # Repeated physical layers using the same material reuse one OpenMC
    # Material object.

    project_material_library = (
        get_material_library()
    )

    materials_by_key: dict[
        str,
        Any,
    ] = {}

    for layer_spec in (
        scenario.geometry.layers
    ):
        material_key = (
            layer_spec.material_key
        )

        if (
            material_key
            in materials_by_key
        ):
            continue

        if (
            material_key
            not in project_material_library
        ):
            raise ValueError(
                "OpenMC model contains an unknown project "
                "material key: "
                f"{material_key}"
            )

        project_material = (
            project_material_library[
                material_key
            ]
        )

        openmc_material_definition = (
            get_openmc_material_definition(
                material_key
            )
        )

        material_id = (
            FIRST_MATERIAL_ID
            + len(materials_by_key)
        )

        openmc_material = (
            openmc_module.Material(
                material_id=material_id,
                name=project_material.name,
            )
        )

        for component in (
            openmc_material_definition
            .normalized_components
        ):
            openmc_material.add_element(
                component.element_symbol,
                component.fraction,
                percent_type=(
                    openmc_material_definition
                    .fraction_type
                ),
            )

        openmc_material.set_density(
            "g/cm3",
            project_material.density,
        )

        materials_by_key[
            material_key
        ] = openmc_material

    if len(materials_by_key) == 0:
        raise ValueError(
            "OpenMC model requires at least one "
            "shielding material."
        )

    materials = openmc_module.Materials(
        list(
            materials_by_key.values()
        )
    )

    materials.cross_sections = (
        cross_sections_path
    )

    return (
        materials,
        materials_by_key,
    )


def create_openmc_photon_source(
    openmc_module: Any,
    scenario: ShieldingScenario,
) -> tuple[
    Any,
    float,
    list[float],
    list[float],
]:
    # Convert the scenario source into a normalized OpenMC photon source.
    #
    # OpenMC samples one source particle per history. The physical emission
    # rate is therefore retained separately and applied during statepoint
    # result normalization.
    #
    # Photon lines with the same energy are combined before probabilities are
    # normalized.

    runtime_source = (
        create_fixed_shield_runtime_source(
            scenario
        )
    )

    (
        _source_name,
        _activity_bq,
        source_lines,
    ) = get_runtime_source_lines(
        runtime_source
    )

    photon_rate_by_energy_ev: dict[
        float,
        float,
    ] = {}

    for (
        photon_line,
        photon_rate_per_s,
    ) in source_lines:
        if photon_rate_per_s < 0:
            raise ValueError(
                "OpenMC photon-line emission rate "
                "cannot be negative."
            )

        if photon_rate_per_s == 0:
            continue

        energy_ev = (
            photon_line.energy
            * EV_PER_MEV
        )

        photon_rate_by_energy_ev[
            energy_ev
        ] = (
            photon_rate_by_energy_ev.get(
                energy_ev,
                0.0,
            )
            + photon_rate_per_s
        )

    if len(photon_rate_by_energy_ev) == 0:
        raise ValueError(
            "OpenMC photon source requires at least "
            "one positive-emission-rate line."
        )

    source_energies_ev = sorted(
        photon_rate_by_energy_ev
    )

    line_rates_per_s = [
        photon_rate_by_energy_ev[
            energy_ev
        ]
        for energy_ev in source_energies_ev
    ]

    physical_source_rate_per_s = sum(
        line_rates_per_s
    )

    if physical_source_rate_per_s <= 0:
        raise ValueError(
            "OpenMC physical photon source rate must "
            "be greater than zero."
        )

    source_probabilities = [
        line_rate_per_s
        / physical_source_rate_per_s
        for line_rate_per_s in line_rates_per_s
    ]

    source = openmc_module.IndependentSource(
        space=openmc_module.stats.Point(
            (
                0.0,
                0.0,
                0.0,
            )
        ),
        angle=openmc_module.stats.Isotropic(),
        energy=openmc_module.stats.Discrete(
            source_energies_ev,
            source_probabilities,
        ),
        particle="photon",
    )

    return (
        source,
        physical_source_rate_per_s,
        source_energies_ev,
        source_probabilities,
    )


def create_openmc_transport_settings(
    openmc_module: Any,
    source: Any,
    settings_profile: OpenMCSettings,
) -> Any:
    # Convert the pure-Python OpenMC settings profile into the actual OpenMC
    # Settings object.
    #
    # Thread count is not written into settings.xml. It is supplied to
    # Model.run() when the model is executed.

    settings = openmc_module.Settings()

    settings.run_mode = (
        "fixed source"
    )

    settings.source = source

    settings.photon_transport = True

    settings.electron_treatment = (
        settings_profile
        .electron_treatment
    )

    settings.atomic_relaxation = (
        settings_profile
        .atomic_relaxation
    )

    settings.cutoff = {
        "energy_photon": (
            settings_profile
            .photon_cutoff_energy_ev
        )
    }

    settings.batches = (
        settings_profile.batches
    )

    settings.particles = (
        settings_profile
        .particles_per_batch
    )

    settings.seed = (
        settings_profile.random_seed
    )

    settings.statepoint = {
        "batches": list(
            settings_profile
            .statepoint_batches
        )
    }

    # Ensure statepoint uncertainties retain the standard-deviation convention
    # expected by OpenMCResponseResult.
    settings.confidence_intervals = False

    return settings


def build_openmc_benchmark_model(
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    evaluation_shell_thickness_cm: float = 1.0,
) -> OpenMCModelBuildResult:
    # Construct a complete untallied OpenMC benchmark model.
    # Construct the complete untallied V1.13 OpenMC model.
    #
    # The evaluation shell is vacuum. It serves as a nonperturbing photon
    # fluence scoring region. Dry-air collision air kerma will later be
    # calculated by applying the validated response function to the flux tally,
    # rather than by filling the region with physical air.

    if (
        scenario.calculation_mode
        != "fixed_shield_response"
    ):
        raise ValueError(
            "OpenMC model construction requires "
            "fixed_shield_response mode."
        )

    geometry_spec = (
        scenario.geometry
    )

    if (
        geometry_spec
        .source_cavity_radius_cm
        <= 0
    ):
        raise ValueError(
            "OpenMC benchmark models require a positive "
            "source-cavity radius."
        )

    if len(
        geometry_spec.layers
    ) == 0:
        raise ValueError(
            "OpenMC benchmark models require at least "
            "one fixed shielding layer."
        )

    evaluation_shell = (
        SphericalEvaluationShell(
            center_radius_cm=(
                geometry_spec
                .evaluation_radius_cm
            ),
            thickness_cm=(
                evaluation_shell_thickness_cm
            ),
        )
    )

    if (
        evaluation_shell.inner_radius_cm
        <= geometry_spec.outer_shield_radius_cm
    ):
        raise ValueError(
            "OpenMC evaluation shell must be entirely "
            "beyond the outer shield radius."
        )

    if (
        settings_profile
        .outer_boundary_radius_cm
        <= evaluation_shell.outer_radius_cm
    ):
        raise ValueError(
            "OpenMC outer boundary must be beyond the "
            "evaluation shell."
        )

    openmc_module = (
        load_openmc_module()
    )

    cross_sections_path = (
        get_configured_cross_sections_path(
            openmc_module
        )
    )

    (
        materials,
        materials_by_key,
    ) = create_openmc_materials(
        openmc_module=openmc_module,
        scenario=scenario,
        cross_sections_path=(
            cross_sections_path
        ),
    )

    (
        source,
        physical_source_rate_per_s,
        source_energies_ev,
        source_probabilities,
    ) = create_openmc_photon_source(
        openmc_module=openmc_module,
        scenario=scenario,
    )

    # ------------------------------------------------------------
    # Concentric spherical surfaces
    # ------------------------------------------------------------

    source_cavity_surface = (
        openmc_module.Sphere(
            surface_id=(
                SOURCE_CAVITY_SURFACE_ID
            ),
            name="v113_source_cavity_boundary",
            r=(
                geometry_spec
                .source_cavity_radius_cm
            ),
        )
    )

    shield_shell_specs = (
        geometry_spec.create_shells()
    )

    shield_outer_surfaces: list[
        Any
    ] = []

    for shell_spec in shield_shell_specs:
        shield_outer_surfaces.append(
            openmc_module.Sphere(
                surface_id=(
                    FIRST_SHIELD_OUTER_SURFACE_ID
                    + shell_spec.layer_index
                ),
                name=(
                    "v113_shield_layer_"
                    f"{shell_spec.layer_index + 1}"
                    "_outer_boundary"
                ),
                r=shell_spec.outer_radius_cm,
            )
        )

    evaluation_shell_inner_surface = (
        openmc_module.Sphere(
            surface_id=(
                EVALUATION_SHELL_INNER_SURFACE_ID
            ),
            name=(
                "v113_evaluation_shell_inner_boundary"
            ),
            r=(
                evaluation_shell.inner_radius_cm
            ),
        )
    )

    evaluation_shell_outer_surface = (
        openmc_module.Sphere(
            surface_id=(
                EVALUATION_SHELL_OUTER_SURFACE_ID
            ),
            name=(
                "v113_evaluation_shell_outer_boundary"
            ),
            r=(
                evaluation_shell.outer_radius_cm
            ),
        )
    )

    outer_boundary_surface = (
        openmc_module.Sphere(
            surface_id=(
                OUTER_BOUNDARY_SURFACE_ID
            ),
            name="v113_outer_vacuum_boundary",
            r=(
                settings_profile
                .outer_boundary_radius_cm
            ),
            boundary_type="vacuum",
        )
    )

    # ------------------------------------------------------------
    # Concentric spherical cells
    # ------------------------------------------------------------

    source_cavity_cell = (
        openmc_module.Cell(
            cell_id=(
                SOURCE_CAVITY_CELL_ID
            ),
            name="v113_source_cavity",
            region=(
                -source_cavity_surface
            ),
        )
    )

    shield_cells: list[
        Any
    ] = []

    current_inner_surface = (
        source_cavity_surface
    )

    for (
        layer_index,
        (
            layer_spec,
            outer_surface,
        ),
    ) in enumerate(
        zip(
            geometry_spec.layers,
            shield_outer_surfaces,
            strict=True,
        )
    ):
        material = materials_by_key[
            layer_spec.material_key
        ]

        shield_cell = (
            openmc_module.Cell(
                cell_id=(
                    FIRST_SHIELD_CELL_ID
                    + layer_index
                ),
                name=(
                    "v113_shield_layer_"
                    f"{layer_index + 1}_"
                    f"{layer_spec.material_key}"
                ),
                fill=material,
                region=(
                    +current_inner_surface
                    & -outer_surface
                ),
            )
        )

        shield_cells.append(
            shield_cell
        )

        current_inner_surface = (
            outer_surface
        )

    transport_void_cell = (
        openmc_module.Cell(
            cell_id=(
                TRANSPORT_VOID_CELL_ID
            ),
            name="v113_transport_void",
            region=(
                +current_inner_surface
                & -evaluation_shell_inner_surface
            ),
        )
    )

    evaluation_shell_cell = (
        openmc_module.Cell(
            cell_id=(
                EVALUATION_SHELL_CELL_ID
            ),
            name="v113_evaluation_shell",
            region=(
                +evaluation_shell_inner_surface
                & -evaluation_shell_outer_surface
            ),
        )
    )

    exterior_void_cell = (
        openmc_module.Cell(
            cell_id=(
                EXTERIOR_VOID_CELL_ID
            ),
            name="v113_exterior_void",
            region=(
                +evaluation_shell_outer_surface
                & -outer_boundary_surface
            ),
        )
    )

    all_cells = [
        source_cavity_cell,
        *shield_cells,
        transport_void_cell,
        evaluation_shell_cell,
        exterior_void_cell,
    ]

    geometry = openmc_module.Geometry(
        all_cells
    )

    settings = (
        create_openmc_transport_settings(
            openmc_module=openmc_module,
            source=source,
            settings_profile=(
                settings_profile
            ),
        )
    )

    model = openmc_module.Model(
        materials=materials,
        geometry=geometry,
        settings=settings,
    )

    return OpenMCModelBuildResult(
        model=model,
        source=source,
        source_cavity_cell=(
            source_cavity_cell
        ),
        shield_cells=shield_cells,
        transport_void_cell=(
            transport_void_cell
        ),
        evaluation_shell_cell=(
            evaluation_shell_cell
        ),
        exterior_void_cell=(
            exterior_void_cell
        ),
        outer_boundary_surface=(
            outer_boundary_surface
        ),
        materials_by_key=(
            materials_by_key
        ),
        evaluation_shell=(
            evaluation_shell
        ),
        physical_source_rate_per_s=(
            physical_source_rate_per_s
        ),
        source_energies_ev=(
            source_energies_ev
        ),
        source_probabilities=(
            source_probabilities
        ),
        cross_sections_path=(
            cross_sections_path
        ),
        openmc_version=str(
            openmc_module.__version__
        ),
    )


def build_openmc_v113_model(
    scenario: ShieldingScenario,
    settings_profile: OpenMCSettings,
    evaluation_shell_thickness_cm: float = 1.0,
) -> OpenMCModelBuildResult:
    # Backward-compatible V1.13 entry point.
    #
    # New benchmark-study code should call
    # build_openmc_benchmark_model() directly.

    return build_openmc_benchmark_model(
        scenario=scenario,
        settings_profile=(
            settings_profile
        ),
        evaluation_shell_thickness_cm=(
            evaluation_shell_thickness_cm
        ),
    )