# V1.13 OpenMC-independent execution and result models.
#
# This module defines the validated data contract used by the future OpenMC
# backend. It intentionally does not import OpenMC so:
#
#   - the deterministic project remains usable without OpenMC installed;
#   - settings profiles can be tested in the normal Windows environment;
#   - parsed Monte Carlo results can be serialized independently;
#   - comparison mathematics can be validated without running particles.
#
# OpenMC backend modules will convert these models into OpenMC Python objects
# and reconstruct these result models from statepoint files.


from dataclasses import dataclass, field
import math
from typing import Literal

from benchmark_models import (
    DeterministicShellAverageResult,
    SphericalEvaluationShell,
)


ElectronTreatment = Literal[
    "led",
    "ttb",
]


VALID_ELECTRON_TREATMENTS = (
    "led",
    "ttb",
)


def openmc_values_match(
    first_value: float,
    second_value: float,
) -> bool:
    # Compare values that should represent the same normalized or derived
    # OpenMC quantity.

    return math.isclose(
        first_value,
        second_value,
        rel_tol=1.0e-10,
        abs_tol=1.0e-20,
    )


def require_positive_integer(
    value: int,
    description: str,
) -> None:
    # Boolean values are rejected even though bool is a subclass of int.

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(
            f"{description} must be a positive integer."
        )


def require_nonnegative_value(
    value: float,
    description: str,
) -> None:
    if value < 0:
        raise ValueError(
            f"{description} cannot be negative."
        )


@dataclass
class OpenMCSettings:
    # OpenMC numerical execution settings.
    #
    # These values describe how OpenMC samples the physical problem. They are
    # intentionally separate from ShieldingScenario, which describes the
    # physical source and shield.
    #
    # The finite evaluation shell is also separate. It is represented by
    # SphericalEvaluationShell because it defines the matched observation
    # region used by both deterministic and OpenMC calculations.
    #
    # particles_per_batch:
    #   Number of source particles simulated in each fixed-source batch.
    #
    # batches:
    #   Number of independent tally realizations.
    #
    # energy_bin_boundaries_ev:
    #   Strictly increasing incident-photon energy boundaries used by the
    #   energy-resolved spectrum tally.
    #
    # photon_cutoff_energy_ev:
    #   Photon energy below which OpenMC terminates particle histories.
    #
    # outer_boundary_radius_cm:
    #   Radius of the outer vacuum boundary surrounding the observation shell.
    #
    # statepoint_batches:
    #   Batches after which OpenMC writes statepoint files. An empty input list
    #   is normalized to the final batch.

    profile_name: str

    particles_per_batch: int
    batches: int
    random_seed: int
    threads: int

    energy_bin_boundaries_ev: list[float]

    electron_treatment: ElectronTreatment = "ttb"
    atomic_relaxation: bool = True

    photon_cutoff_energy_ev: float = 1000.0
    outer_boundary_radius_cm: float = 110.0

    statepoint_batches: list[int] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.profile_name = (
            self.profile_name
            .lower()
            .strip()
        )

        if self.profile_name == "":
            raise ValueError(
                "OpenMC settings profile name cannot be empty."
            )

        require_positive_integer(
            self.particles_per_batch,
            "OpenMC particles per batch",
        )

        require_positive_integer(
            self.batches,
            "OpenMC batch count",
        )

        require_positive_integer(
            self.random_seed,
            "OpenMC random seed",
        )

        require_positive_integer(
            self.threads,
            "OpenMC thread count",
        )

        if (
            self.electron_treatment
            not in VALID_ELECTRON_TREATMENTS
        ):
            raise ValueError(
                "Unsupported OpenMC electron treatment."
            )

        if not isinstance(
            self.atomic_relaxation,
            bool,
        ):
            raise ValueError(
                "OpenMC atomic relaxation setting "
                "must be Boolean."
            )

        if self.photon_cutoff_energy_ev <= 0:
            raise ValueError(
                "OpenMC photon cutoff energy must be "
                "greater than zero."
            )

        if self.outer_boundary_radius_cm <= 0:
            raise ValueError(
                "OpenMC outer boundary radius must be "
                "greater than zero."
            )

        if not isinstance(
            self.energy_bin_boundaries_ev,
            list,
        ):
            raise ValueError(
                "OpenMC energy-bin boundaries must be "
                "stored in a list."
            )

        if len(
            self.energy_bin_boundaries_ev
        ) < 2:
            raise ValueError(
                "OpenMC spectrum tally requires at least "
                "two energy-bin boundaries."
            )

        normalized_boundaries: list[
            float
        ] = []

        for boundary in (
            self.energy_bin_boundaries_ev
        ):
            if (
                isinstance(boundary, bool)
                or not isinstance(
                    boundary,
                    (int, float),
                )
            ):
                raise ValueError(
                    "OpenMC energy-bin boundaries must "
                    "be numerical."
                )

            normalized_boundary = float(
                boundary
            )

            if normalized_boundary <= 0:
                raise ValueError(
                    "OpenMC energy-bin boundaries must "
                    "be greater than zero."
                )

            normalized_boundaries.append(
                normalized_boundary
            )

        for index in range(
            len(normalized_boundaries) - 1
        ):
            if (
                normalized_boundaries[index + 1]
                <= normalized_boundaries[index]
            ):
                raise ValueError(
                    "OpenMC energy-bin boundaries must "
                    "be strictly increasing."
                )

        if (
            normalized_boundaries[0]
            < self.photon_cutoff_energy_ev
        ):
            raise ValueError(
                "OpenMC spectrum minimum energy cannot "
                "be below the photon cutoff energy."
            )

        self.energy_bin_boundaries_ev = (
            normalized_boundaries
        )

        if not isinstance(
            self.statepoint_batches,
            list,
        ):
            raise ValueError(
                "OpenMC statepoint batches must be "
                "stored in a list."
            )

        if len(
            self.statepoint_batches
        ) == 0:
            self.statepoint_batches = [
                self.batches
            ]

        normalized_statepoint_batches: list[
            int
        ] = []

        for batch in self.statepoint_batches:
            require_positive_integer(
                batch,
                "OpenMC statepoint batch",
            )

            if batch > self.batches:
                raise ValueError(
                    "OpenMC statepoint batch cannot "
                    "exceed the total batch count."
                )

            normalized_statepoint_batches.append(
                batch
            )

        if (
            len(
                set(
                    normalized_statepoint_batches
                )
            )
            != len(
                normalized_statepoint_batches
            )
        ):
            raise ValueError(
                "OpenMC statepoint batches must be unique."
            )

        normalized_statepoint_batches.sort()

        if (
            normalized_statepoint_batches[-1]
            != self.batches
        ):
            raise ValueError(
                "OpenMC statepoint batches must include "
                "the final batch."
            )

        self.statepoint_batches = (
            normalized_statepoint_batches
        )

    @property
    def total_source_particles(self) -> int:
        return (
            self.particles_per_batch
            * self.batches
        )

    @property
    def minimum_spectrum_energy_ev(self) -> float:
        return (
            self.energy_bin_boundaries_ev[0]
        )

    @property
    def maximum_spectrum_energy_ev(self) -> float:
        return (
            self.energy_bin_boundaries_ev[-1]
        )


@dataclass
class OpenMCEnergyBinResult:
    # Parsed OpenMC spectrum result for one incident-photon energy bin.
    #
    # raw_track_length_flux:
    #   OpenMC cell-integrated track-length flux tally in cm/source.
    #
    # volume_normalized_fluence:
    #   Raw tally divided by the evaluation-shell volume, producing
    #   photons/(cm² source).
    #
    # physical_fluence_rate:
    #   Volume-normalized fluence multiplied by the physical source rate,
    #   producing photons/(cm² s).
    #
    # response_coefficient:
    #   Dry-air collision-air-kerma response coefficient in
    #   Gy cm²/photon.
    #
    # air_kerma_rate_contribution:
    #   Physical fluence rate multiplied by the response coefficient.

    lower_energy_ev: float
    upper_energy_ev: float

    raw_track_length_flux_mean_cm_per_source: float
    raw_track_length_flux_standard_deviation_cm_per_source: float

    volume_normalized_fluence_mean_per_cm2_per_source: float
    volume_normalized_fluence_standard_deviation_per_cm2_per_source: float

    physical_fluence_rate_mean_per_cm2_s: float
    physical_fluence_rate_standard_deviation_per_cm2_s: float

    response_coefficient_gy_cm2_per_photon: float

    air_kerma_rate_contribution_gy_per_s: float

    def __post_init__(self) -> None:
        if self.lower_energy_ev <= 0:
            raise ValueError(
                "OpenMC energy-bin lower boundary must "
                "be greater than zero."
            )

        if (
            self.upper_energy_ev
            <= self.lower_energy_ev
        ):
            raise ValueError(
                "OpenMC energy-bin upper boundary must "
                "be greater than the lower boundary."
            )

        require_nonnegative_value(
            self.raw_track_length_flux_mean_cm_per_source,
            "Raw OpenMC spectrum mean",
        )

        require_nonnegative_value(
            self.raw_track_length_flux_standard_deviation_cm_per_source,
            "Raw OpenMC spectrum standard deviation",
        )

        require_nonnegative_value(
            self.volume_normalized_fluence_mean_per_cm2_per_source,
            "Volume-normalized OpenMC fluence mean",
        )

        require_nonnegative_value(
            self.volume_normalized_fluence_standard_deviation_per_cm2_per_source,
            "Volume-normalized OpenMC fluence standard deviation",
        )

        require_nonnegative_value(
            self.physical_fluence_rate_mean_per_cm2_s,
            "Physical OpenMC fluence-rate mean",
        )

        require_nonnegative_value(
            self.physical_fluence_rate_standard_deviation_per_cm2_s,
            "Physical OpenMC fluence-rate standard deviation",
        )

        if (
            self
            .response_coefficient_gy_cm2_per_photon
            <= 0
        ):
            raise ValueError(
                "OpenMC energy-bin response coefficient "
                "must be greater than zero."
            )

        require_nonnegative_value(
            self.air_kerma_rate_contribution_gy_per_s,
            "OpenMC energy-bin air-kerma contribution",
        )

        expected_contribution = (
            self
            .physical_fluence_rate_mean_per_cm2_s
            * self
            .response_coefficient_gy_cm2_per_photon
        )

        if not openmc_values_match(
            self.air_kerma_rate_contribution_gy_per_s,
            expected_contribution,
        ):
            raise ValueError(
                "OpenMC energy-bin air-kerma contribution "
                "must equal physical fluence rate times "
                "the response coefficient."
            )


@dataclass
class OpenMCResponseResult:
    # Complete processed OpenMC result for one benchmark scenario.
    #
    # Direct response tally normalization:
    #
    #   raw response tally
    #       [Gy cm³/source]
    #
    #   divided by shell volume
    #       [cm³]
    #
    #   equals response per source
    #       [Gy/source]
    #
    #   multiplied by physical source rate
    #       [source/s]
    #
    #   equals physical collision-air-kerma rate
    #       [Gy/s]
    #
    # The direct response tally is the authoritative OpenMC result.
    #
    # The spectrum-folded result is reconstructed from energy-bin results and
    # used as an independent numerical cross-check.

    scenario_id: str
    settings_profile_name: str

    evaluation_shell: (
        SphericalEvaluationShell
    )

    shell_volume_cm3: float
    physical_source_rate_per_s: float

    energy_bin_results: list[
        OpenMCEnergyBinResult
    ]

    raw_direct_response_mean_gy_cm3_per_source: float
    raw_direct_response_standard_deviation_gy_cm3_per_source: float

    direct_response_mean_gy_per_source: float
    direct_response_standard_deviation_gy_per_source: float

    direct_response_rate_gy_per_s: float
    direct_response_rate_standard_deviation_gy_per_s: float

    relative_uncertainty: float

    spectrum_folded_response_rate_gy_per_s: float

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.scenario_id = (
            self.scenario_id
            .lower()
            .strip()
        )

        self.settings_profile_name = (
            self.settings_profile_name
            .lower()
            .strip()
        )

        if self.scenario_id == "":
            raise ValueError(
                "OpenMC response scenario ID cannot be empty."
            )

        if self.settings_profile_name == "":
            raise ValueError(
                "OpenMC response settings profile "
                "cannot be empty."
            )

        if self.shell_volume_cm3 <= 0:
            raise ValueError(
                "OpenMC response shell volume must be "
                "greater than zero."
            )

        expected_shell_volume = (
            4.0
            * math.pi
            / 3.0
            * (
                self.evaluation_shell
                .outer_radius_cm ** 3
                - self.evaluation_shell
                .inner_radius_cm ** 3
            )
        )

        if not openmc_values_match(
            self.shell_volume_cm3,
            expected_shell_volume,
        ):
            raise ValueError(
                "OpenMC response shell volume must match "
                "the evaluation-shell geometry."
            )

        if self.physical_source_rate_per_s <= 0:
            raise ValueError(
                "OpenMC physical source rate must be "
                "greater than zero."
            )

        if len(
            self.energy_bin_results
        ) == 0:
            raise ValueError(
                "OpenMC response must contain at least "
                "one energy-bin result."
            )

        for index in range(
            len(self.energy_bin_results) - 1
        ):
            current_bin = (
                self.energy_bin_results[index]
            )

            following_bin = (
                self.energy_bin_results[
                    index + 1
                ]
            )

            if not openmc_values_match(
                current_bin.upper_energy_ev,
                following_bin.lower_energy_ev,
            ):
                raise ValueError(
                    "OpenMC energy-bin results must be "
                    "ordered and contiguous."
                )

        require_nonnegative_value(
            self.raw_direct_response_mean_gy_cm3_per_source,
            "Raw OpenMC direct-response mean",
        )

        require_nonnegative_value(
            self.raw_direct_response_standard_deviation_gy_cm3_per_source,
            "Raw OpenMC direct-response standard deviation",
        )

        require_nonnegative_value(
            self.direct_response_mean_gy_per_source,
            "Volume-normalized OpenMC direct-response mean",
        )

        require_nonnegative_value(
            self.direct_response_standard_deviation_gy_per_source,
            "Volume-normalized OpenMC direct-response standard deviation",
        )

        if self.direct_response_rate_gy_per_s <= 0:
            raise ValueError(
                "OpenMC direct response rate must be "
                "greater than zero."
            )

        require_nonnegative_value(
            self.direct_response_rate_standard_deviation_gy_per_s,
            "Physical OpenMC direct-response standard deviation",
        )

        if self.relative_uncertainty < 0:
            raise ValueError(
                "OpenMC relative uncertainty cannot "
                "be negative."
            )

        if (
            self.spectrum_folded_response_rate_gy_per_s
            < 0
        ):
            raise ValueError(
                "OpenMC spectrum-folded response rate "
                "cannot be negative."
            )

        expected_response_mean = (
            self
            .raw_direct_response_mean_gy_cm3_per_source
            / self.shell_volume_cm3
        )

        if not openmc_values_match(
            self.direct_response_mean_gy_per_source,
            expected_response_mean,
        ):
            raise ValueError(
                "OpenMC direct response per source must "
                "equal the raw tally divided by shell volume."
            )

        expected_response_standard_deviation = (
            self
            .raw_direct_response_standard_deviation_gy_cm3_per_source
            / self.shell_volume_cm3
        )

        if not openmc_values_match(
            self
            .direct_response_standard_deviation_gy_per_source,
            expected_response_standard_deviation,
        ):
            raise ValueError(
                "OpenMC direct-response standard deviation "
                "per source must equal the raw uncertainty "
                "divided by shell volume."
            )

        expected_physical_response = (
            self.direct_response_mean_gy_per_source
            * self.physical_source_rate_per_s
        )

        if not openmc_values_match(
            self.direct_response_rate_gy_per_s,
            expected_physical_response,
        ):
            raise ValueError(
                "OpenMC physical direct response must "
                "equal response per source times the "
                "physical source rate."
            )

        expected_physical_standard_deviation = (
            self
            .direct_response_standard_deviation_gy_per_source
            * self.physical_source_rate_per_s
        )

        if not openmc_values_match(
            self
            .direct_response_rate_standard_deviation_gy_per_s,
            expected_physical_standard_deviation,
        ):
            raise ValueError(
                "OpenMC physical direct-response "
                "uncertainty must use the same source-rate "
                "scaling as the mean."
            )

        expected_relative_uncertainty = (
            self
            .direct_response_rate_standard_deviation_gy_per_s
            / self.direct_response_rate_gy_per_s
        )

        if not openmc_values_match(
            self.relative_uncertainty,
            expected_relative_uncertainty,
        ):
            raise ValueError(
                "OpenMC relative uncertainty must equal "
                "standard deviation divided by mean."
            )

        expected_spectrum_folded_response = sum(
            energy_bin_result
            .air_kerma_rate_contribution_gy_per_s
            for energy_bin_result
            in self.energy_bin_results
        )

        if not openmc_values_match(
            self
            .spectrum_folded_response_rate_gy_per_s,
            expected_spectrum_folded_response,
        ):
            raise ValueError(
                "OpenMC spectrum-folded response must "
                "equal the sum of energy-bin contributions."
            )


@dataclass
class OpenMCRunManifest:
    # Reproducibility metadata for one completed OpenMC execution.

    scenario_id: str
    settings_profile_name: str

    openmc_version: str
    python_version: str

    cross_section_library: str

    electron_treatment: ElectronTreatment
    atomic_relaxation: bool
    photon_cutoff_energy_ev: float

    particles_per_batch: int
    batches: int
    total_source_particles: int

    random_seed: int
    threads: int

    runtime_seconds: float

    statepoint_filename: str
    execution_timestamp_utc: str

    git_commit: str | None = None

    def __post_init__(self) -> None:
        self.scenario_id = (
            self.scenario_id
            .lower()
            .strip()
        )

        self.settings_profile_name = (
            self.settings_profile_name
            .lower()
            .strip()
        )

        self.openmc_version = (
            self.openmc_version
            .strip()
        )

        self.python_version = (
            self.python_version
            .strip()
        )

        self.cross_section_library = (
            self.cross_section_library
            .strip()
        )

        self.statepoint_filename = (
            self.statepoint_filename
            .strip()
        )

        self.execution_timestamp_utc = (
            self.execution_timestamp_utc
            .strip()
        )

        if self.scenario_id == "":
            raise ValueError(
                "OpenMC manifest scenario ID cannot be empty."
            )

        if self.settings_profile_name == "":
            raise ValueError(
                "OpenMC manifest settings profile "
                "cannot be empty."
            )

        if self.openmc_version == "":
            raise ValueError(
                "OpenMC manifest version cannot be empty."
            )

        if self.python_version == "":
            raise ValueError(
                "OpenMC manifest Python version cannot be empty."
            )

        if self.cross_section_library == "":
            raise ValueError(
                "OpenMC manifest cross-section library "
                "cannot be empty."
            )

        if (
            self.electron_treatment
            not in VALID_ELECTRON_TREATMENTS
        ):
            raise ValueError(
                "OpenMC manifest contains an unsupported "
                "electron treatment."
            )

        if not isinstance(
            self.atomic_relaxation,
            bool,
        ):
            raise ValueError(
                "OpenMC manifest atomic-relaxation value "
                "must be Boolean."
            )

        if self.photon_cutoff_energy_ev <= 0:
            raise ValueError(
                "OpenMC manifest photon cutoff must be "
                "greater than zero."
            )

        require_positive_integer(
            self.particles_per_batch,
            "OpenMC manifest particles per batch",
        )

        require_positive_integer(
            self.batches,
            "OpenMC manifest batch count",
        )

        require_positive_integer(
            self.total_source_particles,
            "OpenMC manifest total source particles",
        )

        expected_total_particles = (
            self.particles_per_batch
            * self.batches
        )

        if (
            self.total_source_particles
            != expected_total_particles
        ):
            raise ValueError(
                "OpenMC manifest total source particles "
                "must equal particles per batch times batches."
            )

        require_positive_integer(
            self.random_seed,
            "OpenMC manifest random seed",
        )

        require_positive_integer(
            self.threads,
            "OpenMC manifest thread count",
        )

        if self.runtime_seconds < 0:
            raise ValueError(
                "OpenMC manifest runtime cannot be negative."
            )

        if self.statepoint_filename == "":
            raise ValueError(
                "OpenMC manifest statepoint filename "
                "cannot be empty."
            )

        if self.execution_timestamp_utc == "":
            raise ValueError(
                "OpenMC manifest execution timestamp "
                "cannot be empty."
            )

        if self.git_commit is not None:
            self.git_commit = (
                self.git_commit
                .strip()
            )

            if self.git_commit == "":
                self.git_commit = None


@dataclass
class DeterministicOpenMCComparison:
    # Matched deterministic-versus-OpenMC response comparison.

    deterministic_result: (
        DeterministicShellAverageResult
    )

    openmc_result: OpenMCResponseResult

    relative_difference_from_uncollided: float

    relative_difference_from_gp: (
        float | None
    )

    observed_monte_carlo_buildup_ratio: float

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if (
            self.deterministic_result.scenario_id
            != self.openmc_result.scenario_id
        ):
            raise ValueError(
                "Deterministic and OpenMC comparison "
                "scenario IDs must match."
            )

        if (
            self.deterministic_result
            .evaluation_shell
            != self.openmc_result
            .evaluation_shell
        ):
            raise ValueError(
                "Deterministic and OpenMC comparison "
                "evaluation shells must match."
            )

        deterministic_uncollided = (
            self.deterministic_result
            .total_shell_average_uncollided_collision_air_kerma_rate_gy_per_s
        )

        openmc_response = (
            self.openmc_result
            .direct_response_rate_gy_per_s
        )

        expected_uncollided_difference = (
            (
                openmc_response
                - deterministic_uncollided
            )
            / deterministic_uncollided
        )

        if not openmc_values_match(
            self.relative_difference_from_uncollided,
            expected_uncollided_difference,
        ):
            raise ValueError(
                "OpenMC relative difference from the "
                "deterministic uncollided response is inconsistent."
            )

        expected_buildup_ratio = (
            openmc_response
            / deterministic_uncollided
        )

        if not openmc_values_match(
            self.observed_monte_carlo_buildup_ratio,
            expected_buildup_ratio,
        ):
            raise ValueError(
                "Observed Monte Carlo buildup ratio "
                "is inconsistent."
            )

        deterministic_gp = (
            self.deterministic_result
            .total_shell_average_buildup_adjusted_collision_air_kerma_rate_gy_per_s
        )

        if deterministic_gp is None:
            if (
                self.relative_difference_from_gp
                is not None
            ):
                raise ValueError(
                    "A relative difference from G-P may "
                    "only be stored when the deterministic "
                    "G-P response is available."
                )

        else:
            if (
                self.relative_difference_from_gp
                is None
            ):
                raise ValueError(
                    "An available deterministic G-P "
                    "response requires a relative difference."
                )

            expected_gp_difference = (
                (
                    openmc_response
                    - deterministic_gp
                )
                / deterministic_gp
            )

            if not openmc_values_match(
                self.relative_difference_from_gp,
                expected_gp_difference,
            ):
                raise ValueError(
                    "OpenMC relative difference from the "
                    "deterministic G-P response is inconsistent."
                )