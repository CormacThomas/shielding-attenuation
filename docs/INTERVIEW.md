# Interview guide

## 30 seconds

I built a Python photon shielding simulator to compare materials and estimate the thickness needed to meet an uncollided fluence or collision-air-kerma target. The deterministic solver uses tabulated attenuation and computes one contribution per photon line. It can screen many candidates quickly. I also built a matched OpenMC benchmark to see where a single-material buildup approximation agrees with photon transport. In my Cs-137 cases, the difference depended on the material and optical thickness, which changed how much confidence I placed in the screening result.

## Technical discussion

| If asked about | Explain |
| --- | --- |
| Where a result comes from | JSON defines source, geometry, and target. Activity times line yield gives photons/s. Use density and tabulated mass attenuation to compute optical thickness at each energy, apply transmission and inverse-square spreading, and combine line results. |
| Why two solvers | The deterministic kernel makes repeated sizing and ranking practical. OpenMC explicitly samples transport and tracks scattered photons. It adds data requirements, compute time, and statistical uncertainty. |
| What the comparison measures | Both report dry-air collision-kerma rate over the same evaluation shell. In OpenMC, normalize track length by shell volume and scale by source rate. Compare the direct response tally with the spectrum fold as a processing check, then compare to the deterministic shell average. |
| How you verified it | Show the analytical two-layer test, an absorption-edge test, the V1.05 Cs-137 lead regression, the scenario round trips, and the eight deterministic benchmark replays. Separate the historical OpenMC study from the live rerun status of the refactor. |
| One result worth discussing | For lead, OpenMC was about 10.9% below the G-P estimate at 1 MFP and 38.2% above it at 10 MFP. The 10-MFP run had about 3.11% relative statistical uncertainty. The difference concerns this model and geometry. Explain how geometry matching removes one comparison confounder and where model assumptions still differ. |
| Engineering tradeoffs | Different materials minimize thickness and areal mass. Hard limits can remove the unconstrained winner. The cost index supports a relative ranking, and the selected design can change with the set of candidate materials and objective weights. |
| Limits | Point source, simplified radial paths, selected emission lines, homogeneous buildup support, finite bracket scan, and no experimental qualification. Thin-shell results are volume averages. |

For a whiteboard walkthrough, use Cs-137 at 0.661657 MeV in lead at 5 MFP. At 100 cm the recorded shell-average responses were 18.87 µGy/h for uncollided, 45.69 µGy/h for G-P-adjusted, and 46.83 µGy/h for OpenMC. The optical-thickness definition makes the first calculation easy to explain. The difference between the two deterministic results gives a concrete way to discuss the buildup model.

Use the historical design choices you can defend from your own work. Good topics are why you retain rejected candidates, why scenario and run settings are separate, and what you learned from plotting signed differences across the benchmark cases. Explain the decision or observation in your own words and relate it to a specific case.

## Portfolio copy

**GitHub description** — Python photon shielding simulator for deterministic attenuation, material trade studies, and matched OpenMC benchmarks.

Choose bullets that match the work you can explain.

- Built a Python photon shielding simulator using NIST attenuation data, line-by-line source modeling, and G-P exposure buildup to estimate uncollided fluence and dry-air collision kerma.
- Developed a constrained material-selection workflow that solves for shield thickness and ranks feasible designs by thickness, areal mass, or relative cost.
- Compared deterministic and OpenMC collision-kerma estimates in eight matched Cs-137 shielding cases totaling 40 million historical photon histories, identifying a material- and depth-dependent buildup discrepancy.
