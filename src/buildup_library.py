from buildup_models import GPCoefficients

# G-P fitting coefficients for gamma-ray exposure buildup factors.
# Coefficients order: material_name, energy, b, c, a, xk, d.
# Source: ORNL New gamma-ray buildup factor data for point kernel calculations: ANS-6.4.3 standard reference data

def get_gp_coefficients_library() -> dict[str, list[GPCoefficients]]:
    return { 
        "lead": [
            GPCoefficients("Lead", 0.03, 1.003, 0.506, 0.167, 14.21, -0.0950),
            GPCoefficients("Lead", 0.04, 1.007, 0.414, 0.227, 13.71, -0.1370),
            GPCoefficients("Lead", 0.05, 1.013, 0.368, 0.273, 13.99, -0.1844),
            GPCoefficients("Lead", 0.06, 1.020, 0.413, 0.226, 13.73, -0.1353),
            GPCoefficients("Lead", 0.08, 1.044, 0.403, 0.227, 13.24, -0.1318),
            GPCoefficients("Lead", 0.10, 2.014, 1.393, 0.083, 20.93, -0.0912),
            GPCoefficients("Lead", 0.15, 1.783, 0.318, 0.310, 26.45, -0.1233),
            GPCoefficients("Lead", 0.20, 1.588, 0.097, 0.441, 14.49, -0.1076),
            GPCoefficients("Lead", 0.30, 1.494, 0.183, 0.421, 12.80, -0.2485),
            GPCoefficients("Lead", 0.40, 1.237, 0.552, 0.134, 15.25, -0.0504),
            GPCoefficients("Lead", 0.50, 1.332, 0.590, 0.127, 14.62, -0.0572),
            GPCoefficients("Lead", 0.60, 1.424, 0.621, 0.113, 13.77, -0.0478),
            GPCoefficients("Lead", 0.80, 1.533, 0.682, 0.094, 14.43, -0.0455),
            GPCoefficients("Lead", 1.00, 1.589, 0.744, 0.076, 14.76, -0.0406),
            GPCoefficients("Lead", 1.50, 1.656, 0.778, 0.069, 13.61, -0.0452),
            GPCoefficients("Lead", 2.00, 1.670, 0.785, 0.079, 13.58, -0.0696),
            GPCoefficients("Lead", 3.00, 1.575, 0.778, 0.096, 13.78, -0.1032),
            GPCoefficients("Lead", 4.00, 1.612, 0.706, 0.137, 14.11, -0.1471),
            GPCoefficients("Lead", 5.00, 1.530, 0.722, 0.139, 14.19, -0.1526),
            GPCoefficients("Lead", 6.00, 1.497, 0.721, 0.145, 14.37, -0.1578),
            GPCoefficients("Lead", 8.00, 1.443, 0.808, 0.123, 14.30, -0.1385),
            GPCoefficients("Lead", 10.00, 1.424, 0.940, 0.090, 14.20, -0.1121),
        ]
    }