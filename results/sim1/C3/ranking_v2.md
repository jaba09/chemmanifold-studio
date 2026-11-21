# Protocol v2 ranking (pure mode, vs A1r/A2r GA18 DI with radiation)

S = max(F, I, C); each term is 1 at its target (flame abs dT 5 K, ignition 0.3 ms, CO/OH within x1.4).

| Model | S | F | I | C | flame abs dT [K] | d t_ign [ms] | drift [K/10 ms] | V(T>1500) xDI | OOD (flame) | s/step | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C3_iter2 | **2.15** | 2.15 | 0.67 | 0.15 | 10.7 | +0.20 | +1.78 | 0.99 | 5.6 % | 3.65 | yes |
| C3_iter1 | **2.22** | 2.22 | 1.33 | 0.14 | 11.1 | +0.40 | +1.34 | 0.99 | 4.2 % | 3.85 | yes |
