# Changelog

All major development milestones for the Shielding Attenuation Simulator are documented here.

## v1.15.0 — Packaging and verification refactor

- Installed the simulator as the `shielding` Python package and command.
- Moved the original validation checks into pytest and added deterministic replay of the eight-case V1.14 matrix.
- Shared the source, collision-kerma, and ranking logic used by multiple workflows.
- Fixed V1.10 photon-fluence scenario reporting and protected benchmark input files from output-directory replacement.
- Preserved processed benchmark records and put prior Java code, release scripts, and reports under `archive/`.

## v1.13 - Matched Cs-137/Lead OpenMC Benchmark

Added the first complete quantity-matched deterministic/OpenMC photon-shielding benchmark. Version 1.13 uses one shared physical scenario to construct deterministic and Monte Carlo calculations, processes a preserved five-million-history OpenMC production statepoint, compares shell-volume-averaged dry-air collision air kerma, and packages the benchmark with reproducible inputs, processed results, figures, acceptance checks, and provenance metadata.

Changes:
- Added fixed-shield response support to the shared scenario layer.
- Added scenario JSON schema version `1.1`.
- Added the official V1.13 physical scenario:
  - `scenarios/cs137_v113_production.json`.
- Added the official V1.13 OpenMC settings profile:
  - `config/openmc/v113_production.json`.
- Kept physical scenario inputs separate from OpenMC execution settings.
- Added support for scenario-defined:
  - centered isotope photon sources;
  - vacuum source cavities;
  - ordered concentric spherical shield layers;
  - evaluation radii;
  - fixed-shield deterministic response calculations.
- Added reusable OpenMC data models for:
  - benchmark settings;
  - evaluation shells;
  - tally definitions;
  - processed spectrum bins;
  - direct response results;
  - deterministic/OpenMC comparison results.
- Added `openmc_model_builder.py`.
- Added scenario-driven OpenMC construction for:
  - source cavity;
  - spherical shield shells;
  - evaluation shell;
  - exterior vacuum region;
  - outer vacuum boundary.
- Added material construction using project material definitions and OpenMC photon data.
- Added centered isotropic fixed-source construction.
- Added physical photon-source-rate calculation from activity and emission intensity.
- Added OpenMC photon transport settings for:
  - thick-target bremsstrahlung treatment;
  - atomic relaxation;
  - photon cutoff energy;
  - source particles per batch;
  - batch count;
  - random seed;
  - thread count;
  - statepoint batches.
- Added `openmc_tally_builder.py`.
- Added an energy-resolved photon track-length flux tally.
- Added a direct dry-air collision-air-kerma response tally.
- Added stable tally identifiers for benchmark processing.
- Added 42 photon-energy bins spanning 1 keV to 700 keV.
- Added a dedicated narrow bin containing the 661.657 keV Cs-137 source line.
- Added `openmc_statepoint_processor.py`.
- Added automatic extraction of named V1.13 tallies from OpenMC statepoints.
- Added evaluation-shell volume calculation.
- Added shell-volume normalization of track-length flux.
- Added physical source-rate scaling.
- Added energy-bin representative-energy calculation.
- Added bin-level fluence-rate uncertainty processing.
- Added bin-level dry-air response-coefficient folding.
- Added spectrum-folded collision-air-kerma reconstruction.
- Added direct collision-air-kerma mean and standard-deviation processing.
- Added Gy/s and µGy/h output.
- Added relative-uncertainty reporting.
- Added `openmc_result_io.py`.
- Added reproducible JSON output for processed OpenMC response records.
- Added reproducible CSV output for energy-resolved photon spectra.
- Added deterministic/OpenMC comparison JSON output.
- Added `openmc_settings_io.py`.
- Added serialization and validation for OpenMC settings profiles.
- Added deterministic shell-volume averaging so deterministic and OpenMC responses represent the same spatial observable.
- Added deterministic uncollided collision-air-kerma comparison.
- Added deterministic G-P exposure-buildup-adjusted collision-air-kerma comparison.
- Added the observed Monte Carlo response ratio relative to the deterministic uncollided result.
- Added relative-difference reporting from both deterministic response methods.
- Added direct-versus-spectrum-folded consistency checks.
- Added required and preferred Monte Carlo uncertainty checks.
- Added explicit configured tolerances and pass/fail results.
- Added a development benchmark workflow.
- Added a production benchmark workflow.
- Added recovery processing for the preserved production statepoint.
- Added `examples/openmc_v113_production_run.py`.
- Added `examples/openmc_v113_process_production_recovery.py`.
- Added `examples/check_v113_benchmark_plot_data.py`.
- Added a reusable V1.13 benchmark plot-data layer.
- Added validation of:
  - processed response records;
  - comparison records;
  - spectrum rows;
  - benchmark metadata;
  - acceptance-check consistency;
  - plotted result ordering.
- Added `openmc_benchmark_plots.py`.
- Added annotated OpenMC spherical geometry rendering.
- Added combined use of:
  - full-domain OpenMC geometry;
  - central shield-detail inset;
  - coded callouts and scale annotations.
- Added an energy-resolved photon-spectrum panel.
- Added a deterministic/OpenMC collision-air-kerma comparison panel.
- Added a benchmark metadata and acceptance-summary panel.
- Added an official four-panel V1.13 benchmark figure.
- Added separate PNG and SVG exports for:
  - annotated geometry;
  - photon spectrum;
  - response comparison;
  - benchmark summary;
  - combined benchmark figure.
- Added `examples/generate_v113_benchmark_figure.py`.
- Added raw OpenMC geometry-plot generation.
- Added full-domain and central-detail geometry images.
- Added reproducible benchmark-figure generation without requiring OpenMC for processed-result rendering.
- Added the canonical release package:
  - `results/v1.13/cs137_lead_benchmark/`.
- Added authoritative input copies under:
  - `inputs/`.
- Added processed response, comparison, spectrum, and summary records under:
  - `processed/`.
- Added official benchmark figures under:
  - `figures/`.
- Added preservation of raw OpenMC geometry images under:
  - `figures/raw_openmc/`.
- Added `comparison_summary.csv`.
- Added a reconstructed recovery manifest.
- Added explicit identification of unavailable original metadata:
  - wall-clock runtime;
  - original execution timestamp;
  - original Git commit.
- Added SHA-256 verification of the canonical statepoint.
- Added verification that the production statepoint and processing copy are byte-for-byte identical.
- Added overwrite protection for mismatched release artifacts.
- Added `examples/package_v113_release.py`.
- Added the V1.13 benchmark technical report:
  - `results/v1.13/cs137_lead_benchmark/README.md`.
- Updated public photon-response semantics so photon-number response curves expose only uncollided photon fluence.
- Removed G-P exposure-buildup values from current photon-fluence response-curve models.
- Removed ambiguous current-response use of `buildup_corrected_flux`.
- Retained legacy buildup-named fields only where required for historical regression compatibility.
- Preserved V1.12 deterministic collision-air-kerma and strict buildup behavior.
- Preserved execution of the historical V1.10 and V1.12 reference scenarios.
- Preserved all earlier attenuation, source, response, optimization, scenario, and plotting regression behavior.

Validated behavior:
- The official V1.13 scenario reconstructs the same physical geometry for the deterministic and OpenMC backends.
- The source cavity extends from 0 to 1.0 cm.
- The Lead shield extends from 1.0 to 6.0 cm.
- The evaluation shell extends from 99.5 to 100.5 cm.
- The outer vacuum boundary is located at 110.0 cm.
- The source activity is 3.70 × 10¹⁰ Bq.
- The modeled photon emission intensity is 0.851 photons per decay.
- The physical photon source rate is 3.1487 × 10¹⁰ photons/s.
- The OpenMC production profile uses:
  - 50,000 source particles per batch;
  - 100 batches;
  - 5,000,000 total source histories;
  - random seed 113013;
  - four configured threads.
- The processed photon spectrum contains 42 energy bins.
- The evaluation-shell volume is approximately 125664.753341 cm³.
- The total physical photon fluence rate is approximately:
  - 1480.394929639 photons/cm²/s.
- The deterministic uncollided collision-air-kerma rate is approximately:
  - 5.139917558 µGy/h.
- The deterministic G-P-adjusted collision-air-kerma rate is approximately:
  - 13.557461191 µGy/h.
- The direct OpenMC collision-air-kerma rate is approximately:
  - 15.019807382 µGy/h.
- The spectrum-folded OpenMC collision-air-kerma rate is approximately:
  - 15.021290068 µGy/h.
- The direct OpenMC standard deviation is approximately:
  - 0.087341811 µGy/h.
- The direct OpenMC relative uncertainty is approximately:
  - 0.581511%.
- The required 5% relative-uncertainty criterion passes.
- The preferred 2% relative-uncertainty criterion passes.
- The direct and spectrum-folded OpenMC responses differ by approximately:
  - 0.009872%.
- The configured 2% direct-versus-folded tolerance passes.
- The observed Monte Carlo response ratio relative to the deterministic uncollided result is approximately:
  - 2.922188.
- The direct OpenMC result is approximately 192.22% above the deterministic uncollided result.
- The direct OpenMC result is approximately 10.79% above the deterministic G-P result.
- The G-P estimate captures most, but not all, of the transported response in this benchmark.
- The production statepoint and recovery-processing copy share the SHA-256 digest:
  - `3D8342114E7F00A1B590CF1CF77EE9D95B2259E7C576EFB52C956E03B7695562`.
- Processed benchmark records pass structural and numerical consistency checks.
- Figure generation produces the complete PNG and SVG benchmark set.
- Release packaging verifies matching existing artifacts and rejects conflicting overwrites.
- The complete validation runner continues to end with:
  - `All validation tests passed.`

Validated benchmark:
- Source: 1.00 Ci Cs-137
- Activity: 3.70 × 10¹⁰ Bq
- Photon energy: 0.661657 MeV
- Emission intensity: 0.851 photons/decay
- Source-cavity radius: 1.0 cm
- Shield: 5.0 cm Lead
- Shield outer radius: 6.0 cm
- Evaluation-shell center radius: 100.0 cm
- Evaluation-shell thickness: 1.0 cm
- Outer vacuum-boundary radius: 110.0 cm
- OpenMC source histories: 5,000,000
- Energy bins: 42
- Response quantity: shell-volume-averaged dry-air collision air-kerma rate
- Deterministic uncollided response: approximately 5.139918 µGy/h
- Deterministic G-P response: approximately 13.557461 µGy/h
- OpenMC direct response: approximately 15.019807 µGy/h
- OpenMC folded response: approximately 15.021290 µGy/h
- OpenMC relative uncertainty: approximately 0.5815%
- Direct-versus-folded agreement: PASS
- Required uncertainty criterion: PASS
- Preferred uncertainty criterion: PASS

Notes:
- V1.13 is a benchmark-foundation release rather than a broad material, energy, or deep-penetration validation study.
- The benchmark technical README fulfills the V1.13 reproducible-report requirement.
- A broader formal validation report is deferred to the multi-case V1.14 benchmark study.
- Collision air kerma is not effective dose, organ dose, ambient dose equivalent, or a regulatory dose quantity.
- The evaluation shell is modeled as a vacuum scoring region.
- Dry-air collision air kerma is obtained through response-function scoring and folding rather than by filling the shell with physical air.
- The deterministic and OpenMC results are compared using the same shell-volume-averaged response quantity.
- The G-P result is an approximate exposure-buildup-adjusted deterministic response.
- The G-P result is not interpreted as a general photon-number-fluence correction.
- The observed Monte Carlo response ratio is specific to this benchmark and must not be generalized as a universal buildup coefficient.
- V1.13 does not establish universal agreement between G-P buildup and Monte Carlo transport.
- The production benchmark does not use variance-reduction methods.
- The successful production transport result was preserved even though the original post-run workflow failed before writing its normal manifest.
- The reconstructed manifest does not fabricate unavailable runtime, timestamp, or Git metadata.
- The raw statepoint remains outside the compact release package and is referenced by repository path and SHA-256 digest.
- Fresh OpenMC transport is not required to inspect, regenerate figures from, or verify the packaged processed benchmark.
- V1.14 will expand the benchmark into a compact matrix of materials, energies, and shielding depths.

## v1.12 - Radiation-Response Quantity Foundation

Added an explicit radiation-response quantity layer so deterministic shielding results can be compared scientifically with future OpenMC calculations. Version 1.12 separates photon-number fluence from photon energy fluence, uncollided collision air kerma, and G-P exposure-buildup-adjusted collision air kerma.

Changes:
- Added `air_response_library.py`.
- Added a 38-entry NIST dry-air mass energy-absorption coefficient library covering 0.001 to 20 MeV.
- Stored dry-air response coefficients in cm²/g with the source description preserved alongside every entry.
- Preserved the duplicate published values at the 0.00320290 MeV argon K absorption edge.
- Added absorption-edge-aware coefficient lookup.
- Added exact coefficient lookup.
- Added log-log coefficient interpolation.
- Prevented interpolation across the zero-width interval between duplicate absorption-edge entries.
- Added explicit rejection of photon energies outside the supported response-coefficient range.
- Added `unit_conversions.py` for:
  - MeV to joule conversion;
  - energy-fluence area conversion from cm² to m²;
  - cm²/g to m²/kg conversion;
  - Gy/s to µGy/h conversion;
  - µGy/h to Gy/s conversion.
- Added `air_response_models.py`.
- Added `AirKermaCoefficient`.
- Added `PhotonLineAirKermaResult`.
- Added `SourceAirKermaResult`.
- Added explicit buildup statuses:
  - `not_requested`;
  - `applied`;
  - `unavailable`;
  - `fallback`.
- Added line-level storage of:
  - photon energy;
  - emission intensity;
  - photon emission rate;
  - uncollided photon fluence rate;
  - photon energy fluence rate;
  - dry-air mass energy-absorption coefficient;
  - uncollided collision air-kerma rate;
  - calculation method;
  - coefficient source;
  - buildup status;
  - buildup factor;
  - buildup-adjusted collision air-kerma rate;
  - warnings.
- Added source-level storage of:
  - total uncollided photon fluence rate;
  - total uncollided collision air-kerma rate;
  - source buildup status;
  - total buildup-adjusted collision air-kerma rate;
  - combined warnings.
- Added validation preventing adjusted source totals from combining applied and unapplied line responses.
- Added validation preventing buildup-adjusted air-kerma rates from being less than the corresponding uncollided rates.
- Added `air_response.py`.
- Added photon energy-fluence-rate calculation.
- Added collision-air-kerma-rate calculation using NIST dry-air μen/ρ data.
- Added canonical internal air-kerma-rate storage in Gy/s.
- Added primary engineering output in µGy/h.
- Added line-by-line response folding for manual and isotope photon sources.
- Added source-level air-kerma aggregation.
- Added G-P exposure buildup application to compatible collision-air-kerma responses.
- Separated G-P factor calculation from the historical `buildup_corrected_flux` pathway.
- Prevented exposure buildup factors from being applied to public photon-number-fluence results.
- Retained historical buildup-named fields and functions only for V1.10 and earlier regression compatibility.
- Updated legacy comments and output terminology to identify historical G-P-scaled photon results as response proxies rather than physical total photon flux.
- Added `AirKermaRateTarget`.
- Added `AirKermaMinimumThicknessResult`.
- Added separate air-kerma design candidates and material-comparison results.
- Prevented air-kerma values from being stored in legacy fields named `final_flux` or `final_transmission`.
- Added fixed-thickness collision-air-kerma calculations.
- Added air-kerma minimum-thickness calculations.
- Added air-kerma material comparison.
- Added air-kerma constrained material optimization.
- Added explicit selected-response ratios.
- Added strict buildup-aware design behavior.
- Required valid G-P exposure buildup for every contributing photon line when buildup is requested.
- Preserved valid uncollided diagnostic results when buildup is unavailable.
- Prevented unavailable buildup-aware candidates from silently becoming uncollided fallback designs.
- Preserved historical fallback behavior only for legacy V1.10 photon-response pathways.
- Added numerical handling for the physical zero-thickness boundary:
  - `B(E, 0) = 1`.
- Added floating-point tolerance at the exact 40-MFP G-P boundary.
- Continued to reject meaningful extrapolation above 40 MFP.
- Added bracket scanning before bisection for buildup-adjusted minimum-thickness calculations.
- Added support for responses that initially rise because buildup increases faster than Beer-Lambert attenuation decreases.
- Added first-failed-to-passed target-crossing detection.
- Added response-aware CLI input.
- Added response selection between:
  - uncollided photon fluence rate;
  - collision air-kerma rate.
- Updated fixed-thickness CLI routing.
- Updated minimum-thickness CLI routing.
- Updated material-comparison CLI routing.
- Updated material-optimization CLI routing.
- Restricted the G-P exposure-buildup prompt to compatible collision-air-kerma calculations.
- Updated source output terminology to use:
  - uncollided photon fluence rate;
  - collision air-kerma rate;
  - G-P exposure-buildup-adjusted collision air-kerma rate.
- Removed generic `Final Flux` terminology from current material-comparison output.
- Added explicit response-basis and unit labels to minimum-thickness, comparison, optimization, and scenario output.
- Added strict failure output showing:
  - `Unavailable`;
  - `FAILED`;
  - the specific G-P applicability or data limitation.
- Added air-kerma target serialization to the shared scenario format.
- Updated scenario execution to route air-kerma targets through the V1.12 optimizer.
- Added the official V1.12 scenario:
  - `scenarios/cs137_air_kerma_reference.json`.
- Updated `examples/run_scenario.py`.
- Made the scenario runner default to the V1.12 air-kerma reference case.
- Added response-aware scenario output.
- Added selected final air-kerma rate, response ratio, and buildup status to scenario summaries.
- Added explicit reporting of eligible, rejected, and failed candidate counts.
- Preserved execution of the historical V1.10 JSON scenario.
- Added `air_response_plots.py`.
- Added a reusable isotope photon-line air-kerma contribution plot.
- Added validation requiring successful buildup for every line included in the adjusted-response figure.
- Added `examples/generate_v112_line_contribution_figure.py`.
- Added a reproducible Co-60 portfolio case using:
  - 1.00 Ci Co-60;
  - 5.00 cm Lead;
  - 100 cm evaluation distance.
- Added PNG and SVG export under:
  - `docs/figures/v1.12/`.
- Added line annotations showing:
  - line energy;
  - emission intensity;
  - G-P buildup factor;
  - air-kerma contribution;
  - percentage of the corresponding source total.
- Added V1.12 validation coverage for:
  - dry-air coefficient-library size and ordering;
  - exact coefficient lookup;
  - log-log interpolation;
  - absorption-edge handling;
  - coefficient-range rejection;
  - unit conversions;
  - monoenergetic collision-air-kerma calculations;
  - photon-line metadata;
  - source-level summation;
  - Cs-137 line response;
  - Co-60 two-line response;
  - Am-241 low-energy applicability;
  - zero-thickness response;
  - G-P applicability and strict failure behavior;
  - air-kerma targets and result models;
  - minimum-thickness calculations;
  - nonmonotonic response bracketing;
  - air-kerma material comparison;
  - constrained air-kerma optimization;
  - scenario serialization and execution;
  - CLI response routing;
  - output terminology;
  - legacy V1.10 compatibility.
- Added the V1.12 validation report.

Validated behavior:
- The dry-air response library contains 38 ordered entries from 0.001 to 20 MeV.
- Exact lookup at 0.060 MeV returns 0.03041 cm²/g.
- Interpolation at the 0.661657 MeV Cs-137 line returns approximately 0.0292866445539 cm²/g.
- The argon K-edge below value returns 133.0 cm²/g.
- The argon K-edge above value returns 146.0 cm²/g.
- An ambiguous exact absorption-edge request is rejected unless the requested side is specified.
- A 25 MeV coefficient request is rejected as outside the supported range.
- A 0.661657 MeV fluence rate of 100 photons/cm²/s produces:
  - 66.1657 MeV/(cm²·s) energy fluence rate;
  - approximately 3.10465195908 × 10⁻¹⁰ Gy/s collision air-kerma rate;
  - approximately 1.11767470527 µGy/h.
- Source-level photon fluence and air-kerma totals equal the sums of their line contributions.
- A buildup-adjusted source total is produced only when buildup is applied successfully to every line.
- Mixed `not_requested` and `applied` line states are rejected.
- The Co-60 portfolio case produces approximately:
  - 402.828646 µGy/h uncollided collision air kerma;
  - 1086.362490 µGy/h G-P-adjusted collision air kerma.
- The 1.332492 MeV Co-60 line contributes approximately:
  - 60.3% of the uncollided total;
  - 59.8% of the buildup-adjusted total.
- The Am-241 59.541 keV line through 5 cm of Lead produces approximately 290.34 MFP.
- The Am-241 case retains the valid uncollided response, marks buildup unavailable, omits the adjusted total, and preserves the applicability warning.
- G-P buildup returns exactly one at zero shielding thickness.
- The adjusted zero-thickness response equals the uncollided response.
- A 0.100 MeV Water case demonstrates an initial rise in buildup-adjusted response.
- The bracket-first solver identifies and refines the first valid target crossing rather than assuming endpoint monotonicity.
- The 1 Ci Cs-137, 100 cm, 1 µGy/h Lead design requires approximately:
  - 6.299137035 cm without buildup;
  - 7.180648660 cm with G-P exposure buildup.
- The official V1.12 scenario evaluates nine materials.
- Lead is selected at approximately 7.180648660 cm.
- Lead mass per area is approximately 81.428555808 g/cm².
- The selected adjusted collision air-kerma rate is approximately 1.000000 µGy/h.
- The selected response ratio is approximately 3.570781 × 10⁻⁴.
- Lead and Tungsten are eligible.
- Aluminum, Ordinary Concrete, Copper, and Tin are rejected by engineering constraints.
- Barite Concrete and Polyethylene fail because validated G-P exposure buildup data are unavailable.
- Water fails because it cannot reach the target within the 100 cm calculation range.
- Strict failed candidates are displayed as unavailable and failed rather than as fallback designs.
- Public photon-response output identifies uncollided photon fluence rate in photons/cm²/s.
- Public photon material-comparison output no longer uses the generic `Final Flux` column.
- Historical G-P-scaled photon results are identified as legacy response proxies.
- The historical V1.10 scenario remains reproducible.
- The complete validation runner produces 684 PASS assertions.
- V1.12 adds 365 focused assertions while preserving all 319 assertions documented through V1.11.

Validated example:
- Source: 1.00 Ci Cs-137
- Activity: 3.70 × 10¹⁰ Bq
- Photon line: 0.661657 MeV
- Emission intensity: 0.851 photons/decay
- Evaluation radius: 100 cm
- Target: G-P exposure-buildup-adjusted collision air-kerma rate ≤ 1 µGy/h
- Calculation search limit: 100 cm
- Maximum design thickness: 20 cm
- Maximum mass per area: 120 g/cm²
- Optimization objective: minimum mass per area
- G-P exposure buildup required
- Nine candidate materials evaluated
- Two materials eligible
- Four materials rejected
- Three materials failed
- Lead selected at approximately 7.180649 cm
- Lead mass per area approximately 81.428556 g/cm²
- Final adjusted response approximately 1.000000 µGy/h

Notes:
- V1.12 defines a matched radiation-response quantity but does not yet claim deterministic-versus-OpenMC agreement.
- Dry-air μen/ρ folding produces a collision air-kerma-rate estimate.
- Collision air kerma is not effective dose, organ dose, ambient dose equivalent, or a regulatory dose quantity.
- Published exposure buildup factors are used as dimensionless response-ratio approximations for compatible collision-air-kerma calculations.
- G-P exposure buildup is not interpreted as a photon-number-fluence correction.
- G-P exposure buildup remains limited to supported homogeneous single-material shields.
- Deterministic multilayer buildup is intentionally not claimed.
- G-P calculations remain limited to 40 MFP.
- Strict buildup-aware air-kerma designs do not silently fall back to uncollided results.
- Legacy fields such as `final_flux`, `uncollided_flux`, and `buildup_corrected_flux` remain only for backward compatibility.
- `FluxTarget` remains the internal compatibility name for an uncollided photon-fluence-rate target.
- The isotope library contains selected useful photon lines rather than complete decay spectra.
- The Co-60 line-contribution figure is a deterministic engineering visualization rather than a Monte Carlo result.
- V1.13 will construct the first quantity-matched OpenMC photon benchmark using energy-resolved photon fluence folded with the same NIST dry-air response coefficients.

## v1.11 - Reproducible Scenarios and Spherical Geometry

Added a reproducible scenario layer and concentric spherical geometry foundation above the validated V1.10 deterministic shielding and optimization workflow.

Changes:
- Added `geometry_models.py` with:
  - `ShieldLayerSpec`;
  - `SphericalShell`;
  - `ConcentricSphericalGeometry`.
- Added automatic derivation of ordered spherical-shell inner and outer radii.
- Added validation for:
  - source-cavity radius;
  - evaluation radius;
  - shielding-layer thickness;
  - outer shield radius;
  - layer ordering.
- Added serializable source specifications for:
  - manual monoenergetic photon sources;
  - isotope sources.
- Added `DeterministicSettings` for buildup selection and numerical thickness-search limits.
- Added the complete `ShieldingScenario` model containing:
  - scenario metadata;
  - source specification;
  - spherical geometry;
  - candidate materials;
  - design target;
  - engineering constraints;
  - optimization objective;
  - optional balanced weights;
  - deterministic settings.
- Added scenario-level validation preventing:
  - empty or duplicate candidate material keys;
  - unsupported calculation modes;
  - inconsistent optimization weights;
  - fixed layers in material-optimization scenarios;
  - numerical search limits beyond available radial space.
- Added `scenario_io.py` for:
  - typed dictionary conversion;
  - formatted JSON saving;
  - JSON loading;
  - schema-version validation;
  - malformed-file rejection;
  - readable missing-field errors;
  - save/load round-trip reconstruction.
- Added JSON schema version `1.0`.
- Added `scenario_runner.py` to:
  - convert source specifications into existing runtime source objects;
  - resolve material keys through the material library;
  - route validated scenario inputs into the existing optimizer.
- Added the official reference scenario:
  - `scenarios/cs137_v110_reference.json`.
- Added `examples/run_scenario.py` for one-command JSON scenario execution.
- Added V1.11 architecture documentation showing the planned shared deterministic/OpenMC scenario pathway.
- Added `examples/openmc_smoke_test.py`.
- Verified OpenMC 0.15.3 through the official Docker image.
- Confirmed:
  - continuous-energy data access;
  - fixed-source photon transport;
  - spherical Lead-shell model execution;
  - statepoint generation;
  - named tally extraction through Python.
- Added V1.11 validation coverage for:
  - shell-radius derivation;
  - geometry rejection;
  - source normalization;
  - runtime-source conversion;
  - material resolution;
  - scenario consistency;
  - JSON serialization;
  - JSON round trips;
  - malformed and incomplete JSON;
  - unsupported schema versions;
  - official reference-case reproduction.
- Added the V1.11 validation report.

Validated behavior:
- A 2 cm source cavity with 5 cm of Lead and 1 cm of Copper produces:
  - 6 cm total shielding thickness;
  - 8 cm outer shield radius;
  - Lead spanning 2–7 cm;
  - Copper spanning 7–8 cm.
- Scenario JSON save/load operations reconstruct equivalent `ShieldingScenario` objects.
- Invalid geometry, unknown materials, duplicate materials, unsupported schemas, malformed JSON, and inconsistent scenario combinations are rejected.
- The official JSON scenario evaluates all nine candidate materials.
- Lead remains selected at approximately 7.088213 cm.
- Lead mass per area remains approximately 80.380339 g/cm².
- The complete validation runner produces 319 PASS assertions.
- V1.11 adds 46 focused assertions while preserving all 273 previously documented regression assertions.
- The OpenMC smoke test successfully produces and reads a statepoint.

Notes:
- V1.11 does not modify the previously validated attenuation, buildup, source, thickness-solver, optimization, Pareto, or plotting equations.
- The scenario runner currently supports `material_optimization`.
- Fixed shielding layers are intentionally rejected in material-optimization scenarios.
- The deterministic backend does not yet calculate total spherical shield mass or full three-dimensional transport.
- The OpenMC smoke test is independent of `ShieldingScenario` and verifies environment readiness only.
- The OpenMC tally is not yet a quantity-matched deterministic comparison.
- Shared scenario-to-OpenMC model construction is planned for V1.13.

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