# Concentric spherical shielding geometry models.
#
# V1.11 introduces a reproducible physical geometry definition that can
# eventually be shared by the deterministic and OpenMC calculation backends.
#
# Initial supported geometry:
#   - point source at the center
#   - optional spherical source cavity
#   - zero or more concentric shielding layers
#   - evaluation location at a fixed radius
#
# The geometry model stores physical inputs and derives shell radii. It does
# not perform photon attenuation, optimization, or OpenMC calculations.


from dataclasses import dataclass, field


@dataclass
class ShieldLayerSpec:
    # Input specification for one concentric shielding layer.
    #
    # material_key:
    #   Stable internal material identifier from material_library.py.
    #
    # thickness_cm:
    #   Radial thickness of the spherical layer in centimeters.

    material_key: str
    thickness_cm: float

    def __post_init__(self) -> None:
        self.material_key = self.material_key.lower().strip()

        if self.material_key == "":
            raise ValueError(
                "Shield layer material key cannot be empty."
            )

        if self.thickness_cm <= 0:
            raise ValueError(
                "Shield layer thickness must be greater than zero."
            )


@dataclass(frozen=True)
class SphericalShell:
    # Derived physical bounds for one spherical shielding shell.
    #
    # These values are calculated from the source-cavity radius and the
    # ordered layer thicknesses. Users do not enter the inner and outer
    # radii separately.

    layer_index: int
    material_key: str
    inner_radius_cm: float
    outer_radius_cm: float

    @property
    def thickness_cm(self) -> float:
        return self.outer_radius_cm - self.inner_radius_cm


@dataclass
class ConcentricSphericalGeometry:
    # Concentric spherical point-source geometry.
    #
    # source_cavity_radius_cm:
    #   Radius of the unshielded central source cavity.
    #   Zero is allowed for backward-compatible point-source cases.
    #
    # evaluation_radius_cm:
    #   Radial distance from the source center to the detector or response
    #   evaluation location.
    #
    # layers:
    #   Ordered shielding layers from innermost to outermost.
    #
    # An empty layer list is permitted for optimization scenarios where the
    # shield design has not yet been selected.

    source_cavity_radius_cm: float
    evaluation_radius_cm: float
    layers: list[ShieldLayerSpec] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.source_cavity_radius_cm < 0:
            raise ValueError(
                "Source cavity radius cannot be negative."
            )

        if self.evaluation_radius_cm <= 0:
            raise ValueError(
                "Evaluation radius must be greater than zero."
            )

        if (
            self.evaluation_radius_cm
            <= self.source_cavity_radius_cm
        ):
            raise ValueError(
                "Evaluation radius must be greater than "
                "the source cavity radius."
            )

        if (
            self.outer_shield_radius_cm
            >= self.evaluation_radius_cm
        ):
            raise ValueError(
                "Evaluation radius must be beyond the outer "
                "shield radius."
            )

    @property
    def total_shield_thickness_cm(self) -> float:
        return sum(
            layer.thickness_cm
            for layer in self.layers
        )

    @property
    def outer_shield_radius_cm(self) -> float:
        return (
            self.source_cavity_radius_cm
            + self.total_shield_thickness_cm
        )

    def create_shells(self) -> list[SphericalShell]:
        # Derive the inner and outer radius of every layer.
        #
        # Layer order is preserved:
        #   layers[0] is the innermost shielding layer.

        shells = []
        current_inner_radius = self.source_cavity_radius_cm

        for layer_index, layer in enumerate(self.layers):
            outer_radius = (
                current_inner_radius
                + layer.thickness_cm
            )

            shell = SphericalShell(
                layer_index=layer_index,
                material_key=layer.material_key,
                inner_radius_cm=current_inner_radius,
                outer_radius_cm=outer_radius,
            )

            shells.append(shell)
            current_inner_radius = outer_radius

        return shells