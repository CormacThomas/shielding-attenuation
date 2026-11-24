# Public plotting API.
#
# Callers import plotting functions from this module while the
# implementations remain separated by figure type.


from shielding.reporting.air_kerma import (
    plot_isotope_line_air_kerma_contributions,
)
from shielding.reporting.benchmark_plots import (
    plot_openmc_v113_benchmark,
)
from shielding.reporting.optimization import (
    plot_constraint_feasibility_matrix,
    plot_material_design_comparison,
    plot_thickness_mass_tradeoff,
)
from shielding.reporting.response_curves import (
    plot_response_vs_thickness,
)
from shielding.reporting.style import (
    save_figure,
    save_figure_formats,
)

__all__ = [
    "plot_constraint_feasibility_matrix",
    "plot_isotope_line_air_kerma_contributions",
    "plot_material_design_comparison",
    "plot_response_vs_thickness",
    "plot_thickness_mass_tradeoff",
    "save_figure",
    "save_figure_formats",
    "plot_openmc_v113_benchmark",
]
