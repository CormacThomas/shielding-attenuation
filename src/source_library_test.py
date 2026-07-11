from material_library import get_material_library
from models import Layer
from source_calculator import calculate_isotope_source_result
from source_library import create_isotope_source, get_available_isotopes
from unit_conversions import convert_activity_to_bq


materials = get_material_library()
layers = [Layer(5.0, materials["lead"])]
detector_distance = 100.0

activity_bq = convert_activity_to_bq(1.0, "ci")

print("Available isotope sources:")
for isotope_key in get_available_isotopes():
    print(f"- {isotope_key}")

cs137_source = create_isotope_source("cs137", activity_bq)

cs137_result = calculate_isotope_source_result(
    cs137_source,
    layers,
    detector_distance,
    apply_buildup=True,
)

print("\nCs-137 source result:")
print(f"Source name: {cs137_result.source_name}")
print(f"Activity: {cs137_result.activity_bq:.6e} Bq")
print(f"Number of photon lines: {len(cs137_result.line_results)}")
print(f"Total uncollided flux: {cs137_result.total_uncollided_flux:.6e} photons/cm^2/s")
print(
    f"Total buildup-corrected flux: "
    f"{cs137_result.total_buildup_corrected_flux:.6e} photons/cm^2/s"
)

co60_source = create_isotope_source("co60", activity_bq)

co60_result = calculate_isotope_source_result(
    co60_source,
    layers,
    detector_distance,
    apply_buildup=True,
)

print("\nCo-60 source result:")
print(f"Source name: {co60_result.source_name}")
print(f"Activity: {co60_result.activity_bq:.6e} Bq")
print(f"Number of photon lines: {len(co60_result.line_results)}")
print(f"Total uncollided flux: {co60_result.total_uncollided_flux:.6e} photons/cm^2/s")
print(
    f"Total buildup-corrected flux: "
    f"{co60_result.total_buildup_corrected_flux:.6e} photons/cm^2/s"
)

am241_source = create_isotope_source("am241", activity_bq)

am241_result = calculate_isotope_source_result(
    am241_source,
    layers,
    detector_distance,
    apply_buildup=True,
)

print("\nAm-241 source result:")
print(f"Source name: {am241_result.source_name}")
print(f"Activity: {am241_result.activity_bq:.6e} Bq")
print(f"Number of photon lines: {len(am241_result.line_results)}")
print(f"Total uncollided flux: {am241_result.total_uncollided_flux:.6e} photons/cm^2/s")
print(
    f"Total buildup-corrected flux: "
    f"{am241_result.total_buildup_corrected_flux:.6e} photons/cm^2/s"
)