from dataclasses import dataclass, field
from models import ShieldingResult


@dataclass
class PhotonLine:
    # A single emitted photon line from a radioactive or manual source.
    # energy is stored in MeV.
    # intensity is stored as photons emitted per decay.
    # Example: Cs-137 has a 0.661657 MeV photon line with intensity about 0.851.
    energy: float
    intensity: float

    def __post_init__(self):
        if self.energy <= 0:
            raise ValueError("Photon line energy must be greater than zero.")

        if self.intensity < 0:
            raise ValueError("Photon line intensity cannot be negative.")


@dataclass
class IsotopeSource:
    # A radioactive isotope source with one or more emitted photon lines.
    # activity_bq is the decay rate in decays per second.
    # photon_lines stores the photon energies and intensities used for shielding calculations.
    name: str
    activity_bq: float
    photon_lines: list[PhotonLine]

    def __post_init__(self):
        if self.name.strip() == "":
            raise ValueError("Source name cannot be empty.")

        if self.activity_bq < 0:
            raise ValueError("Source activity cannot be negative.")

        if len(self.photon_lines) == 0:
            raise ValueError("Isotope source must have at least one photon line.")


@dataclass
class ManualPhotonSource:
    # A user-defined monoenergetic photon source.
    # This preserves the original V1.05 behavior where the user directly enters
    # photon energy and photon emission rate instead of selecting an isotope.
    energy: float
    photon_rate: float

    def __post_init__(self):
        if self.energy <= 0:
            raise ValueError("Photon energy must be greater than zero.")

        if self.photon_rate < 0:
            raise ValueError("Photon rate cannot be negative.")


@dataclass
class SourceLineResult:
    # Stores the shielding result for one photon line.
    # photon_rate is calculated from activity * intensity for isotope sources,
    # or directly from the user-entered photon rate for manual sources.
    photon_line: PhotonLine
    photon_rate: float
    shielding_result: ShieldingResult

    def __post_init__(self):
        if self.photon_rate < 0:
            raise ValueError("Photon rate cannot be negative.")


@dataclass
class SourceCalculationResult:
    # Stores the complete result for a source calculation.
    # For isotope sources, this contains one SourceLineResult per photon line.
    # total_uncollided_flux is always available.
    # total_buildup_corrected_flux is only available when buildup was requested
    # and successfully applied to every photon line.
    # warnings stores non-fatal modeling limitations, such as skipped buildup.
    source_name: str
    activity_bq: float | None
    line_results: list[SourceLineResult]
    total_uncollided_flux: float
    total_buildup_corrected_flux: float | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.source_name.strip() == "":
            raise ValueError("Source name cannot be empty.")

        if self.activity_bq is not None and self.activity_bq < 0:
            raise ValueError("Source activity cannot be negative.")

        if len(self.line_results) == 0:
            raise ValueError("SourceCalculationResult must have at least one line result.")

        if self.total_uncollided_flux < 0:
            raise ValueError("Total uncollided flux cannot be negative.")

        if (
            self.total_buildup_corrected_flux is not None
            and self.total_buildup_corrected_flux < 0
        ):
            raise ValueError("Total buildup-corrected flux cannot be negative.")