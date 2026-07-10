from models import Layer
from calculator import calculate_layer_mfp, calculate_layer_transmission

# Function to print:
    # Photon energy: MeV
    # Source strength: photons/s
    # Distance between source and detector: cm
    # Number of layers of shielding material
    # Total MFP (optical thickness)
    # Total transmission (fractional value)
    # Flux at detector: photons/cm^2/s
    # Shielding material properties
        # Material name
        # Material thickness: cm
        # Material density: g/cm^3

def print_results(
        layers: list[Layer],
        photon_energy: float,
        source_strength: float,
        detector_distance: float,
        total_thickness: float,
        total_mfp: float,
        total_transmission: float,
        flux: float,
        buildup_factor: float | None = None,
        buildup_corrected_flux: float | None = None) -> None:
    
    
    if buildup_factor is not None and buildup_corrected_flux is not None:
        print("Calculation mode: Narrow-beam uncollided flux + G-P buildup correction\n")
    else:
        print("Calculation mode: Narrow-beam uncollided flux\n")
    print(f"Photon energy: {photon_energy} MeV")
    print(f"Source strength: {source_strength:.3e} photons/s")
    print(f"Detector distance: {detector_distance} cm")
    print(f"Number of layers: {len(layers)}")
    print(f"Total thickness: {total_thickness} cm")
    print(f"Total MFP: {total_mfp}")
    print(f"Total transmission = {total_transmission}")
    print(f"Flux at detector: {flux:.6e} photons/cm^2/s")
    if buildup_factor is not None and buildup_corrected_flux is not None:
        print("\nG-P buildup correction:")
        print("Buildup mode: Single-layer lead exposure buildup")
        print(f"Buildup factor: {buildup_factor}")
        print(f"Buildup-corrected flux: {buildup_corrected_flux:.6e} photons/cm^2/s")

    print("\nLayers:")

    for layer in layers:

        layer_mfp = calculate_layer_mfp(layer, photon_energy)
        layer_transmission = calculate_layer_transmission(layer, photon_energy)
        
        print(f"\nMaterial: {layer.material.name}")
        print(f"Thickness: {layer.thickness} cm")
        print(f"Density: {layer.material.density} g/cm^3")
        print(f"Layer MFP: {layer_mfp}")
        print(f"Layer transmission: {layer_transmission}")