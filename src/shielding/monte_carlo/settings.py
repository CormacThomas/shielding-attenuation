"""Validated OpenMC execution, physics, geometry, and tally settings."""

from dataclasses import dataclass, field
from typing import Literal

ElectronTreatment = Literal[
    "led",
    "ttb",
]


VALID_ELECTRON_TREATMENTS = (
    "led",
    "ttb",
)


def require_positive_integer(
    value: int,
    description: str,
) -> None:
    # Boolean values are rejected even though bool is a subclass of int.

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{description} must be a positive integer.")


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

    statepoint_batches: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.profile_name = self.profile_name.lower().strip()

        if self.profile_name == "":
            raise ValueError("OpenMC settings profile name cannot be empty.")

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

        if self.electron_treatment not in VALID_ELECTRON_TREATMENTS:
            raise ValueError("Unsupported OpenMC electron treatment.")

        if not isinstance(
            self.atomic_relaxation,
            bool,
        ):
            raise ValueError("OpenMC atomic relaxation setting must be Boolean.")

        if self.photon_cutoff_energy_ev <= 0:
            raise ValueError("OpenMC photon cutoff energy must be greater than zero.")

        if self.outer_boundary_radius_cm <= 0:
            raise ValueError("OpenMC outer boundary radius must be greater than zero.")

        if not isinstance(
            self.energy_bin_boundaries_ev,
            list,
        ):
            raise ValueError("OpenMC energy-bin boundaries must be stored in a list.")

        if len(self.energy_bin_boundaries_ev) < 2:
            raise ValueError(
                "OpenMC spectrum tally requires at least two energy-bin boundaries."
            )

        normalized_boundaries: list[float] = []

        for boundary in self.energy_bin_boundaries_ev:
            if isinstance(boundary, bool) or not isinstance(
                boundary,
                (int, float),
            ):
                raise ValueError("OpenMC energy-bin boundaries must be numerical.")

            normalized_boundary = float(boundary)

            if normalized_boundary <= 0:
                raise ValueError(
                    "OpenMC energy-bin boundaries must be greater than zero."
                )

            normalized_boundaries.append(normalized_boundary)

        for index in range(len(normalized_boundaries) - 1):
            if normalized_boundaries[index + 1] <= normalized_boundaries[index]:
                raise ValueError(
                    "OpenMC energy-bin boundaries must be strictly increasing."
                )

        if normalized_boundaries[0] < self.photon_cutoff_energy_ev:
            raise ValueError(
                "OpenMC spectrum minimum energy cannot "
                "be below the photon cutoff energy."
            )

        self.energy_bin_boundaries_ev = normalized_boundaries

        if not isinstance(
            self.statepoint_batches,
            list,
        ):
            raise ValueError("OpenMC statepoint batches must be stored in a list.")

        if len(self.statepoint_batches) == 0:
            self.statepoint_batches = [self.batches]

        normalized_statepoint_batches: list[int] = []

        for batch in self.statepoint_batches:
            require_positive_integer(
                batch,
                "OpenMC statepoint batch",
            )

            if batch > self.batches:
                raise ValueError(
                    "OpenMC statepoint batch cannot exceed the total batch count."
                )

            normalized_statepoint_batches.append(batch)

        if len(set(normalized_statepoint_batches)) != len(
            normalized_statepoint_batches
        ):
            raise ValueError("OpenMC statepoint batches must be unique.")

        normalized_statepoint_batches.sort()

        if normalized_statepoint_batches[-1] != self.batches:
            raise ValueError("OpenMC statepoint batches must include the final batch.")

        self.statepoint_batches = normalized_statepoint_batches

    @property
    def total_source_particles(self) -> int:
        return self.particles_per_batch * self.batches

    @property
    def minimum_spectrum_energy_ev(self) -> float:
        return self.energy_bin_boundaries_ev[0]

    @property
    def maximum_spectrum_energy_ev(self) -> float:
        return self.energy_bin_boundaries_ev[-1]
