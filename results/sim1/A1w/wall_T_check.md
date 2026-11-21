# G1 wall-temperature check (A1w)

10 Nov 2026, 14:50-16:20 CET, sim1, 8 ranks, 7.7 s/step. R2 (A1) restarted at t = 0.2 s with Fluent's own wall-face
temperatures (corrected `.dat.h5`) imposed as fixedValue T on the three pot walls
(`openfoam/tools/fluent_wall_T_to_foam.py`, faces matched one to one by position):
fuel side (pot bottom over the gap) 643-921 K (was adiabatic), mixing side 409-611 K, exhaust side 336-406 K
(both were h 15 W/m2K to 323 K). Everything else as A1 (LeFoam + constantLewis, GA18 DI, dt 2e-5 s).

| t (s) | V(T > 1500 K) (cm3) | Tmax (K) | flame base (mm) | mean hot-cell abs(dT) vs Fluent (K) |
|---|---|---|---|---|
| 0.200 (R2) | 54.5 | 2136 | 1.39 | 353 |
| 0.204 | 38.5 | 2125 | 1.39 | 189 |
| 0.214 | 28.0 | 2119 | 1.39 | 110 |
| Fluent DI | 18.25 | 2087.5 | 1.15 | - |

**The diagnosis is confirmed.** With the pot bottom at Fluent's radiating-wall temperature, the hot volume fell by 26 of the
36 cm3 excess in 14 ms and was still falling. Mean abs(dT) fell from 353 to 110 K. The run was stopped at 0.2144 s, so its
cores could go to the real fix: A1 with fvDOM radiation (`/opt/ofb/runs/A1r_R2rad`, `openfoam/quemadorUnico/enable_radiation.sh`).
The imposed wall temperatures are a check only: they would be wrong during ignition and for other flames.
