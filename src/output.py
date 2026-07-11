
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

from models import ShieldingResult
from source_models import SourceCalculationResult


def print_results(result: ShieldingResult) -> None:
    if result.buildup_factor is not None and result.buildup_corrected_flux is not None:
        print("Calculation mode: Narrow-beam uncollided flux + G-P buildup correction\n")
    else:
        print("Calculation mode: Narrow-beam uncollided flux\n")

    print(f"Photon energy: {result.photon_energy} MeV")
    print(f"Source strength: {result.source_strength:.3e} photons/s")
    print(f"Detector distance: {result.detector_distance} cm")
    print(f"Number of layers: {len(result.layers)}")
    print(f"Total thickness: {result.total_thickness} cm")
    print(f"Total MFP: {result.total_mfp}")
    print(f"Total transmission: {result.total_transmission}")
    print(f"Uncollided flux at detector: {result.uncollided_flux:.6e} photons/cm^2/s")

    if result.buildup_factor is not None and result.buildup_corrected_flux is not None:
        print("\nG-P buildup correction:")
        print(f"Buildup mode: Single-layer {result.layers[0].material.name} exposure buildup")
        print(f"Buildup factor: {result.buildup_factor}")
        print(
            f"Buildup-corrected flux: "
            f"{result.buildup_corrected_flux:.6e} photons/cm^2/s"
        )

    print("\nLayers:")

    for layer_result in result.layer_results:
        print(f"\nMaterial: {layer_result.layer.material.name}")
        print(f"Thickness: {layer_result.layer.thickness} cm")
        print(f"Density: {layer_result.layer.material.density} g/cm^3")
        print(f"mu/rho: {layer_result.mu_over_p} cm^2/g")
        print(f"mu: {layer_result.mu} 1/cm")
        print(f"Layer MFP: {layer_result.mfp}")
        print(f"Layer transmission: {layer_result.transmission}")


def print_source_results(result: SourceCalculationResult) -> None:
    print("\nSource calculation results")
    print(f"Source: {result.source_name}")

    if result.activity_bq is not None:
        print(f"Activity: {result.activity_bq:.6e} Bq")

    print(f"Number of photon lines: {len(result.line_results)}")
    print(f"Total uncollided flux: {result.total_uncollided_flux:.6e} photons/cm^2/s")

    if result.total_buildup_corrected_flux is not None:
        print(
            f"Total buildup-corrected flux: "
            f"{result.total_buildup_corrected_flux:.6e} photons/cm^2/s"
        )

    print("\nPhoton line results:")

    for i, line_result in enumerate(result.line_results):
        shielding_result = line_result.shielding_result

        print(f"\nLine {i + 1}")
        print(f"Photon energy: {line_result.photon_line.energy} MeV")
        print(f"Emission intensity: {line_result.photon_line.intensity} photons/decay")
        print(f"Photon emission rate: {line_result.photon_rate:.6e} photons/s")
        print(f"Transmission: {shielding_result.total_transmission}")
        print(f"Total MFP: {shielding_result.total_mfp}")
        print(
            f"Uncollided flux: "
            f"{shielding_result.uncollided_flux:.6e} photons/cm^2/s"
        )

        if shielding_result.buildup_factor is not None:
            print(f"Buildup factor: {shielding_result.buildup_factor}")

        if shielding_result.buildup_corrected_flux is not None:
            print(
                f"Buildup-corrected flux: "
                f"{shielding_result.buildup_corrected_flux:.6e} photons/cm^2/s"
            )