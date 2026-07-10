from buildup_models import GPCoefficients

# G-P fitting coefficients for gamma-ray exposure buildup factors.
# Coefficients order: material_name, energy, b, c, a, xk, d.
# Dictionary keys must match Material.key values from material_library.py
# Source: ORNL  gamma-ray buildup factor data for point kernel calculations: ANS-6.4.3 standard reference data

def get_gp_coefficients_library() -> dict[str, list[GPCoefficients]]:
    return { 

        # Lead

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
        ],

        # Aluminum

        "aluminum": [
            GPCoefficients("aluminum", 0.015, 1.029, 0.364, 0.240, 14.12, -0.1704),
            GPCoefficients("aluminum", 0.020, 1.072, 0.349, 0.241, 14.25, -0.1280),
            GPCoefficients("aluminum", 0.030, 1.226, 0.415, 0.206, 14.06, -0.1131),
            GPCoefficients("aluminum", 0.040, 1.504, 0.492, 0.172, 14.83, -0.0948),
            GPCoefficients("aluminum", 0.050, 1.935, 0.570, 0.148, 14.64, -0.0888),
            GPCoefficients("aluminum", 0.060, 2.436, 0.683, 0.109, 14.74, -0.0784),
            GPCoefficients("aluminum", 0.080, 3.399, 0.926, 0.033, 14.11, -0.0328),
            GPCoefficients("aluminum", 0.100, 3.991, 1.148, -0.020,13.53, -0.0085),
            GPCoefficients("aluminum", 0.150, 4.141, 1.441, -0.076,14.24,  0.0185),
            GPCoefficients("aluminum", 0.200, 3.690, 1.585, -0.100,14.16,  0.0316),
            GPCoefficients("aluminum", 0.300, 3.101, 1.636, -0.109,14.26,  0.0349),
            GPCoefficients("aluminum", 0.400, 2.791, 1.593, -0.103,14.76,  0.0306),
            GPCoefficients("aluminum", 0.500, 2.609, 1.528, -0.093,15.47,  0.0249),
            GPCoefficients("aluminum", 0.600, 2.428, 1.521, -0.096,14.79,  0.0322),
            GPCoefficients("aluminum", 0.800, 2.237, 1.439, -0.084,14.68,  0.0284),
            GPCoefficients("aluminum", 1.000, 2.119, 1.368, -0.073,15.07,  0.0257),
            GPCoefficients("aluminum", 1.500, 1.940, 1.245, -0.052,14.72,  0.0196),
            GPCoefficients("aluminum", 2.000, 1.835, 1.160, -0.034,14.89,  0.0107),
            GPCoefficients("aluminum", 3.000, 1.694, 1.059, -0.011,10.74, -0.0011),
            GPCoefficients("aluminum", 4.000, 1.605, 0.992, 0.006, 12.74, -0.0087),
            GPCoefficients("aluminum", 5.000, 1.533, 0.945, 0.021, 14.17, -0.0223),
            GPCoefficients("aluminum", 6.000, 1.464, 0.936, 0.024, 15.05, -0.0290),
            GPCoefficients("aluminum", 8.000, 1.374, 0.913, 0.031, 14.15, -0.0269),
            GPCoefficients("aluminum", 10.000,1.308, 0.904, 0.036, 14.30, -0.0322)
        ],

        # Concrete (Ordinary)

        "concrete_ordinary": [
            GPCoefficients("Concrete (Ordinary)", 0.015, 1.028, 0.429, 0.174, 27.56, -0.2976),
            GPCoefficients("Concrete (Ordinary)", 0.020, 1.067, 0.396, 0.204, 13.32, -0.0960),
            GPCoefficients("Concrete (Ordinary)", 0.030, 1.220, 0.403, 0.212, 14.44, -0.1160),
            GPCoefficients("Concrete (Ordinary)", 0.040, 1.472, 0.489, 0.172, 14.92, -0.0943),
            GPCoefficients("Concrete (Ordinary)", 0.050, 1.826, 0.602, 0.127, 15.51, -0.0687),
            GPCoefficients("Concrete (Ordinary)", 0.060, 2.249, 0.723, 0.087, 16.62, -0.0622),
            GPCoefficients("Concrete (Ordinary)", 0.080, 3.263, 0.885, 0.045, 14.03, -0.0402),
            GPCoefficients("Concrete (Ordinary)", 0.100, 3.867, 1.101, -0.009,13.91, -0.0161),
            GPCoefficients("Concrete (Ordinary)", 0.150, 4.066, 1.413, -0.072,13.89,  0.0174),
            GPCoefficients("Concrete (Ordinary)", 0.200, 3.682, 1.552, -0.095,13.73,  0.0285),
            GPCoefficients("Concrete (Ordinary)", 0.300, 3.090, 1.617, -0.106,14.23,  0.0331),
            GPCoefficients("Concrete (Ordinary)", 0.400, 2.774, 1.593, -0.104,14.36,  0.0323),
            GPCoefficients("Concrete (Ordinary)", 0.500, 2.572, 1.552, -0.099,14.76,  0.0315),
            GPCoefficients("Concrete (Ordinary)", 0.600, 2.433, 1.507, -0.093,14.78,  0.0296),
            GPCoefficients("Concrete (Ordinary)", 0.800, 2.243, 1.429, -0.082,14.85,  0.0270),
            GPCoefficients("Concrete (Ordinary)", 1.000, 2.124, 1.359, -0.071,15.31,  0.0243),
            GPCoefficients("Concrete (Ordinary)", 1.500, 1.934, 1.249, -0.053,14.53,  0.0201),
            GPCoefficients("Concrete (Ordinary)", 2.000, 1.834, 1.161, -0.035,13.88,  0.0117),
            GPCoefficients("Concrete (Ordinary)", 3.000, 1.701, 1.051, -0.009,10.11, -0.0021),
            GPCoefficients("Concrete (Ordinary)", 4.000, 1.613, 0.981, 0.010, 12.99, -0.0133),
            GPCoefficients("Concrete (Ordinary)", 5.000, 1.551, 0.951,0.030, 11.99, -0.0263),
            GPCoefficients("Concrete (Ordinary)", 6.000, 1.475, 0.930, 0.024, 15.87, -0.0273),
            GPCoefficients("Concrete (Ordinary)", 8.000, 1.383, 0.909, 0.031, 12.43, -0.0218),
            GPCoefficients("Concrete (Ordinary)", 10.000,1.320, 0.902, 0.033, 14.83, -0.0258)
        ],

        # Water

        "water": [
            GPCoefficients("water", 0.015, 1.188, 0.464, 0.172, 14.00, -0.0829),
            GPCoefficients("water", 0.020, 1.449, 0.532, 0.152, 14.61, -0.0764),
            GPCoefficients("water", 0.030, 2.411, 0.741, 0.084, 14.62, -0.0452),
            GPCoefficients("water", 0.040, 3.587, 1.114, -0.018,12.48,  0.0013),
            GPCoefficients("water", 0.050, 4.554, 1.457, -0.084,13.69,  0.0341),
            GPCoefficients("water", 0.060, 5.018, 1.735, -0.127, 13.70, 0.0676),
            GPCoefficients("water", 0.080, 5.030, 2.054, -0.167, 13.84, 0.0763),
            GPCoefficients("water", 0.100, 4.627, 2.207, -0.184, 13.27, 0.0799),
            GPCoefficients("water", 0.150, 3.888, 2.206, -0.180, 14.27, 0.0738),
            GPCoefficients("water", 0.200, 3.462, 2.132, -0.173, 14.51, 0.0750),
            GPCoefficients("water", 0.300, 2.897, 2.008, -0.162, 14.18, 0.0641),
            GPCoefficients("water", 0.400, 2.646, 1.874, -0.148, 14.16, 0.0591),
            GPCoefficients("water", 0.500, 2.499, 1.749, -0.132, 14.36, 0.0517),
            GPCoefficients("water", 0.600, 2.383, 1.662, -0.121, 14.19, 0.0482),
            GPCoefficients("water", 0.800, 2.223, 1.524, -0.101, 14.31, 0.0403),
            GPCoefficients("water", 1.000, 2.106, 1.436, -0.088, 14.19, 0.0367),
            GPCoefficients("water", 1.500, 1.948, 1.265, -0.057, 14.98, 0.0245),
            GPCoefficients("water", 2.000, 1.843, 1.169, -0.038, 14.22, 0.0157),
            GPCoefficients("water", 3.000, 1.716, 1.050, -0.011, 13.63, 0.0027),
            GPCoefficients("water", 4.000, 1.633, 0.979, 0.007, 14.23, -0.0060),
            GPCoefficients("water", 5.000, 1.571, 0.928, 0.022, 13.20, -0.0157),
            GPCoefficients("water", 6.000, 1.521, 0.893, 0.033, 11.92, -0.0208),
            GPCoefficients("water", 8.000, 1.432, 0.873, 0.038, 11.56, -0.0204),
            GPCoefficients("water", 10.000, 1.378, 0.849, 0.045, 14.34,-0.0280)
        ],

        # Tungsten

        "tungsten": [
            GPCoefficients("tungsten", 0.015, 1.001, 0.277, 0.342, 19.18, -0.3351),
            GPCoefficients("tungsten", 0.020, 1.002, 0.258, 0.394, 13.12, -0.3192),
            GPCoefficients("tungsten", 0.030,1.004, 0.554, 0.136, 15.36, -0.0677),
            GPCoefficients("tungsten", 0.040, 1.011, 0.346, 0.279, 14.35, -0.1832),
            GPCoefficients("tungsten", 0.050, 1.018, 0.407, 0.230, 13.80, -0.1384),
            GPCoefficients("tungsten", 0.060, 1.029, 0.415, 0.224, 13.44, -0.1325),
            GPCoefficients("tungsten", 0.080, 1.956, 1.461, 0.073, 27.21, -0.1584),
            GPCoefficients("tungsten", 0.100, 1.809, 0.852, 0.164, 16.39, -0.1348),
            GPCoefficients("tungsten", 0.150, 1.613, 0.124, 0.194, 8.36,   0.0659),
            GPCoefficients("tungsten", 0.200, 1.528, 0.073, 0.634, 13.97, -0.2997),
            GPCoefficients("tungsten", 0.300, 1.563, 0.204, 0.395, 13.29, -0.2179),
            GPCoefficients("tungsten", 0.400, 1.683, 0.327, 0.294, 13.68, -0.1857),
            GPCoefficients("tungsten", 0.500, 1.802, 0.416, 0.237, 13.74, -0.1550),
            GPCoefficients("tungsten", 0.600, 1.759, 0.534, 0.171, 13.78, -0.1124),
            GPCoefficients("tungsten", 0.800, 1.910, 0.607, 0.139, 13.57, -0.0952),
            GPCoefficients("tungsten", 1.00,1.869, 0.689, 0.106, 13.54, -0.0760),
            GPCoefficients("tungsten", 1.50, 1.840, 0.818, 0.061, 13.42, -0.0512),
            GPCoefficients("tungsten", 2.00, 1.748, 0.827, 0.068, 13.39, -0.0694),
            GPCoefficients("tungsten", 3.00, 1.582, 0.840, 0.076, 13.53, -0.0922),
            GPCoefficients("tungsten", 4.00, 1.460, 0.828, 0.091, 13.78, -0.1126),
            GPCoefficients("tungsten", 5.00, 1.509, 0.756, 0.126, 14.11, -0.1441),
            GPCoefficients("tungsten", 6.00, 1.480, 0.768, 0.127, 14.27, -0.1441),
            GPCoefficients("tungsten", 8.00, 1.431, 0.839, 0.112, 14.28, -0.1304),
            GPCoefficients("tungsten", 10.00, 1.481, 0.844, 0.128, 14.12, -0.1624)
        ],

        # Copper

        "copper": [
            GPCoefficients("copper", 0.015, 1.001, 2.044, -0.310, 11.15, 0.2519),
            GPCoefficients("copper", 0.020, 1.006, 0.230, 0.442, 12.61, -0.5099),
            GPCoefficients("copper", 0.030, 1.017, 0.370, 0.247, 11.26, -0.1771),
            GPCoefficients("copper", 0.040, 1.038, 0.392, 0.197, 25.45, -0.2886),
            GPCoefficients("copper", 0.050, 1.071, 0.353, 0.243, 12.89, -0.1407),
            GPCoefficients("copper", 0.060, 1.121, 0.340, 0.250, 14.53, -0.1501),
            GPCoefficients("copper", 0.080, 1.246, 0.395, 0.217, 14.39, -0.1226),
            GPCoefficients("copper", 0.100, 1.381, 0.539, 0.133, 19.42, -0.0874),
            GPCoefficients("copper", 0.150, 2.120, 0.472, 0.208, 13.51, -0.1372),
            GPCoefficients("copper", 0.200, 2.603, 0.671, 0.120, 13.45, -0.0928),
            GPCoefficients("copper", 0.300, 2.926, 0.921, 0.039, 12.80, -0.0495),
            GPCoefficients("copper", 0.400, 2.795, 1.070, 0.002, 12.19, -0.0331),
            GPCoefficients("copper", 0.500, 2.612, 1.158, -0.020, 11.56,-0.0190),
            GPCoefficients("copper", 0.600, 2.479, 1.191, -0.028, 10.74,-0.0147),
            GPCoefficients("copper", 0.800, 2.270, 1.210, -0.033, 8.79, -0.0131),
            GPCoefficients("copper", 1.000, 2.129, 1.211, -0.036, 7.13, -0.0090),
            GPCoefficients("copper", 1.500, 1.952, 1.149, -0.025, 8.18, -0.0085),
            GPCoefficients("copper", 2.000, 1.835, 1.113, -0.019, 9.49, -0.0052),
            GPCoefficients("copper", 3.000, 1.673, 1.041, 0.001, 12.27, -0.0174),
            GPCoefficients("copper", 4.000, 1.542, 1.016, 0.010, 14.08, -0.0286),
            GPCoefficients("copper", 5.000, 1.451, 0.993, 0.019, 14.15, -0.0372),
            GPCoefficients("copper", 6.000, 1.381, 0.984, 0.023, 14.30, -0.0395),
            GPCoefficients("copper", 8.000, 1.289, 0.959, 0.036, 14.05, -0.0494),
            GPCoefficients("copper", 10.000, 1.226, 0.958, 0.041, 14.33, -0.0536)
        ],

        # Tin

        "tin": [
            GPCoefficients("tin", 0.015, 1.003, 0.405, 0.215, 26.26, -0.3092),
            GPCoefficients("tin", 0.020, 1.006, 0.381, 0.252, 13.99, -0.1592),
            GPCoefficients("tin", 0.030, 1.787, 1.859, 0.042, 11.10, -0.0316),
            GPCoefficients("tin", 0.040, 1.691, 1.229, 0.096, 29.62, -0.1824),
            GPCoefficients("tin", 0.050, 1.636, 0.496, 0.276, 16.81, -0.2316),
            GPCoefficients("tin", 0.060, 1.566, 0.258, -0.080, 21.22, 0.0579),
            GPCoefficients("tin", 0.080, 1.393, 0.033, 0.741, 14.35, -0.2278),
            GPCoefficients("tin", 0.100, 1.123, 0.245, 0.342, 12.99, -0.2053),
            GPCoefficients("tin", 0.150, 1.170, 0.504, 0.152, 13.45, -0.0750),
            GPCoefficients("tin", 0.200, 1.456, 0.356, 0.263, 14.22, -0.1497),
            GPCoefficients("tin", 0.300, 1.924, 0.460, 0.213, 14.10, -0.1426),
            GPCoefficients("tin", 0.400, 2.224, 0.589, 0.151, 13.88, -0.1057),
            GPCoefficients("tin", 0.500, 2.337, 0.702, 0.110, 13.90, -0.0892),
            GPCoefficients("tin", 0.600, 2.391, 0.769, 0.085, 13.78, -0.0736),
            GPCoefficients("tin", 0.800, 2.332, 0.852,0.057, 13.76, -0.0574),
            GPCoefficients("tin", 1.00, 2.236, 0.901, 0.041, 13.52, -0.0463 ),
            GPCoefficients("tin", 1.50, 1.929, 1.030, 0.001, 13.25, -0.0179),
            GPCoefficients("tin", 2.00, 1.814, 0.981, 0.021, 13.33, -0.0392),
            GPCoefficients("tin", 3.00, 1.643, 0.933, 0.043, 13.32, -0.0665),
            GPCoefficients("tin", 4.00, 1.517, 0.891, 0.063, 13.52, -0.0873),
            GPCoefficients("tin", 5.00, 1.575, 0.814, 0.096, 13.88, -0.1167),
            GPCoefficients("tin", 6.00, 1.568, 0.732, 0.136, 14.03, -0.1584),
            GPCoefficients("tin", 8.00, 1.469, 0.807, 0.112, 14.26, -0.1297),
            GPCoefficients("tin", 10.00, 1.435, 0.895, 0.088, 14.80, -0.1043)
        ]
    }