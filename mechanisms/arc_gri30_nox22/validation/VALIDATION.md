# ARC_GRI30_NOx22 validation against GRI-Mech 3.0 (15 Nov 2026)

Rebuilt C core (`../arc_gri30_nox22.c`); sim1 later found Javier's original `arc_gri30_nox22.hpp` and showed the
two agree to 2e-8 in production rates on 400 hot burner cells.

## Rates
Skeletal-43 rates of the C core vs Cantera `gri30_skel43.yaml`: max relative error 4e-9 (30 random states, 300-2400 K).

## 0D ignition, constant pressure, CH4/air (O2 0.21 / N2 0.79 by mole), `ignition.py`
Ignition delay = time of max dT/dt; 1000 K cases do not ignite within 0.5 s and are left out.

| T0 [K] | p [atm] | phi | tau GRI [s] | skel43 err | ARC err |
|---|---|---|---|---|---|
| 1200 | 1 | 0.5 / 1 / 2 | 3.15e-2 / 4.55e-2 / 6.69e-2 | +0.35 / +0.20 / +0.13 % | +0.28 / +0.15 / +0.10 % |
| 1400 | 1 | 0.5 / 1 / 2 | 2.51e-3 / 3.44e-3 / 4.93e-3 | +0.76 / +0.63 / +0.81 % | +0.45 / +0.39 / +0.64 % |
| 1600 | 1 | 0.5 / 1 / 2 | 4.01e-4 / 4.68e-4 / 5.96e-4 | +1.04 / +1.25 / +2.12 % | +0.32 / +0.51 / +1.43 % |
| 1100 | 5 | 0.5 / 1 / 2 | 2.80e-2 / 3.84e-2 / 5.66e-2 | +0.26 / +0.17 / +0.13 % | +0.24 / +0.15 / +0.12 % |
| 1400 | 5 | 0.5 / 1 / 2 | 6.89e-4 / 9.38e-4 / 1.35e-3 | +0.90 / +0.61 / +0.79 % | +0.64 / +0.40 / +0.64 % |

Max ARC error 1.43 %. Burnt-gas temperature 3 ms after ignition: within 0.6 K for phi <= 1; rich phi 2 is
7-14 K low and NO 11-16 % high even with the element projection every 2e-5 s (lean/stoichiometric NO within 1-3 %).

## Laminar flame speed, 1 atm, 300 K (`flame1d.py`)
Cantera cannot run quasi-steady species, so ARC and skel43 run in our own 1D solver with the burner's constant-Lewis
transport (identical for both); skel43 vs GRI comes from Cantera (mixture-averaged).

| phi | Cantera GRI [cm/s] | Cantera skel43 | own solver skel43 | own solver ARC | ARC vs skel43 | ARC vs GRI (combined) |
|---|---|---|---|---|---|---|
| 0.7 | 19.51 | 19.36 (-0.73 %) | 19.06 | 19.09 | +0.12 % | about -0.6 % |
| 1.0 | 38.05 | 37.87 (-0.47 %) | 36.91 | 37.01 | +0.29 % | about -0.2 % |
| 1.3 | 23.69 | 23.50 (-0.82 %) | 23.03 | 22.91 (+-0.4 %) | -0.50 % | about -1.3 % |

The constant-Lewis transport itself gives 2-3 % lower speeds than Cantera's mixture-averaged model, for both mechanisms.
