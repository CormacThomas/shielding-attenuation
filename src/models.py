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
    # A single shielding layer that stores thickness and references a material object.
    thickness: float
    material: Material

    def __post_init__(self):
        if self.thickness < 0:
            raise ValueError("Layer thickness cannot be negative.")
        

@dataclass
class LayerResult:
    # Stores calculated quantities for one shielding layer.
    # This separates calculated values from the input Layer object.
    # layer = original layer input
    # mu_over_p = interpolated mass attenuation coefficient in cm^2/g
    # mu = linear attenuation coefficient in 1/cm
    # mfp = optical thickness of this layer in mean free paths
    # transmission = narrow-beam transmission through this layer


    layer: Layer
    mu_over_p: float
    mu: float
    mfp: float
    transmission: float

    def __post_init__(self):
        if self.mu_over_p < 0:
            raise ValueError("LayerResult mu/rho cannot be negative.")

        if self.mu < 0:
            raise ValueError("LayerResult mu cannot be negative.")

        if self.mfp < 0:
            raise ValueError("LayerResult MFP cannot be negative.")

        if self.transmission < 0:
            raise ValueError("LayerResult transmission cannot be negative.")
        
        if self.transmission > 1:
            raise ValueError("LayerResult transmission cannot be greater than 1.")


@dataclass
class ShieldingResult:
    # Stores the complete result of one shielding calculation.
    # This object keeps all output values together so main.py and output.py
    # do not need to pass many separate floats.
    # buildup_factor and buildup_corrected_flux are optional because not all
    # calculations use G-P buildup correction.

    
    layers: list[Layer]
    layer_results: list[LayerResult]
    photon_energy: float
    source_strength: float
    detector_distance: float
    total_thickness: float
    total_mfp: float
    total_transmission: float
    uncollided_flux: float
    buildup_factor: float | None = None
    buildup_corrected_flux: float | None = None

    def __post_init__(self):
        if self.photon_energy <= 0:
            raise ValueError("Photon energy must be greater than zero.")

        if self.source_strength < 0:
            raise ValueError("Source strength cannot be negative.")

        if self.detector_distance <= 0:
            raise ValueError("Detector distance must be greater than zero.")

        if self.total_thickness < 0:
            raise ValueError("Total thickness cannot be negative.")

        if self.total_mfp < 0:
            raise ValueError("Total MFP cannot be negative.")

        if self.total_transmission < 0:
            raise ValueError("Total transmission cannot be negative.")
        
        if self.total_transmission > 1:
            raise ValueError("Total transmission cannot be greater than 1.")

        if self.uncollided_flux < 0:
            raise ValueError("Uncollided flux cannot be negative.")

        if self.buildup_factor is not None and self.buildup_factor < 1:
            raise ValueError("Buildup factor cannot be less than 1.")

        if self.buildup_corrected_flux is not None and self.buildup_corrected_flux < 0:
            raise ValueError("Buildup-corrected flux cannot be negative.")