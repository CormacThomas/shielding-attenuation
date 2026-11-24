"""Verification cases migrated from the original validation runner."""

from typing import cast

from shielding.data.materials import get_material_library
from shielding.monte_carlo.materials import (
    FRACTION_SUM_ABSOLUTE_TOLERANCE,
    get_openmc_material_definition,
    get_openmc_material_definition_library,
)
from shielding.monte_carlo.model_builder import create_openmc_materials
from shielding.scenarios.models import ShieldingScenario
from tests.checks import (
    assert_close,
    assert_equal,
    assert_not_none,
    assert_raises,
)


def test_material_library_coverage() -> None:
    material_definitions = get_openmc_material_definition_library()

    project_material_keys = set(get_material_library())

    expected_material_keys = {
        "lead",
        "aluminum",
        "concrete_ordinary",
        "concrete_barite",
        "water",
        "tungsten",
        "copper",
        "tin",
        "polyethylene",
    }

    assert_equal(
        "V1.14 deterministic material library contains the expected nine materials",
        project_material_keys,
        expected_material_keys,
    )

    assert_equal(
        "V1.14 every deterministic material has an OpenMC composition definition",
        set(material_definitions),
        project_material_keys,
    )


def test_elemental_materials() -> None:
    # Elemental materials

    lead_definition = get_openmc_material_definition("  LEAD  ")

    assert_equal(
        "V1.14 OpenMC material lookup normalizes Lead key",
        lead_definition.material_key,
        "lead",
    )

    assert_equal(
        "V1.14 Lead uses atom fractions",
        lead_definition.fraction_type,
        "ao",
    )

    assert_equal(
        "V1.14 Lead uses natural Pb",
        [
            (
                component.element_symbol,
                component.fraction,
            )
            for component in lead_definition.components
        ],
        [
            (
                "Pb",
                1.0,
            )
        ],
    )

    tungsten_definition = get_openmc_material_definition("tungsten")

    assert_equal(
        "V1.14 Tungsten uses atom fractions",
        tungsten_definition.fraction_type,
        "ao",
    )

    assert_equal(
        "V1.14 Tungsten uses natural W",
        [
            (
                component.element_symbol,
                component.fraction,
            )
            for component in tungsten_definition.components
        ],
        [
            (
                "W",
                1.0,
            )
        ],
    )


def test_water_material() -> None:
    # Water

    water_definition = get_openmc_material_definition("water")

    assert_equal(
        "V1.14 Water uses atom fractions",
        water_definition.fraction_type,
        "ao",
    )

    water_fraction_by_element = {
        component.element_symbol: (component.fraction)
        for component in water_definition.components
    }

    assert_equal(
        "V1.14 Water contains Hydrogen and Oxygen",
        set(water_fraction_by_element),
        {
            "H",
            "O",
        },
    )

    assert_close(
        "V1.14 Water Hydrogen atom fraction",
        water_fraction_by_element["H"],
        2.0 / 3.0,
        1.0e-12,
    )

    assert_close(
        "V1.14 Water Oxygen atom fraction",
        water_fraction_by_element["O"],
        1.0 / 3.0,
        1.0e-12,
    )


def test_ordinary_concrete_material() -> None:
    # Ordinary Concrete

    concrete_definition = get_openmc_material_definition("concrete_ordinary")

    assert_equal(
        "V1.14 Ordinary Concrete uses weight fractions",
        concrete_definition.fraction_type,
        "wo",
    )

    assert_equal(
        "V1.14 Ordinary Concrete contains ten elements",
        len(concrete_definition.components),
        10,
    )

    expected_concrete_fraction_by_element = {
        "H": 0.022100,
        "C": 0.002484,
        "O": 0.574930,
        "Na": 0.015208,
        "Mg": 0.001266,
        "Al": 0.019953,
        "Si": 0.304627,
        "K": 0.010045,
        "Ca": 0.042951,
        "Fe": 0.006435,
    }

    concrete_fraction_by_element = {
        component.element_symbol: (component.fraction)
        for component in concrete_definition.components
    }

    assert_equal(
        "V1.14 Ordinary Concrete preserves NIST elements",
        set(concrete_fraction_by_element),
        set(expected_concrete_fraction_by_element),
    )

    for (
        element_symbol,
        expected_fraction,
    ) in expected_concrete_fraction_by_element.items():
        assert_close(
            "V1.14 Ordinary Concrete preserves "
            f"{element_symbol} source weight fraction",
            concrete_fraction_by_element[element_symbol],
            expected_fraction,
            1.0e-12,
        )

    assert_close(
        "V1.14 rounded NIST Concrete fractions remain within accepted tolerance",
        concrete_definition.component_fraction_sum,
        1.0,
        (FRACTION_SUM_ABSOLUTE_TOLERANCE),
    )

    assert_close(
        "V1.14 normalized Concrete fractions sum to one",
        sum(
            component.fraction
            for component in (concrete_definition.normalized_components)
        ),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.14 Concrete definition preserves NIST reference density metadata",
        assert_not_none(
            "V1.14 Concrete reference density exists",
            (concrete_definition.reference_density_g_per_cm3),
        ),
        2.30,
        1.0e-12,
    )


def test_synthetic_material_construction() -> None:
    expected_material_keys = {
        "lead",
        "aluminum",
        "concrete_ordinary",
        "concrete_barite",
        "water",
        "tungsten",
        "copper",
        "tin",
        "polyethylene",
    }

    # Synthetic OpenMC material construction

    class SyntheticOpenMCMaterial:
        def __init__(
            self,
            material_id: int,
            name: str,
        ) -> None:
            self.material_id = material_id

            self.name = name

            self.element_calls: list[
                tuple[
                    str,
                    float,
                    str,
                ]
            ] = []

            self.density_units: str | None = None

            self.density_value: float | None = None

        def add_element(
            self,
            element_symbol: str,
            fraction: float,
            percent_type: str = "ao",
        ) -> None:
            self.element_calls.append(
                (
                    element_symbol,
                    fraction,
                    percent_type,
                )
            )

        def set_density(
            self,
            units: str,
            density: float,
        ) -> None:
            self.density_units = units
            self.density_value = density

    class SyntheticOpenMCMaterials(list):
        def __init__(
            self,
            materials,
        ) -> None:
            super().__init__(materials)

            self.cross_sections: str | None = None

    class SyntheticOpenMCModule:
        Material = SyntheticOpenMCMaterial

        Materials = SyntheticOpenMCMaterials

    class SyntheticLayerSpec:
        def __init__(
            self,
            material_key: str,
        ) -> None:
            self.material_key = material_key

    class SyntheticGeometry:
        def __init__(
            self,
            material_keys: list[str],
        ) -> None:
            self.layers = [
                SyntheticLayerSpec(material_key) for material_key in material_keys
            ]

    class SyntheticScenario:
        def __init__(
            self,
            material_keys: list[str],
        ) -> None:
            self.geometry = SyntheticGeometry(material_keys)

    synthetic_scenario = cast(
        ShieldingScenario,
        SyntheticScenario(
            [
                "lead",
                "lead",
                "aluminum",
                "concrete_ordinary",
                "concrete_barite",
                "water",
                "tungsten",
                "copper",
                "tin",
                "polyethylene",
            ]
        ),
    )

    (
        synthetic_material_collection,
        synthetic_materials_by_key,
    ) = create_openmc_materials(
        openmc_module=(SyntheticOpenMCModule()),
        scenario=synthetic_scenario,
        cross_sections_path=("/synthetic/cross_sections.xml"),
    )

    assert_equal(
        "V1.14 repeated layers reuse one OpenMC material",
        len(synthetic_materials_by_key),
        9,
    )

    assert_equal(
        "V1.14 OpenMC material collection contains nine materials",
        len(synthetic_material_collection),
        9,
    )

    assert_equal(
        "V1.14 OpenMC material collection stores cross-section path",
        (synthetic_material_collection.cross_sections),
        "/synthetic/cross_sections.xml",
    )

    project_materials = get_material_library()

    for material_key in sorted(expected_material_keys):
        synthetic_material = synthetic_materials_by_key[material_key]

        assert_equal(
            f"V1.14 {material_key} OpenMC density units",
            synthetic_material.density_units,
            "g/cm3",
        )

        synthetic_density = synthetic_material.density_value

        if synthetic_density is None:
            raise AssertionError(
                f"V1.14 synthetic OpenMC material {material_key} did not store density."
            )

        assert_close(
            f"V1.14 {material_key} OpenMC density matches project material",
            synthetic_density,
            (project_materials[material_key].density),
            1.0e-12,
        )

    assert_close(
        "V1.14 Ordinary Concrete retains project density for matched calculations",
        (synthetic_materials_by_key["concrete_ordinary"].density_value),
        2.40,
        1.0e-12,
    )
    assert_close(
        "V1.14 Barite Concrete retains project density for matched calculations",
        (synthetic_materials_by_key["concrete_barite"].density_value),
        3.50,
        1.0e-12,
    )
    assert_equal(
        "V1.14 Lead OpenMC construction remains one natural Pb atom-fraction component",
        (synthetic_materials_by_key["lead"].element_calls),
        [
            (
                "Pb",
                1.0,
                "ao",
            )
        ],
    )

    assert_equal(
        "V1.14 Tungsten OpenMC construction uses one natural W atom-fraction component",
        (synthetic_materials_by_key["tungsten"].element_calls),
        [
            (
                "W",
                1.0,
                "ao",
            )
        ],
    )

    water_element_calls = synthetic_materials_by_key["water"].element_calls

    assert_equal(
        "V1.14 Water OpenMC construction uses two atom-fraction components",
        len(water_element_calls),
        2,
    )

    assert_equal(
        "V1.14 Water OpenMC construction uses only atom fractions",
        {
            percent_type
            for (
                _element_symbol,
                _fraction,
                percent_type,
            ) in water_element_calls
        },
        {
            "ao",
        },
    )

    concrete_element_calls = synthetic_materials_by_key[
        "concrete_ordinary"
    ].element_calls

    assert_equal(
        "V1.14 Concrete OpenMC construction uses ten weight-fraction components",
        len(concrete_element_calls),
        10,
    )

    assert_equal(
        "V1.14 Concrete OpenMC construction uses only weight fractions",
        {
            percent_type
            for (
                _element_symbol,
                _fraction,
                percent_type,
            ) in concrete_element_calls
        },
        {
            "wo",
        },
    )

    assert_close(
        "V1.14 Concrete OpenMC construction normalizes weight fractions",
        sum(
            fraction
            for (
                _element_symbol,
                fraction,
                _percent_type,
            ) in concrete_element_calls
        ),
        1.0,
        1.0e-12,
    )

    assert_raises(
        "V1.14 undefined OpenMC material composition lookup is rejected",
        ValueError,
        lambda: get_openmc_material_definition("unobtainium"),
        ("OpenMC material composition has not yet been defined"),
    )

    unknown_project_scenario = cast(
        ShieldingScenario,
        SyntheticScenario(
            [
                "unobtainium",
            ]
        ),
    )

    assert_raises(
        "V1.14 unknown project material is rejected before OpenMC construction",
        ValueError,
        lambda: create_openmc_materials(
            openmc_module=(SyntheticOpenMCModule()),
            scenario=(unknown_project_scenario),
            cross_sections_path=("/synthetic/cross_sections.xml"),
        ),
        "unknown project material key",
    )

    polyethylene_definition = get_openmc_material_definition("polyethylene")

    assert_equal(
        "V1.14 Polyethylene uses atom fractions",
        polyethylene_definition.fraction_type,
        "ao",
    )

    polyethylene_fraction_by_element = {
        component.element_symbol: (component.fraction)
        for component in polyethylene_definition.components
    }

    assert_close(
        "V1.14 Polyethylene Carbon atom fraction",
        polyethylene_fraction_by_element["C"],
        1.0 / 3.0,
        1.0e-12,
    )

    assert_close(
        "V1.14 Polyethylene Hydrogen atom fraction",
        polyethylene_fraction_by_element["H"],
        2.0 / 3.0,
        1.0e-12,
    )

    project_material_keys = set(get_material_library())

    openmc_material_keys = set(get_openmc_material_definition_library())

    assert_equal(
        "V1.14 every deterministic material has an OpenMC composition definition",
        openmc_material_keys,
        project_material_keys,
    )

    barite_definition = get_openmc_material_definition("concrete_barite")

    assert_equal(
        "V1.14 Barite Concrete uses weight fractions",
        barite_definition.fraction_type,
        "wo",
    )

    assert_equal(
        "V1.14 Barite Concrete contains nine elements",
        len(barite_definition.components),
        9,
    )

    barite_fraction_by_element = {
        component.element_symbol: (component.fraction)
        for component in barite_definition.components
    }

    assert_close(
        "V1.14 Barite Concrete preserves Barium source weight fraction",
        barite_fraction_by_element["Ba"],
        0.463400,
        1.0e-12,
    )

    assert_close(
        "V1.14 normalized Barite Concrete fractions sum to one",
        sum(
            component.fraction
            for component in (barite_definition.normalized_components)
        ),
        1.0,
        1.0e-12,
    )

    assert_close(
        "V1.14 Barite Concrete preserves NIST reference density metadata",
        assert_not_none(
            "V1.14 Barite Concrete reference density exists",
            (barite_definition.reference_density_g_per_cm3),
        ),
        3.35,
        1.0e-12,
    )

    barite_element_calls = synthetic_materials_by_key["concrete_barite"].element_calls

    assert_equal(
        "V1.14 Barite Concrete OpenMC construction "
        "uses nine weight-fraction components",
        len(barite_element_calls),
        9,
    )

    assert_equal(
        "V1.14 Barite Concrete OpenMC construction uses only weight fractions",
        {
            percent_type
            for (
                _element_symbol,
                _fraction,
                percent_type,
            ) in barite_element_calls
        },
        {
            "wo",
        },
    )

    assert_close(
        "V1.14 Barite Concrete OpenMC construction normalizes weight fractions",
        sum(
            fraction
            for (
                _element_symbol,
                fraction,
                _percent_type,
            ) in barite_element_calls
        ),
        1.0,
        1.0e-12,
    )
