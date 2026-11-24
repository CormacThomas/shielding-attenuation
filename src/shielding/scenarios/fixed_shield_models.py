# V1.13 fixed-shield deterministic result models.
#
# These models preserve both parts of each deterministic photon-line
# calculation:
#
#   1. the complete narrow-beam shielding result;
#   2. the explicit collision-air-kerma response result.
#
# Keeping both results allows later OpenMC comparisons to inspect:
#   - attenuation coefficients
#   - mean free paths
#   - transmission
#   - point photon fluence
#   - collision air kerma
#   - G-P exposure buildup
#
# The matched evaluation-shell average will be added by the benchmark
# comparison layer. The existing V1.12 response remains a point result at the
# scenario evaluation radius.


import math
from dataclasses import dataclass

from shielding.physics.models import (
    Layer,
    ShieldingResult,
)
from shielding.physics.response_models import (
    BuildupStatus,
    PhotonLineAirKermaResult,
    SourceAirKermaResult,
)
from shielding.physics.source_models import (
    PhotonLine,
)
from shielding.scenarios.geometry import (
    ConcentricSphericalGeometry,
)


def values_match(
    first_value: float,
    second_value: float,
) -> bool:
    # Compare values that should represent the same calculated or input
    # quantity.
    #
    # A tight tolerance permits harmless floating-point representation
    # differences without allowing inconsistent result objects.

    return math.isclose(
        first_value,
        second_value,
        rel_tol=1.0e-12,
        abs_tol=1.0e-15,
    )


@dataclass
class FixedShieldPhotonLineResult:
    # Complete deterministic result for one photon line through a completed
    # fixed shield.
    #
    # photon_line:
    #   Original photon energy and emission intensity.
    #
    # photon_rate_per_s:
    #   Physical photon emission rate for this line.
    #
    # shielding_result:
    #   Narrow-beam attenuation, MFP, transmission, and point fluence result.
    #
    # air_kerma_result:
    #   Explicit V1.12 collision-air-kerma response for the same line.

    photon_line: PhotonLine
    photon_rate_per_s: float

    shielding_result: ShieldingResult
    air_kerma_result: PhotonLineAirKermaResult

    def __post_init__(self) -> None:
        if self.photon_rate_per_s < 0:
            raise ValueError("Fixed-shield photon rate cannot be negative.")

        if not values_match(
            self.photon_line.energy,
            self.shielding_result.photon_energy,
        ):
            raise ValueError(
                "Fixed-shield photon-line energy must match the shielding result."
            )

        if not values_match(
            self.photon_line.energy,
            self.air_kerma_result.photon_energy_mev,
        ):
            raise ValueError(
                "Fixed-shield photon-line energy must match the air-kerma result."
            )

        if not values_match(
            self.photon_line.intensity,
            self.air_kerma_result.emission_intensity,
        ):
            raise ValueError(
                "Fixed-shield photon-line intensity must match the air-kerma result."
            )

        if not values_match(
            self.photon_rate_per_s,
            self.shielding_result.source_strength,
        ):
            raise ValueError(
                "Fixed-shield photon rate must match the "
                "shielding-result source strength."
            )

        if not values_match(
            self.photon_rate_per_s,
            self.air_kerma_result.photon_rate_per_s,
        ):
            raise ValueError(
                "Fixed-shield photon rate must match the air-kerma result."
            )

        if not values_match(
            self.shielding_result.uncollided_flux,
            (self.air_kerma_result.uncollided_photon_fluence_rate_per_cm2_s),
        ):
            raise ValueError(
                "Fixed-shield shielding and air-kerma fluence rates must match."
            )


@dataclass
class FixedShieldDeterministicResult:
    # Complete deterministic response of one fixed shielding scenario.
    #
    # The source-level air-kerma result contains the aggregate response.
    # The fixed-shield line results preserve the detailed attenuation result
    # used to create every response contribution.
    #
    # The response stored here is evaluated at the point radius contained in
    # geometry.evaluation_radius_cm. A later V1.13 comparison layer will derive
    # the matched evaluation-shell average from this result.

    scenario_id: str
    source_name: str
    activity_bq: float | None

    geometry: ConcentricSphericalGeometry

    line_results: list[FixedShieldPhotonLineResult]

    source_air_kerma_result: SourceAirKermaResult

    buildup_requested: bool

    def __post_init__(self) -> None:
        self.scenario_id = self.scenario_id.lower().strip()

        self.source_name = self.source_name.strip()

        if self.scenario_id == "":
            raise ValueError("Fixed-shield result scenario ID cannot be empty.")

        if self.source_name == "":
            raise ValueError("Fixed-shield result source name cannot be empty.")

        if self.activity_bq is not None and self.activity_bq < 0:
            raise ValueError("Fixed-shield result activity cannot be negative.")

        if len(self.geometry.layers) == 0:
            raise ValueError(
                "Fixed-shield result geometry must contain at least one shield layer."
            )

        if len(self.line_results) == 0:
            raise ValueError(
                "Fixed-shield result must contain at least one photon-line result."
            )

        if self.source_air_kerma_result.source_name != self.source_name:
            raise ValueError(
                "Fixed-shield source name must match the source air-kerma result."
            )

        if self.source_air_kerma_result.activity_bq != self.activity_bq:
            raise ValueError(
                "Fixed-shield activity must match the source air-kerma result."
            )

        if len(self.source_air_kerma_result.line_results) != len(self.line_results):
            raise ValueError(
                "Fixed-shield line count must match the source air-kerma result."
            )

        source_buildup_status = self.source_air_kerma_result.buildup_status

        if self.buildup_requested:
            if source_buildup_status == "not_requested":
                raise ValueError(
                    "Requested fixed-shield buildup cannot have not-requested status."
                )

        elif source_buildup_status != "not_requested":
            raise ValueError(
                "Unrequested fixed-shield buildup must have not-requested status."
            )

        for (
            fixed_line_result,
            source_line_result,
        ) in zip(
            self.line_results,
            (self.source_air_kerma_result.line_results),
            strict=True,
        ):
            if fixed_line_result.air_kerma_result != source_line_result:
                raise ValueError(
                    "Fixed-shield line result must match "
                    "the aggregated source line result."
                )

            runtime_layers = fixed_line_result.shielding_result.layers

            if len(runtime_layers) != len(self.geometry.layers):
                raise ValueError(
                    "Fixed-shield runtime layer count must match the scenario geometry."
                )

            for (
                runtime_layer,
                layer_spec,
            ) in zip(
                runtime_layers,
                self.geometry.layers,
                strict=True,
            ):
                if runtime_layer.material.key != layer_spec.material_key:
                    raise ValueError(
                        "Fixed-shield runtime material must "
                        "match the scenario geometry."
                    )

                if not values_match(
                    runtime_layer.thickness,
                    layer_spec.thickness_cm,
                ):
                    raise ValueError(
                        "Fixed-shield runtime thickness must "
                        "match the scenario geometry."
                    )

    @property
    def layers(self) -> list[Layer]:
        # Every photon line uses the same physical shield.
        # Return a new list so callers cannot replace the stored list itself.

        return list(self.line_results[0].shielding_result.layers)

    @property
    def evaluation_radius_cm(self) -> float:
        return self.geometry.evaluation_radius_cm

    @property
    def total_shield_thickness_cm(self) -> float:
        return self.geometry.total_shield_thickness_cm

    @property
    def total_uncollided_photon_fluence_rate_per_cm2_s(
        self,
    ) -> float:
        return (
            self.source_air_kerma_result.total_uncollided_photon_fluence_rate_per_cm2_s
        )

    @property
    def total_uncollided_collision_air_kerma_rate_gy_per_s(
        self,
    ) -> float:
        return self.source_air_kerma_result.total_uncollided_collision_air_kerma_rate_gy_per_s

    @property
    def buildup_status(self) -> BuildupStatus:
        return self.source_air_kerma_result.buildup_status

    @property
    def total_buildup_adjusted_collision_air_kerma_rate_gy_per_s(
        self,
    ) -> float | None:
        return self.source_air_kerma_result.total_buildup_adjusted_collision_air_kerma_rate_gy_per_s

    @property
    def warnings(self) -> list[str]:
        return list(self.source_air_kerma_result.warnings)
