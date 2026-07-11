import math
from models import Material


def calculate_mu(mu_over_p: float, density: float) -> float:
    if mu_over_p < 0:
        raise ValueError("Mass attenuation coefficient cannot be negative.")

    if density <= 0:
        raise ValueError("Density must be greater than zero.")

    return mu_over_p * density


def calculate_transmission(mu: float, thickness: float) -> float:
    # Calculates narrow-beam transmission through a slab. Returns a transmission fraction.
    # T = exp(-mu * x)

    if mu < 0:
        raise ValueError("Linear attenuation coefficient cannot be negative.")
    
    if thickness < 0:
        raise ValueError("Thickness cannot be negative.")
    
    return math.exp(-mu * thickness)


def calculate_flux(source_strength: float, transmission: float, distance: float) -> float:
    # calculate_flux() explanation:
        # Ensures possible configuration.
        # Calculates photon flux at a detector from a point source.
        # source_strength = photon emission rate in photons/s
        # transmission = Shield transmission as a fraction
        # distance = Source to detector distance in cm
        # returns photon flux in photons/cm^2/s

    if source_strength < 0:
        raise ValueError("Source strength cannot be negative.")

    if transmission < 0:
        raise ValueError("Transmission cannot be negative.")

    if transmission > 1:
        raise ValueError("Transmission cannot be greater than 1.")

    if distance <= 0:
        raise ValueError("Detector distance must be greater than zero.")
    
    return source_strength * transmission / (4 * math.pi * distance ** 2)

 
def get_exact_y_value(x: float, x_values: list[float], y_values: list[float]) -> float | None:
    
    # Loops through every index in x_values. If x equals x_values[index].
    # Set exact_value equal to y_values[index]. Returns exact_values or None.
    
    exact_value = None
    
    for i in range (len(x_values)):
        if x == x_values[i]:
            exact_value = y_values[i]

    return exact_value


def linear_interpolate(x: float, x_values: list[float], y_values: list[float]) -> float:
    # interpolate() explanation:
        # exact_value cancels interpolation if the user selects and exact value from the table.
        # x = user defined energy value (what the user selects)
        # x_values = list of given data points from XCOM of energies
        # y_values = list of given data points from XCOM of mu/rho values
        # Returns a linearly interpolated mu/rho value.
        # Interpolation formula: y = y1 + ((y2 - y1)/(x2 - x1)) * (x - x1)
    
    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length.")

    exact_value = get_exact_y_value(x, x_values, y_values)

    if exact_value is not None:
        return exact_value

    for i in range(len(x_values)-1):
        x1 = x_values[i]
        x2 = x_values[i + 1]

        if x1 == x2: # Prevents division by zero when two adjacent values are identical.
            continue

        if x1 <= x <= x2:
            y1 = y_values[i]
            y2 = y_values[i + 1]

            return y1 + ((x - x1) / (x2 - x1)) * (y2 - y1)
        
    raise ValueError("Requested value is outside the data range.")


def log_log_interpolate(x: float, x_values: list[float], y_values: list[float]) -> float:
    # Log-log interpolation fits attenuation data better because photon cross sections
    # vary approximately as power laws between tabulated energy points.

    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length.")

    exact_value = get_exact_y_value(x, x_values, y_values)

    if exact_value is not None:
        return exact_value

    for i in range(len(x_values) - 1):
        x1 = x_values[i]
        x2 = x_values[i + 1]

        if x1 == x2:
            continue

        if x1 <= x <= x2:
            y1 = y_values[i]
            y2 = y_values[i + 1]

            if x1 <= 0 or x2 <= 0 or y1 <= 0 or y2 <= 0:
                return linear_interpolate(x, x_values, y_values)

            log_x = math.log(x)
            log_x1 = math.log(x1)
            log_x2 = math.log(x2)
            log_y1 = math.log(y1)
            log_y2 = math.log(y2)

            log_y = log_y1 + ((log_x - log_x1) / (log_x2 - log_x1)) * (log_y2 - log_y1)

            return math.exp(log_y)

    raise ValueError("Requested value is outside the data range.")


def get_mu_over_p_at_energy(material: Material, energy: float) -> float:
    if energy <= 0:
        raise ValueError("Photon energy must be greater than zero.")
    return log_log_interpolate(energy, material.energy, material.mu_over_p)