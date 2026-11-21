# Protocol v2 ranking (pure mode, vs A1r/A2r GA18 DI with radiation)

S = max(F, I, C); each term is 1 at its target (flame abs dT 5 K, ignition 0.3 ms, CO/OH within x1.4).

| Model | S | F | I | C | flame abs dT [K] | d t_ign [ms] | drift [K/10 ms] | V(T>1500) xDI | OOD (flame) | s/step | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| isann_D | **1.04** | 1.04 | 0.67 | 0.15 | 5.2 | -0.20 | +0.43 | 1.01 | 0.0 % | 1.94 | yes |
