# V1.11 reproducible scenario execution.
#
# This module converts backend-independent scenario specifications into the
# existing validated runtime objects used by the deterministic calculator.
#
# Responsibilities:
#   - convert source specifications into runtime source objects
#   - resolve stable material keys through the material library
#   - pass scenario inputs into the V1.09 optimizer
#
# This module does not:
#   - read or write JSON
#   - perform attenuation calculations directly
#   - contain optimization formulas
#   - generate OpenMC models


from constraint_optimizer import optimize_material_selection
from material_library import get_material_library
from models import Material
from optimization_models import OptimizedDesignResult
from scenario_models import (
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ShieldingScenario,
    SourceSpec,
)
from source_library import create_isotope_source
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
)


RuntimeSource = (
    ManualPhotonSource
    | IsotopeSource
)


def create_runtime_source(
    source_spec: SourceSpec,
) -> RuntimeSource:
    # Convert a serializable source specification into the existing runtime
    # source object expected by the deterministic calculation modules.

    if isinstance(
        source_spec,
        ManualPhotonSourceSpec,
    ):
        return ManualPhotonSource(
            energy=source_spec.photon_energy_mev,
            photon_rate=source_spec.photon_rate_per_s,
        )

    if isinstance(
        source_spec,
        IsotopeSourceSpec,
    ):
        return create_isotope_source(
            source_spec.isotope_key,
            source_spec.activity_bq,
        )

    raise ValueError(
        "Unsupported scenario source specification."
    )


def resolve_candidate_materials(
    candidate_material_keys: list[str],
) -> list[Material]:
    # Convert stable scenario material keys into the Material objects required
    # by the existing optimizer.
    #
    # Material order is preserved so scenario files remain deterministic and
    # readable. The optimizer performs its own objective-specific ranking later.

    material_library = get_material_library()
    selected_materials = []
    unknown_material_keys = []

    for material_key in candidate_material_keys:
        if material_key not in material_library:
            unknown_material_keys.append(
                material_key
            )

            continue

        selected_materials.append(
            material_library[material_key]
        )

    if len(unknown_material_keys) > 0:
        formatted_keys = ", ".join(
            unknown_material_keys
        )

        raise ValueError(
            "Scenario contains unknown material keys: "
            f"{formatted_keys}"
        )

    return selected_materials


def run_material_optimization_scenario(
    scenario: ShieldingScenario,
) -> OptimizedDesignResult:
    # Run one V1.11 material-optimization scenario through the existing
    # deterministic V1.09 optimization pathway.

    if scenario.calculation_mode != "material_optimization":
        raise ValueError(
            "Scenario runner expected material_optimization mode."
        )

    runtime_source = create_runtime_source(
        scenario.source
    )

    candidate_materials = resolve_candidate_materials(
        scenario.candidate_material_keys
    )

    settings = scenario.deterministic_settings

    return optimize_material_selection(
        source=runtime_source,
        materials=candidate_materials,
        detector_distance=(
            scenario.geometry.evaluation_radius_cm
        ),
        target=scenario.target,
        constraints=scenario.constraints,
        optimization_mode=scenario.optimization_mode,
        weights=scenario.optimization_weights,
        calculation_max_thickness=(
            settings.calculation_max_thickness_cm
        ),
        apply_buildup=settings.apply_buildup,
    )


def run_scenario(
    scenario: ShieldingScenario,
) -> OptimizedDesignResult:
    # Public V1.11 scenario execution entry point.
    #
    # Later versions can route additional calculation modes here without
    # changing the JSON loading or scenario-model layers.

    if scenario.calculation_mode == "material_optimization":
        return run_material_optimization_scenario(
            scenario
        )

    raise ValueError(
        "Unsupported scenario calculation mode."
    )