# Per-regime coverage of the A1r DI hot cells by the tix2c training data

44,013 hot cells (T >= 600 K) of 3 A1r snapshots (A1r_t0100.00ms, A1r_t0125.00ms, A1r_t0150.00ms); nearest of 662,188 training pairs in the model's OOD coordinates (isann_lib.features at dt 2e-05 s); distance in landmark thresholds (2.268; > 1 = far from the data in the UDF). DI states are only measured.

| regime | label | nearest for cells | (volume-weighted) | median distance | p95 distance | cells > 1 | training share |
|---|---|---|---|---|---|---|---|
| 15 | dilution_cooling | 19.5 % | 28.7 % | 0.241 | 0.369 | 0 | 7.7 % |
| 7 | vitiated_ignition | 18.4 % | 8.7 % | 0.132 | 0.329 | 0 | 31.5 % |
| 2 | flamelet_states | 15.9 % | 16.8 % | 0.286 | 0.397 | 0 | 1.5 % |
| 17 | induction_layer | 12.2 % | 4.4 % | 0.197 | 0.345 | 0 | 21.6 % |
| 8 | burnt_relaxation | 9.4 % | 7.2 % | 0.229 | 0.418 | 0 | 4.2 % |
| 21 | committee | 7.7 % | 13.7 % | 0.210 | 0.356 | 0 | 4.8 % |
| 5 | unsteady_flamelets | 5.6 % | 2.3 % | 0.247 | 0.526 | 0 | 1.9 % |
| 0 | reactor_0D | 5.4 % | 3.7 % | 0.279 | 0.410 | 0 | 17.9 % |
| 19 | relaxation_flame_dt | 2.0 % | 5.2 % | 0.274 | 0.416 | 0 | 1.6 % |
| 16 | dynamic_PaSR | 2.0 % | 0.6 % | 0.369 | 0.432 | 0 | 0.5 % |
| 4 | recirculation | 1.8 % | 8.6 % | 0.269 | 0.404 | 0 | 1.0 % |
| 6 | equilibrium_tail_0D | 0.2 % | 0.1 % | 0.151 | 0.163 | 0 | 0.5 % |
| 3 | wall_cooled_0D | 0.0 % | 0.0 % | 0.448 | 0.449 | 0 | 1.1 % |

All hot cells: median distance 0.234, p95 0.397, 0 cells (0.00 %) beyond one landmark threshold.

## By temperature band (share of the band's cells whose nearest pair is in each of the top regimes)

| T band [K] | cells | median d | dilution_cooling | vitiated_ignition | flamelet_states | induction_layer | burnt_relaxation | committee |
|---|---|---|---|---|---|---|---|---|
| 600-1000 | 13,414 | 0.284 | 28.5 % | 0.0 % | 11.2 % | 11.8 % | 10.9 % | 14.2 % |
| 1000-1400 | 11,069 | 0.210 | 31.0 % | 12.6 % | 10.0 % | 12.1 % | 12.3 % | 11.0 % |
| 1400-1800 | 11,163 | 0.134 | 11.9 % | 42.4 % | 10.7 % | 11.8 % | 10.3 % | 0.9 % |
| 1800-2400 | 8,367 | 0.242 | 0.2 % | 23.8 % | 38.0 % | 13.5 % | 2.0 % | 1.7 % |
