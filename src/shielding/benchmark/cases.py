# V1.14 benchmark-case resolution and core-matrix definitions.
#
# MFP-defined benchmark cases are converted into ordinary physical
# ShieldingScenario objects containing centimeter layer thicknesses.
#
# This module deliberately reuses the existing project XCOM interpolation
# and linear-attenuation calculation.


from __future__ import annotations

from shielding.benchmark.case_models import (
    BenchmarkCaseDefinition,
    ResolvedBenchmarkCase,
)
from shielding.data.isotopes import (
    get_available_isotopes,
)
from shielding.data.materials import (
    get_material_library,
)
from shielding.physics.attenuation import (
    calculate_mu,
    get_mu_over_p_at_energy,
)
from shielding.physics.models import (
    Material,
)
from shielding.scenarios.geometry import (
    ConcentricSphericalGeometry,
    ShieldLayerSpec,
)
from shielding.scenarios.models import (
    DeterministicSettings,
    IsotopeSourceSpec,
    ShieldingScenario,
)

V114_CORE_ACTIVITY_BQ = 3.7e10
CS137_REFERENCE_ENERGY_MEV = 0.661657

V114_CORE_SOURCE_CAVITY_RADIUS_CM = 1.0
V114_CORE_EVALUATION_RADIUS_CM = 100.0


def resolve_benchmark_case(
    definition: BenchmarkCaseDefinition,
    material_library: (dict[str, Material] | None) = None,
) -> ResolvedBenchmarkCase:
    if not isinstance(
        definition,
        BenchmarkCaseDefinition,
    ):
        raise ValueError(
            "Benchmark case resolution requires a BenchmarkCaseDefinition."
        )

    available_isotopes = set(get_available_isotopes())

    if definition.isotope_key not in available_isotopes:
        raise ValueError(
            f"Benchmark case contains an unknown isotope key: {definition.isotope_key}"
        )

    if material_library is None:
        material_library = get_material_library()

    if definition.material_key not in material_library:
        raise ValueError(
            "Benchmark case contains an unknown "
            "material key: "
            f"{definition.material_key}"
        )

    material = material_library[definition.material_key]

    if not (
        material.energy[0] <= definition.reference_energy_mev <= material.energy[-1]
    ):
        raise ValueError(
            "Benchmark reference energy is outside "
            f"the {material.name} attenuation-data "
            "range: "
            f"{definition.reference_energy_mev} MeV."
        )

    try:
        mu_over_rho_cm2_per_g = get_mu_over_p_at_energy(
            material,
            definition.reference_energy_mev,
        )

    except ValueError as error:
        raise ValueError(
            "Unable to resolve the benchmark mass "
            "attenuation coefficient for "
            f"{definition.case_id}."
        ) from error

    linear_attenuation_coefficient_per_cm = calculate_mu(
        mu_over_p=(mu_over_rho_cm2_per_g),
        density=material.density,
    )

    physical_thickness_cm = (
        definition.target_mean_free_paths / linear_attenuation_coefficient_per_cm
    )

    outer_shield_radius_cm = definition.source_cavity_radius_cm + physical_thickness_cm

    if outer_shield_radius_cm >= definition.evaluation_radius_cm:
        raise ValueError(
            "Benchmark shield reaches or exceeds "
            "the evaluation radius. "
            f"Case {definition.case_id} resolves to "
            f"{physical_thickness_cm:.12g} cm with "
            f"an outer radius of "
            f"{outer_shield_radius_cm:.12g} cm."
        )

    reconstructed_mean_free_paths = (
        linear_attenuation_coefficient_per_cm * physical_thickness_cm
    )

    scenario = ShieldingScenario(
        schema_version="1.1",
        scenario_id=definition.case_id,
        description=(
            "V1.14 deterministic-versus-OpenMC "
            "single-material benchmark with a centered "
            f"{definition.isotope_key} source and "
            f"{definition.target_mean_free_paths:g} MFP "
            f"of {material.name} at the explicit "
            f"{definition.reference_energy_mev:.8g} MeV "
            "reference energy."
        ),
        calculation_mode=("fixed_shield_response"),
        source=IsotopeSourceSpec(
            isotope_key=(definition.isotope_key),
            activity_bq=(definition.activity_bq),
        ),
        geometry=ConcentricSphericalGeometry(
            source_cavity_radius_cm=(definition.source_cavity_radius_cm),
            evaluation_radius_cm=(definition.evaluation_radius_cm),
            layers=[
                ShieldLayerSpec(
                    material_key=(definition.material_key),
                    thickness_cm=(physical_thickness_cm),
                )
            ],
        ),
        deterministic_settings=(
            DeterministicSettings(
                apply_buildup=(definition.apply_gp_buildup),
                calculation_max_thickness_cm=None,
            )
        ),
    )

    return ResolvedBenchmarkCase(
        definition=definition,
        material_name=material.name,
        mu_over_rho_cm2_per_g=(mu_over_rho_cm2_per_g),
        density_g_per_cm3=(material.density),
        linear_attenuation_coefficient_per_cm=(linear_attenuation_coefficient_per_cm),
        physical_thickness_cm=(physical_thickness_cm),
        reconstructed_mean_free_paths=(reconstructed_mean_free_paths),
        outer_shield_radius_cm=(outer_shield_radius_cm),
        scenario=scenario,
    )


def resolve_benchmark_cases(
    definitions: list[BenchmarkCaseDefinition],
) -> list[ResolvedBenchmarkCase]:
    if len(definitions) == 0:
        raise ValueError("Benchmark case collection cannot be empty.")

    case_ids = [definition.case_id for definition in definitions]

    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Benchmark case IDs must be unique.")

    material_library = get_material_library()

    return [
        resolve_benchmark_case(
            definition=definition,
            material_library=(material_library),
        )
        for definition in definitions
    ]


def create_v114_core_case_definitions() -> list[BenchmarkCaseDefinition]:
    def create_core_definition(
        *,
        case_id: str,
        material_key: str,
        target_mean_free_paths: float,
    ) -> BenchmarkCaseDefinition:
        return BenchmarkCaseDefinition(
            case_id=case_id,
            isotope_key="cs137",
            activity_bq=(V114_CORE_ACTIVITY_BQ),
            material_key=material_key,
            reference_energy_mev=(CS137_REFERENCE_ENERGY_MEV),
            target_mean_free_paths=(target_mean_free_paths),
            source_cavity_radius_cm=(V114_CORE_SOURCE_CAVITY_RADIUS_CM),
            evaluation_radius_cm=(V114_CORE_EVALUATION_RADIUS_CM),
            apply_gp_buildup=True,
        )

    return [
        create_core_definition(
            case_id="cs137_lead_01mfp",
            material_key="lead",
            target_mean_free_paths=1.0,
        ),
        create_core_definition(
            case_id="cs137_lead_05mfp",
            material_key="lead",
            target_mean_free_paths=5.0,
        ),
        create_core_definition(
            case_id="cs137_lead_10mfp",
            material_key="lead",
            target_mean_free_paths=10.0,
        ),
        create_core_definition(
            case_id=("cs137_tungsten_01mfp"),
            material_key="tungsten",
            target_mean_free_paths=1.0,
        ),
        create_core_definition(
            case_id=("cs137_tungsten_05mfp"),
            material_key="tungsten",
            target_mean_free_paths=5.0,
        ),
        create_core_definition(
            case_id=("cs137_concrete_ordinary_01mfp"),
            material_key=("concrete_ordinary"),
            target_mean_free_paths=1.0,
        ),
        create_core_definition(
            case_id=("cs137_concrete_ordinary_05mfp"),
            material_key=("concrete_ordinary"),
            target_mean_free_paths=5.0,
        ),
        create_core_definition(
            case_id="cs137_water_05mfp",
            material_key="water",
            target_mean_free_paths=5.0,
        ),
    ]


def resolved_benchmark_case_to_dict(
    resolved_case: ResolvedBenchmarkCase,
) -> dict[str, object]:
    definition = resolved_case.definition

    return {
        "case_id": definition.case_id,
        "isotope_key": (definition.isotope_key),
        "activity_bq": (definition.activity_bq),
        "material_key": (definition.material_key),
        "material_name": (resolved_case.material_name),
        "reference_energy_mev": (definition.reference_energy_mev),
        "target_mean_free_paths": (definition.target_mean_free_paths),
        "mu_over_rho_cm2_per_g": (resolved_case.mu_over_rho_cm2_per_g),
        "density_g_per_cm3": (resolved_case.density_g_per_cm3),
        "linear_attenuation_coefficient_per_cm": (
            resolved_case.linear_attenuation_coefficient_per_cm
        ),
        "physical_thickness_cm": (resolved_case.physical_thickness_cm),
        "reconstructed_mean_free_paths": (resolved_case.reconstructed_mean_free_paths),
        "source_cavity_radius_cm": (definition.source_cavity_radius_cm),
        "outer_shield_radius_cm": (resolved_case.outer_shield_radius_cm),
        "evaluation_radius_cm": (definition.evaluation_radius_cm),
        "apply_gp_buildup": (definition.apply_gp_buildup),
    }
