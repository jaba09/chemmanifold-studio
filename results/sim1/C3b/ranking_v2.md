# Protocol v2 ranking (pure mode, vs A1r/A2r GA18 DI with radiation)

S = max(F, I, C); each term is 1 at its target (flame abs dT 5 K, ignition 0.3 ms, CO/OH within x1.4).

| Model | S | F | I | C | flame abs dT [K] | d t_ign [ms] | drift [K/10 ms] | V(T>1500) xDI | OOD (flame) | s/step | valid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C3b_iter1 | **6.86** | 6.86 | 0.00 | 0.21 | 34.3 | +0.00 | +25.55 | 0.98 | 5.3 % | 3.41 | yes |
| C3b_iter2 | **16.80** | 16.80 | 1.33 | 0.16 | 84.0 | +0.40 | +65.09 | 1.00 | 5.8 % | 3.33 | yes |
