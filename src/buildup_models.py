from dataclasses import dataclass


@dataclass
class GPCoefficients:
    material_name: str
    energy: float
    b: float
    c: float
    a: float
    xk: float
    d: float


    def __post_init__(self):
        if self.energy <= 0:
            raise ValueError("G-P coefficient energy must be greater than zero.")

        if self.xk <= 0:
            raise ValueError("G-P coefficient xk must be greater than zero.")