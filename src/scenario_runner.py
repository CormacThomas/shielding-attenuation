# Reproducible deterministic scenario execution.
#
# This module converts backend-independent scenario specifications into
# validated runtime calculations.
#
# Supported calculation modes:
#
#   material_optimization
#       -> constrained material-selection workflow
#
#   fixed_shield_response
#       -> deterministic response of a completed physical shield
#
# This module does not:
#   - read or write JSON
#   - implement attenuation formulas directly
#   - generate OpenMC models


from typing import Any

from constraint_optimizer import (
    optimize_air_kerma_material_selection,
    optimize_material_selection,
)
from fixed_shield_models import (
    FixedShieldDeterministicResult,
)
from fixed_shield_response import (
    calculate_fixed_shield_response,
)
from material_library import (
    get_material_library,
)
from models import Material
from optimization_models import (
    DesignConstraints,
    OptimizedDesignResult,
    OptimizationMode,
)
from scenario_models import (
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    ShieldingScenario,
    SourceSpec,
    TargetSpec,
)
from source_library import (
    create_isotope_source,
)
from source_models import (
    IsotopeSource,
    ManualPhotonSource,
)
from target_models import (
    AirKermaRateTarget,
)


RuntimeSource = (
    ManualPhotonSource
    | IsotopeSource
)


ScenarioResult = (
    OptimizedDesignResult
    | FixedShieldDeterministicResult
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
    # readable. The optimizer later performs objective-specific ranking.

    material_library = (
        get_material_library()
    )

    selected_materials: list[
        Material
    ] = []

    unknown_material_keys: list[
        str
    ] = []

    for material_key in (
        candidate_material_keys
    ):
        if (
            material_key
            not in material_library
        ):
            unknown_material_keys.append(
                material_key
            )

            continue

        selected_materials.append(
            material_library[
                material_key
            ]
        )

    if len(
        unknown_material_keys
    ) > 0:
        formatted_keys = ", ".join(
            unknown_material_keys
        )

        raise ValueError(
            "Scenario contains unknown material keys: "
            f"{formatted_keys}"
        )

    return selected_materials


def require_material_optimization_inputs(
    scenario: ShieldingScenario,
) -> tuple[
    TargetSpec,
    DesignConstraints,
    OptimizationMode,
]:
    # Narrow fields that are optional on the shared scenario dataclass but
    # required by material-optimization mode.
    #
    # ShieldingScenario already validates these invariants. Rechecking them at
    # the execution boundary keeps this module independently defensive and
    # gives static type checkers non-optional values.

    if (
        scenario.calculation_mode
        != "material_optimization"
    ):
        raise ValueError(
            "Scenario runner expected "
            "material_optimization mode."
        )

    target = scenario.target
    constraints = scenario.constraints
    optimization_mode = (
        scenario.optimization_mode
    )

    if target is None:
        raise ValueError(
            "Material-optimization scenario is "
            "missing its target."
        )

    if constraints is None:
        raise ValueError(
            "Material-optimization scenario is "
            "missing its constraints."
        )

    if optimization_mode is None:
        raise ValueError(
            "Material-optimization scenario is missing "
            "its optimization mode."
        )

    return (
        target,
        constraints,
        optimization_mode,
    )


def run_material_optimization_scenario(
    scenario: ShieldingScenario,
) -> OptimizedDesignResult:
    # Run one reproducible material-optimization scenario.
    #
    # AirKermaRateTarget uses the explicit V1.12 air-kerma optimizer.
    # Legacy photon-number targets retain the compatible photon optimizer.

    (
        target,
        constraints,
        optimization_mode,
    ) = require_material_optimization_inputs(
        scenario
    )

    runtime_source = create_runtime_source(
        scenario.source
    )

    candidate_materials = (
        resolve_candidate_materials(
            scenario.candidate_material_keys
        )
    )

    settings = (
        scenario.deterministic_settings
    )

    if isinstance(
        target,
        AirKermaRateTarget,
    ):
        return (
            optimize_air_kerma_material_selection(
                source=runtime_source,
                materials=candidate_materials,
                detector_distance=(
                    scenario
                    .geometry
                    .evaluation_radius_cm
                ),
                target=target,
                constraints=constraints,
                optimization_mode=(
                    optimization_mode
                ),
                weights=(
                    scenario
                    .optimization_weights
                ),
                calculation_max_thickness=(
                    settings
                    .calculation_max_thickness_cm
                ),
                apply_buildup=(
                    settings.apply_buildup
                ),
            )
        )

    return optimize_material_selection(
        source=runtime_source,
        materials=candidate_materials,
        detector_distance=(
            scenario
            .geometry
            .evaluation_radius_cm
        ),
        target=target,
        constraints=constraints,
        optimization_mode=(
            optimization_mode
        ),
        weights=(
            scenario.optimization_weights
        ),
        calculation_max_thickness=(
            settings
            .calculation_max_thickness_cm
        ),
        apply_buildup=(
            settings.apply_buildup
        ),
    )


def run_fixed_shield_response_scenario(
    scenario: ShieldingScenario,
) -> FixedShieldDeterministicResult:
    # Run one completed physical shield through the deterministic response
    # pathway.

    if (
        scenario.calculation_mode
        != "fixed_shield_response"
    ):
        raise ValueError(
            "Scenario runner expected "
            "fixed_shield_response mode."
        )

    return calculate_fixed_shield_response(
        scenario
    )


def run_scenario(
    scenario: ShieldingScenario,
) -> Any:
    # Public dynamic scenario-routing entry point.
    #
    # The specialized functions above retain precise return annotations.
    # This router returns Any because ShieldingScenario is currently one shared
    # dataclass rather than a statically discriminated scenario-class hierarchy.
    # That preserves clean static checking for existing optimization callers
    # while still allowing runtime mode dispatch.

    if (
        scenario.calculation_mode
        == "material_optimization"
    ):
        return (
            run_material_optimization_scenario(
                scenario
            )
        )

    if (
        scenario.calculation_mode
        == "fixed_shield_response"
    ):
        return (
            run_fixed_shield_response_scenario(
                scenario
            )
        )

    raise ValueError(
        "Unsupported scenario calculation mode: "
        f"{scenario.calculation_mode}"
    )