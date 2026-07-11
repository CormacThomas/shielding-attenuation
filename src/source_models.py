from dataclasses import dataclass, field
from models import ShieldingResult


@dataclass
class PhotonLine:
    # A single photon emission line from a source. ex: .6617 MeV at .85 photons/decay
    # energy = photon energy in MeV
    # intensity = photons emitted per decay
    # Useful in determining photon rate which = activity * intesity.
    energy: float
    intensity: float

    def __post_init__(self):
        if self.energy <= 0:
            raise ValueError("Photon line energy must be greater than zero.")

        if self.intensity < 0:
            raise ValueError("Photon line intensity cannot be negative.")


@dataclass
class IsotopeSource:
    # A radioactive isotope source with one or more photon emission lines. Some sources have multiple gamma lines.
    # activity_bq = decays per second
    # photon_lines = list of emitted photon lines and their intensities
    # Ex: Co-60, activity = 3.7e10 Bq, photon lines = [1.173 MeV, 1.333 MeV].

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
    # A manual monoenergetic photon source.
    # This preserves the original V1.05 behavior where the user directly
    # enters photon energy and photon emission rate.
    # Ex: .500 MeV photon line

    energy: float
    photon_rate: float

    def __post_init__(self):
        if self.energy <= 0:
            raise ValueError("Photon energy must be greater than zero.")

        if self.photon_rate < 0:
            raise ValueError("Photon rate cannot be negative.")


@dataclass
class SourceLineResult:
    # Result for one photon line after shielding calculation.
    photon_line: PhotonLine
    photon_rate: float
    shielding_result: ShieldingResult

    def __post_init__(self):
        if self.photon_rate < 0:
            raise ValueError("Photon rate cannot be negative.")


@dataclass
class SourceCalculationResult:
    # Complete result for a source calculation.
    # For isotope sources, this stores line-by-line shielding results
    # and the summed detector flux over all photon lines.
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