# Step 3 gate vs fluent_di_corrected (factor 2.0 on p1/p50/p99, psi within 0.05)

| run | check | ok | p1 | p50 | p99 |
| --- | --- | --- | --- | --- | --- |
| R2rad_DI_0.1875 | chi@z_st | n/a | | | |
| R2rad_DI_0.1875 | age@z_st | n/a | | | |
| R2rad_DI_0.1875 | tau_cell@overall | n/a | | | |
| R2rad_DI_0.1875 | strain@z_st | n/a | | | |
| R2rad_DI_0.1875 | psi@overall | False | -0.062 | -0.053 | -0.007 |
| R2rad_DI_0.1875 | **passed** | **False** | T_max 2121 K | | |
| A3r_wd2_lefoam_rad | chi@z_st | n/a | | | |
| A3r_wd2_lefoam_rad | age@z_st | n/a | | | |
| A3r_wd2_lefoam_rad | tau_cell@overall | n/a | | | |
| A3r_wd2_lefoam_rad | strain@z_st | n/a | | | |
| A3r_wd2_lefoam_rad | psi@overall | True | -0.025 | -0.033 | -0.008 |
| A3r_wd2_lefoam_rad | **passed** | **True** | T_max 2230 K | | |
