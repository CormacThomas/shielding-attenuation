# OpenMC benchmark workflow

The Python interface, OpenMC executable, and compatible continuous-energy data with photon evaluations must be configured separately. For Linux or macOS with Conda, install OpenMC from conda-forge and then install this project in that environment. On Windows, the OpenMC installation guide describes a container route. The historical matrix used OpenMC 0.15.3.

```bash
conda create -n shielding-openmc -c conda-forge openmc=0.15.3
conda activate shielding-openmc
python -m pip install -e ".[test]"
export OPENMC_CROSS_SECTIONS=/absolute/path/to/cross_sections.xml
openmc --version
```

See the [OpenMC installation and data guide](https://docs.openmc.org/en/stable/usersguide/install.html) for platform and data details. The historical manifests record an NNDC HDF5 path from the original environment. Match the nuclear-data release and configuration where possible when reproducing published comparisons.

## Export, run, and process

Run from the repository root in the configured environment.

```text
shielding benchmark --mode export --scenario scenarios/v1.14/cs137_lead_05mfp.json --settings config/openmc/v114_smoke.json --output-directory output/lead-export

shielding benchmark --mode run --scenario scenarios/v1.14/cs137_lead_05mfp.json --settings config/openmc/v114_smoke.json --output-directory output/lead-smoke

shielding benchmark --mode process --scenario scenarios/v1.14/cs137_lead_05mfp.json --settings config/openmc/v114_production.json --statepoint benchmarks/reference/v1.14/statepoints/lead-05mfp.h5 --output-directory output/lead-reprocessed
```

The export command builds model XML and adds tallies without executing transport. The run command exports the model, executes the requested histories, records settings and provenance, and processes the final statepoint. Process mode reads an existing statepoint with the matching scenario, profile, and shell thickness. Use a fresh output directory or specify `--overwrite` to replace an existing run directory. Exit codes 2 and 3 indicate a required uncertainty criterion or direct-versus-folded criterion failed, respectively. The smoke profile uses 100,000 histories. Use the production profile for five million histories per case and the default 1 cm shell thickness for the recorded matrix.

## Historical evidence and optional tests

- [Matrix CSV](../benchmarks/reference/v1.14/analysis/v114_core_matrix.csv) and [summary](../benchmarks/reference/v1.14/analysis/v114_core_matrix_summary.txt) contain the historical eight-case comparison. The `production/` subdirectories beside them preserve processed response spectra, comparison JSON, and execution manifests. The lead 5-MFP final statepoint supports reprocessing. The original upload contains the remaining raw statepoints and release outputs.
- `python examples/aggregate_v114_core_results.py` rebuilds the matrix from the processed records without OpenMC. `python -m pytest -m openmc` reprocesses the archived lead statepoint and runs a live smoke case when the relevant OpenMC prerequisites are available. These optional integration cases were skipped in the refactor environment.
- In the historical matrix, eight cases passed the 5% required direct-tally uncertainty threshold, seven passed the preferred 2% threshold, and all eight passed the 2% direct-versus-spectrum-folded threshold. Lead at 10 MFP had the largest relative statistical uncertainty, approximately 3.11%. Thresholds concern the run diagnostics and do not bound the error of the deterministic approximation.
