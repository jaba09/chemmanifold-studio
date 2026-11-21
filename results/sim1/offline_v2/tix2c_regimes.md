# Regime labels of the tix2c training data (P_tix2c parent, data/openfoam_tix2c/04_prep/dataset.npz)

752,486 pairs (662,188 train / 90,298 validation). All physics-only (Cantera); no CFD/DI state.

| regime | label | pairs | share | train | val | T_in range [K] |
|---|---|---|---|---|---|---|
| 0 | reactor_0D | 134,670 | 17.9 % | 118,561 | 16,109 | 300-2145 |
| 1 | PaSR | 15,600 | 2.1 % | 13,758 | 1,842 | 300-2012 |
| 2 | flamelet_states | 11,720 | 1.6 % | 10,254 | 1,466 | 300-2208 |
| 3 | wall_cooled_0D | 8,108 | 1.1 % | 7,093 | 1,015 | 300-1877 |
| 4 | recirculation | 7,200 | 1.0 % | 6,330 | 870 | 300-2127 |
| 5 | unsteady_flamelets | 14,326 | 1.9 % | 12,578 | 1,748 | 350-2182 |
| 6 | equilibrium_tail_0D | 3,600 | 0.5 % | 3,195 | 405 | 1227-2149 |
| 7 | vitiated_ignition | 237,340 | 31.5 % | 208,870 | 28,470 | 300-2231 |
| 8 | burnt_relaxation | 31,780 | 4.2 % | 27,958 | 3,822 | 457-2199 |
| 15 | dilution_cooling | 57,766 | 7.7 % | 50,853 | 6,913 | 450-2173 |
| 16 | dynamic_PaSR | 3,714 | 0.5 % | 3,278 | 436 | 450-2184 |
| 17 | induction_layer | 162,600 | 21.6 % | 143,081 | 19,519 | 450-2210 |
| 18 | hot_wall | 16,428 | 2.2 % | 14,456 | 1,972 | 451-1312 |
| 19 | relaxation_flame_dt | 11,778 | 1.6 % | 10,362 | 1,416 | 602-1675 |
| 21 | committee | 35,856 | 4.8 % | 31,561 | 4,295 | 800-2216 |
