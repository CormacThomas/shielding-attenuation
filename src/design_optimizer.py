# V1.08 single-material design optimizer.
#
# This module sits above the V1.07 minimum-thickness calculator.
# V1.07 answers:
#   "How much of this selected material is required?"
#
# V1.08 answers:
#   "How much of each candidate material is required for the same source and target?"
#
# Important design choice:
# Failed materials are not hidden. If a material cannot meet the target within the
# allowed thickness, the optimizer stores a FAILED candidate with the reason.
# This makes the comparison table more honest and useful for engineering design.


from dataclasses import dataclass, field
from models import Material
from source_models import IsotopeSource, ManualPhotonSource
from target_models import (
    AirKermaMinimumThicknessResult,
    AirKermaRateTarget,
    FluxTarget,
    MinimumThicknessResult,
    ReductionFactorTarget,
    TransmissionTarget,
)
from thickness_calculator import (
    calculate_air_kerma_minimum_thickness,
    calculate_isotope_minimum_thickness,
    calculate_manual_minimum_thickness,
    get_target_description,
)


Target = TransmissionTarget | ReductionFactorTarget | FluxTarget
Source = ManualPhotonSource | IsotopeSource


@dataclass
class MaterialDesignCandidate:
    # Result for one material in a material comparison calculation.
    #
    # A candidate can either PASS or FAILED.
    #
    # Engineering constraint rejection is handled separately by the V1.09
    # constraint optimizer
    #
    # PASS means:
    #   - the material reached the requested target
    #   - required_thickness, final_flux, and final_transmission are available
    #
    # FAILED means:
    #   - the material calculation could not produce a usable design within the
    #     calculation search bounds or current model limitations
    #   - the failure_reason explains why
    #
    # Failed candidates are intentionally kept in the comparison result so the
    # user can see why a material was rejected instead of wondering why it vanished.

    material: Material
    status: str
    required_thickness: float | None = None
    final_flux: float | None = None
    final_transmission: float | None = None
    buildup_used: bool = False
    calculation_mode: str | None = None
    warnings: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    def __post_init__(self):
        if self.status not in ["PASS", "FAILED"]:
            raise ValueError("MaterialDesignCandidate status must be PASS or FAILED.")

        # PASS candidates represent usable shielding designs.
        # These must contain numerical result values because they will appear
        # in the comparison table and may later be used for optimization.

        if self.status == "PASS":
            if self.required_thickness is None:
                raise ValueError("Passing candidates must store required thickness.")

            if self.final_flux is None:
                raise ValueError("Passing candidates must store final flux.")

            if self.final_transmission is None:
                raise ValueError("Passing candidates must store final transmission.")

            if self.required_thickness < 0:
                raise ValueError("Required thickness cannot be negative.")

            if self.final_flux < 0:
                raise ValueError("Final flux cannot be negative.")

            if self.final_transmission < 0:
                raise ValueError("Final transmission cannot be negative.")

            if self.final_transmission > 1:
                raise ValueError("Final transmission cannot be greater than 1.")

            if self.calculation_mode is None or self.calculation_mode.strip() == "":
                raise ValueError("Passing candidates must store calculation mode.")

        # FAILED candidates do not need thickness/flux values, but they must
        # preserve the reason for failure so the result remains transparent.

        if self.status == "FAILED":
            if self.failure_reason is None or self.failure_reason.strip() == "":
                raise ValueError("Failed candidates must store a failure reason.")


@dataclass
class MaterialComparisonResult:
    # Complete result of comparing multiple shielding materials for the same
    # source, detector distance, target, max-thickness limit, and buildup setting.
    #
    # candidates contains both passing and failed materials.
    # Passing candidates are sorted by required thickness.
    # Failed candidates are placed after passing candidates.
    target_description: str
    apply_buildup: bool
    candidates: list[MaterialDesignCandidate]

    def __post_init__(self):
        if self.target_description.strip() == "":
            raise ValueError("Target description cannot be empty.")

        if len(self.candidates) == 0:
            raise ValueError("Material comparison must contain at least one candidate.")

    def passing_candidates(self) -> list[MaterialDesignCandidate]:
        return [
            candidate
            for candidate in self.candidates
            if candidate.status == "PASS"
        ]

    def failed_candidates(self) -> list[MaterialDesignCandidate]:
        return [
            candidate
            for candidate in self.candidates
            if candidate.status == "FAILED"
        ]


@dataclass
class AirKermaMaterialDesignCandidate:
    # Result for one material in an air-kerma-rate comparison.
    #
    # PASS:
    #   design_result contains the complete minimum-thickness result,
    #   including the source-level and photon-line response data.
    #
    # FAILED:
    #   design_result is unavailable and failure_reason explains why.
    #
    # This model remains separate from MaterialDesignCandidate because
    # air-kerma results must not be stored in fields named final_flux or
    # final_transmission.

    material: Material
    status: str

    design_result: (
        AirKermaMinimumThicknessResult
        | None
    ) = None

    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in [
            "PASS",
            "FAILED",
        ]:
            raise ValueError(
                "Air-kerma material candidate status "
                "must be PASS or FAILED."
            )

        if self.status == "PASS":
            if self.design_result is None:
                raise ValueError(
                    "Passing air-kerma candidates must "
                    "store a design result."
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "Passing air-kerma candidates cannot "
                    "store a failure reason."
                )

            if (
                self.design_result.material.key
                != self.material.key
            ):
                raise ValueError(
                    "Air-kerma candidate material must match "
                    "the design-result material."
                )

        if self.status == "FAILED":
            if self.design_result is not None:
                raise ValueError(
                    "Failed air-kerma candidates cannot "
                    "store a design result."
                )

            if (
                self.failure_reason is None
                or self.failure_reason.strip() == ""
            ):
                raise ValueError(
                    "Failed air-kerma candidates must "
                    "store a failure reason."
                )

    @property
    def required_thickness(self) -> float | None:
        if self.design_result is None:
            return None

        return self.design_result.required_thickness

    @property
    def final_air_kerma_rate_microgy_per_h(
        self,
    ) -> float | None:
        if self.design_result is None:
            return None

        return (
            self
            .design_result
            .final_air_kerma_rate_microgy_per_h
        )

    @property
    def final_response_ratio(self) -> float | None:
        if self.design_result is None:
            return None

        return self.design_result.final_response_ratio

    @property
    def buildup_used(self) -> bool:
        if self.design_result is None:
            return False

        return self.design_result.buildup_used

    @property
    def calculation_mode(self) -> str | None:
        if self.design_result is None:
            return None

        return self.design_result.calculation_mode

    @property
    def warnings(self) -> list[str]:
        if self.design_result is None:
            return []

        return list(
            self.design_result.warnings
        )


@dataclass
class AirKermaMaterialComparisonResult:
    # Complete air-kerma-rate comparison across multiple materials.

    target_description: str
    apply_buildup: bool
    candidates: list[
        AirKermaMaterialDesignCandidate
    ]

    def __post_init__(self) -> None:
        if self.target_description.strip() == "":
            raise ValueError(
                "Air-kerma comparison target description "
                "cannot be empty."
            )

        if len(self.candidates) == 0:
            raise ValueError(
                "Air-kerma material comparison must "
                "contain at least one candidate."
            )

    def passing_candidates(
        self,
    ) -> list[AirKermaMaterialDesignCandidate]:
        return [
            candidate
            for candidate in self.candidates
            if candidate.status == "PASS"
        ]

    def failed_candidates(
        self,
    ) -> list[AirKermaMaterialDesignCandidate]:
        return [
            candidate
            for candidate in self.candidates
            if candidate.status == "FAILED"
        ]


def calculate_air_kerma_material_candidate(
    source: Source,
    material: Material,
    detector_distance_cm: float,
    target: AirKermaRateTarget,
    max_thickness_cm: float | None = None,
    apply_buildup: bool = False,
    thickness_tolerance_cm: float = 1.0e-8,
    maximum_iterations: int = 200,
    bracket_scan_intervals: int = 200,
) -> AirKermaMaterialDesignCandidate:
    # Calculate one material candidate for an air-kerma-rate target.
    #
    # Any solver failure becomes a preserved FAILED candidate so one
    # unsupported or insufficient material does not stop the comparison.

    try:
        design_result = (
            calculate_air_kerma_minimum_thickness(
                source=source,
                material=material,
                detector_distance_cm=(
                    detector_distance_cm
                ),
                target=target,
                max_thickness_cm=(
                    max_thickness_cm
                ),
                apply_buildup=apply_buildup,
                thickness_tolerance_cm=(
                    thickness_tolerance_cm
                ),
                maximum_iterations=(
                    maximum_iterations
                ),
                bracket_scan_intervals=(
                    bracket_scan_intervals
                ),
            )
        )

        return AirKermaMaterialDesignCandidate(
            material=material,
            status="PASS",
            design_result=design_result,
        )

    except ValueError as error:
        return AirKermaMaterialDesignCandidate(
            material=material,
            status="FAILED",
            failure_reason=str(error),
        )


def get_air_kerma_candidate_thickness_for_sort(
    candidate: AirKermaMaterialDesignCandidate,
) -> float:
    required_thickness = (
        candidate.required_thickness
    )

    if required_thickness is None:
        raise ValueError(
            "Passing air-kerma candidate for "
            f"{candidate.material.name} is missing "
            "required thickness."
        )

    return required_thickness


def sort_air_kerma_material_candidates(
    candidates: list[
        AirKermaMaterialDesignCandidate
    ],
) -> list[AirKermaMaterialDesignCandidate]:
    # Passing candidates are ranked by required thickness.
    # Failed candidates remain visible and are listed afterward.

    passing_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == "PASS"
    ]

    failed_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == "FAILED"
    ]

    passing_candidates.sort(
        key=get_air_kerma_candidate_thickness_for_sort
    )

    failed_candidates.sort(
        key=lambda candidate: (
            candidate.material.name
        )
    )

    return (
        passing_candidates
        + failed_candidates
    )


def compare_materials_for_air_kerma_target(
    source: Source,
    materials: list[Material],
    detector_distance_cm: float,
    target: AirKermaRateTarget,
    max_thickness_cm: float | None = None,
    apply_buildup: bool = False,
    thickness_tolerance_cm: float = 1.0e-8,
    maximum_iterations: int = 200,
    bracket_scan_intervals: int = 200,
) -> AirKermaMaterialComparisonResult:
    # Compare the required homogeneous shielding thickness across
    # multiple materials for one collision-air-kerma-rate target.

    if len(materials) == 0:
        raise ValueError(
            "At least one material is required for "
            "air-kerma comparison."
        )

    candidates: list[
        AirKermaMaterialDesignCandidate
    ] = []

    for material in materials:
        candidate = (
            calculate_air_kerma_material_candidate(
                source=source,
                material=material,
                detector_distance_cm=(
                    detector_distance_cm
                ),
                target=target,
                max_thickness_cm=(
                    max_thickness_cm
                ),
                apply_buildup=apply_buildup,
                thickness_tolerance_cm=(
                    thickness_tolerance_cm
                ),
                maximum_iterations=(
                    maximum_iterations
                ),
                bracket_scan_intervals=(
                    bracket_scan_intervals
                ),
            )
        )

        candidates.append(candidate)

    sorted_candidates = (
        sort_air_kerma_material_candidates(
            candidates
        )
    )

    if apply_buildup:
        response_name = (
            "G-P exposure-buildup-adjusted collision "
            "air-kerma rate"
        )
    else:
        response_name = (
            "Uncollided collision air-kerma rate"
        )

    target_description = (
        f"{response_name} <= "
        f"{target.target_air_kerma_rate_microgy_per_h:.6g} "
        "µGy/h"
    )

    return AirKermaMaterialComparisonResult(
        target_description=target_description,
        apply_buildup=apply_buildup,
        candidates=sorted_candidates,
    )


def create_candidate_from_minimum_thickness_result(
    result: MinimumThicknessResult,
) -> MaterialDesignCandidate:
    # Convert a successful MinimumThicknessResult into a comparison candidate.

    return MaterialDesignCandidate(
        material=result.material,
        status="PASS",
        required_thickness=result.required_thickness,
        final_flux=result.final_flux,
        final_transmission=result.final_transmission,
        buildup_used=result.buildup_used,
        calculation_mode=result.calculation_mode,
        warnings=result.warnings,
        failure_reason=None,
    )


def calculate_material_candidate(
    source: Source,
    material: Material,
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    apply_buildup: bool = False,
) -> MaterialDesignCandidate:
    # Calculate one material's required thickness for a shared design problem.
    #
    # This function is the bridge between V1.08 material comparison and the
    # V1.07 minimum-thickness engine.
    #
    # It chooses the correct V1.07 solver based on source type:
    #   - ManualPhotonSource uses calculate_manual_minimum_thickness()
    #   - IsotopeSource uses calculate_isotope_minimum_thickness()
    #
    # Any ValueError from the lower-level solver becomes a FAILED candidate.
    # This prevents one impossible material from stopping the entire comparison.

    try:
        if isinstance(source, ManualPhotonSource):
            thickness_result = calculate_manual_minimum_thickness(
                source,
                material,
                detector_distance,
                target,
                max_thickness,
                apply_buildup=apply_buildup,
            )

        elif isinstance(source, IsotopeSource):
            thickness_result = calculate_isotope_minimum_thickness(
                source,
                material,
                detector_distance,
                target,
                max_thickness,
                apply_buildup=apply_buildup,
            )

        else:
            raise ValueError("Unsupported source type.")

        return create_candidate_from_minimum_thickness_result(thickness_result)

    except ValueError as error:
        return MaterialDesignCandidate(
            material=material,
            status="FAILED",
            warnings=[],
            failure_reason=str(error),
        )


def get_required_thickness_for_sort(candidate: MaterialDesignCandidate) -> float:
    # Passing candidates should always have required_thickness set.
    # This helper makes that guarantee explicit for sorting and type checking.

    if candidate.required_thickness is None:
        raise ValueError(
            f"Passing candidate for {candidate.material.name} is missing required thickness."
        )

    return candidate.required_thickness


def sort_material_candidates(
    candidates: list[MaterialDesignCandidate],
) -> list[MaterialDesignCandidate]:
    # Sort comparison results for readable engineering output.
    #
    # Passing candidates are sorted from smallest required thickness to largest.
    # This makes the table immediately useful for design comparison.
    #
    # Failed candidates are kept at the bottom. They are sorted alphabetically
    # so the output remains deterministic and easy to scan.

    passing_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == "PASS"
    ]

    failed_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == "FAILED"
    ]

    passing_candidates.sort(
        key=get_required_thickness_for_sort
    )

    failed_candidates.sort(
        key=lambda candidate: candidate.material.name
    )

    return passing_candidates + failed_candidates


def compare_materials_for_target(
    source: Source,
    materials: list[Material],
    detector_distance: float,
    target: Target,
    max_thickness: float | None = None,
    apply_buildup: bool = False,
) -> MaterialComparisonResult:
    # Run the same target-driven design calculation for multiple materials.
    #
    # This is the main V1.08 workflow function.
    #
    # Inputs define one shared shielding problem:
    #   - source
    #   - detector distance
    #   - design target
    #   - optional maximum thickness
    #   - buildup setting
    #
    # Each material is tested independently. The result is a ranked comparison
    # table showing how much of each material is required.

    if len(materials) == 0:
        raise ValueError("At least one material is required for comparison.")

    candidates = []

    for material in materials:
        candidate = calculate_material_candidate(
            source,
            material,
            detector_distance,
            target,
            max_thickness,
            apply_buildup,
        )

        candidates.append(candidate)

    sorted_candidates = sort_material_candidates(candidates)

    return MaterialComparisonResult(
        get_target_description(target),
        apply_buildup,
        sorted_candidates,
    )