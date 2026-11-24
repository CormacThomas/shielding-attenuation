# Refactor and verification record

## Inventory and data flow

| Original repository | Refactored repository |
| --- | --- |
| Flat `src/` directory containing 54 Python modules and nine Java files | Installable `shielding` package with physics, reference data, design, scenario, benchmark, OpenMC, reporting, and CLI modules |
| Standalone interactive and batch scripts with `sys.path` setup | One installed `shielding` command with `interactive`, `scenario`, and `benchmark` subcommands. The two principal example scripts also run from an installed checkout. |
| One 12,066-line runner spanning six release-era validation sequences | Independently runnable pytest cases under `unit/`, `regression/`, and `benchmark/` |
| Multiple OpenMC release scripts, processed outputs, XML files, statepoints, and plots in the working tree | Generic model export, transport, and statepoint processing. Committed benchmark evidence is under `benchmarks/reference/`, with runtime results written to `output/`. |
| Separate release-era source conversion, collision-kerma buildup logic, and candidate-ranking paths | Shared implementations for each of those operations, with separate solvers for fluence and kerma targets |
| Historical docs, Java predecessor, and legacy scripts alongside current usage instructions | Historical snapshots under `archive/`, with a short README and current model, OpenMC, and interview guides |

The original execution paths were `src/main.py` for the interactive session, `examples/run_scenario.py` for deterministic JSON runs, the generic and version-specific scripts for OpenMC, and `src/validation_runner.py` for checks. The original scenario and profile directories remain inputs, including schemas 1.0 and 1.1. Material and source tables remain Python data modules. Matplotlib sits above the numerical result APIs. Live OpenMC imports occur only when the backend is invoked.

The refactor used local Git checkpoints for the original import, baseline tests, package move, module extraction, CLI bug fix, deduplication, asset curation, and OpenMC boundary changes. The downloadable ZIP is a clean source snapshot. The original upload remains intact.

## Verification performed

- The uploaded validation runner completed and printed 1,121 passing checks. Its assertions were migrated into 81 independently runnable pytest cases before moving the package. Case counts and console check counts measure different things.
- Eight deterministic replays check both uncollided and G-P shell-averaged air kerma against the archived matrix at a relative tolerance of 1e-10. The added analytical test independently checks two-layer Beer–Lambert attenuation and inverse-square spreading.
- The baseline headless scenario runner completed 11 of the 12 bundled scenarios. The V1.10 fluence design ran and then crashed during formatting because a photon design candidate has no `buildup_used` attribute. The new CLI reports the already-computed uncollided design and covers both reference design paths with a regression test.
- The offline aggregation reproduced the archived benchmark CSV field for field. Three figure scripts rendered 16 PNG and SVG outputs headlessly. Generated figures were kept out of the final repository snapshot.
- The isolated wheel installation successfully ran documented deterministic scenarios without NumPy, Matplotlib, or OpenMC. The local Python version was 3.12. The Linux and Windows CI matrix is included for downstream execution.
- Final local pytest result was **94 passed and 2 skipped**. Both skips require the OpenMC Python package. Model XML export with OpenMC, the live smoke test, and archived HDF5 reprocessing through the OpenMC API require an external OpenMC environment. No fresh transport calculation was performed.

## Numerical findings and remaining debt

- Historical G-P versus OpenMC discrepancy is material- and depth-dependent. The recorded signed OpenMC difference ranges from −46.13% to +38.23%. The sample is one isotope in eight homogeneous shields. The result gives no general bound on real-world accuracy.
- The G-P solver scans a finite grid before bisection. It may miss a short feasible interval. This behavior and the 40-MFP validity boundary were retained.
- The legacy activity parser lowercases suffixes and interprets `mbq` as megabecquerels. An input written as `mBq` therefore maps to the same multiplier. The behavior was retained for compatibility. Scenario files store activity explicitly in Bq.
- The inherited material coefficients, isotope yields, and relative costs have incomplete row-level provenance. A future data audit should compare transcriptions, absorption-edge energies, material compositions, and densities against their primary tables.
- Some plotters and migrated regression cases are still large. The verification suite exercises representative paths and the release benchmarks. It does not check every input combination or independently validate every coefficient. Transport still needs a pinned, repeatable data and execution environment for an automated OpenMC job.

## Size

Counts are physical Python lines, including comments and blanks. Package marker files are included. Archived scripts and binary assets are excluded from the active totals.

| Scope | Uploaded | Active refactor |
| --- | ---: | ---: |
| Source Python excluding the original validation runner | 26,702 lines / 53 modules | 22,332 lines / 72 files |
| Validation and automated tests | 12,066 lines / 1 runner | 10,830 lines / 24 files |
| Runnable example Python | 12,467 lines / 23 scripts | about 1,960 lines / 6 scripts |
| Total active Python | 51,235 lines | about 35,100 lines |

The nine Java files were archived. Forty selected reference files preserve the processed benchmark evidence, associated metadata, and one final statepoint. Remaining raw results are available in the original upload.
