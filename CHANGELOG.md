# Changelog

All major development milestones for the Shielding Attenuation Simulator are documented here.

## v1.10 - Engineering Visualization and Pareto Tradeoff Analysis

Added a reusable engineering visualization subsystem above the validated V1.09 constraint-based optimizer. Version 1.10 converts optimization results into validated plot-ready data, classifies feasible thickness-mass Pareto tradeoffs, samples detector response across shielding thickness, and generates a reproducible four-figure engineering analysis package in PNG and SVG formats.

Changes:
- Added `plot_models.py` for validated visualization data models.
- Added plot-ready dataclasses for:
  - material design points;
  - optimization plot datasets;
  - Pareto points;
  - constraint-feasibility rows;
  - response-curve points;
  - response-curve results.
- Added strict model validation preventing:
  - fabricated numerical metrics for failed candidates;
  - objective scores on rejected candidates;
  - selected status on ineligible candidates;
  - unordered response-curve thickness values;
  - buildup values when buildup was not requested;
  - selected thickness values outside the plotted range.
- Added `plot_data.py` for numerical data preparation independent of Matplotlib.
- Added optimizer-to-plot-data conversion preserving:
  - candidate count;
  - material identity;
  - required thickness;
  - mass per area;
  - relative cost index;
  - buildup status;
  - optimization status;
  - rejection reasons;
  - calculation failure reasons;
  - selected-candidate status;
  - warnings.
- Added independent constraint-feasibility classification supporting:
  - `PASS`;
  - `FAIL`;
  - `INACTIVE`;
  - `UNAVAILABLE`.
- Added thickness-mass Pareto dominance logic.
- Added feasible-only Pareto-front classification by default.
- Preserved rejected designs in the visualization dataset for engineering context without allowing infeasible designs to define the feasible Pareto front.
- Added deterministic Pareto-point ordering.
- Added `response_curve.py` for numerical response sampling independent of rendering.
- Added response-curve range validation.
- Added ordered shield-thickness sample generation.
- Added exact insertion of the optimized shielding thickness when it does not coincide with the uniform sampling grid.
- Added manual monoenergetic response-curve evaluation.
- Added isotope-source response-curve evaluation.
- Added separate storage of:
  - narrow-beam uncollided photon flux;
  - G-P exposure-buildup target-comparison response.
- Added transparent handling of unavailable buildup values.
- Added warning preservation when buildup is unsupported or exceeds the validated 40-MFP range.
- Prevented silent substitution of narrow-beam values into unavailable buildup series.
- Added `optimization_plots.py` for:
  - material design comparison;
  - engineering constraint-feasibility matrix;
  - thickness-mass engineering tradeoff visualization.
- Added `response_plots.py` for detector response versus shielding thickness.
- Added `plotting_utils.py` for:
  - shared visual theme;
  - figure typography;
  - engineering colors;
  - legend formatting;
  - unit and symbol formatting;
  - PNG and SVG export.
- Reduced `plotting.py` to a stable public plotting API.
- Added a modern dark-figure and light-plot visual design.
- Added consistent visual roles for:
  - primary engineering data;
  - selected designs;
  - feasible candidates;
  - infeasible candidates;
  - engineering limits;
  - PASS and FAIL states.
- Added scenario context to every finalized figure:
  - source;
  - activity;
  - detector distance;
  - deterministic model description;
  - target;
  - optimization objective;
  - buildup setting.
- Added metric-specific engineering-limit visualization.
- Added selected-design highlighting across all figures.
- Added deterministic material-label positioning and leader lines in the Pareto figure.
- Added exact target and selected-thickness annotations in the response figure.
- Added four finalized engineering figures:
  - shielding material design comparison;
  - engineering constraint feasibility by material;
  - shielding thickness-mass engineering tradeoff;
  - lead detector response versus shield thickness.
- Combined required thickness, mass per area, and relative cost index into one aligned three-panel material comparison.
- Added `examples/generate_v110_figures.py`.
- Added reproducible generation of the official V1.10 Cs-137 engineering case.
- Added noninteractive rendering using the Matplotlib `Agg` backend.
- Added deterministic PNG and SVG output generation.
- Added automatic output-directory creation.
- Added figure closing after export.
- Added a runtime check confirming that the documented scenario continues to select lead.
- Added Matplotlib to the project requirements.
- Added V1.10 validation tests for:
  - plot-data integrity;
  - selected-candidate preservation;
  - rejected-candidate preservation;
  - failed-candidate metadata;
  - Pareto dominance;
  - Pareto-front membership;
  - deterministic Pareto sorting;
  - response-curve endpoint preservation;
  - strictly increasing thickness samples;
  - exact optimized-thickness insertion;
  - zero-thickness response;
  - manual-source response curves;
  - isotope-source response curves;
  - monotonic narrow-beam attenuation;
  - target conversion;
  - target intersection;
  - unsupported buildup;
  - 40-MFP buildup termination;
  - constraint feasibility;
  - equality at engineering limits;
  - invalid response-curve ranges.
- Added the V1.10 validation report.
- Updated visualization terminology to identify the G-P curve as an exposure-buildup target-comparison response proxy rather than a general photon-flux estimate.

Validated behavior:
- Optimization plot data preserves all nine candidates in the official Cs-137 case.
- Lead remains the selected material.
- Rejected designs preserve every applicable rejection reason.
- Failed candidates do not receive fabricated thickness, mass, cost, score, or feasibility values.
- Lead and tungsten form the feasible thickness-mass Pareto front.
- Rejected candidates remain visible but do not define the feasible Pareto front.
- Response-curve thickness values are strictly increasing.
- Response-curve endpoints are preserved.
- The exact selected lead thickness is inserted into the sampled curve.
- Zero shielding thickness reproduces the unshielded source response.
- Narrow-beam response decreases monotonically with increasing shield thickness.
- Manual monoenergetic and isotope sources use their respective validated calculation pathways.
- The selected lead thickness reproduces the 100 photons/cm²/s target-comparison response within solver tolerance.
- Unsupported and out-of-range buildup values remain unavailable and generate warnings.
- Narrow-beam values continue to be reported when buildup becomes unavailable.
- Constraint checks correctly distinguish `PASS`, `FAIL`, `INACTIVE`, and `UNAVAILABLE`.
- Values equal to an active maximum constraint are classified as passing.
- Invalid curve ranges and insufficient sample counts are rejected.
- The complete validation runner produces 273 passing assertions.
- V1.10 adds 58 focused assertions while preserving the 215 previously documented regression assertions.
- The reproducible figure-generation script selects lead at approximately 7.08821 cm.
- The script produces four PNG and four SVG files.
- All eight output files are nonempty.
- PNG outputs decode successfully.
- SVG outputs parse as valid XML.
- All previous attenuation, interpolation, source, buildup, minimum-thickness, material-comparison, and optimization regression tests remain passing.

Validated example:
- Source: 1.00 Ci Cs-137
- Activity: 3.70 × 10¹⁰ Bq
- Detector distance: 100 cm
- Target-comparison response: ≤ 100 photons/cm²/s
- Calculation search limit: 100 cm
- Maximum design thickness: 20 cm
- Maximum mass per area: 120 g/cm²
- Optimization objective: minimum mass per area
- G-P exposure buildup requested
- Nine candidate materials evaluated
- Lead and tungsten satisfy both active engineering constraints.
- Tungsten is the thinner eligible design at 4.90817 cm.
- Lead has the lower eligible mass per area at 80.3803 g/cm².
- Lead is selected at approximately 7.08821 cm.
- Lead and tungsten both belong to the feasible thickness-mass Pareto front.
- Copper and tin satisfy the thickness limit but violate the mass limit.
- Water, polyethylene, and barite concrete satisfy the mass limit but violate the thickness limit.
- Aluminum and ordinary concrete violate both active constraints.
- The G-P target-comparison response reaches approximately 100 photons/cm²/s at the selected lead thickness.
- The corresponding narrow-beam uncollided photon flux is approximately 33.1023 photons/cm²/s.

Notes:
- V1.10 does not introduce a new attenuation equation, source model, buildup equation, minimum-thickness solver, engineering constraint, or optimization objective.
- Previously validated V1.09 physics and optimization results are reused rather than independently rederived.
- Plot validation is based on numerical data integrity, deterministic classification, and structural artifact verification rather than pixel-perfect image comparison.
- Exact pixel output may vary across operating systems, Matplotlib versions, and installed fonts.
- Recorded file sizes are traceability observations rather than permanent regression thresholds.
- The plotted buildup-corrected series uses exposure-buildup coefficients and is intentionally labeled a target-comparison response proxy.
- The G-P response proxy must not be interpreted as a general photon-number-flux estimate.
- Pareto classification currently evaluates required thickness and mass per unit area.
- The official figures compare homogeneous single-material designs.
- Relative-cost indices remain simplified comparative assumptions rather than market prices or currency.
- Multilayer optimization, total-mass geometry, separated response quantities, and OpenMC benchmarking remain planned for later versions.

## v1.09 - Constraint-Based Material Selection

Added a constraint-based engineering optimization layer above the V1.08 single-material comparison workflow. Version 1.09 calculates mass per area and a simplified relative-cost metric for each successful material candidate, applies optional hard design constraints, separates feasible designs from engineering rejections and calculation failures, and selects the best eligible material using one of four optimization objectives.

Changes:
- Added `optimization_models.py` for V1.09 optimization data models and type definitions.
- Added optimization dataclasses:
  - `DesignConstraints`
  - `OptimizationWeights`
  - `OptimizedMaterialCandidate`
  - `OptimizedDesignResult`
- Added explicit optimization statuses:
  - `ELIGIBLE`
  - `REJECTED`
  - `FAILED`
- Added optimization modes:
  - `minimum_thickness`
  - `minimum_mass`
  - `minimum_cost`
  - `balanced`
- Added `material_cost_library.py` with:
  - `MaterialCostData`
  - user-editable relative material cost indices
  - ordinary concrete baseline index of 1.0
  - warnings that the values are comparative assumptions rather than market prices
- Added `constraint_optimizer.py` for the complete V1.09 workflow.
- Added mass-per-area calculation:
  - `mass per area = density × required thickness`
  - output units of g/cm²
- Added relative-cost-index-per-area calculation:
  - `relative cost per area = mass per area × relative material cost index`
- Added hard engineering constraints for:
  - maximum design thickness
  - maximum mass per area
  - maximum relative cost index per area
- Kept the numerical thickness search limit separate from the engineering maximum-thickness constraint.
- Added candidate conversion from the validated V1.08 `MaterialDesignCandidate` result.
- Added preservation of all violated engineering constraints so one candidate can report multiple rejection reasons.
- Added min-max normalization of eligible thickness, mass, and relative-cost metrics.
- Added weighted balanced scoring with user-selected thickness, mass, and cost weights.
- Added deterministic objective-specific tie-breaking using secondary metrics and stable material keys.
- Added best-candidate selection and readable selection explanations.
- Added infeasibility handling when no material satisfies all active constraints.
- Added a fourth CLI calculation mode:
  - fixed-thickness shielding calculation
  - minimum-thickness shielding design
  - material comparison
  - constraint-based material optimization
- Added CLI prompts for:
  - optional maximum design thickness
  - optional maximum mass per area
  - optional maximum relative cost index per area
  - optimization objective
  - balanced optimization weights
- Added optimized output formatting showing:
  - material name
  - required thickness
  - mass per area
  - relative cost index per area
  - objective score
  - buildup or fallback status
  - optimization status
  - rejection reasons
  - calculation failures
  - candidate warnings
  - optimizer warnings
- Updated V1.08 comments to distinguish lower-level calculation failure from V1.09 engineering rejection.
- Added V1.09 validation tests for engineering metrics, constraint rejection, multiple rejection reasons, objective selection, balanced scoring, lower-level failure preservation, infeasibility, and invalid optimizer inputs.
- Added V1.09 validation report for the complete constraint-based material-selection workflow.

Validated behavior:
- Mass per area equals material density multiplied by required thickness.
- Relative cost index per area equals mass per area multiplied by the material cost index.
- A successful V1.08 design becomes `ELIGIBLE` when it satisfies every active engineering constraint.
- A physically successful design becomes `REJECTED` rather than `FAILED` when it violates a hard engineering constraint.
- Rejected candidates preserve multiple simultaneous rejection reasons.
- Lower-level V1.08 calculation failures remain `FAILED`.
- Minimum-thickness mode selects the eligible candidate with the smallest required thickness.
- Minimum-mass mode selects the eligible candidate with the smallest mass per area.
- Minimum-cost mode selects the eligible candidate with the smallest relative cost index per area.
- Balanced mode produces normalized scores between 0 and 1 and selects the smallest weighted score.
- Rejected and failed candidates are excluded from balanced normalization and ranking.
- An infeasible constraint set returns `best_candidate = None` and generates a warning.
- Negative constraint values are rejected.
- All-zero balanced optimization weights are rejected.
- The complete validation runner produces 215 passing assertions and ends with `All validation tests passed.`
- Previous attenuation, source, buildup, minimum-thickness, fallback, and V1.08 comparison regression tests remain passing.

Validated example:
- Source: 1 Ci Cs-137
- Detector distance: 100 cm
- Target flux: 100 photons/cm²/s
- Buildup requested
- Maximum design thickness: 20 cm
- Maximum mass per area: 120 g/cm²
- Objective: minimum mass per area
- Lead and tungsten remain eligible.
- Lead is selected at 80.3803 g/cm².
- Tungsten is thinner at 4.90817 cm but has a greater mass per area.
- Water has the lowest simplified relative-cost value but is rejected by the thickness constraint.
- Other materials remain visible with explicit rejection reasons.

Notes:
- V1.09 does not introduce new attenuation physics, source physics, buildup equations, or minimum-thickness solution methods.
- V1.09 reuses the V1.08 comparison workflow and the V1.07 minimum-thickness solver.
- The optimizer currently evaluates homogeneous single-material shields.
- Mass is compared per unit area because a complete three-dimensional shield geometry is not yet defined.
- Relative-cost indices are simplified, user-editable assumptions and are not currency, market prices, or procurement estimates.
- Balanced scores depend on the eligible candidate set and user-selected weights.
- Hard constraints currently cover thickness, mass per area, and relative cost only.
- Buildup-aware optimization remains limited to supported single-layer homogeneous cases and the 40-MFP validity range.
- Some candidates may use documented narrow-beam fallback results when buildup is unavailable.
- V1.09 does not yet calculate total mass, dose rate, exposure rate, air kerma, or effective dose.
- Multilayer optimization and OpenMC benchmarking are planned for later versions.
## v1.08 - Single-Material Design Comparison Mode

Added material comparison mode for target-driven shielding design. Version 1.08 allows the simulator to apply the previously validated V1.07 minimum-thickness design pathway across multiple candidate shielding materials and report how much of each material is required for the same source, detector distance, target, maximum thickness setting, and buildup setting.

Changes:
- Added `design_optimizer.py` for material comparison workflow logic.
- Added material comparison dataclasses:
  - `MaterialDesignCandidate`
  - `MaterialComparisonResult`
- Added `calculate_material_candidate()` to calculate the required thickness for one material in a shared design problem.
- Added `compare_materials_for_target()` to run the same target-driven design calculation across multiple selected materials.
- Added candidate sorting so passing materials are ranked by required shielding thickness.
- Added failed candidate preservation so materials that cannot meet the target remain visible in the comparison result.
- Added failure reasons for failed material candidates.
- Added warning preservation for passing candidates that fall back from buildup-aware design to narrow-beam design.
- Added material comparison input handling for comma-separated material lists.
- Added support for pressing Enter to compare all available materials.
- Added a third CLI calculation mode:
  - fixed-thickness shielding calculation
  - minimum-thickness shielding design
  - material comparison
- Added material comparison output formatting showing:
  - material name
  - required thickness
  - final target-comparison flux
  - buildup status
  - pass/fail status
  - fallback warnings
  - failure reasons
- Updated code comments to explain the V1.08 workflow layer and future maintainability.
- Added validation checks for material comparison structure, target satisfaction, buildup fallback behavior, warning preservation, and failed candidate preservation.
- Added V1.08 validation report for single-material design comparison behavior.

Validated behavior:
- Material comparison returns one candidate per selected material.
- Lead material comparison candidate passes for the Cs-137 benchmark case.
- Lead material comparison candidate reaches the requested flux target.
- Lead material comparison candidate uses buildup when buildup is requested and valid.
- Every passing material comparison candidate reaches the requested flux target.
- Unsupported buildup materials can fall back to narrow-beam design when the target is reachable.
- Unsupported buildup fallback candidates report `buildup_used = False`.
- Unsupported buildup fallback warnings are preserved.
- Impossible material candidates are preserved with `status = FAILED`.
- Failed material candidates preserve failure reasons.
- Manual command-line testing produces a readable material comparison table.
- Passing command-line material comparison results are sorted by required shielding thickness.
- Previous V1.05, V1.06, and V1.07 validation tests remain passing.

Notes:
- V1.08 does not introduce new attenuation physics, source physics, buildup equations, or target conversion math.
- V1.08 reuses the V1.07 minimum-thickness design solver for each candidate material.
- Material comparison currently evaluates one material at a time and compares the results.
- Material comparison is not yet full constraint-based optimization.
- Mass, cost, and weighted design scoring are planned for later versions.
- Buildup-aware material comparison remains limited by the same single-layer homogeneous G-P buildup assumptions as V1.07.
- If buildup-aware design is unavailable for a material, the simulator falls back to narrow-beam design and reports a warning.
- V1.08 reports photon flux, not dose rate, exposure rate, air kerma, or effective dose.

## v1.07 - Target Classes and Minimum Shielding Thickness Design

Added target-driven minimum shielding thickness calculations for manual monoenergetic photon sources and isotope sources. Version 1.07 allows the simulator to answer design questions such as how much shielding is required to meet a specified transmission, reduction-factor, or flux target.

Changes:
- Added target model dataclasses:
  - `TransmissionTarget`
  - `ReductionFactorTarget`
  - `FluxTarget`
  - `MinimumThicknessResult`
- Added `thickness_calculator.py` for minimum shielding thickness calculations.
- Added target conversion logic that converts transmission, reduction-factor, and flux targets into equivalent detector flux requirements.
- Added analytical narrow-beam minimum-thickness calculation for manual monoenergetic photon sources.
- Added bisection-based minimum-thickness calculation for isotope sources.
- Added support for source-level isotope minimum-thickness design using line-by-line flux summation.
- Added optional buildup-aware minimum-thickness design.
- Added automatic fallback to narrow-beam design when buildup-aware design is unavailable.
- Added warnings when buildup is requested but cannot be used within the valid G-P buildup range.
- Added CLI calculation mode selection:
  - fixed-thickness shielding calculation
  - minimum-thickness shielding design
- Updated minimum-thickness output formatting to report:
  - calculation mode
  - selected material
  - target description
  - required thickness
  - final target-comparison flux
  - final narrow-beam uncollided flux
  - final buildup-corrected flux when available
  - warnings
- Added validation checks for target conversion, manual analytical thickness calculation, isotope bisection, buildup-aware design, fallback behavior, and impossible design target rejection.
- Added V1.07 validation report for target-driven minimum shielding thickness calculations.

Validated behavior:
- Manual source transmission targets produce the expected final transmission.
- Manual source reduction-factor targets produce the expected final transmission.
- Manual source flux targets produce final flux at or below the requested target.
- Cs-137 isotope flux targets produce final source flux at or below the requested target.
- Isotope minimum-thickness calculations return required thickness greater than zero when shielding is required.
- Very high flux targets correctly return zero required thickness with a warning.
- Impossible manual-source targets with insufficient maximum thickness are rejected.
- Buildup-aware manual-source design reaches the requested flux target when buildup is valid.
- Buildup-aware manual-source design reports `buildup_used = True` when G-P buildup is successfully used.
- Buildup-aware manual-source required thickness is greater than the equivalent narrow-beam required thickness.
- Buildup-aware Cs-137 isotope design reaches the requested flux target when buildup is valid.
- Buildup-aware Cs-137 isotope design reports `buildup_used = True`.
- Low-energy Am-241-style manual source design falls back to narrow-beam calculation when the buildup-aware solution cannot reach the target within the valid G-P range.
- Fallback minimum-thickness results still reach the requested narrow-beam flux target.
- Fallback minimum-thickness results report `buildup_used = False`.
- Fallback minimum-thickness results generate warnings.
- Manual source V1.05 regression behavior remains preserved.

Notes:
- Minimum-thickness design currently evaluates one shielding material at a time.
- Narrow-beam manual-source minimum thickness uses the analytical attenuation solution.
- Isotope-source minimum thickness uses bisection because each photon line attenuates differently.
- Buildup-aware minimum-thickness design uses bisection because the G-P buildup factor depends on shield thickness in mean free paths.
- Buildup-aware design remains limited to single-layer homogeneous shielding.
- If buildup-aware design is unavailable, the simulator falls back to narrow-beam design and reports a warning.
- V1.07 reports photon flux, not dose rate, exposure rate, air kerma, or effective dose.

## v1.06 - Isotope Source Library and Source-Level Flux Calculation

Added isotope source modeling, activity unit conversion, line-by-line photon source calculations, and warning behavior for buildup requests outside the valid G-P mean-free-path range.

Changes:
- Added source model dataclasses:
  - `PhotonLine`
  - `IsotopeSource`
  - `ManualPhotonSource`
  - `SourceLineResult`
  - `SourceCalculationResult`
- Added isotope photon source library with selected major photon lines for:
  - Cs-137
  - Co-60
  - Am-241
  - Ba-133
  - Na-22
  - Mn-54
  - Co-57
  - Zn-65
  - Eu-152
  - Ir-192
- Added activity unit conversion to Bq for:
  - Bq
  - kBq
  - MBq
  - GBq
  - Ci
  - mCi
  - uCi
- Added isotope source mode to the command-line interface.
- Preserved manual monoenergetic photon source mode from previous versions.
- Added line-by-line source calculation for multi-line isotope sources.
- Added source-level summation of uncollided detector flux.
- Added source-level summation of buildup-corrected flux when buildup is valid for all photon lines.
- Added warning behavior when G-P buildup is requested outside the supported 40 MFP range.
- Updated output formatting to show source name, activity, photon line results, total flux, buildup results, and warnings.
- Added validation checks for source-library structure, activity conversion, photon emission rates, source flux summation, and invalid buildup range handling.
- Added V1.06 validation report for isotope source modeling and source-level calculation behavior.

Validated behavior:
- Activity conversion for Ci, mCi, and uCi.
- Creation of all 10 isotope sources.
- Correct photon line counts for each isotope source.
- Positive photon energy and intensity values for all source-library entries.
- Photon emission rate calculation using activity multiplied by emission intensity.
- Total uncollided source flux equals the sum of line-by-line uncollided flux values.
- Co-60 buildup-corrected source flux equals the sum of valid line-by-line buildup-corrected flux values.
- Manual source mode reproduces the V1.05 single-energy lead shielding regression case.
- Am-241 through 5 cm of lead correctly reports narrow-beam flux while skipping buildup above the valid G-P MFP range.
- Unsupported activity units are rejected.
- Unsupported isotope source names are rejected.
- Negative activity values are rejected.

Notes:
- The isotope library uses selected major photon lines, not complete decay spectra.
- Photon intensities are treated as emitted photons per decay before source self-attenuation, encapsulation, air attenuation, or detector-window effects.
- G-P buildup correction remains limited to single-layer homogeneous shielding.
- Buildup correction is only applied through 40 mean free paths. Above this range, narrow-beam flux is still reported but buildup is skipped with a warning.
- V1.06 reports photon flux, not dose rate, exposure rate, air kerma, or effective dose.

## v1.05 - Expanded Single-Layer G-P Buildup Material Support

Expanded Geometric Progression (G-P) gamma-ray buildup correction from lead-only support to multiple single-layer shielding materials.

Changes:
- Added G-P exposure buildup coefficient tables for:
  - Lead
  - Aluminum
  - Ordinary Concrete
  - Water
  - Tungsten
  - Copper
  - Tin
- Added a `key` field to the `Material` dataclass for stable internal material lookup.
- Updated buildup lookup to use `Material.key` instead of display names.
- Updated output text so buildup mode displays the selected material.
- Added validation runner checks for all supported buildup materials.
- Added validation checks confirming:
  - `B(0 MFP) = 1`
  - `B(1 MFP) = b`
  - `B(5 MFP) > 1`
- Added geometry validation preventing total shielding thickness from exceeding source-to-detector distance.
- Added V1.05 validation report for expanded buildup material support.

Validated behavior:
- Supported buildup material lookup.
- G-P buildup behavior for lead, aluminum, ordinary concrete, water, tungsten, copper, and tin.
- Material key lookup for display names such as `Concrete (Ordinary)`.
- Rejection of unsupported buildup materials.
- Rejection of multilayer buildup cases.
- Rejection of physically invalid source-to-detector geometry.

Notes:
- G-P buildup remains limited to single-layer homogeneous shielding.
- Barite concrete and polyethylene remain available for narrow-beam attenuation but do not currently support buildup correction.

## v1.04 - G-P Buildup Factor Support for Lead

Added the first implementation of Geometric Progression gamma-ray buildup correction.

Changes:
- Added `GPCoefficients` dataclass.
- Added G-P coefficient library structure.
- Added lead exposure buildup coefficients from ANS-6.4.3 reference data.
- Added exact and interpolated G-P coefficient lookup.
- Added G-P buildup factor calculation.
- Added buildup-corrected flux calculation.
- Added optional user prompt for G-P buildup correction.
- Restricted buildup mode to single-layer lead shielding.
- Added V1.04 validation report for G-P buildup behavior.

Validated behavior:
- Coefficient interpolation for lead.
- Buildup factor calculation at 0, 1, 5, and 10 mean free paths.
- Buildup-corrected flux calculation.
- Rejection of unsupported materials.
- Rejection of multilayer buildup cases.

## v1.03 - Python CLI and Code Organization Improvements

Intermediate development version after the Python rewrite.

Changes:
- Added user input for materials, layer thicknesses, photon energy, source strength, and detector distance.
- Added material selection from a dictionary-based material library.
- Added support for multiple shielding materials in the Python version.
- Improved file organization into separate modules:
  - `main.py`
  - `models.py`
  - `material_library.py`
  - `physics.py`
  - `calculator.py`
  - `input_handler.py`
  - `output.py`
- Improved command-line usability.

Notes:
- No major new physics model was added in this version.
- This version served as a cleanup and usability bridge between v1.02 and v1.04.

## v1.02 - Python Rewrite and Validation

Python rewrite of the original Java photon attenuation simulator.

Changes:
- Reimplemented the photon attenuation simulator in Python.
- Added dataclass-based `Material` and `Layer` models.
- Added NIST XCOM mass attenuation coefficient lookup.
- Added log-log interpolation for attenuation coefficients.
- Added narrow-beam Beer-Lambert attenuation through one or more layers.
- Added inverse-square point-source flux calculation.
- Added validation checks for:
  - Lead attenuation
  - Aluminum attenuation
  - Multilayer transmission
  - Exact table lookup
  - Duplicate-edge handling
  - Zero-thickness shielding
  - Invalid distance handling
  - HVL and TVL behavior

Documentation:
- Added V1.02 validation report.

## v1.01 - Original Java Version

Original Java implementation of the photon attenuation simulator.

Features:
- Modeled photon attenuation through shielding materials.
- Used NIST XCOM mass attenuation coefficient data.
- Converted mass attenuation coefficients to linear attenuation coefficients using material density.
- Calculated Beer-Lambert transmission.
- Included multilayer attenuation support.
- Included inverse-square geometric spreading.
- Included early material library and validation work.

Notes:
- This version established the original project concept and physics foundation.
- Later rewritten in Python to improve organization, readability, and future compatibility with scientific Python tools and possible OpenMC integration.