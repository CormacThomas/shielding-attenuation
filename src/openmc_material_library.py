# OpenMC-independent elemental material definitions.
#
# This module defines how project shielding materials are represented
# elementally in OpenMC.
#
# It deliberately does not import OpenMC. This allows:
#
#   - normal validation to run without OpenMC installed;
#   - material definitions to be tested on Windows;
#   - composition provenance to remain explicit;
#   - project density and OpenMC composition to remain separate concerns.
#
# Density is not assigned here. The authoritative density used during
# deterministic and OpenMC calculations remains the value stored in
# material_library.py.
#
# Supported V1.14 benchmark materials:
#
#   - natural Lead
#   - natural Tungsten
#   - Water as stoichiometric H2O
#   - Ordinary Concrete using NIST elemental weight fractions


from __future__ import annotations


from dataclasses import dataclass
import math
from typing import Literal


OpenMCFractionType = Literal[
    "ao",
    "wo",
]


FRACTION_SUM_ABSOLUTE_TOLERANCE = (
    2.0e-6
)


OPENMC_NATURAL_ELEMENT_SOURCE = (
    "Natural-element composition expanded by OpenMC "
    "using the configured continuous-energy data library."
)

STOICHIOMETRIC_WATER_SOURCE = (
    "Stoichiometric H2O elemental atom fractions."
)

NIST_ORDINARY_CONCRETE_SOURCE = (
    "NIST X-Ray Mass Attenuation Coefficients, "
    "Table 2, Concrete, Ordinary."
)

PROJECT_DENSITY_SOURCE = (
    "Shielding Attenuation Simulator "
    "material_library.py."
)

NIST_BARITE_CONCRETE_SOURCE = (
    "NIST X-Ray Mass Attenuation Coefficients, "
    "Table 2, Concrete, Barite (Type BA)."
)


@dataclass(
    frozen=True
)
class OpenMCMaterialComponent:
    # One elemental component of an OpenMC material definition.
    #
    # fraction:
    #   Atom fraction when the parent definition uses "ao".
    #   Weight fraction when the parent definition uses "wo".

    element_symbol: str
    fraction: float

    def __post_init__(
        self,
    ) -> None:
        normalized_symbol = (
            self.element_symbol.strip()
        )

        if normalized_symbol == "":
            raise ValueError(
                "OpenMC material component element "
                "symbol cannot be empty."
            )

        if self.fraction <= 0:
            raise ValueError(
                "OpenMC material component fraction "
                "must be greater than zero."
            )

        object.__setattr__(
            self,
            "element_symbol",
            normalized_symbol,
        )


@dataclass(
    frozen=True
)
class OpenMCMaterialDefinition:
    # OpenMC-independent elemental composition for one project material.
    #
    # material_key:
    #   Must match the stable key in material_library.py.
    #
    # fraction_type:
    #   "ao" for atom fractions.
    #   "wo" for weight fractions.
    #
    # reference_density_g_per_cm3:
    #   Optional density associated with the external composition source.
    #   This value is provenance metadata only. It is not used to construct
    #   the OpenMC material. The project material-library density remains
    #   authoritative for matched deterministic/OpenMC calculations.

    material_key: str
    fraction_type: OpenMCFractionType

    components: tuple[
        OpenMCMaterialComponent,
        ...,
    ]

    composition_source: str
    density_source: str

    reference_density_g_per_cm3: (
        float
        | None
    ) = None

    notes: str = ""

    def __post_init__(
        self,
    ) -> None:
        normalized_key = (
            self.material_key
            .lower()
            .strip()
        )

        if normalized_key == "":
            raise ValueError(
                "OpenMC material-definition key "
                "cannot be empty."
            )

        if self.fraction_type not in (
            "ao",
            "wo",
        ):
            raise ValueError(
                "OpenMC material fraction type must "
                "be 'ao' or 'wo'."
            )

        if len(
            self.components
        ) == 0:
            raise ValueError(
                "OpenMC material definition requires "
                "at least one component."
            )

        element_symbols = [
            component.element_symbol
            for component
            in self.components
        ]

        if (
            len(
                element_symbols
            )
            != len(
                set(
                    element_symbols
                )
            )
        ):
            raise ValueError(
                "OpenMC material-definition element "
                "symbols must be unique."
            )

        fraction_sum = sum(
            component.fraction
            for component
            in self.components
        )

        if not math.isclose(
            fraction_sum,
            1.0,
            rel_tol=0.0,
            abs_tol=(
                FRACTION_SUM_ABSOLUTE_TOLERANCE
            ),
        ):
            raise ValueError(
                "OpenMC material-component fractions "
                "must sum to one within tolerance. "
                f"Received {fraction_sum:.12g}."
            )

        if (
            self.composition_source
            .strip()
            == ""
        ):
            raise ValueError(
                "OpenMC material composition source "
                "cannot be empty."
            )

        if (
            self.density_source
            .strip()
            == ""
        ):
            raise ValueError(
                "OpenMC material density source "
                "cannot be empty."
            )

        if (
            self.reference_density_g_per_cm3
            is not None
            and (
                self.reference_density_g_per_cm3
                <= 0
            )
        ):
            raise ValueError(
                "OpenMC material reference density "
                "must be greater than zero."
            )

        object.__setattr__(
            self,
            "material_key",
            normalized_key,
        )

    @property
    def component_fraction_sum(
        self,
    ) -> float:
        return sum(
            component.fraction
            for component
            in self.components
        )

    @property
    def normalized_components(
        self,
    ) -> tuple[
        OpenMCMaterialComponent,
        ...,
    ]:
        # Normalize source fractions before passing them to OpenMC.
        #
        # The published NIST Ordinary Concrete fractions sum to 0.999999
        # because of decimal rounding. Normalization preserves their relative
        # proportions while ensuring the OpenMC fractions sum to exactly one
        # within floating-point precision.

        fraction_sum = (
            self.component_fraction_sum
        )

        return tuple(
            OpenMCMaterialComponent(
                element_symbol=(
                    component.element_symbol
                ),
                fraction=(
                    component.fraction
                    / fraction_sum
                ),
            )
            for component
            in self.components
        )


def create_lead_openmc_definition(
) -> OpenMCMaterialDefinition:
    return OpenMCMaterialDefinition(
        material_key="lead",
        fraction_type="ao",
        components=(
            OpenMCMaterialComponent(
                element_symbol="Pb",
                fraction=1.0,
            ),
        ),
        composition_source=(
            OPENMC_NATURAL_ELEMENT_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        notes=(
            "Natural elemental Lead. The project "
            "density remains 11.34 g/cm3."
        ),
    )


def create_tungsten_openmc_definition(
) -> OpenMCMaterialDefinition:
    return OpenMCMaterialDefinition(
        material_key="tungsten",
        fraction_type="ao",
        components=(
            OpenMCMaterialComponent(
                element_symbol="W",
                fraction=1.0,
            ),
        ),
        composition_source=(
            OPENMC_NATURAL_ELEMENT_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        notes=(
            "Natural elemental Tungsten. The project "
            "density remains 19.254 g/cm3."
        ),
    )


def create_barite_concrete_openmc_definition(
) -> OpenMCMaterialDefinition:
    # NIST Concrete, Barite (Type BA) elemental weight fractions.
    #
    # The published rounded fractions sum to 0.999999. They are normalized
    # before being passed to OpenMC.
    #
    # NIST lists a reference density of 3.35 g/cm3. The existing project
    # material uses 3.50 g/cm3. V1.14 retains the project density so the
    # deterministic and OpenMC calculations describe the same material.

    return OpenMCMaterialDefinition(
        material_key=(
            "concrete_barite"
        ),
        fraction_type="wo",
        components=(
            OpenMCMaterialComponent(
                element_symbol="H",
                fraction=0.003585,
            ),
            OpenMCMaterialComponent(
                element_symbol="O",
                fraction=0.311622,
            ),
            OpenMCMaterialComponent(
                element_symbol="Mg",
                fraction=0.001195,
            ),
            OpenMCMaterialComponent(
                element_symbol="Al",
                fraction=0.004183,
            ),
            OpenMCMaterialComponent(
                element_symbol="Si",
                fraction=0.010457,
            ),
            OpenMCMaterialComponent(
                element_symbol="S",
                fraction=0.107858,
            ),
            OpenMCMaterialComponent(
                element_symbol="Ca",
                fraction=0.050194,
            ),
            OpenMCMaterialComponent(
                element_symbol="Fe",
                fraction=0.047505,
            ),
            OpenMCMaterialComponent(
                element_symbol="Ba",
                fraction=0.463400,
            ),
        ),
        composition_source=(
            NIST_BARITE_CONCRETE_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        reference_density_g_per_cm3=(
            3.35
        ),
        notes=(
            "NIST Type BA elemental weight fractions "
            "are used with the project's established "
            "3.50 g/cm3 Barite Concrete density."
        ),
    )


def create_water_openmc_definition(
) -> OpenMCMaterialDefinition:
    return OpenMCMaterialDefinition(
        material_key="water",
        fraction_type="ao",
        components=(
            OpenMCMaterialComponent(
                element_symbol="H",
                fraction=(
                    2.0
                    / 3.0
                ),
            ),
            OpenMCMaterialComponent(
                element_symbol="O",
                fraction=(
                    1.0
                    / 3.0
                ),
            ),
        ),
        composition_source=(
            STOICHIOMETRIC_WATER_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        notes=(
            "Stoichiometric H2O represented using "
            "elemental atom fractions. The project "
            "density remains 1.0 g/cm3."
        ),
    )


def create_aluminum_openmc_definition(
) -> OpenMCMaterialDefinition:
    return create_natural_element_definition(
        material_key="aluminum",
        element_symbol="Al",
        notes=(
            "Natural elemental Aluminum. The project "
            "density remains 2.70 g/cm3."
        ),
    )


def create_copper_openmc_definition(
) -> OpenMCMaterialDefinition:
    return create_natural_element_definition(
        material_key="copper",
        element_symbol="Cu",
        notes=(
            "Natural elemental Copper. The project "
            "density remains 8.96 g/cm3."
        ),
    )


def create_tin_openmc_definition(
) -> OpenMCMaterialDefinition:
    return create_natural_element_definition(
        material_key="tin",
        element_symbol="Sn",
        notes=(
            "Natural elemental Tin. The project "
            "density remains 7.31 g/cm3."
        ),
    )


def create_ordinary_concrete_openmc_definition(
) -> OpenMCMaterialDefinition:
    # NIST Ordinary Concrete elemental weight fractions.
    #
    # The published rounded values sum to 0.999999. The definition accepts
    # that source-level rounding, and normalized_components returns fractions
    # normalized to unity before OpenMC construction.
    #
    # NIST lists 2.30 g/cm3 with this reference composition. The existing
    # project material uses 2.40 g/cm3. V1.14 retains the project density so
    # the deterministic and OpenMC calculations describe the same material.

    return OpenMCMaterialDefinition(
        material_key=(
            "concrete_ordinary"
        ),
        fraction_type="wo",
        components=(
            OpenMCMaterialComponent(
                element_symbol="H",
                fraction=0.022100,
            ),
            OpenMCMaterialComponent(
                element_symbol="C",
                fraction=0.002484,
            ),
            OpenMCMaterialComponent(
                element_symbol="O",
                fraction=0.574930,
            ),
            OpenMCMaterialComponent(
                element_symbol="Na",
                fraction=0.015208,
            ),
            OpenMCMaterialComponent(
                element_symbol="Mg",
                fraction=0.001266,
            ),
            OpenMCMaterialComponent(
                element_symbol="Al",
                fraction=0.019953,
            ),
            OpenMCMaterialComponent(
                element_symbol="Si",
                fraction=0.304627,
            ),
            OpenMCMaterialComponent(
                element_symbol="K",
                fraction=0.010045,
            ),
            OpenMCMaterialComponent(
                element_symbol="Ca",
                fraction=0.042951,
            ),
            OpenMCMaterialComponent(
                element_symbol="Fe",
                fraction=0.006435,
            ),
        ),
        composition_source=(
            NIST_ORDINARY_CONCRETE_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        reference_density_g_per_cm3=(
            2.30
        ),
        notes=(
            "NIST elemental weight fractions are "
            "used with the project's established "
            "2.40 g/cm3 Ordinary Concrete density."
        ),
    )

def create_polyethylene_openmc_definition(
) -> OpenMCMaterialDefinition:
    return OpenMCMaterialDefinition(
        material_key="polyethylene",
        fraction_type="ao",
        components=(
            OpenMCMaterialComponent(
                element_symbol="C",
                fraction=1.0 / 3.0,
            ),
            OpenMCMaterialComponent(
                element_symbol="H",
                fraction=2.0 / 3.0,
            ),
        ),
        composition_source=(
            "Stoichiometric polyethylene repeating-unit "
            "composition, (CH2)n."
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        notes=(
            "Polyethylene represented by the CH2 repeating "
            "unit. The project density remains 0.94 g/cm3."
        ),
    )


def get_openmc_material_definition_library(
) -> dict[
    str,
    OpenMCMaterialDefinition,
]:
    definitions = [
        create_lead_openmc_definition(),
        create_aluminum_openmc_definition(),
        create_ordinary_concrete_openmc_definition(),
        create_barite_concrete_openmc_definition(),
        create_water_openmc_definition(),
        create_tungsten_openmc_definition(),
        create_copper_openmc_definition(),
        create_tin_openmc_definition(),
        create_polyethylene_openmc_definition(),
    ]

    library = {
        definition.material_key: definition
        for definition
        in definitions
    }

    if (
        len(
            library
        )
        != len(
            definitions
        )
    ):
        raise ValueError(
            "OpenMC material-definition keys "
            "must be unique."
        )

    return library


def get_openmc_material_definition(
    material_key: str,
) -> OpenMCMaterialDefinition:
    normalized_key = (
        material_key
        .lower()
        .strip()
    )

    library = (
        get_openmc_material_definition_library()
    )

    if normalized_key not in library:
        raise ValueError(
            "OpenMC material composition has not yet "
            "been defined for project material: "
            f"{normalized_key}"
        )

    return library[
        normalized_key
    ]


def create_natural_element_definition(
    material_key: str,
    element_symbol: str,
    notes: str,
) -> OpenMCMaterialDefinition:
    return OpenMCMaterialDefinition(
        material_key=material_key,
        fraction_type="ao",
        components=(
            OpenMCMaterialComponent(
                element_symbol=element_symbol,
                fraction=1.0,
            ),
        ),
        composition_source=(
            OPENMC_NATURAL_ELEMENT_SOURCE
        ),
        density_source=(
            PROJECT_DENSITY_SOURCE
        ),
        notes=notes,
    )