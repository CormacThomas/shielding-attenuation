from material_library import get_material_library
from models import Layer
from source_calculator import calculate_isotope_source_result, calculate_manual_source_result
from source_models import IsotopeSource, ManualPhotonSource, PhotonLine
from unit_conversions import convert_activity_to_bq


materials = get_material_library()
layers = [Layer(5.0, materials["lead"])]
detector_distance = 100.0

manual_source = ManualPhotonSource(
    0.6617,
    3.7e10,
)

manual_result = calculate_manual_source_result(
    manual_source,
    layers,
    detector_distance,
    apply_buildup=True,
)

print("\nManual source result:")
print(f"Total uncollided flux: {manual_result.total_uncollided_flux:.6e}")
print(f"Total buildup-corrected flux: {manual_result.total_buildup_corrected_flux:.6e}")

cs137_activity_bq = convert_activity_to_bq(1.0, "ci")

cs137_source = IsotopeSource(
    "Cs-137",
    cs137_activity_bq,
    [
        PhotonLine(0.6617, 1.0),
    ],
)

cs137_result = calculate_isotope_source_result(
    cs137_source,
    layers,
    detector_distance,
    apply_buildup=True,
)

print("\nCs-137 source result:")
print(f"Activity: {cs137_result.activity_bq:.6e} Bq")
print(f"Total uncollided flux: {cs137_result.total_uncollided_flux:.6e}")
print(f"Total buildup-corrected flux: {cs137_result.total_buildup_corrected_flux:.6e}")