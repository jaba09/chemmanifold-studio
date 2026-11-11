# GA18 burner, corrected outlets, realistic species diffusion vs Fluent

Run on Javier's PC (WSL Ubuntu, OpenFOAM v2412 from conda, 8 ranks), 9-11 Nov 2026.

- Case: `openfoam/quemadorUnico` with the corrected outlets (top and chimney open, r = 0.14 m side a wall).
- Solver: `rhoReactingBuoyantLeFoam` (`openfoam/simpleFlame/solver`) with `constant/speciesDiffusion`:
  rho D_k = kappa/(cp Le_k) + mu_t/Sct, Le_k from a Cantera GA18 flame, Sct = 0.7 (Fluent's value).
  The previous runs used the stock solver: rho D_k = mu + mu_t for every species (Sc = Sc_t = 1).
- Steady state by local time stepping, 10,264 iterations (~13-15 s/iteration once lit, ~43 h of computing).
- Reference: Fluent solution `quemadorUnicoTesis_60KCells-GA18--ID.dat.h5` (corrected case). Same mesh, so
  the comparison is cell by cell (`openfoam/tools/compare_fluent.py`).

## Convergence

The flame went through a long transient: close to Fluent at iteration 2200, a wide S-shaped flame by 4000
(hot volume 92 cm3), then back. From 8800 to 10200 every metric changed by less than 2.5 %.

| iteration | Tmax [K] | flame base [mm] | hot volume T>1500 K [cm3] | mean abs dT, hot cells [K] |
|---|---|---|---|---|
| Fluent | 2088 | 1.1 | 18.2 | |
| 2200 | 2115 | 6.9 | 19.8 | 356 |
| 4000 | 2163 | 9.9 | 92.3 | 777 |
| 6200 | 2096 | 6.4 | 49.9 | 410 |
| 7400 | 2121 | 2.9 | 42.4 | 344 |
| 8400 | 2140 | 1.4 | 55.3 | 421 |
| 8800 | 2136 | 1.6 | 58.8 | 425 |
| 9200 | 2129 | 1.9 | 59.7 | 421 |
| 10000 | 2125 | 1.6 | 59.8 | 416 |
| 10200 | 2126 | 1.6 | 60.1 | 415 |

## Final state (iteration 10200) vs Fluent

| | Fluent | OpenFOAM, Le_k + Sct 0.7 |
|---|---|---|
| Tmax | 2088 K | 2126 K |
| Flame base (lowest x with T > 1500 K) | 1.1 mm | 1.6 mm |
| OH max | 0.00328 | 0.00297 |
| CO max | 0.0532 | 0.0634 |
| Hot volume T > 1500 K, below disk, r < 20 mm | 14.0 cm3 | 18.1 cm3 |
| Hot volume T > 1500 K, below disk, 20 < r < 50 mm | 4.3 cm3 | 42.1 cm3 |
| Volume T > 1800 K | 8.6 cm3 | 39.4 cm3 |
| Volume T > 2000 K | 3.0 cm3 | 19.6 cm3 |

The flame now sits where Fluent's does: a thin sheet at r ~ 9 mm from the nozzle that turns outward under
the disk, attached at the nozzle, with peak T and OH within 2 % and 10 %. What remains different is the
outer part, where the sheet runs along the underside of the disk (r = 20-50 mm): OpenFOAM keeps a thick
layer of gas above 1500 K there (42 cm3 against 4 cm3), so the gas under the disk holds about 2.8 times
Fluent's sum of V (T - 300). Candidate causes to check next: the disk wall heat transfer (Fluent: fixed
300 K on wall-disk), the wall treatment of k-omega SST near the disk, and the hood baffle coupling.

Figures: `compare_it2200.png`, `compare_it4000.png`, `compare_it10200.png` (Fluent left, OpenFOAM right).
