# ARC22 vs GRI-Mech 3.0, both OpenFOAM DI (server/sim1/compare_of_fields.py)

## Mean 0.125-0.15 s

ARC22: 0.1250-0.1500 s, 11 snapshots   GRI53: 0.1250-0.1500 s, 11 snapshots
| Metric | ARC22 | GRI53 |
|---|---|---|
| V(T > 1500 K) [cm3] | 19.48 | 19.46 |
| Tmax [K] | 2108.1 | 2106.9 |
| x(OH max) [mm] | 19.4 | 19.1 |
| OH max | 0.00345 | 0.00347 |
| CO max | 0.0515 | 0.0547 |
| H max | 7.44e-05 | 7.59e-05 |
| NO max | 0.000233 | 0.00024 |
| NO2 max | 3.29e-05 | 2.82e-05 |
| N2O max | 2.6e-06 | 1.12e-06 |
| HCN max | 0.000129 | 0.000106 |
| C2H2 max | 0.0151 | 0.0139 |
| CH3OH max | 8.46e-05 | 8.54e-05 |

hot cells (10054): mean abs(dT) 2.9 K, volume-weighted 3.2 K, bias +1.2 K, max abs(dT) 17 K

| Species | L1 rel, hot cells | total ARC22/GRI53 |
|---|---|---|
| OH | 1.5 % | 0.994 |
| CO | 3.4 % | 0.971 |
| CO2 | 0.4 % | 1.001 |
| H | 3.6 % | 0.971 |
| H2 | 3.3 % | 0.970 |
| CH4 | 0.4 % | 1.002 |
| NO | 7.6 % | 1.039 |
| NO2 | 4.0 % | 0.981 |
| N2O | 34.2 % | 1.266 |
| HCN | 20.6 % | 1.206 |
| C2H2 | 8.9 % | 1.088 |
| CH3OH | 3.2 % | 0.971 |

## Instantaneous 0.15 s

ARC22: 0.1500-0.1500 s, 1 snapshots   GRI53: 0.1500-0.1500 s, 1 snapshots
| Metric | ARC22 | GRI53 |
|---|---|---|
| V(T > 1500 K) [cm3] | 19.36 | 19.30 |
| Tmax [K] | 2106.3 | 2104.5 |
| x(OH max) [mm] | 17.6 | 17.6 |
| OH max | 0.00345 | 0.00347 |
| CO max | 0.0511 | 0.0543 |
| H max | 7.44e-05 | 7.58e-05 |
| NO max | 0.000245 | 0.000255 |
| NO2 max | 3.72e-05 | 3.14e-05 |
| N2O max | 4.4e-06 | 2.21e-06 |
| HCN max | 0.000143 | 0.000116 |
| C2H2 max | 0.0154 | 0.0142 |
| CH3OH max | 8.59e-05 | 8.66e-05 |

hot cells (10059): mean abs(dT) 3.4 K, volume-weighted 4.1 K, bias +1.6 K, max abs(dT) 24 K

| Species | L1 rel, hot cells | total ARC22/GRI53 |
|---|---|---|
| OH | 1.7 % | 0.995 |
| CO | 3.7 % | 0.968 |
| CO2 | 0.5 % | 1.001 |
| H | 3.7 % | 0.971 |
| H2 | 3.4 % | 0.969 |
| CH4 | 0.7 % | 1.002 |
| NO | 7.6 % | 1.026 |
| NO2 | 4.6 % | 0.974 |
| N2O | 41.5 % | 1.310 |
| HCN | 20.8 % | 1.208 |
| C2H2 | 9.1 % | 1.091 |
| CH3OH | 3.5 % | 0.970 |
