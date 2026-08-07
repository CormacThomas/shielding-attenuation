# V1.14 real-OpenMC material XML construction check.
#
# This script:
#
#   - loads the actual OpenMC Python package;
#   - constructs every material in the deterministic material library;
#   - verifies one-to-one deterministic/OpenMC material coverage;
#   - verifies project densities;
#   - exports a real OpenMC materials.xml file;
#   - parses the exported XML;
#   - writes a compact JSON summary;
#   - performs no particle transport.
#
# Run this script inside the same OpenMC environment used for V1.13.


from __future__ import annotations


import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ElementTree


REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT
    / "src"
)

if str(
    SOURCE_DIRECTORY
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SOURCE_DIRECTORY
        ),
    )


from material_library import (  # noqa: E402
    get_material_library,
)
from openmc_material_library import (  # noqa: E402
    get_openmc_material_definition_library,
)
from openmc_model_builder import (  # noqa: E402
    create_openmc_materials,
    get_configured_cross_sections_path,
    load_openmc_module,
)


OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "results"
    / "v1.14"
    / "development"
    / "material_xml_check"
)

MATERIALS_XML_PATH = (
    OUTPUT_DIRECTORY
    / "materials.xml"
)

SUMMARY_PATH = (
    OUTPUT_DIRECTORY
    / "material_check_summary.json"
)

DENSITY_ABSOLUTE_TOLERANCE = (
    1.0e-12
)


class MaterialCheckLayer:
    def __init__(
        self,
        material_key: str,
    ) -> None:
        self.material_key = (
            material_key
        )


class MaterialCheckGeometry:
    def __init__(
        self,
        material_keys: list[str],
    ) -> None:
        self.layers = [
            MaterialCheckLayer(
                material_key
            )
            for material_key
            in material_keys
        ]


class MaterialCheckScenario:
    def __init__(
        self,
        material_keys: list[str],
    ) -> None:
        self.geometry = (
            MaterialCheckGeometry(
                material_keys
            )
        )


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(
            message
        )


def create_material_summary(
    *,
    material_key: str,
    project_material,
    openmc_material,
    material_definition,
) -> dict[str, object]:
    require(
        openmc_material.name
        == project_material.name,
        (
            "OpenMC material name does not match "
            f"project material for {material_key}."
        ),
    )

    require(
        openmc_material.density_units
        == "g/cm3",
        (
            "OpenMC density units are not g/cm3 "
            f"for {material_key}."
        ),
    )

    openmc_density = (
        openmc_material.density
    )

    require(
        openmc_density is not None,
        (
            "OpenMC material has no density "
            f"for {material_key}."
        ),
    )

    require(
        math.isclose(
            openmc_density,
            project_material.density,
            rel_tol=0.0,
            abs_tol=(
                DENSITY_ABSOLUTE_TOLERANCE
            ),
        ),
        (
            "OpenMC density does not match the "
            f"project density for {material_key}: "
            f"{openmc_density} versus "
            f"{project_material.density}."
        ),
    )

    normalized_components = [
        {
            "element_symbol": (
                component.element_symbol
            ),
            "fraction": (
                component.fraction
            ),
        }
        for component
        in (
            material_definition
            .normalized_components
        )
    ]

    return {
        "material_key": material_key,
        "display_name": (
            project_material.name
        ),
        "openmc_material_id": (
            openmc_material.id
        ),
        "density_g_per_cm3": (
            openmc_density
        ),
        "fraction_type": (
            material_definition
            .fraction_type
        ),
        "normalized_components": (
            normalized_components
        ),
        "composition_source": (
            material_definition
            .composition_source
        ),
        "density_source": (
            material_definition
            .density_source
        ),
        "reference_density_g_per_cm3": (
            material_definition
            .reference_density_g_per_cm3
        ),
        "expanded_openmc_nuclide_count": len(
            openmc_material.nuclides
        ),
    }


def validate_exported_xml(
    *,
    materials_xml_path: Path,
    expected_material_names: set[str],
    expected_material_count: int,
) -> None:
    require(
        materials_xml_path.is_file(),
        (
            "OpenMC materials XML was not created: "
            f"{materials_xml_path}"
        ),
    )

    xml_tree = (
        ElementTree.parse(
            materials_xml_path
        )
    )

    xml_root = (
        xml_tree.getroot()
    )

    require(
        xml_root.tag == "materials",
        (
            "Unexpected materials XML root tag: "
            f"{xml_root.tag}"
        ),
    )

    material_nodes = (
        xml_root.findall(
            "material"
        )
    )

    require(
        len(
            material_nodes
        )
        == expected_material_count,
        (
            "Exported materials XML contains "
            f"{len(material_nodes)} materials; "
            f"expected {expected_material_count}."
        ),
    )

    material_names = {
        material_node.attrib.get(
            "name",
            "",
        )
        for material_node
        in material_nodes
    }

    require(
        material_names
        == expected_material_names,
        (
            "Exported materials XML names do not "
            "match the project material library. "
            f"Received {sorted(material_names)}."
        ),
    )

    material_ids = [
        material_node.attrib.get(
            "id"
        )
        for material_node
        in material_nodes
    ]

    require(
        None not in material_ids,
        (
            "At least one exported OpenMC material "
            "does not have an ID."
        ),
    )

    require(
        len(
            material_ids
        )
        == len(
            set(
                material_ids
            )
        ),
        (
            "Exported OpenMC material IDs are "
            "not unique."
        ),
    )


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    project_material_library = (
        get_material_library()
    )

    openmc_definition_library = (
        get_openmc_material_definition_library()
    )

    project_material_keys = set(
        project_material_library
    )

    openmc_material_keys = set(
        openmc_definition_library
    )

    require(
        openmc_material_keys
        == project_material_keys,
        (
            "OpenMC material-definition coverage "
            "does not match the deterministic "
            "material library.\n"
            f"Project-only keys: "
            f"{sorted(project_material_keys - openmc_material_keys)}\n"
            f"OpenMC-only keys: "
            f"{sorted(openmc_material_keys - project_material_keys)}"
        ),
    )

    ordered_material_keys = list(
        project_material_library
    )

    require(
        len(
            ordered_material_keys
        )
        == 9,
        (
            "V1.14 material XML check expected "
            "nine project materials."
        ),
    )

    openmc_module = (
        load_openmc_module()
    )

    cross_sections_path = (
        get_configured_cross_sections_path(
            openmc_module
        )
    )

    scenario = (
        MaterialCheckScenario(
            ordered_material_keys
        )
    )

    (
        openmc_materials,
        openmc_materials_by_key,
    ) = create_openmc_materials(
        openmc_module=(
            openmc_module
        ),
        scenario=scenario,
        cross_sections_path=(
            cross_sections_path
        ),
    )

    require(
        set(
            openmc_materials_by_key
        )
        == project_material_keys,
        (
            "Real OpenMC material construction did "
            "not return all project material keys."
        ),
    )

    require(
        len(
            openmc_materials
        )
        == len(
            ordered_material_keys
        ),
        (
            "Real OpenMC Materials collection has "
            "the wrong number of materials."
        ),
    )

    material_summaries = []

    for material_key in (
        ordered_material_keys
    ):
        material_summaries.append(
            create_material_summary(
                material_key=(
                    material_key
                ),
                project_material=(
                    project_material_library[
                        material_key
                    ]
                ),
                openmc_material=(
                    openmc_materials_by_key[
                        material_key
                    ]
                ),
                material_definition=(
                    openmc_definition_library[
                        material_key
                    ]
                ),
            )
        )

    if MATERIALS_XML_PATH.exists():
        MATERIALS_XML_PATH.unlink()

    openmc_materials.export_to_xml(
        path=(
            MATERIALS_XML_PATH
        )
    )

    validate_exported_xml(
        materials_xml_path=(
            MATERIALS_XML_PATH
        ),
        expected_material_names={
            material.name
            for material
            in (
                project_material_library
                .values()
            )
        },
        expected_material_count=len(
            ordered_material_keys
        ),
    )

    summary = {
        "record_type": (
            "openmc_material_xml_check"
        ),
        "version": "1.14",
        "transport_executed": False,
        "openmc_version": str(
            openmc_module.__version__
        ),
        "cross_sections_path": (
            cross_sections_path
        ),
        "material_count": len(
            material_summaries
        ),
        "materials_xml_path": str(
            MATERIALS_XML_PATH
            .relative_to(
                REPOSITORY_ROOT
            )
        ),
        "materials": (
            material_summaries
        ),
    }

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "=" * 72
    )
    print(
        "V1.14 OPENMC MATERIAL XML CHECK"
    )
    print(
        "=" * 72
    )

    print(
        "OpenMC version: "
        f"{openmc_module.__version__}"
    )

    print(
        "Cross sections: "
        f"{cross_sections_path}"
    )

    print(
        "Transport executed: No"
    )

    print(
        "Materials constructed: "
        f"{len(material_summaries)}"
    )

    print()

    for material_summary in (
        material_summaries
    ):
        print(
            f"{material_summary['material_key']}: "
            f"{material_summary['display_name']}"
        )

        print(
            "  Density: "
            f"{material_summary['density_g_per_cm3']:.6g} "
            "g/cm3"
        )

        print(
            "  Fraction basis: "
            f"{material_summary['fraction_type']}"
        )

        print(
            "  OpenMC nuclides: "
            f"{material_summary['expanded_openmc_nuclide_count']}"
        )

    print()

    print(
        "Created:"
    )

    print(
        "  "
        f"{MATERIALS_XML_PATH}"
    )

    print(
        "  "
        f"{SUMMARY_PATH}"
    )

    print()

    print(
        "PASS: All nine project materials were "
        "constructed and exported by real OpenMC "
        "without particle transport."
    )


if __name__ == "__main__":
    main()