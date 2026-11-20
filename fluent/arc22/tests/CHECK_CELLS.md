# A priori check on the Fluent GRI-Mech 3.0 burner solution

300 random cells with T > 1000 K (of 9608); after one chemistry dt, ARC22 UDF step vs Cantera GRI-Mech 3.0 from the full 53-species state.

| dt [s] | mean abs dT err [K] | max [K] | mean abs dT [K] (GRI) | OH rel err | CO rel err | NO rel err | UDF ms/cell |
|---|---|---|---|---|---|---|---|
| 1e-05 | 0.00 | 0.1 | 0.5 | 0.001 | 0.000 | 0.001 | 0.56 |
| 0.0001 | 0.02 | 0.3 | 3.2 | 0.006 | 0.000 | 0.004 | 0.93 |
| 0.001 | 0.11 | 1.5 | 13.8 | 0.012 | 0.002 | 0.014 | 1.66 |
