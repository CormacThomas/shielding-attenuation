"""Resolve serialized photon source inputs into runtime sources."""

from shielding.data.isotopes import create_isotope_source
from shielding.physics.source_models import IsotopeSource, ManualPhotonSource
from shielding.scenarios.models import (
    IsotopeSourceSpec,
    ManualPhotonSourceSpec,
    SourceSpec,
)

RuntimeSource = ManualPhotonSource | IsotopeSource


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

    raise ValueError("Unsupported scenario source specification.")
