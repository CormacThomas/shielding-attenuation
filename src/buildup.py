import math
from buildup_models import GPCoefficients


def get_exact_gp_coefficients(
        material_name: str,
        energy: float,
        gp_library: dict[str, list[GPCoefficients]]
        ) -> GPCoefficients:
    
    material_key = material_name.lower().strip()

    if material_key not in gp_library:
        raise ValueError(f"No G-P coefficients found for material: {material_name}")
    
    coefficients_list = gp_library[material_key]

    for coefficients in coefficients_list:
        if coefficients.energy == energy:
            return coefficients
        
    raise ValueError(f"No exact G-P coefficients found for {material_name} at {energy} MeV.")


def calculate_gp_buildup_factor(coefficients: GPCoefficients, mfp: float) -> float:
    if mfp < 0:
        raise ValueError("Mean free paths cannot be negative.")
    
    if mfp == 0:
        return 1.0
    
    k_value =(coefficients.c * (mfp ** coefficients.a) + coefficients.d * (math.tanh(mfp / coefficients.xk - 2.0) - math.tanh(-2.0)) / (1.0 - math.tanh(-2.0)))

    if abs(k_value - 1.0) < 1e-12:
        return 1.0 + (coefficients.b - 1.0) * mfp
    
    buildup_factor = 1.0 + ((coefficients.b - 1.0) / (k_value - 1.0)) * ((k_value ** mfp) - 1.0)

    return buildup_factor

def linear_interpolate_value(
        x: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
) -> float:
    
    if x1 == x2:
        raise ValueError("Cannot interpolate between duplicate x-values.")
    
    return y1 + ((x - x1) / (x2 - x1)) * (y2 - y1)


def get_gp_coefficients_at_energy(
    material_name: str,
    energy: float,
    gp_library: dict[str, list[GPCoefficients]],
) -> GPCoefficients:
    
    # "Return exact or linearly interpolated G-P coefficients for a material and energy.
    if energy <= 0:
        raise ValueError("Photon energy must be greater than zero.")

    material_key = material_name.lower().strip()

    if material_key not in gp_library:
        raise ValueError(f"No G-P coefficients found for material: {material_name}")

    coefficients_list = gp_library[material_key]

    for coefficients in coefficients_list:
        if coefficients.energy == energy:
            return coefficients

    for i in range(len(coefficients_list) - 1):
        lower = coefficients_list[i]
        upper = coefficients_list[i + 1]

        if lower.energy <= energy <= upper.energy:
            interpolated_b = linear_interpolate_value(
                energy, lower.energy, lower.b, upper.energy, upper.b
            )
            interpolated_c = linear_interpolate_value(
                energy, lower.energy, lower.c, upper.energy, upper.c
            )
            interpolated_a = linear_interpolate_value(
                energy, lower.energy, lower.a, upper.energy, upper.a
            )
            interpolated_xk = linear_interpolate_value(
                energy, lower.energy, lower.xk, upper.energy, upper.xk
            )
            interpolated_d = linear_interpolate_value(
                energy, lower.energy, lower.d, upper.energy, upper.d
            )

            return GPCoefficients(
                lower.material_name,
                energy,
                interpolated_b,
                interpolated_c,
                interpolated_a,
                interpolated_xk,
                interpolated_d,
            )

    raise ValueError("Requested energy is outside the G-P coefficient data range.")

def calculate_buildup_corrected_flux(uncollided_flux: float, buildup_factor: float) -> float:
    if uncollided_flux < 0:
        raise ValueError("Uncollided flux cannot be negative.")

    if buildup_factor < 1:
        raise ValueError("Buildup factor should not be less than 1.")

    return uncollided_flux * buildup_factor