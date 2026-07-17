# V1.09 relative material cost library.
#
# These values are intentionally simplified, user-editable cost indices.
# They are not current market prices and should not be interpreted as dollars.
#
# Ordinary concrete is assigned the baseline index of 1.0.
# Other values provide a first comparative design metric.
#
# Future versions can replace these values with:
#   - documented cost per unit mass
#   - user-entered cost data
#   - scenario-specific procurement estimates


from dataclasses import dataclass


RELATIVE_COST_BASIS_DESCRIPTION = (
    "Relative cost indices are simplified comparative values with ordinary "
    "concrete assigned an index of 1.0. They are not market prices."
)


@dataclass(frozen=True)
class MaterialCostData:
    material_key: str
    relative_cost_index: float
    description: str

    def __post_init__(self):
        if self.material_key.strip() == "":
            raise ValueError("Material cost key cannot be empty.")

        if self.relative_cost_index <= 0:
            raise ValueError(
                "Relative material cost index must be greater than zero."
            )

        if self.description.strip() == "":
            raise ValueError(
                "Material cost description cannot be empty."
            )


def get_material_cost_library() -> dict[str, MaterialCostData]:
    # Initial comparative cost assumptions.
    #
    # These are deliberately approximate and only intended to make relative
    # cost optimization possible before a more rigorous procurement model is
    # introduced.

    return {
        "water": MaterialCostData(
            "water",
            0.25,
            "Low-cost bulk shielding medium.",
        ),
        "concrete_ordinary": MaterialCostData(
            "concrete_ordinary",
            1.0,
            "Baseline relative cost material.",
        ),
        "concrete_barite": MaterialCostData(
            "concrete_barite",
            1.6,
            "Specialty high-density concrete.",
        ),
        "polyethylene": MaterialCostData(
            "polyethylene",
            2.0,
            "Manufactured polymer shielding material.",
        ),
        "lead": MaterialCostData(
            "lead",
            3.0,
            "Dense metal with moderate comparative material cost.",
        ),
        "aluminum": MaterialCostData(
            "aluminum",
            4.0,
            "Manufactured structural metal.",
        ),
        "tin": MaterialCostData(
            "tin",
            7.0,
            "Higher comparative metal cost.",
        ),
        "copper": MaterialCostData(
            "copper",
            8.0,
            "Higher comparative metal cost.",
        ),
        "tungsten": MaterialCostData(
            "tungsten",
            25.0,
            "Very high comparative material and manufacturing cost.",
        ),
    }


def get_relative_cost_index(material_key: str) -> float:
    key = material_key.lower().strip()
    cost_library = get_material_cost_library()

    if key not in cost_library:
        raise ValueError(
            f"No relative cost index found for material: {material_key}"
        )

    return cost_library[key].relative_cost_index