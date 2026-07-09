from dataclasses import dataclass


@dataclass
class Material:
    # shielding material with energy dependent attenuation data.
        # name = material name ex: "Lead"
        # density = material density in g/cm^3
        # energy = photon energy table in MeV
        # mu_over_p = mass attenuation coefficient in cm^2/g
    name: str
    density: float
    energy: list[float]
    mu_over_p: list[float]

    def __post_init__(self): # Error checks. Statements to prevent errors that could lead to incorrect values.
        if len(self.energy) != len(self.mu_over_p):
            raise ValueError(
                f"{self.name} has {len(self.energy)} energy values "f"but {len(self.mu_over_p)} mu/rho values."
            )
        if self.density <= 0:
            raise ValueError(f"{self.name} density must be positive.")
        
        if len(self.energy) < 2:
            raise ValueError(f"{self.name} must have at least two energy values.")

        for energy_value in self.energy:
            if energy_value <= 0:
                raise ValueError(f"{self.name} has a non positive energy value.")

        for mu_over_p_value in self.mu_over_p:
            if mu_over_p_value <= 0:
                raise ValueError(f"{self.name} has a non positive mu/rho value.")

        for i in range(len(self.energy) - 1):
            if self.energy[i] > self.energy[i + 1]:
                raise ValueError(f"{self.name} energy values must be sorted.")
            

@dataclass
class Layer:
    # a single shielding layer that stores thickness and references a material object.
    thickness: float
    material: Material

    def __post_init__(self):
        if self.thickness < 0:
            raise ValueError("Layer thickness cannot be negative.")