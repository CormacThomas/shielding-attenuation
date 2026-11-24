"""Analytical checks for layer composition and absorption-edge interpolation."""

from math import exp, pi

import pytest

from shielding.physics.attenuation import get_mu_over_p_at_energy
from shielding.physics.layers import calculate_shielding_result
from shielding.physics.models import Layer, Material


def test_multilayer_uncollided_point_kernel():
    first = Material("first", "First test material", 2.0, [1.0, 2.0], [0.25, 0.25])
    second = Material("second", "Second test material", 4.0, [1.0, 2.0], [0.5, 0.5])
    result = calculate_shielding_result(
        [Layer(4.0, first), Layer(0.5, second)], 1.0, 1000.0, 20.0
    )

    assert result.total_mfp == pytest.approx(3.0)
    assert result.total_transmission == pytest.approx(exp(-3.0))
    assert result.uncollided_flux == pytest.approx(
        1000.0 * exp(-3.0) / (4 * pi * 20.0**2)
    )


def test_attenuation_uses_post_edge_value_at_exact_duplicate():
    material = Material(
        "edge", "Synthetic edge", 1.0, [1.0, 2.0, 2.0, 4.0], [4.0, 1.0, 16.0, 4.0]
    )

    assert get_mu_over_p_at_energy(material, 2.0) == 16.0
    assert get_mu_over_p_at_energy(material, 2.0**0.5) == pytest.approx(2.0)
    assert get_mu_over_p_at_energy(material, 8.0**0.5) == pytest.approx(8.0)
