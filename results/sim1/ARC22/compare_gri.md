# ARC_GRI30_NOx22 OpenFOAM DI vs Fluent DI (GRI-Mech 3.0 benchmark) and GA18

| metric | Fluent GRI | Fluent GA18 | OF GA18 A1r mean | OF ARC22 mean |
|---|---|---|---|---|
| Tmax [K] | 2077 | 2088 | 2121 | 2104 |
| x(Tmax) [mm] | 43.35 | 42.85 | 43.6 | 43.85 |
| r(Tmax) [mm] | 9.367 | 8.867 | 9.866 | 9.866 |
| V(T>1500) [cm3] | 18.08 | 18.25 | 19.94 | 18.79 |
| V(T>1800) [cm3] | 7.993 | 8.574 | 9.597 | 8.59 |
| V(T>2000) [cm3] | 2.659 | 2.986 | 3.837 | 3.084 |
| flame base x(T>1500) [mm] | 1.146 | 1.146 | 1.395 | 1.395 |
| axis Tmax [K] | 1364 | 1437 | 1472 | 1398 |
| x(OH max) [mm] | 16.87 | 15.12 | 15.87 | 17.62 |
| OH max | 0.003474 | 0.003277 | 0.003335 | 0.003456 |
| CO max | 0.04902 | 0.05319 | 0.05987 | 0.05099 |
| CO2 max | 0.1652 | 0.1613 | 0.1569 | 0.159 |
| H2 max | 0.002787 | 0.0021 | 0.002428 | 0.003031 |
| CH4 max | 1 | 1 | 1 | 1 |
| NO max | 0.000247 | nan | nan | 0.000248 |
| NO2 max | 5.475e-05 | nan | nan | 4.016e-05 |
| N2O max | 5.953e-06 | nan | nan | 6.135e-06 |
| HCN max | 0.0001139 | nan | nan | 0.0001462 |
| C2H2 max | 0.01328 | nan | nan | 0.01546 |
| CH3OH max | 0.000109 | nan | nan | 8.726e-05 |

Cell-by-cell differences (volume-weighted; rel L1 = mean |a-b| / mean max(a,b) over cells above 600 K):

| | OF ARC22 mean vs Fluent GRI | OF GA18 A1r mean vs Fluent GA18 | Fluent GRI vs Fluent GA18 | OF ARC22 mean vs OF GA18 A1r mean | OF GA18 A1r mean vs Fluent GRI |
|---|---|---|---|---|---|
| mean hot |dT| [K] (vol-w) | 38.6 | 48.8 | 26.6 | 33.4 | 55.4 |
| mean |dT| T>600 [K] (vol-w) | 34.8 | 45.1 | 17.1 | 17.2 | 41.2 |
| max |dT| [K] | 226 | 243 | 75.5 | 86.9 | 248 |
| OH rel L1 (T>600) | 0.195 | 0.217 | 0.125 | 0.153 | 0.253 |
| CO rel L1 (T>600) | 0.0758 | 0.117 | 0.0609 | 0.117 | 0.153 |
| CO2 rel L1 (T>600) | 0.0347 | 0.0326 | 0.0194 | 0.0233 | 0.0386 |
| H2 rel L1 (T>600) | 0.114 | 0.168 | 0.242 | 0.195 | 0.151 |
| CH4 rel L1 (T>600) | 0.112 | 0.0921 | 0.138 | 0.149 | 0.148 |
| NO rel L1 (T>600) | 0.367 | nan | nan | nan | nan |
| NO2 rel L1 (T>600) | 0.625 | nan | nan | nan | nan |
| N2O rel L1 (T>600) | 0.529 | nan | nan | nan | nan |
| HCN rel L1 (T>600) | 0.205 | nan | nan | nan | nan |
| C2H2 rel L1 (T>600) | 0.148 | nan | nan | nan | nan |
| CH3OH rel L1 (T>600) | 0.215 | nan | nan | nan | nan |
