"""Smoke test of the coverage tool: synthetic states (mixing + equilibrium) with injected OOD and failing checks."""
import sys, os, subprocess, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import cantera as ct
from chemmanifold.coverage import plateau

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
mech = os.path.join(root, "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml")
g = ct.Solution(mech); rng = np.random.default_rng(1)
g.TPX = 300, ct.one_atm, "CH4:1"; Yf = g.Y.copy(); hf = g.enthalpy_mass
g.TPX = 300, ct.one_atm, "O2:0.21,N2:0.79"; Yo = g.Y.copy(); ho = g.enthalpy_mass
T, Y = [], []
for z in rng.uniform(0.0, 0.2, 400):
    g.HPY = z * hf + (1 - z) * ho, ct.one_atm, z * Yf + (1 - z) * Yo
    g.equilibrate("HP"); T.append(g.T); Y.append(g.Y.copy())
T, Y = np.array(T), np.array(Y)
ood = np.zeros(len(T), bool); ood[:40] = True
d = "/tmp/claude-0/smoke_cov"; os.makedirs(d, exist_ok=True)
np.savez(f"{d}/cells.npz", T=T, Y=Y, species=np.array(g.species_names), mass=np.ones(len(T)), ood=ood)
np.savez(f"{d}/shadow.npz", T=np.repeat(T, 8), Y=np.repeat(Y, 8, 0), species=np.array(g.species_names),
         **{"pass": np.repeat(np.arange(len(T)) % 7 != 0, 8)})
out = subprocess.run([sys.executable, "-I", os.path.join(root, "scripts", "25_coverage.py"), "--mech", mech,
                      "--cells", f"{d}/cells.npz", "--shadow", f"{d}/shadow.npz", "--out", f"{d}/out"],
                     capture_output=True, text=True)
print(out.stdout, out.stderr[-2000:])
s = json.load(open(f"{d}/out/coverage.json")); print(s)
assert 0.0 < s["C"] < s["C_data"] <= 1.0
assert plateau([0.5, 0.6, 0.605, 0.608]) and not plateau([0.5, 0.6, 0.65])
print("SMOKE OK")
