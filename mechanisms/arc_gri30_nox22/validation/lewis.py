#!/usr/bin/env python3
"""Lewis numbers of the 22 ARC species for constantLewis, by the method used for
the GA18 burner case: Le_k = kappa/(rho cp D_k,mix) in a Cantera counterflow CH4/air
flame (mixture-averaged, 1 atm, strain ~35 1/s), weighted by |dY_k/dx| where T > 600 K.
Mechanism: GRI-Mech 3.0 (transport of the ODE species)."""
import sys
import numpy as np, cantera as ct
ODE = "H2 H O O2 OH H2O HO2 H2O2 CH4 CH3 CO CO2 CH2O CH3OH C2H2 C2H4 C2H6 N2 NO NO2 N2O HCN".split()
if "--all" in sys.argv:  # every GRI-Mech 3.0 species (for the OpenFOAM GRI case)
    ODE = [s for s in ct.Solution("gri30.yaml").species_names if s != "AR"]
g = ct.Solution("gri30.yaml"); g.transport_model = "mixture-averaged"
f = ct.CounterflowDiffusionFlame(g, width=0.03)
f.P = ct.one_atm
f.fuel_inlet.X = "CH4:1"; f.fuel_inlet.T = 300
f.oxidizer_inlet.X = "O2:0.21, N2:0.79"; f.oxidizer_inlet.T = 300
# strain a = (|u_f| + |u_o|)/L ~ 35 1/s with momentum balance
rho_f = ct.Solution("gri30.yaml"); rho_f.TPX = 300, ct.one_atm, "CH4:1"
rho_o = ct.Solution("gri30.yaml"); rho_o.TPX = 300, ct.one_atm, "O2:0.21, N2:0.79"
uo = 35 * 0.03 / 2 / (1 + (rho_o.density / rho_f.density) ** 0.5) * 2 / 2
uf = uo * (rho_o.density / rho_f.density) ** 0.5
f.fuel_inlet.mdot = rho_f.density * uf; f.oxidizer_inlet.mdot = rho_o.density * uo
f.set_refine_criteria(ratio=3, slope=0.1, curve=0.2)
f.solve(loglevel=0, auto=True)
x, T = f.grid, f.T
print("Tmax %.1f K, strain %.1f 1/s" % (T.max(), f.strain_rate("max")))
Le = {}
for k in ODE:
    i = g.species_index(k); lek = []; w = []
    for j in range(len(x)):
        g.TPY = T[j], f.P, f.Y[:, j]
        D = g.mix_diff_coeffs[i]
        lek.append(g.thermal_conductivity / (g.density * g.cp_mass * D))
    dY = np.abs(np.gradient(f.Y[i], x)); m = T > 600
    Le[k] = np.sum(np.array(lek)[m] * dY[m]) / max(np.sum(dY[m]), 1e-300) if np.sum(dY[m]) > 0 else np.mean(np.array(lek)[m])
    print("    %-7s %.3f;" % (k, Le[k]))
