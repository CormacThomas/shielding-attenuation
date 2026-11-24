# V1.13 deterministic fixed-shield response calculations.
#
# This module evaluates the completed shield stored directly in a
# fixed_shield_response scenario.
#
# Workflow:
#
#   serializable scenario source
#       -> runtime source
#
#   geometry layer specifications
#       -> runtime Material and Layer objects
#
#   each photon line
#       -> narrow-beam ShieldingResult
#       -> explicit collision-air-kerma response
#       -> optional G-P exposure-buildup adjustment
#
#   all photon lines
#       -> aggregate FixedShieldDeterministicResult
#
# This module does not import OpenMC.


from shielding.data.materials import (
    get_material_library,
)
from shielding.physics.air_kerma import (
    aggregate_source_air_kerma_results,
    calculate_air_kerma_from_shielding_result,
)
from shielding.physics.layers import (
    calculate_shielding_result,
)
from shielding.physics.models import (
    Layer,
)
from shielding.physics.source_models import (
    ManualPhotonSource,
    PhotonLine,
)
from shielding.scenarios.fixed_shield_models import (
    FixedShieldDeterministicResult,
    FixedShieldPhotonLineResult,
)
from shielding.scenarios.models import (
    ShieldingScenario,
)
from shielding.scenarios.sources import RuntimeSource, create_runtime_source


def resolve_fixed_shield_layers(
    scenario: ShieldingScenario,
) -> list[Layer]:
    # Convert the ordered physical layer specifications into runtime Layer
    # objects using the authoritative project material library.

    material_library = get_material_library()

    layers: list[Layer] = []
    unknown_material_keys: list[str] = []

    for layer_spec in scenario.geometry.layers:
        material_key = layer_spec.material_key

        if material_key not in material_library:
            unknown_material_keys.append(material_key)

            continue

        layers.append(
            Layer(
                thickness=layer_spec.thickness_cm,
                material=material_library[material_key],
            )
        )

    if len(unknown_material_keys) > 0:
        formatted_keys = ", ".join(unknown_material_keys)

        raise ValueError(
            f"Fixed-shield scenario contains unknown material keys: {formatted_keys}"
        )

    if len(layers) == 0:
        # ShieldingScenario normally rejects this condition first.
        # Retaining the execution-boundary check makes this function safe
        # when called independently.
        raise ValueError(
            "Fixed-shield response requires at least one resolved shielding layer."
        )

    return layers


def get_runtime_source_lines(
    source: RuntimeSource,
) -> tuple[
    str,
    float | None,
    list[tuple[PhotonLine, float]],
]:
    # Convert a runtime source into:
    #
    #   source name
    #   optional activity
    #   photon line and physical photon-rate pairs

    if isinstance(
        source,
        ManualPhotonSource,
    ):
        return (
            "Manual Photon Source",
            None,
            [
                (
                    PhotonLine(
                        energy=source.energy,
                        intensity=1.0,
                    ),
                    source.photon_rate,
                )
            ],
        )

    source_lines = [
        (
            photon_line,
            (source.activity_bq * photon_line.intensity),
        )
        for photon_line in source.photon_lines
    ]

    return (
        source.name,
        source.activity_bq,
        source_lines,
    )


def calculate_fixed_shield_photon_line_result(
    photon_line: PhotonLine,
    photon_rate_per_s: float,
    layers: list[Layer],
    evaluation_radius_cm: float,
    apply_buildup: bool,
) -> FixedShieldPhotonLineResult:
    # Calculate attenuation and collision air kerma for one photon line
    # without discarding the detailed ShieldingResult.

    shielding_result = calculate_shielding_result(
        layers=layers,
        photon_energy=photon_line.energy,
        source_strength=photon_rate_per_s,
        detector_distance=evaluation_radius_cm,
    )

    air_kerma_result = calculate_air_kerma_from_shielding_result(
        photon_line, shielding_result, apply_buildup
    )

    return FixedShieldPhotonLineResult(
        photon_line=photon_line,
        photon_rate_per_s=photon_rate_per_s,
        shielding_result=shielding_result,
        air_kerma_result=air_kerma_result,
    )


def calculate_fixed_shield_response(
    scenario: ShieldingScenario,
) -> FixedShieldDeterministicResult:
    # Calculate the deterministic response of one completed fixed shield.

    if scenario.calculation_mode != "fixed_shield_response":
        raise ValueError(
            "Fixed-shield response calculation requires fixed_shield_response mode."
        )

    runtime_source = create_runtime_source(scenario.source)

    layers = resolve_fixed_shield_layers(scenario)

    (
        source_name,
        activity_bq,
        source_lines,
    ) = get_runtime_source_lines(runtime_source)

    line_results: list[FixedShieldPhotonLineResult] = []

    for (
        photon_line,
        photon_rate_per_s,
    ) in source_lines:
        line_result = calculate_fixed_shield_photon_line_result(
            photon_line=photon_line,
            photon_rate_per_s=(photon_rate_per_s),
            layers=layers,
            evaluation_radius_cm=(scenario.geometry.evaluation_radius_cm),
            apply_buildup=(scenario.deterministic_settings.apply_buildup),
        )

        line_results.append(line_result)

    source_air_kerma_result = aggregate_source_air_kerma_results(
        source_name=source_name,
        activity_bq=activity_bq,
        line_results=[line_result.air_kerma_result for line_result in line_results],
    )

    return FixedShieldDeterministicResult(
        scenario_id=scenario.scenario_id,
        source_name=source_name,
        activity_bq=activity_bq,
        geometry=scenario.geometry,
        line_results=line_results,
        source_air_kerma_result=(source_air_kerma_result),
        buildup_requested=(scenario.deterministic_settings.apply_buildup),
    )
