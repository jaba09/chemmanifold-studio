# Step 3 gate vs R2rad_DI_0.1875 (factor 2.0 on p1/p50/p99, psi within 0.05)

| run | check | ok | p1 | p50 | p99 |
| --- | --- | --- | --- | --- | --- |
| A3r_wd2_lefoam_rad | chi@z_st | True | x1.62 | x0.97 | x1.23 |
| A3r_wd2_lefoam_rad | age@z_st | n/a | | | |
| A3r_wd2_lefoam_rad | tau_cell@overall | True | x1.00 | x1.02 | x1.00 |
| A3r_wd2_lefoam_rad | strain@z_st | True | x0.90 | x0.90 | x0.85 |
| A3r_wd2_lefoam_rad | psi@overall | True | +0.038 | +0.020 | -0.001 |
| A3r_wd2_lefoam_rad | **passed** | **True** | T_max 2230 K | | |
